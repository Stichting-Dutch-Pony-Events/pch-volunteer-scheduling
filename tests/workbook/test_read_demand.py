from datetime import time

import openpyxl
import pytest
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.model import Settings
from scheduler.workbook import WorkbookError, read_demand


# The blocks depend on the days, so the tests pass them explicitly instead of relying on
# the defaults in model.py. Friday 14:00 = block 32, Saturday 01:00 (the night) = block 172.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))

HEADER = ("Day", "Time", "Tickets", "Infobooth")


def _demand_sheet(rows: list[tuple], header: tuple[str, ...] = HEADER) -> Worksheet:
    """A new in-memory sheet called Demand: the header in row 1, then one row per block."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Demand"           # so the error messages can name the tab
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    return sheet


def test_each_open_block_gets_the_number_of_people_needed():
    """Every number on the tab becomes the demand of that post in that block."""
    # Arrange
    rows = [("Friday", "14:00", 1, 2),
            ("Friday", "14:15", 1, None)]   # None = an empty cell: Infobooth closed
    sheet = _demand_sheet(rows)

    # Act
    demand = read_demand(sheet, RULES)

    # Assert
    assert demand == {("Tickets", 32): 1, ("Infobooth", 32): 2, ("Tickets", 33): 1}


def test_zero_means_closed_and_is_left_out():
    """A 0 counts the same as an empty cell: the post is closed in that block."""
    # Arrange
    rows = [("Friday", "14:00", 1, 0)]
    sheet = _demand_sheet(rows)

    # Act
    demand = read_demand(sheet, RULES)

    # Assert
    assert demand == {("Tickets", 32): 1}


def test_night_time_belongs_to_the_previous_convention_day():
    """Saturday 01:00 is the Saturday night (block 172), not Saturday morning."""
    # Arrange
    rows = [("Saturday", "01:00", 1, None)]
    sheet = _demand_sheet(rows)

    # Act
    demand = read_demand(sheet, RULES)

    # Assert
    assert demand == {("Tickets", 172): 1}


def test_time_typed_as_an_excel_time_is_accepted():
    """A Time typed into Excel as a time value counts the same as the text "14:00"."""
    # Arrange
    rows = [("Friday", time(14, 0), 1, None)]
    sheet = _demand_sheet(rows)

    # Act
    demand = read_demand(sheet, RULES)

    # Assert
    assert demand == {("Tickets", 32): 1}


def test_a_number_typed_as_text_is_accepted():
    """A number stored as text, e.g. after copy and paste, counts the same as a number."""
    # Arrange
    rows = [("Friday", "14:00", "2", None)]
    sheet = _demand_sheet(rows)

    # Act
    demand = read_demand(sheet, RULES)

    # Assert
    assert demand == {("Tickets", 32): 2}


def test_notes_column_is_not_a_post():
    """The Notes column is not read as a post, whatever is in it."""
    # Arrange
    header = HEADER + ("Notes",)   # a tuple with one item needs the comma
    rows = [("Friday", "14:00", 1, None, "Opening")]
    sheet = _demand_sheet(rows, header=header)

    # Act
    demand = read_demand(sheet, RULES)

    # Assert
    assert demand == {("Tickets", 32): 1}


def test_empty_rows_are_skipped():
    """A completely empty row between the blocks is no problem."""
    # Arrange
    rows = [("Friday", "14:00", 1, None),
            (),                              # an empty row
            ("Friday", "14:15", 1, None)]
    sheet = _demand_sheet(rows)

    # Act
    demand = read_demand(sheet, RULES)

    # Assert
    assert demand == {("Tickets", 32): 1, ("Tickets", 33): 1}


def test_row_with_a_day_and_time_but_no_number_means_everything_is_closed():
    """A row with a day and time but no demand (e.g. before opening) is fine: all closed."""
    # Arrange
    rows = [("Friday", "13:45", None, None),    # before opening
            ("Friday", "14:00", 1, None),
            ("Friday", "14:15", 0, 0)]          # after closing
    sheet = _demand_sheet(rows)

    # Act
    demand = read_demand(sheet, RULES)

    # Assert
    assert demand == {("Tickets", 32): 1}


@pytest.mark.parametrize(
    "day, time_text",
    [("Satruday", "13:45"),
     ("Friday", "13:50"),
     ("Saturday", None)],
    ids=["unknown day", "not on a 15-minute step", "day without a time"])
def test_row_without_numbers_still_needs_a_valid_day_and_time(day, time_text):
    """A row without demand is checked too: its Day and Time must be valid."""
    # Arrange
    rows = [(day, time_text, None, None)]
    sheet = _demand_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Demand.*row 2"):   # row 1 is the header
        read_demand(sheet, RULES)


def test_row_without_numbers_on_a_day_and_time_already_used_raises_workbook_error():
    """A row without demand may not repeat a Day and Time that is already on the tab."""
    # Arrange
    rows = [("Friday", "14:00", 1, None),
            ("Friday", "14:00", None, None)]    # the same block again, now without demand
    sheet = _demand_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Friday.*14:00"):
        read_demand(sheet, RULES)


def test_missing_time_column_raises_workbook_error():
    """A Demand tab without a Time column is an error."""
    # Arrange
    header = ("Day", "Hour", "Tickets", "Infobooth")   # "Hour" instead of "Time"
    rows = [("Friday", "14:00", 1, None)]
    sheet = _demand_sheet(rows, header=header)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Demand.*Time"):
        read_demand(sheet, RULES)


@pytest.mark.parametrize(
    "day, time_text",
    [("Satruday", "10:00"),
     ("Saturday", "10:10"),
     ("Saturday", "25:00")],
    ids=["unknown day", "not on a 15-minute step", "hour too high"])
def test_invalid_day_or_time_raises_workbook_error_naming_the_row(day, time_text):
    """A row with demand and an impossible Day or Time is an error naming the row."""
    # Arrange
    rows = [(day, time_text, 1, None)]
    sheet = _demand_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Demand.*row 2"):   # row 1 is the header
        read_demand(sheet, RULES)


def test_the_same_day_and_time_twice_raises_workbook_error():
    """Two rows for the same block are an error: it is unclear which numbers count."""
    # Arrange
    rows = [("Saturday", "10:00", 2, 1),
            ("Saturday", "10:00", 1, 1)]
    sheet = _demand_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Saturday.*10:00"):
        read_demand(sheet, RULES)


@pytest.mark.parametrize(
    "needed",
    [-1, "x", 1.5],
    ids=["negative", "text", "decimal"])
def test_invalid_number_raises_workbook_error_naming_row_and_post(needed):
    """A number of people that is not a whole number of at least 0 is an error."""
    # Arrange
    rows = [("Saturday", "10:00", needed, None)]   # the invalid number is at Tickets
    sheet = _demand_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="row 2.*Tickets"):
        read_demand(sheet, RULES)


@pytest.mark.parametrize(
    "day, time_text",
    [(None, "14:00"),
     ("Friday", None),
     (None, None)],
    ids=["no day", "no time", "no day and no time"])
def test_row_with_numbers_but_no_day_or_time_raises_workbook_error(day, time_text):
    """A row with demand but without a Day, a Time or both is an error naming the row."""
    # Arrange
    rows = [(day, time_text, 1, 1)]
    sheet = _demand_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Demand.*row 2"):   # row 1 is the header
        read_demand(sheet, RULES)

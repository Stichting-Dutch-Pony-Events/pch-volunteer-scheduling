import openpyxl
import pytest
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.model import Settings
from scheduler.errors import WorkbookError
from scheduler.reading.volunteers import read_volunteers


# The blocks depend on the days, so the tests pass them explicitly instead of relying on
# the defaults in model.py. Friday = blocks 0-95, Saturday = 96-191, Sunday = 192-287.
# The default hour limits are 6 hours per day and 12 in total (360 and 720 minutes).
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"),
                 default_max_minutes_per_day=360, default_max_minutes_total=720)

# Like the real Volunteers tab: Team and Notes are there but not read. A row with only the
# first five values leaves the hour limit cells empty (= the defaults from the settings).
HEADER = ("Nickname", "Team", "Friday", "Saturday", "Sunday", "Max hours per day",
          "Max hours total", "Notes")


def _volunteers_sheet(rows: list[tuple], header: tuple[str, ...] = HEADER) -> Worksheet:
    """A new in-memory sheet called Volunteers: the header in row 1, then one row each."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Volunteers"       # so the error messages can name the tab
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    return sheet


# --- Availability ---

def test_each_volunteer_gets_their_available_blocks():
    """Every volunteer gets the blocks of the days they are available."""
    # Arrange
    volunteer_rows = []
    volunteer_rows.append(("Mock Mane",         None, "yes", "no", "no"))
    volunteer_rows.append(("Testy Hooves",      None, "no", "08:00-18:00", "no"))
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    volunteers = read_volunteers(sheet, RULES)

    # Assert
    assert volunteers["Mock Mane"].available_blocks == set(range(0, 96))
    assert volunteers["Testy Hooves"].available_blocks == set(range(104, 144))


def test_availability_of_several_days_is_combined():
    """Available on Saturday and Sunday morning gives the blocks of both together."""
    # Arrange
    volunteer_rows = [("Mock Mane", None, "no", "yes", "08:00-14:00")]
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    volunteers = read_volunteers(sheet, RULES)

    # Assert
    assert volunteers["Mock Mane"].available_blocks == set(range(96, 192)) | set(range(200, 224))


def test_the_days_come_from_the_settings():
    """The day columns follow the Days setting: with Saturday as first day, it starts at block 0."""
    # Arrange
    # No Friday column, and the day columns in another order than in the settings.
    custom_header = ("Nickname", "Team", "Sunday", "Saturday", "Notes", "Max hours per day",
                     "Max hours total")
    volunteer_rows = [("Mock Mane", None, "no", "yes", "Columns in another order")]
    sheet = _volunteers_sheet(rows=volunteer_rows, header=custom_header)

    custom_rules = Settings(min_stretch_minutes=60, max_stretch_minutes=180,
                            min_break_minutes=30, days=("Saturday", "Sunday"))

    # Act
    volunteers = read_volunteers(sheet=sheet, settings=custom_rules)

    # Assert
    assert volunteers["Mock Mane"].available_blocks == set(range(0, 96))  # Saturday: 0-95


def test_empty_rows_are_skipped():
    """A completely empty row between the volunteers is no problem."""
    # Arrange
    volunteer_rows = []
    volunteer_rows.append(("Mock Mane",         None, "yes", "no", "no"))
    volunteer_rows.append(tuple())
    volunteer_rows.append(("Testy Hooves",      None, "no", "08:00-18:00", "no"))
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    volunteers = read_volunteers(sheet, RULES)

    # Assert
    assert list(volunteers) == ["Mock Mane", "Testy Hooves"]


def test_missing_day_column_raises_workbook_error():
    """A day from the settings without its own column is an error naming that day."""
    # Arrange
    custom_header = ("Nickname", "Team", "Friday", "Saturday", "Notes", "Max hours per day",
                     "Max hours total")
    volunteer_rows = [("Mock Mane", None, "no", "yes", "Is the Sunday missing?")]
    sheet = _volunteers_sheet(volunteer_rows, header=custom_header)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Volunteers.*Sunday"):
        read_volunteers(sheet, RULES)


def test_the_same_nickname_twice_raises_workbook_error():
    """Two rows with the same nickname are an error naming the nickname."""
    # Arrange
    volunteer_rows = []
    volunteer_rows.append(("Mock Mane",         None, "yes", "no", "no"))
    volunteer_rows.append(("Mock Mane",         None, "no", "08:00-18:00", "no"))
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Mock Mane"):
        read_volunteers(sheet, RULES)


def test_invalid_availability_raises_workbook_error_naming_volunteer_and_day():
    """An availability like "yse" is an error naming the volunteer, the day and the value."""
    # Arrange
    volunteer_rows = [("Mock Mane", None, "yes", "yse", "no")]   # a typo on Saturday
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Mock Mane.*Saturday.*yse"):
        read_volunteers(sheet, RULES)


def test_volunteer_who_is_never_available_raises_workbook_error():
    """A volunteer who is not available on any day is an error naming the volunteer."""
    # Arrange
    volunteer_rows = [("Mock Mane", None, "no", "no", None)]   # None = an empty cell
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Mock Mane"):
        read_volunteers(sheet, RULES)


@pytest.mark.parametrize(
    "row",
    [(None, None, "yes", "yes", "yes"),           # availability, no nickname
     (None, None, None, None, None, 8, None)],    # only an hour limit, no nickname
    ids=["availability", "hour limit"])
def test_row_with_values_but_no_nickname_raises_workbook_error(row):
    """A row with availability or an hour limit but no nickname is an error naming the row."""
    # Arrange
    sheet = _volunteers_sheet([row])   # the nickname was forgotten

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Volunteers.*row 2"):   # row 1 is the header
        read_volunteers(sheet, RULES)


# --- Hour limits ---

def test_written_hour_limits_are_read_in_minutes():
    """Max hours per day 4 and total 10 become 240 and 600 minutes on the Volunteer."""
    # Arrange
    volunteer_rows = [("Mock Mane", None, "yes", "yes", "yes", 4, 10)]
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    volunteers = read_volunteers(sheet, RULES)

    # Assert
    assert volunteers["Mock Mane"].max_minutes_per_day == 240
    assert volunteers["Mock Mane"].max_minutes_total == 600


def test_empty_hour_limit_cell_gets_the_default_from_the_settings():
    """An empty Max hours cell gets the default hour limit from the settings."""
    # Arrange
    volunteer_rows = [("Mock Mane", None, "yes", "yes", "yes", None, None)]   # both empty
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    volunteers = read_volunteers(sheet, RULES)

    # Assert
    assert volunteers["Mock Mane"].max_minutes_per_day == 360   # the defaults in RULES
    assert volunteers["Mock Mane"].max_minutes_total == 720


@pytest.mark.parametrize("value", ["none", "None", " NONE "])
def test_none_as_hour_limit_means_no_limit(value):
    """A Max hours cell with "none" means no limit (None); case and spaces are ignored."""
    # Arrange
    volunteer_rows = [("Mock Mane", None, "yes", "yes", "yes", value, value)]
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    volunteers = read_volunteers(sheet, RULES)

    # Assert
    assert volunteers["Mock Mane"].max_minutes_per_day is None
    assert volunteers["Mock Mane"].max_minutes_total is None


@pytest.mark.parametrize("value", [7.5, "eight", "8h"], ids=["decimal", "word", "unit"])
def test_hour_limit_that_is_not_a_whole_number_raises_workbook_error(value):
    """A Max hours cell that is not a whole number is an error naming volunteer and column."""
    # Arrange
    volunteer_rows = [("Mock Mane", None, "yes", "yes", "yes", value, None)]
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match=f"Mock Mane.*Max hours per day.*{value}"):
        read_volunteers(sheet, RULES)


@pytest.mark.parametrize("value", [0, -2], ids=["zero", "negative"])
def test_hour_limit_of_zero_or_less_raises_workbook_error(value):
    """A Max hours cell of 0 or less is an error naming the volunteer."""
    # Arrange
    volunteer_rows = [("Mock Mane", None, "yes", "yes", "yes", value, None)]
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Mock Mane.*Max hours per day.*at least 1"):
        read_volunteers(sheet, RULES)


def test_daily_limit_over_24_hours_raises_workbook_error():
    """More than 24 Max hours per day is an error naming the volunteer (probably a typo)."""
    # Arrange
    # Total "none", so the error can only come from the 24 hours, not from per day > total.
    volunteer_rows = [("Mock Mane", None, "yes", "yes", "yes", 25, "none")]
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Mock Mane.*Max hours per day.*24"):
        read_volunteers(sheet, RULES)


def test_total_limit_over_24_hours_per_day_raises_workbook_error():
    """A Max hours total above 24 times the number of days is an error naming the volunteer."""
    # Arrange
    # Three days in RULES, so at most 72 hours; per day empty (the default, never compared).
    volunteer_rows = [("Mock Mane", None, "yes", "yes", "yes", None, 73)]
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Mock Mane.*Max hours total.*72"):
        read_volunteers(sheet, RULES)


def test_daily_limit_above_the_total_limit_in_the_same_row_raises_workbook_error():
    """Per day higher than total, both written as a number, is an error naming the volunteer."""
    # Arrange
    volunteer_rows = [("Mock Mane", None, "yes", "yes", "yes", 10, 8)]
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Mock Mane.*Max hours per day.*Max hours total"):
        read_volunteers(sheet, RULES)


@pytest.mark.parametrize("column", ["Max hours per day", "Max hours total"])
def test_missing_hour_limit_column_raises_workbook_error(column):
    """A missing Max hours column is an error naming that column."""
    # Arrange
    header_without_column = []
    for name in HEADER:
        if name != column:
            header_without_column.append(name)
    volunteer_rows = [("Mock Mane", None, "yes", "yes", "yes", 4)]
    sheet = _volunteers_sheet(volunteer_rows, header=tuple(header_without_column))

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match=f"Volunteers.*{column}"):
        read_volunteers(sheet, RULES)

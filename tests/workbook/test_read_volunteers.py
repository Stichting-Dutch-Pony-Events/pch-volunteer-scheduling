import openpyxl
import pytest
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.model import Settings
from scheduler.workbook import WorkbookError, read_volunteers


# The blocks depend on the days, so the tests pass them explicitly instead of relying on
# the defaults in model.py. Friday = blocks 0-95, Saturday = 96-191, Sunday = 192-287.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))

# Like the real Volunteers tab: Team and Notes are there but not read.
HEADER = ("Nickname", "Team", "Friday", "Saturday", "Sunday", "Notes")


def _volunteers_sheet(rows: list[tuple], header: tuple[str, ...] = HEADER) -> Worksheet:
    """A new in-memory sheet called Volunteers: the header in row 1, then one row each."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Volunteers"       # so the error messages can name the tab
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    return sheet


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
    assert volunteers == {"Mock Mane": set(range(0, 96)),
                          "Testy Hooves": set(range(104, 144))}


def test_availability_of_several_days_is_combined():
    """Available on Saturday and Sunday morning gives the blocks of both together."""
    # Arrange
    volunteer_rows = [("Mock Mane", None, "no", "yes", "08:00-14:00")]
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    volunteers = read_volunteers(sheet, RULES)

    # Assert
    assert volunteers == {"Mock Mane": set(range(96, 192)) | set(range(200, 224))}


def test_the_days_come_from_the_settings():
    """The day columns follow the Days setting: with Saturday as first day, it starts at block 0."""
    # Arrange
    # No Friday column, and the day columns in another order than in the settings.
    custom_header = ("Nickname", "Team", "Sunday", "Saturday", "Notes")
    volunteer_rows = [("Mock Mane", None, "no", "yes", "Columns in another order")]
    sheet = _volunteers_sheet(rows=volunteer_rows, header=custom_header)

    custom_rules = Settings(min_stretch_minutes=60, max_stretch_minutes=180,
                            min_break_minutes=30, days=("Saturday", "Sunday"))

    # Act
    volunteers = read_volunteers(sheet=sheet, settings=custom_rules)

    # Assert
    assert volunteers == {"Mock Mane": set(range(0, 96))}  # Saturday is now blocks 0-95


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
    assert volunteers == {"Mock Mane": set(range(0, 96)),
                          "Testy Hooves": set(range(104, 144))}


def test_missing_day_column_raises_workbook_error():
    """A day from the settings without its own column is an error naming that day."""
    # Arrange
    custom_header = ("Nickname", "Team", "Friday", "Saturday", "Notes")
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


def test_row_with_availability_but_no_nickname_raises_workbook_error():
    """A row with availability but no nickname is an error naming the row."""
    # Arrange
    volunteer_rows = [(None, None, "yes", "yes", "yes")]   # the nickname was forgotten
    sheet = _volunteers_sheet(volunteer_rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Volunteers.*row 2"):   # row 1 is the header
        read_volunteers(sheet, RULES)

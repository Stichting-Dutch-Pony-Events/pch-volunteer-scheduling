from datetime import time

import openpyxl
import pytest
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.errors import WorkbookError
from scheduler.model import Settings
from scheduler.reading.settings import read_settings


HEADER = ("Setting", "Value", "Unit", "Meaning")

# A complete, correct Settings tab. The values differ from the defaults in model.py, so a
# test can't pass by accident through those defaults.
GOOD_ROWS = [
    ("Workbook format version", 1),
    ("Time step", 15),
    ("Day boundary", "06:00"),
    ("Days", "Friday, Saturday"),
    ("Minimum work stretch", 45),
    ("Maximum work stretch", 150),
    ("Minimum break", 20),
    ("Default maximum hours per day", 6),
    ("Default maximum hours total", 12),
    ("Weight: skill score 1", 5),
    ("Weight: skill score 2", 3),
    ("Weight: skill score 3", 1),
    ("Weight: start or end off the half hour", 7),
]

# The reader switches every soft rule on; update this when a soft rule is added.
ALL_SOFT_RULES = frozenset({"fewer_stretches","round_times", "skill_score"})

# What GOOD_ROWS should give.
GOOD_SETTINGS = Settings(min_stretch_minutes=45, max_stretch_minutes=150,
                         min_break_minutes=20, days=("Friday", "Saturday"),
                         default_max_minutes_per_day=360, default_max_minutes_total=720,
                         weight_skill_score_1=5, weight_skill_score_2=3, weight_skill_score_3=1,
                         weight_off_round_time=7, weight_work_stretch=20,
                         soft_rules=ALL_SOFT_RULES)

# The settings that must be there with a value (missing or empty = error).
REQUIRED_SETTINGS = ["Workbook format version", "Time step", "Day boundary", "Days",
                     "Minimum work stretch", "Maximum work stretch", "Minimum break",
                     "Default maximum hours per day", "Default maximum hours total"]

# The optional settings: (row name, Settings field, default). Missing or empty = default.
# A new optional setting = one line here (plus its row in GOOD_ROWS and GOOD_SETTINGS).
OPTIONAL_SETTINGS = [("Weight: skill score 1", "weight_skill_score_1", 6),
                     ("Weight: skill score 2", "weight_skill_score_2", 2),
                     ("Weight: skill score 3", "weight_skill_score_3", 0),
                     ("Weight: start or end off the half hour", "weight_off_round_time", 10)]


def _settings_sheet(rows: list[tuple], header: tuple[str, ...] = HEADER) -> Worksheet:
    """A new in-memory sheet called Settings: the header in row 1, then one row per setting."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Settings"         # so the error messages can name the tab
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    return sheet


def _rows_with(name: str, value: object, rows: list[tuple] = GOOD_ROWS) -> list[tuple]:
    """A copy of rows (default GOOD_ROWS) in which the setting with this name has another
    value. Pass the result back in as rows to change a second setting."""
    new_rows = []
    for setting, good_value in rows:
        if setting == name:
            new_rows.append((setting, value))
        else:
            new_rows.append((setting, good_value))
    return new_rows


def _rows_without(name: str, rows: list[tuple] = GOOD_ROWS) -> list[tuple]:
    """A copy of rows (default GOOD_ROWS) without the setting with this name."""
    new_rows = []
    for setting, good_value in rows:
        if setting != name:
            new_rows.append((setting, good_value))
    return new_rows


# --- Reading the tab ---

def test_settings_tab_is_read_into_settings():
    """A complete, correct Settings tab gives the matching Settings."""
    # Arrange
    sheet = _settings_sheet(GOOD_ROWS)

    # Act
    result = read_settings(sheet)

    # Assert
    assert result == GOOD_SETTINGS


def test_order_of_the_rows_does_not_matter():
    """The settings are found by name, wherever their row is."""
    # Arrange
    rows = list(reversed(GOOD_ROWS))   # a new list, last row first
    sheet = _settings_sheet(rows)

    # Act
    result = read_settings(sheet)

    # Assert
    assert result == GOOD_SETTINGS


def test_rows_without_a_setting_name_are_skipped():
    """An empty row between the settings is no problem."""
    # Arrange
    rows = GOOD_ROWS[0:2] + [(None, None)] + GOOD_ROWS[2:]   # slicing and + make a new list
    sheet = _settings_sheet(rows)

    # Act
    result = read_settings(sheet)

    # Assert
    assert result == GOOD_SETTINGS


def test_missing_value_column_raises_workbook_error():
    """A Settings tab without a Value column is an error."""
    # Arrange
    sheet = _settings_sheet(GOOD_ROWS, header=("Setting", "Amount", "Unit", "Meaning"))

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Settings.*Value"):
        read_settings(sheet)


def test_the_same_setting_twice_raises_workbook_error():
    """Two rows with the same setting are an error: it is unclear which value is meant."""
    # Arrange
    rows = GOOD_ROWS + [("Minimum break", 30)]   # a second Minimum break row
    sheet = _settings_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Minimum break"):
        read_settings(sheet)


# --- Setting names and presence ---

def test_known_settings_the_scheduler_does_not_use_yet_are_accepted():
    """A setting like "Lunch break length" is known, so it is accepted (and ignored for now)."""
    # Arrange
    rows = GOOD_ROWS + [("Lunch break length", 30)]   # + makes a new list
    sheet = _settings_sheet(rows)

    # Act
    result = read_settings(sheet)

    # Assert
    assert result == GOOD_SETTINGS


def test_unknown_setting_raises_workbook_error():
    """A setting name the scheduler doesn't know, e.g. a typo, is an error naming it."""
    # Arrange
    rows = GOOD_ROWS + [("Minimum brake", 30)]   # a typo of "Minimum break"
    sheet = _settings_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Minimum brake"):
        read_settings(sheet)


@pytest.mark.parametrize("missing_setting", REQUIRED_SETTINGS)
def test_missing_setting_raises_workbook_error(missing_setting: str):
    """Leaving out a required setting is an error naming that setting."""
    # Arrange
    sheet = _settings_sheet(_rows_without(missing_setting))

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match=missing_setting):
        read_settings(sheet)


@pytest.mark.parametrize("empty_setting", REQUIRED_SETTINGS)
def test_required_setting_with_an_empty_value_raises_workbook_error(empty_setting: str):
    """A required setting with an empty Value cell is an error naming that setting."""
    # Arrange
    rows = _rows_with(empty_setting, None)
    sheet = _settings_sheet(rows)

    # Act
    # (Act and Assert in the same line)

    # Assert
    with pytest.raises(WorkbookError, match=f"Settings:.*{empty_setting}"):
        read_settings(sheet)


@pytest.mark.parametrize("missing_setting, field, default", OPTIONAL_SETTINGS)
def test_missing_optional_setting_gets_the_default(missing_setting: str, field: str,
                                                   default: int):
    """An optional setting that is left out gets its default."""
    # Arrange
    rows = _rows_without(missing_setting)
    sheet = _settings_sheet(rows)

    # Act
    settings = read_settings(sheet)

    # Assert
    assert getattr(settings, field) == default


@pytest.mark.parametrize("empty_setting, field, default", OPTIONAL_SETTINGS)
def test_empty_optional_setting_gets_the_default(empty_setting: str, field: str, default: int):
    """An optional setting with an empty Value cell gets its default."""
    rows = _rows_with(empty_setting, None)
    sheet = _settings_sheet(rows)

    # Act
    settings = read_settings(sheet)

    # Assert
    assert getattr(settings, field) == default


# --- Settings with one allowed value ---

def test_other_workbook_format_version_raises_workbook_error():
    """A workbook made for another layout (another format version) is an error."""
    # Arrange
    sheet = _settings_sheet(_rows_with("Workbook format version", 2))

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Workbook format version"):
        read_settings(sheet)


def test_time_step_other_than_15_raises_workbook_error():
    """For now the scheduler only supports 15-minute blocks."""
    # Arrange
    sheet = _settings_sheet(_rows_with("Time step", 30))

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Time step"):
        read_settings(sheet)


def test_day_boundary_other_than_06_00_raises_workbook_error():
    """For now the scheduler only supports convention days that start at 06:00."""
    # Arrange
    sheet = _settings_sheet(_rows_with("Day boundary", "05:00"))

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Day boundary"):
        read_settings(sheet)


def test_day_boundary_typed_as_an_excel_time_is_accepted():
    """A Day boundary typed into Excel as the time 06:00 counts the same as the text "06:00"."""
    # Arrange
    sheet = _settings_sheet(_rows_with("Day boundary", time(6, 0)))

    # Act
    result = read_settings(sheet)

    # Assert
    assert result == GOOD_SETTINGS


# --- Values ---
# What exactly is a valid value is tested in test_parse_values.py; this test checks
# that the reader uses the right parse function for each kind of setting and turns
# its ValueError into a WorkbookError naming the tab and the setting.

@pytest.mark.parametrize("setting, value", [
    ("Minimum break", "six"),
    ("Time step", "fifteen"),
    ("Days", "Friday, Friday"),
    ("Default maximum hours per day", "eight"),
    ("Weight: skill score 1", -1)],
    ids=["whole number", "setting with one allowed value", "days", "hour limit",
         "optional whole number"])
def test_invalid_value_raises_workbook_error_naming_the_setting(setting: str, value: object):
    """An invalid value of any kind raises WorkbookError starting with the tab and setting."""
    # Arrange
    rows = _rows_with(setting, value)
    sheet = _settings_sheet(rows)

    # Act
    # (Act and Assert in the same line)

    # Assert
    with pytest.raises(WorkbookError, match=f"Settings,.*{setting}"):
        read_settings(sheet)


# --- Default hour limits ---

def test_default_hour_limits_are_read_in_minutes():
    """Default maximum hours per day 6 and total 12 become 360 and 720 minutes."""
    # Arrange
    sheet = _settings_sheet(GOOD_ROWS)

    # Act
    result = read_settings(sheet)

    # Assert
    assert result.default_max_minutes_per_day == 360
    assert result.default_max_minutes_total == 720


@pytest.mark.parametrize("setting, field", [
    ("Default maximum hours per day", "default_max_minutes_per_day"),
    ("Default maximum hours total", "default_max_minutes_total")])
def test_none_as_default_hour_limit_means_no_limit(setting, field):
    """A default hour limit of "none" means no limit (None)."""
    # Arrange
    rows = _rows_with(setting, "none")
    sheet = _settings_sheet(rows)

    # Act
    result = read_settings(sheet)

    # Assert
    assert getattr(result, field) is None


def test_default_daily_limit_over_24_hours_raises_workbook_error():
    """A default maximum of more than 24 hours per day is an error (probably a typo)."""
    # Arrange
    # Total "none", so the check "per day at most the total" can't be the one that fires.
    rows = _rows_with("Default maximum hours per day", 25)
    rows = _rows_with("Default maximum hours total", "none", rows=rows)
    sheet = _settings_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Settings.*Default maximum hours per day.*24"):
        read_settings(sheet)


def test_default_total_limit_over_24_hours_per_day_raises_workbook_error():
    """A default total of more than 24 hours times the number of days is an error."""
    # Arrange
    # GOOD_ROWS has 2 days, so at most 48 hours: 49 is just over.
    rows = _rows_with("Default maximum hours total", 49)
    sheet = _settings_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Settings.*Default maximum hours total.*48"):
        read_settings(sheet)


def test_default_daily_limit_above_the_default_total_raises_workbook_error():
    """A default per day higher than the default total is an error naming both settings."""
    # Arrange
    rows = _rows_with("Default maximum hours per day", 13)  # more than the total of 12
    sheet = _settings_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    match = "Default maximum hours per day.*Default maximum hours total"
    with pytest.raises(WorkbookError, match=match):
        read_settings(sheet)


# --- Soft rules ---

def test_every_soft_rule_is_switched_on():
    """The reader switches every soft rule on (a switch per rule in the workbook is later)."""
    # Arrange
    sheet = _settings_sheet(GOOD_ROWS)

    # Act
    settings = read_settings(sheet)

    # Assert
    assert settings.soft_rules == ALL_SOFT_RULES

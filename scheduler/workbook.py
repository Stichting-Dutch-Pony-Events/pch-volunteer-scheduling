"""Reads the input workbook (.xlsx) into a Problem the solver can work with.

Helpers like cell_text are plain functions without openpyxl, so they can be tested with
simple values instead of a workbook file. Functions that read a tab take an openpyxl
sheet; the tests build small sheets in memory.
"""
from datetime import time

from openpyxl.worksheet.worksheet import Worksheet

from scheduler.model import Settings, block_of
from scheduler.model import MINUTES_PER_BLOCK, DAY_STARTS_AT_HOUR, BLOCKS_PER_DAY

# The layout of the input workbook this scheduler reads (the "Workbook format version"
# setting). Raise it only when the workbook layout changes, e.g. a renamed setting or a
# new required column, not for every new version of the scheduler.
WORKBOOK_FORMAT_VERSION = 1

KNOWN_SETTINGS = {"Workbook format version", "Time step", "Day boundary", "Days",
                  "Shift start step", "Minimum work stretch", "Preferred maximum shift length",
                  "Maximum work stretch", "Minimum break", "Lunch window start",
                  "Lunch window end", "Lunch break length", "Dinner window start",
                  "Dinner window end", "Dinner break length", "Default maximum hours per day",
                  "Default maximum hours total", "Weight: miss a REALLY-want event",
                  "Weight: miss a like-to-attend event", "Weight: skill score 3",
                  "Weight: skill score 2", "Weight: skill score 1",
                  "Weight: shift longer than preferred", "Weight: unfair spread of hours"}

REQUIRED_SETTINGS = {"Workbook format version", "Time step", "Day boundary", "Days",
                    "Minimum work stretch", "Maximum work stretch", "Minimum break"}


class WorkbookError(Exception):
    """Raised when the input workbook has a mistake, e.g. a missing column or a typo.

    The message starts with the tab, so the user knows where to look.
    """


def cell_text(value: str | int | float | time | None) -> str:
    """The value of a cell as tidy text: spaces around it removed, empty cell = "".

    A time value (when someone types 14:00 into a cell) becomes "14:00".
    """
    if value is None:
        result = ""
    elif isinstance(value, time):
        result = value.strftime("%H:%M")
    else:  # str, int or float
        result = str(value).strip()

    return result


def parse_availability(text: str, day: str, settings: Settings) -> set[int]:
    """The blocks a volunteer is available on this convention day, from one Volunteers cell.

    text is the cell after cell_text, upper or lower case doesn't matter:
    "yes" = the whole convention day (06:00 to 06:00), "no" or "" = not that day,
    "08:00-18:00" = from 08:00 up to (not including) 18:00. A range may pass midnight
    (Saturday "20:00-02:00"); an end of "06:00" means until the end of the convention day.
    Anything else raises ValueError naming the value (the reader adds volunteer and row).
    """
    # The convention day starts at block_of(day, "06:00"); this also checks the day name.
    day_start = block_of(day, "06:00", settings)
    lowered = text.lower()

    # 1. The whole day, or not at all.
    if lowered == "yes":
        return set(range(day_start, day_start + BLOCKS_PER_DAY))
    if lowered == "no" or lowered == "":
        return set()

    # 2. Anything else must be one range "start-end".
    parts = lowered.split("-")
    if len(parts) != 2:
        raise ValueError(f"Availability {text!r} is not 'yes', 'no' or a time range "
                         f"like 08:00-18:00.")
    first_block = block_of(day, parts[0].strip(), settings)
    block_after_last = block_of(day, parts[1].strip(), settings)

    # An end of 06:00 gives the start of the day; as an end it means the end of the day.
    if block_after_last == day_start:
        block_after_last = day_start + BLOCKS_PER_DAY

    if block_after_last <= first_block:
        raise ValueError(f"Availability {text!r}: the end must be after the start.")

    return set(range(first_block, block_after_last))


def find_columns(sheet: Worksheet, names: list[str]) -> dict[str, int]:
    """The column number of each header in names, read from row 1 of the sheet.

    Example: header Setting, Value, Unit and names ["Setting", "Value"] gives
    {"Setting": 1, "Value": 2}. Spaces around a header are ignored. Raises WorkbookError
    (naming the tab) when a column is missing or a header appears twice.
    """
    # Row 1 as tidy text, e.g. ["Setting", "Value", "Unit"].
    headers = []
    for cell in sheet[1]:
        headers.append(cell_text(cell.value))

    columns = {}
    for name in names:
        # Every column with this header; enumerate counts from 1, like column A = 1.
        matching = []
        for column_number, header in enumerate(headers, start=1):
            if header == name:
                matching.append(column_number)

        if len(matching) == 0:
            raise WorkbookError(f"{sheet.title}: no column {name!r} in the header row (row 1).")
        if len(matching) > 1:
            raise WorkbookError(f"{sheet.title}: the header {name!r} is in more than one column.")
        columns[name] = matching[0]

    return columns


def read_settings(sheet: Worksheet) -> Settings:
    """The Settings tab as Settings: one setting per row, in the columns Setting and Value.

    The order of the rows is free. Required: Workbook format version (must be
    WORKBOOK_FORMAT_VERSION), Time step (must be 15), Day boundary (must be 06:00), Days
    (comma separated, no duplicates), Minimum work stretch, Maximum work stretch and
    Minimum break (whole numbers, in minutes). Settings the scheduler does not use yet
    (meals, maximum hours, weights) are accepted and ignored. Raises WorkbookError for a
    missing, empty, duplicate or unknown setting, or a value that is not allowed.
    """
    # 1. Isolate the headers and their respective column numbers
    columns = find_columns(sheet, ["Setting", "Value"])

    # 2. Fetch all (unparsed) settings from Setttings sheet
    unparsed_settings = dict()
    for rownumber in range(2,sheet.max_row + 1):
        setting_name = cell_text(sheet.cell(row=rownumber, column=columns["Setting"]).value)
        if setting_name == "":
            continue

        if setting_name in unparsed_settings:
            raise WorkbookError(f"Settings: two settings with name {setting_name!r}.")
        else:
            unparsed_value = cell_text(sheet.cell(row=rownumber, column=columns["Value"]).value)
            unparsed_settings[setting_name] = unparsed_value

    # 3. Check for unknown settings
    for key, value in unparsed_settings.items():
        if key not in KNOWN_SETTINGS:
            raise WorkbookError(f"Settings: unknown setting {key!r}")

    # 4. Check for presence of all required settings
    for required_setting in REQUIRED_SETTINGS:
        if required_setting not in unparsed_settings:
            raise WorkbookError(f"Settings: Missing required setting {required_setting!r}")

    # 5. Check the required settings one by one and turn them into Settings
    version = _whole_number(unparsed_settings, "Workbook format version")
    if version != WORKBOOK_FORMAT_VERSION:
        raise WorkbookError(f"Settings, 'Workbook format version': this workbook is version "
                            f"{version}, this scheduler reads version {WORKBOOK_FORMAT_VERSION}.")

    time_step = _whole_number(unparsed_settings, "Time step")
    if time_step != MINUTES_PER_BLOCK:
        raise WorkbookError(f"Settings, 'Time step': the scheduler only supports "
                            f"{MINUTES_PER_BLOCK} minutes for now, not {time_step}.")

    # cell_text already turned a time typed into Excel into text, so compare as text.
    day_boundary = unparsed_settings["Day boundary"]
    expected_day_boundary = f"{DAY_STARTS_AT_HOUR:02d}:00"
    if day_boundary != expected_day_boundary:
        raise WorkbookError(f"Settings, 'Day boundary': the scheduler only supports "
                            f"{expected_day_boundary} for now, not {day_boundary}.")

    # Days: "Friday, Saturday, Sunday" -> ["Friday", "Saturday", "Sunday"]
    days = []
    for day in unparsed_settings["Days"].split(","):
        day = day.strip()
        if day in days:
            raise WorkbookError(f"Settings, 'Days': {day!r} appears more than once.")
        days.append(day)

    return Settings(
        min_stretch_minutes=_whole_number(unparsed_settings, "Minimum work stretch"),
        max_stretch_minutes=_whole_number(unparsed_settings, "Maximum work stretch"),
        min_break_minutes=_whole_number(unparsed_settings, "Minimum break"),
        days=tuple(days))  # a tuple, like the default in Settings


def _whole_number(settings: dict[str, str], name: str) -> int:
    """The setting with this name as a whole number; WorkbookError if it isn't one."""
    try:
        return int(settings[name])
    except ValueError:
        # from None: show only our clear message, not the ValueError behind it
        raise WorkbookError(f"Settings, {name!r}: {settings[name]!r} is not a whole "
                            f"number.") from None

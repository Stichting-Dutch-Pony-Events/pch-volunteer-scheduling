"""Helpers that turn cells into values, shared by the tab readers.

cell_text tidies one cell; find_columns and find_post_columns find columns by their
header; parse_availability and parse_hour_limits turn a cell's text into blocks or
minutes. They raise WorkbookError (naming the tab) or ValueError (the reader puts the
tab and row in front). cell_text and parse_availability are plain functions without
openpyxl, so they can be tested with simple values instead of a workbook.
"""
from datetime import time

from openpyxl.worksheet.worksheet import Worksheet

from scheduler.errors import WorkbookError
from scheduler.model import Settings, block_of, BLOCKS_PER_DAY


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


def find_post_columns(sheet: Worksheet, not_posts: list[str]) -> dict[str, int]:
    """Every column in row 1 that is a post, as {post: column number}.

    A post column is any column whose header is not empty and not in not_posts (used by
    the Skills and Demand tabs, where the posts are the columns). Raises WorkbookError
    (naming the tab) when a post has more than one column.
    """
    post_columns = {}
    for column, cell in enumerate(sheet[1], start=1):
        header = cell_text(cell.value)
        if header == "" or header in not_posts:
            continue
        if header in post_columns:
            raise WorkbookError(f"{sheet.title}: the post {header!r} has more than one column.")
        post_columns[header] = column
    return post_columns


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


def parse_hour_limits(per_day: tuple[str, str], total: tuple[str, str],
                      number_of_days: int) -> tuple[int | None, int | None]:
    """The hour limits per day and in total of one Settings or Volunteers row, in minutes.

    per_day and total are (name, text): the setting or column name for the messages, and
    the cell text (already through cell_text). Each text goes through _parse_hour_limit, with at
    most 24 hours per day and in total at most 24 hours for each day of the convention.
    An empty text gives None: read_volunteers then fills in the default, read_settings
    never lets an empty value get here. Per day may not be more than the total, but only
    when both are a number. Raises ValueError naming the setting or column; the reader
    puts the tab (and row) in front of the message.
    """
    per_day_name, per_day_text = per_day   # unpack the (name, text) pairs
    total_name, total_text = total

    per_day_minutes = None
    if per_day_text != "":
        per_day_minutes = _parse_hour_limit(per_day_name, per_day_text, 24)

    total_minutes = None
    if total_text != "":
        total_minutes = _parse_hour_limit(total_name, total_text, 24 * number_of_days)

    # Only compare two numbers: an empty text or "none" (both None here) is never compared.
    if per_day_minutes is not None and total_minutes is not None:
        if per_day_minutes > total_minutes:
            raise ValueError(f"{per_day_name} ({per_day_minutes // 60}) is more than "
                             f"{total_name} ({total_minutes // 60}).")

    return per_day_minutes, total_minutes


def _parse_hour_limit(name: str, text: str, max_hours: int) -> int | None:
    """One hour limit cell (already through cell_text) as minutes.

    Whole hours from 1 up to max_hours (24 for a day, 24 times the number of days for the
    total) give that many hours in minutes; "none" (case ignored) = no limit, None.
    Anything else raises ValueError starting with name (the setting or column); the
    reader puts the tab (and row) in front. An empty text is handled by parse_hour_limits.
    """
    if text.lower() == "none":
        return None

    try:
        hours = int(text)
    except ValueError:
        # from None: show only our clear message, not the ValueError behind it
        raise ValueError(f"{name}: {text!r} is not a whole number of hours "
                         f"(or \"none\" for no limit).") from None

    if hours < 1:
        raise ValueError(f"{name}: {hours} hours is not allowed: at least 1 "
                         f"(or \"none\" for no limit).")
    if hours > max_hours:
        raise ValueError(f"{name}: {hours} is more than the maximum of {max_hours} hours.")

    return hours * 60  # hours -> minutes

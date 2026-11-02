"""Reads the input workbook (.xlsx) into a Problem the solver can work with.

Helpers like cell_text are plain functions without openpyxl, so they can be tested with
simple values instead of a workbook file.
"""
from datetime import time

from scheduler.model import Settings, BLOCKS_PER_DAY, block_of


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

"""Reads the input workbook (.xlsx) into a Problem the solver can work with.

Helpers like cell_text are plain functions without openpyxl, so they can be tested with
simple values instead of a workbook file.
"""
from datetime import time


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

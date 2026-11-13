"""Reads the Demand tab: read_demand."""
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.errors import WorkbookError
from scheduler.debug import debug_print
from scheduler.model import Settings, block_of
from scheduler.reading.cells import cell_text, find_columns, find_post_columns


def read_demand(sheet: Worksheet, settings: Settings) -> dict[tuple[str, int], int]:
    """The Demand tab as {(post, block): number of people needed}, like Problem.demand.

    Each row is one block, given by its Day and Time (night times belong to the day
    before, as in block_of); every other column except Notes is a post. Empty or 0 means
    closed and is left out, so a row with a Day and Time but no number means everything
    is closed then. A completely empty row is skipped. Raises WorkbookError for a missing
    Day or Time column, a row with an invalid or missing Day or Time (also without
    numbers), the same Day and Time twice, or a number that is not a whole number of at
    least 0.
    """
    debug_print(f"read_demand: reading tab {sheet.title}")
    columns = find_columns(sheet, ["Day", "Time"])
    post_columns = find_post_columns(sheet, not_posts=["Day", "Time", "Notes"])

    demand = {}
    rows_of_blocks = {}   # block -> the row it is on, to spot the same Day and Time twice
    for row in range(2, sheet.max_row + 1):
        day = cell_text(sheet.cell(row=row, column=columns["Day"]).value)
        time_text = cell_text(sheet.cell(row=row, column=columns["Time"]).value)

        # 1. The numbers of this row: {"Tickets": 2, ...}, empty and 0 left out.
        needed_per_post = {}
        for post, column in post_columns.items():
            text = cell_text(sheet.cell(row=row, column=column).value)
            if text == "":
                continue  # empty = closed
            try:
                needed = int(text)
            except ValueError:
                needed = -1   # not a whole number: reported just below
            if needed < 0:
                raise WorkbookError(f"Demand, row {row} ({day} {time_text}), {post}: {text!r} "
                                    f"is not a number of people (a whole number, 0 = closed).")
            if needed > 0:
                needed_per_post[post] = needed

        # 2. A completely empty row is skipped; any other row needs a valid Day and Time.
        if day == "" and time_text == "" and len(needed_per_post) == 0:
            continue

        # 3. Which block this row is, and not one we have seen already.
        try:
            block = block_of(day, time_text, settings)
        except ValueError as error:
            raise WorkbookError(f"Demand, row {row}: {error}") from None
        if block in rows_of_blocks:
            raise WorkbookError(f"Demand, row {row}: {day} {time_text} is already on row "
                                f"{rows_of_blocks[block]}.")
        rows_of_blocks[block] = row

        # 4. Only the open posts go into the demand.
        for post, needed in needed_per_post.items():
            demand[(post, block)] = needed

    return demand

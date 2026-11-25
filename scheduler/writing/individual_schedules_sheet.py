"""The tab "Individual schedules" of the output workbook: one column per volunteer.

One row per half hour, one column per volunteer (alphabetical), each shift a box with the
post on top and the times at the bottom. create_individual_schedules_sheet first, then the
helpers it uses. The helpers are plain functions without openpyxl, so they can be tested
without writing a file.
"""
from openpyxl import Workbook

from scheduler.model import BLOCKS_PER_DAY, Problem, Schedule, Volunteer
from scheduler.writing.schedule_sheet import rows_to_show


def create_individual_schedules_sheet(workbook: Workbook, problem: Problem,
                                      schedule: Schedule) -> None:
    """Add the tab "Individual schedules" to the workbook: one column per volunteer.

    Columns A and B hold the day and time of every half-hour row (half_hour_rows, with a
    margin of one row: half an hour, like the Schedule tab), then
    one column per volunteer in alphabetical order; row 1 the nicknames, row 2 their
    group (empty for now). Each shift is a box of cells with an outside border: the post
    in the top cell, the times in the bottom cell. A free cell is white when the volunteer
    could work then (free_cell_is_white), grey otherwise.
    """
    # TODO: written after the helpers (step 4); not yet called from write_output.
    raise NotImplementedError


def half_hour_rows(problem: Problem, margin_rows: int = 0) -> list[int]:
    """The rows of the tab, as the even block that starts each half hour, in time order.

    Every half hour with demand gives one row: a block on :15 or :45 belongs to the row of
    the half hour it falls in (block 33 = 14:15 -> row 32 = 14:00); gaps in a day's demand
    are included, like in rows_to_show. Then margin_rows extra rows before the first and
    after the last row of each day (in half-hour rows: 1 = half an hour), but never outside
    that day. A row appears only once.
    """
    # 1. Every block from the first to the last demand of each day (gaps included), without
    #    a margin: the margin is added below in whole rows.
    blocks = rows_to_show(problem)

    # 2. Each block to the row of its half hour, grouped per convention day. An even block
    #    starts its own row; an odd one (:15 or :45) belongs to the row one block earlier,
    #    so block - block % 2 is the row in both cases. A set keeps each row once.
    rows_per_day = {}  # day number -> set of rows
    for block in blocks:
        day_number = block // BLOCKS_PER_DAY
        if day_number not in rows_per_day:
            rows_per_day[day_number] = set()
        rows_per_day[day_number].add(block - block % 2)

    # 3. The margin: margin_rows extra rows before the first and after the last row of each
    #    day. One row is 2 blocks. The margin stays within its own day: not before the
    #    day's first block, not after its last row (the last even block of the day).
    for day_number in rows_per_day:
        first_row = min(rows_per_day[day_number])
        last_row = max(rows_per_day[day_number])

        first_row_of_day = day_number * BLOCKS_PER_DAY
        last_row_of_day = (day_number + 1) * BLOCKS_PER_DAY - 2
        margin_start = max(first_row - 2 * margin_rows, first_row_of_day)
        margin_end = min(last_row + 2 * margin_rows, last_row_of_day)

        # With margin_rows = 0 both ranges are empty, so nothing is added.
        for row in range(margin_start, first_row, 2):         # the rows before the first
            rows_per_day[day_number].add(row)
        for row in range(last_row + 2, margin_end + 2, 2):    # the rows after the last
            rows_per_day[day_number].add(row)

    # 4. All days together, in time order.
    all_rows = []
    for day_number in rows_per_day:
        for row in rows_per_day[day_number]:
            all_rows.append(row)

    return sorted(all_rows)


def free_cell_is_white(volunteer: Volunteer, row: int, problem: Problem) -> bool:
    """Whether a free cell of this volunteer in this half-hour row is white (else grey).

    White when both: the volunteer is available in at least one of the row's two blocks
    (row and row + 1), and some post has demand in at least one of them (the convention is
    going on). Grey otherwise. A row that is not an even block (not on the half hour)
    raises ValueError.
    """
    raise NotImplementedError

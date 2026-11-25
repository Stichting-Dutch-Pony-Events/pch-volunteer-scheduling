"""The tab "Individual schedules" of the output workbook: one column per volunteer.

One row per half hour, one column per volunteer (alphabetical), each shift a box with the
post on top and the times at the bottom. create_individual_schedules_sheet first, then the
helpers it uses. The helpers are plain functions without openpyxl, so they can be tested
without writing a file.
"""
from openpyxl import Workbook

from scheduler.model import Problem, Schedule, Volunteer


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
    raise NotImplementedError


def free_cell_is_white(volunteer: Volunteer, row: int, problem: Problem) -> bool:
    """Whether a free cell of this volunteer in this half-hour row is white (else grey).

    White when both: the volunteer is available in at least one of the row's two blocks
    (row and row + 1), and some post has demand in at least one of them (the convention is
    going on). Grey otherwise. A row that is not an even block (not on the half hour)
    raises ValueError.
    """
    raise NotImplementedError

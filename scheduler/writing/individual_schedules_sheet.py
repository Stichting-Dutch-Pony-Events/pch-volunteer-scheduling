"""The tab "Individual schedules" of the output workbook: one column per volunteer.

One row per half hour, one column per volunteer (alphabetical), each shift a box with the
post on top and the times at the bottom. create_individual_schedules_sheet first, then the
helpers it uses. The helpers are plain functions without openpyxl, so they can be tested
without writing a file.
"""
from dataclasses import dataclass

from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Border, Side, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.debug import debug_print
from scheduler.model import (BLOCKS_PER_DAY, Problem, Schedule, Settings, Volunteer,
                             day_and_time_of, end_time_of)
from scheduler.writing.schedule_sheet import rows_to_show

FIRST_ROW = 3
FIRST_VOLUNTEER_COLUMN = 3

# The fill of a free cell when the volunteer can't work then (not available, or the
# convention is not going on). A white cell has no fill at all.
GREY = "D9D9D9"
GREY_FILL = PatternFill(fill_type="solid", fgColor=GREY, bgColor=GREY)
BOLD = InlineFont(b=True)

LINE = Side(style="thin")
BORDER_TOP = Border(top=LINE, left=LINE, right=LINE)
BORDER_MIDDLE = Border(left=LINE, right=LINE)
BORDER_BOTTOM = Border(left=LINE, right=LINE, bottom=LINE)
BORDER_FULL = Border(top=LINE, left=LINE, right=LINE, bottom=LINE)


@dataclass(frozen=True)
class ShiftBox:
    """Where one shift goes on the tab: the cells of its box and which times are bold.

    Rows are named by the even block that starts their half hour, like in half_hour_rows.
    The box covers the rows first_row up to and including last_row (the same row for a
    one-row box). The shift's own times are kept, so the text can show them exactly.
    """
    post: str
    first_block: int        # the shift's real start
    block_after_last: int   # the shift's real end (the block after its last one)
    first_row: int          # the top row of the box
    last_row: int           # the bottom row of the box
    start_bold: bool        # the start time does not line up with the top of the box
    end_bold: bool          # the end time does not line up with the bottom of the box


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
    debug_print("create_individual_schedules_sheet: creating tab Individual schedules")

    # 1. Guard against duplicate sheets
    if "Individual schedules" in workbook.sheetnames:
        raise ValueError("The workbook already has an 'Individual schedules' tab.")
    sheet: Worksheet = workbook.create_sheet("Individual schedules")

    # 2. The boxes of every volunteer.
    boxes_per_volunteer = {}
    for volunteer in problem.volunteers:
        shifts = schedule.shifts_of(volunteer.name)
        boxes_per_volunteer[volunteer.name] = place_shift_boxes(shifts)

    # 3. The rows: half_hour_rows(problem, margin_rows=1), plus any row a box is in that
    #    is missing (a box pushed past the end of its day); never hide a shift.
    rows = half_hour_rows(problem, margin_rows=1)
    for boxes in boxes_per_volunteer.values():
        for box in boxes:
            if box.last_row not in rows:
                rows.append(box.last_row)
                rows.sort()  # Sort in place

    # 4. Header: Day, Time, the nicknames in alphabetical order; row 2 (groups) empty.
    headers = ["Day", "Time"]
    volunteer_names = []
    for volunteer in problem.volunteers:
        volunteer_names.append(volunteer.name)

    volunteer_column_of = {}
    volunteer_column = FIRST_VOLUNTEER_COLUMN
    for name in sorted(volunteer_names):
        headers.append(name)
        volunteer_column_of[name] = volunteer_column

        volunteer_column += 1

    sheet.append(headers)
    sheet.append([])

    # 5. Day and time on every row from row 3 (day_and_time_of).
    sheet_row_of = {}
    sheet_row = FIRST_ROW
    for row in rows:
        sheet_row_of[row] = sheet_row
        day, time = day_and_time_of(row, problem.settings)

        sheet.cell(row=sheet_row, column=1).value = day
        sheet.cell(row=sheet_row, column=2).value = time

        sheet_row += 1

    # 6. Free cells: grey (GREY) unless free_cell_is_white.
    for row in rows:
        for volunteer in problem.volunteers:
            if free_cell_is_white(volunteer, row, problem) is True:
                continue

            sheet_row = sheet_row_of[row]
            sheet_column = volunteer_column_of[volunteer.name]
            sheet.cell(row=sheet_row, column=sheet_column).fill = GREY_FILL

    # 7. The boxes (_write_box).
    for volunteer_name, boxes in boxes_per_volunteer.items():
        for box in boxes:
            _write_box(sheet=sheet,
                       column=volunteer_column_of[volunteer_name],
                       box=box,
                       sheet_row_of=sheet_row_of,
                       settings=problem.settings)

    # 8. Freeze panes at "C3".
    sheet.freeze_panes = "C3"


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
    # A row is named by the even block that starts its half hour; an odd block here means
    # a mistake in the calling code, so say so instead of guessing.
    if row % 2 != 0:
        raise ValueError(f"Row {row} is not the start of a half hour (an even block).")

    # Available for at least part of the half hour (arriving or leaving on :15 is enough)?
    is_available = row in volunteer.available_blocks or (row + 1) in volunteer.available_blocks

    # Is the convention going on: demand at any post (not only the volunteer's own posts)
    # in at least one of the row's two blocks? Stop looking at the first one found.
    convention_is_going_on = False
    for post, block in problem.demand:
        if block in [row, row + 1]:
            convention_is_going_on = True
            break

    # White only when both are true; grey when either is false.
    return is_available and convention_is_going_on


def place_shift_boxes(shifts: list[tuple[str, int, int]]) -> list[ShiftBox]:
    """The boxes of one volunteer's shifts, in the same (time) order as the shifts.

    shifts is a list of (post, first_block, block_after_last), as Schedule.shifts_of gives
    it. A box runs from the row of its first block to the row of its last block. A box
    whose first row is on or above the previous box's last row (a switch on :15 or :45)
    starts one row lower instead; it keeps its own last row, but always has at least one
    row, so it may in turn push the next box down. A time is bold when it does not line
    up with its edge of the box: start_bold when first_row != first_block, end_bold when
    last_row + 2 != block_after_last.
    """
    shiftblocks = []
    # The last row of the box before this one (after any push), so the next box can be
    # pushed below it. None = no box yet, so the first box is never pushed.
    previous_last_row = None
    for post, first_block, block_after_last in shifts:
        # 1. The rows the shift naturally covers: the row of its first block and the row of
        #    its last block (block_after_last - 1, not block_after_last itself). An odd block
        #    (:15 or :45) belongs to the row one block earlier, like in half_hour_rows.
        first_row = first_block - first_block % 2
        last_row = (block_after_last - 1) - (block_after_last - 1) % 2

        # 2. The push: a box may not start on or above the previous box's last row (that
        #    happens after a post switch on :15 or :45), so it starts one row below it.
        if previous_last_row is not None and first_row <= previous_last_row:
            first_row = previous_last_row + 2

        # 3. A pushed box keeps its own last row, but always has at least one row: if the
        #    push moved its top below its bottom, it becomes a one-row box. That box can
        #    stick out below the shift's real end and push the next box down in turn.
        if last_row <= first_row:
            last_row = first_row

        # 4. A time is bold when it doesn't line up with its edge of the box: the start
        #    when the box starts at another block (on :15/:45, or pushed down), the end
        #    when the box ends at another block (row + 2 = the block after the box).
        start_bold = first_row != first_block
        end_bold = last_row + 2 != block_after_last

        shiftblocks.append(ShiftBox(post=post,
                                    first_block=first_block,
                                    block_after_last=block_after_last,
                                    first_row=first_row,
                                    last_row=last_row,
                                    start_bold=start_bold,
                                    end_bold=end_bold))

        # 5. Remember where this box ends (pushed or not), for the next shift: this is what
        #    makes a cascade work.
        previous_last_row = last_row

    return shiftblocks


def _write_box(sheet: Worksheet, column: int, box: ShiftBox, sheet_row_of: dict[int, int],
               settings: Settings) -> None:
    """Write one shift box into the volunteer's column of the sheet.

    sheet_row_of turns a row (an even block) into the row number on the sheet. The post goes
    in the top cell and the times ("08:15-10:00", day_and_time_of and end_time_of) in the
    bottom cell; a one-row box gets both in one cell ("Tickets 14:00-14:30"). A bold time
    (box.start_bold, box.end_bold) is written as rich text (CellRichText). The box gets an
    outside border; its cells are not merged.
    """
    _, start_time = day_and_time_of(box.first_block, settings)
    # end_time_of, not day_and_time_of: a shift until the very end of the convention ends at
    # a block after the last day, which day_and_time_of refuses ("06:00" here).
    stop_time = end_time_of(box.block_after_last, settings)

    hyphen = "-"

    if box.start_bold:
        start_time = TextBlock(BOLD, start_time)

    if box.end_bold:
        stop_time = TextBlock(BOLD, stop_time)

    if box.first_row == box.last_row:
        text = [box.post, " ", start_time, hyphen, stop_time]

        sheet.cell(row=sheet_row_of[box.first_row],
                   column=column).value = CellRichText(text)
        sheet.cell(row=sheet_row_of[box.first_row],
                   column=column).border = BORDER_FULL
        return

    # else box_length > 1
    # Top cell
    sheet.cell(row=sheet_row_of[box.first_row],
               column=column).value = CellRichText(box.post)
    sheet.cell(row=sheet_row_of[box.first_row],
               column=column).border = BORDER_TOP

    # Bottom cell
    sheet.cell(row=sheet_row_of[box.last_row],
               column=column).value = CellRichText([start_time, hyphen, stop_time])
    sheet.cell(row=sheet_row_of[box.last_row],
               column=column).border = BORDER_BOTTOM

    # Middle cells
    for middle_row in range(box.first_row + 2, box.last_row, 2):
        sheet.cell(row=sheet_row_of[middle_row],
                   column=column).border = BORDER_MIDDLE

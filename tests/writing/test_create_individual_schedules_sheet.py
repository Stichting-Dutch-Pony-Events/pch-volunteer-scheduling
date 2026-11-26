import openpyxl
import pytest
from openpyxl.cell.cell import Cell
from openpyxl.cell.rich_text import CellRichText, TextBlock

from scheduler.model import Post, Problem, Schedule, Settings, Volunteer, all_blocks
from scheduler.writing.individual_schedules_sheet import GREY, create_individual_schedules_sheet


# Passed explicitly instead of relying on the defaults in model.py. Friday = blocks 0-95,
# Saturday = 96-191, Sunday = 192-287 (block 0 = Friday 06:00, block 32 = Friday 14:00).
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))

ALL_DAYS = all_blocks(RULES)

# The layout of the tab: row 1 = nicknames, row 2 = groups (empty for now), the half-hour
# rows from row 3 on; columns A and B = Day and Time, the first volunteer in column C.
FIRST_ROW = 3
FIRST_VOLUNTEER_COLUMN = 3


def _volunteer(name: str, available_blocks: set[int]) -> Volunteer:
    """A volunteer who can do every post in these tests; only name and availability matter."""
    return Volunteer(name=name,
                     skills={"Tickets": 1, "Infobooth": 1},
                     available_blocks=available_blocks)


def _problem(volunteers: list[Volunteer],
             demand: dict[tuple[str, int], int],
             settings: Settings = RULES) -> Problem:
    """A problem with these volunteers and this demand; the posts are Tickets and Infobooth."""
    return Problem(volunteers=volunteers,
                   posts=[Post("Tickets"), Post("Infobooth")],
                   demand=demand,
                   settings=settings)


def _works(name: str, post: str, first_block: int, block_after_last: int) -> set[tuple]:
    """The assignments for one volunteer at one post, from first_block up to block_after_last.

    Uses the same convention as range(): block_after_last itself is not included.
    """
    assignments = set()
    for block in range(first_block, block_after_last):
        assignments.add((name, post, block))
    return assignments


def _bold_parts(cell: Cell) -> list[str]:
    """The pieces of text in the cell that are bold, in order; [] for a plain text cell.

    A cell with bold parts holds a CellRichText (openpyxl.cell.rich_text): a list of plain
    str pieces and TextBlock pieces; a TextBlock has .text and .font (bold = font.b).
    """
    if not isinstance(cell.value, CellRichText):
        return []

    bold_pieces = []
    for piece in cell.value:
        if isinstance(piece, TextBlock):
            if piece.font.b:  # TextBlock is bold
                bold_pieces.append(piece.text)

    return bold_pieces


def _border_sides(cell: Cell) -> list[str]:
    """The sides of the cell that have a border, in the order top, bottom, left, right.

    A side without a border is either None or a Side with style None (openpyxl allows
    both); any other style (thin, thick, ...) counts.
    """
    sides = set()
    for name, side in [("top", cell.border.top), ("bottom", cell.border.bottom),
                       ("left", cell.border.left), ("right", cell.border.right)]:
        if side is not None and side.style is not None:
            sides.add(name)
    return sides


def _fill_colour(cell: Cell) -> str | None:
    """The fill colour of the cell as "RRGGBB", or None when the cell has no fill.

    openpyxl stores a colour as "AARRGGBB" (e.g. "D9D9D9" becomes "00D9D9D9"), so only the
    last six characters are kept.
    """
    # Every cell has a fill object, also an untouched one: then its fill_type is None.
    if cell.fill.fill_type is None:
        return None
    return cell.fill.fgColor.rgb[-6:]


# The tab

def test_sheet_is_called_individual_schedules():
    """The function adds a tab called "Individual schedules" to the workbook."""
    # Arrange
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36))

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    assert "Individual schedules" in workbook.sheetnames


def test_existing_individual_schedules_sheet_raises_value_error():
    """A workbook that already has an "Individual schedules" tab is an error."""
    # Arrange
    workbook = openpyxl.Workbook()
    workbook.create_sheet("Individual schedules")
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36))

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(ValueError, match="Individual schedules"):
        create_individual_schedules_sheet(workbook, problem, schedule)


def test_header_rows_and_day_time_columns_are_frozen():
    """The nickname and group rows and the Day and Time columns stay in view when scrolling."""
    # Arrange
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36))

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    assert workbook["Individual schedules"].freeze_panes == "C3"


# Header and rows

def test_header_row_has_day_time_and_the_volunteers_in_alphabetical_order():
    """Row 1 holds Day, Time and one nickname per volunteer, sorted by nickname."""
    # Arrange
    # volunteers given as Mock Mane, Testy Hooves, Dummy Dash.
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 3
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS),
                                   _volunteer("Testy Hooves", ALL_DAYS),
                                   _volunteer("Dummy Dash", ALL_DAYS)],
                       demand=demand)
    assignments = (_works("Mock Mane", "Tickets", 32, 36)
                   | _works("Testy Hooves", "Tickets", 32, 36)
                   | _works("Dummy Dash", "Tickets", 32, 36))
    schedule = Schedule(assignments=assignments)

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Individual schedules"]
    headers = []
    for column in range(1, sheet.max_column + 1):
        headers.append(sheet.cell(row=1, column=column).value)
    assert headers == ["Day", "Time", "Dummy Dash", "Mock Mane", "Testy Hooves"]


def test_volunteer_without_shifts_still_gets_a_column():
    """A volunteer who works nowhere still has a column, so nobody silently disappears."""
    # Arrange
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 2
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS),
                                   _volunteer("Testy Hooves", ALL_DAYS),
                                   _volunteer("Dummy Dash", ALL_DAYS)],
                       demand=demand)
    assignments = (_works("Mock Mane", "Tickets", 32, 36)
                   | _works("Testy Hooves", "Tickets", 32, 36))  # No assignments for Dummy Dash
    schedule = Schedule(assignments=assignments)

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Individual schedules"]
    headers = []
    for column in range(1, sheet.max_column + 1):
        headers.append(sheet.cell(row=1, column=column).value)
    assert "Dummy Dash" in headers


def test_each_row_shows_the_day_and_time_of_its_half_hour():
    """From row 3 on, columns A and B hold the day and time of each half-hour row."""
    # Arrange
    # Tickets Friday 14:00-15:00 (blocks 32-35).
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36))

    expected = []
    for time in ["13:30", "14:00", "14:30", "15:00"]:
        expected.append(("Friday", time))

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Individual schedules"]
    result = []
    for row in range(FIRST_ROW, sheet.max_row + 1):
        result.append((sheet.cell(row=row, column=1).value,
                       sheet.cell(row=row, column=2).value))
    assert result == expected


def test_night_rows_show_their_convention_day():
    """A half hour after midnight is shown under the convention day before it."""
    # Arrange
    # Saturday night 01:00 = block 172.
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(172, 176):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 172, 176))

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Individual schedules"]
    result = (sheet.cell(row=FIRST_ROW + 1, column=1).value,
              sheet.cell(row=FIRST_ROW + 1, column=2).value)
    assert result == ("Saturday", "01:00")


# Boxes

def test_post_is_in_the_top_cell_and_the_times_in_the_bottom_cell():
    """A shift shows its post in its first row and its times in its last row, between empty."""
    # Arrange
    # Tickets 08:00-10:00 (blocks 8-15), so the leading zeros are checked too.
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(8, 16):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 8, 16))

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Individual schedules"]
    box_texts = []
    for row in range(4, 8):
        cell_value = sheet.cell(row=row, column=FIRST_VOLUNTEER_COLUMN).value
        if cell_value is not None:
            box_texts.append(str(cell_value))
        else:
            box_texts.append(None)

    assert box_texts == ["Tickets", None, None, "08:00-10:00"]


def test_one_row_box_has_the_post_and_times_in_one_cell():
    """A shift of one half hour shows post and times together in its only cell."""
    # Arrange
    # Tickets 14:00-14:30 (blocks 32-33).
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 34):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 34))

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Individual schedules"]
    box_text = str(sheet.cell(row=FIRST_ROW + 1, column=FIRST_VOLUNTEER_COLUMN).value)

    assert box_text == "Tickets 14:00-14:30"


def test_time_off_the_half_hour_is_bold():
    """A start on :15 or :45 is written in bold; the end on the half hour is not."""
    # Arrange
    # Tickets 14:15-15:00 (blocks 33-35): a box in the rows 14:00 and 14:30.
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(33, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 33, 36))

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    # The times are in the bottom cell, the 14:30 row (row FIRST_ROW is the margin row 13:30).
    sheet = workbook["Individual schedules"]
    times_cell = sheet.cell(row=FIRST_ROW + 2, column=FIRST_VOLUNTEER_COLUMN)

    assert str(times_cell.value) == "14:15-15:00"
    assert _bold_parts(times_cell) == ["14:15"]


def test_times_on_the_half_hour_are_not_bold():
    """A shift that starts and ends on the half hour has no bold text."""
    # Arrange
    # Tickets 14:00-14:30 (blocks 32-33).
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 34):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 34))

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Individual schedules"]
    box_cell = sheet.cell(row=FIRST_ROW + 1, column=FIRST_VOLUNTEER_COLUMN)

    assert _bold_parts(box_cell) == []


def test_pushed_box_starts_one_row_lower_with_its_start_in_bold():
    """After a post switch on :45 the next box starts in the row below, its start time bold."""
    # Arrange
    # Tickets 14:00-14:45 (blocks 32-34), then Infobooth 14:45-16:00 (blocks 35-39).
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 35):
        demand[("Tickets", block)] = 1
    for block in range(35, 40):
        demand[("Infobooth", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=(_works("Mock Mane", "Tickets", 32, 35)
                                     | _works("Mock Mane", "Infobooth", 35, 40)))

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    # Rows: 13:30 (margin), 14:00 and 14:30 (Tickets), 15:00 and 15:30 (Infobooth, pushed
    # down from the 14:30 row where its first block 14:45 falls).
    sheet = workbook["Individual schedules"]
    post_cell = sheet.cell(row=FIRST_ROW + 3, column=FIRST_VOLUNTEER_COLUMN)
    times_cell = sheet.cell(row=FIRST_ROW + 4, column=FIRST_VOLUNTEER_COLUMN)
    assert str(post_cell.value) == "Infobooth"
    assert str(times_cell.value) == "14:45-16:00"
    assert _bold_parts(times_cell) == ["14:45"]


def test_box_has_an_outside_border():
    """The cells of a box have a border on its outside edges and none inside the box."""
    # Arrange
    # Tickets 14:00-15:30 (blocks 32-37): a box of three rows (14:00, 14:30, 15:00).
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 38):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 38))

    # The top cell has no bottom border and the bottom cell no top one: inside the box no
    # lines at all, only on its outside edges.
    expected = [set(["top", "left", "right"]),      # 14:00, the top cell
                set(["left", "right"]),             # 14:30, the middle cell
                set(["left", "right", "bottom"])]   # 15:00, the bottom cell

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    # Row FIRST_ROW is the margin row 13:30, so the box starts one row lower.
    sheet = workbook["Individual schedules"]
    result = []
    for row in range(FIRST_ROW + 1, FIRST_ROW + 4):
        result.append(_border_sides(sheet.cell(row=row, column=FIRST_VOLUNTEER_COLUMN)))
    assert result == expected


def test_one_row_box_has_a_border_on_all_four_sides():
    """A box of one row has a border at the top, bottom, left and right of its cell."""
    # Arrange
    # Tickets 14:00-14:30 (blocks 32-33): a box of one row (14:00).
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 34):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 34))

    expected = set(["top", "left", "right", "bottom"])  # all sides, in the order of _border_sides

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Individual schedules"]
    result = _border_sides(sheet.cell(row=FIRST_ROW + 1, column=FIRST_VOLUNTEER_COLUMN))
    assert result == expected


def test_box_pushed_past_the_end_of_its_day_still_gets_its_row():
    """A box pushed into the first row of the next day gets that row, so no shift is hidden."""
    # Arrange
    # Friday night: Tickets 05:00-05:45 (blocks 92-94), then Infobooth 05:45-06:00 (block 95),
    # the last quarter of Friday. Mock Mane works both.
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(92, 95):
        demand[("Tickets", block)] = 1
    demand[("Infobooth", 95)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 92, 95)
                        | _works("Mock Mane", "Infobooth", 95, 96))

    # The Tickets box fills the rows 05:00 and 05:30, so the Infobooth box is pushed to the
    # next row: block 96 = Saturday 06:00. Saturday has no demand and the margin stays
    # within Friday, so without the box that row would not be on the tab at all.
    expected = (("Saturday", "06:00"), "Infobooth 05:45-06:00")

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    # The last row of the tab. The text has bold times (rich text), so compare it as str.
    sheet = workbook["Individual schedules"]
    last_row = sheet.max_row
    result = ((sheet.cell(row=last_row, column=1).value,
               sheet.cell(row=last_row, column=2).value),
              str(sheet.cell(row=last_row, column=FIRST_VOLUNTEER_COLUMN).value))
    assert result == expected


# Free cells

def test_free_cell_is_white_when_the_volunteer_could_work():
    """A free cell during convention hours of an available volunteer has no fill."""
    # Arrange
    # Tickets 14:00-15:00. Mock Mane works, Testy Hooves (column D, alphabetical) is free
    # but available all weekend.
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS),
                                   _volunteer("Testy Hooves", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36))

    expected = [None, None]  # 14:00 and 14:30: no fill

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    # Only the rows with demand (14:00, 14:30), not the margin rows 13:30 and 15:00.
    sheet = workbook["Individual schedules"]
    result = []
    for row in range(FIRST_ROW + 1, FIRST_ROW + 3):
        result.append(_fill_colour(sheet.cell(row=row, column=FIRST_VOLUNTEER_COLUMN + 1)))
    assert result == expected


def test_free_cell_is_grey_when_the_volunteer_is_not_available():
    """A free cell of a volunteer who is not available then is filled grey."""
    # Arrange
    # Tickets Friday 14:00-15:00. Mock Mane works, Testy Hooves (column D, alphabetical) is
    # only there on Saturday morning (blocks 96-105), so not on Friday.
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS),
                                   _volunteer("Testy Hooves", set(range(96, 106)))],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36))

    expected = [GREY, GREY]  # 14:00 and 14:30

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    # Only the rows with demand (14:00, 14:30), like the white test.
    sheet = workbook["Individual schedules"]
    result = []
    for row in range(FIRST_ROW + 1, FIRST_ROW + 3):
        result.append(_fill_colour(sheet.cell(row=row, column=FIRST_VOLUNTEER_COLUMN + 1)))
    assert result == expected


def test_margin_rows_are_grey():
    """The margin rows have no demand, so they are grey even for someone available all weekend."""
    # Arrange
    # Tickets Friday 14:00-15:00, so the margin rows are 13:30 and 15:00. Mock Mane is
    # available all weekend and works the whole demand.
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(volunteers=[_volunteer("Mock Mane", ALL_DAYS)],
                       demand=demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36))

    expected = [GREY, GREY]  # 13:30 and 15:00

    # Act
    create_individual_schedules_sheet(workbook, problem, schedule)

    # Assert
    # The first row (13:30) and the last row (15:00) of the tab.
    sheet = workbook["Individual schedules"]
    result = [_fill_colour(sheet.cell(row=FIRST_ROW, column=FIRST_VOLUNTEER_COLUMN)),
              _fill_colour(sheet.cell(row=sheet.max_row, column=FIRST_VOLUNTEER_COLUMN))]
    assert result == expected

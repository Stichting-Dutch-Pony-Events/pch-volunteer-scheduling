import openpyxl
import pytest
from openpyxl.cell.cell import Cell

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
             posts: list[Post] = [Post("Tickets"), Post("Infotbooth")],
             settings: Settings = RULES):
    """Returns a problem, with filled in default values."""
    return Problem(volunteers=volunteers,
                   posts=posts,
                   demand=demand,
                   settings=RULES)


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
    raise NotImplementedError


# The tab

def test_sheet_is_called_individual_schedules():
    """The function adds a tab called "Individual schedules" to the workbook."""
    # Arrange



def test_existing_individual_schedules_sheet_raises_value_error():
    """A workbook that already has an "Individual schedules" tab is an error."""
    # Arrange

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    pytest.skip("not written yet")


def test_header_rows_and_day_time_columns_are_frozen():
    """The nickname and group rows and the Day and Time columns stay in view when scrolling."""
    # Arrange

    # Act

    # Assert
    # Idea: freeze_panes == "C3".
    pytest.skip("not written yet")


# Header and rows

def test_header_row_has_day_time_and_the_volunteers_in_alphabetical_order():
    """Row 1 holds Day, Time and one nickname per volunteer, sorted by nickname."""
    # Arrange
    # Idea: volunteers given as Testy Hooves, Mock Mane, Dummy Dash.

    # Act

    # Assert
    # Idea: ["Day", "Time", "Dummy Dash", "Mock Mane", "Testy Hooves"].
    pytest.skip("not written yet")


def test_volunteer_without_shifts_still_gets_a_column():
    """A volunteer who works nowhere still has a column, so nobody silently disappears."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_each_row_shows_the_day_and_time_of_its_half_hour():
    """From row 3 on, columns A and B hold the day and time of each half-hour row."""
    # Arrange
    # Idea: Tickets Friday 14:00-15:00 (blocks 32-35).

    # Act

    # Assert
    # Idea: the demand plus one margin row each side: 13:30, 14:00, 14:30, 15:00.
    pytest.skip("not written yet")


def test_night_rows_show_their_convention_day():
    """A half hour after midnight is shown under the convention day before it."""
    # Arrange
    # Idea: Saturday night 01:00 = block 172.

    # Act

    # Assert
    # Idea: row 4 (after one margin row) = ("Saturday", "01:00").
    pytest.skip("not written yet")


# Boxes

def test_post_is_in_the_top_cell_and_the_times_in_the_bottom_cell():
    """A shift shows its post in its first row and its times in its last row, between empty."""
    # Arrange
    # Idea: Tickets 08:00-10:00 (blocks 8-15), so the leading zeros are checked too.

    # Act

    # Assert
    # Idea: "Tickets", None, None, "08:00-10:00" in the four rows of the box.
    pytest.skip("not written yet")


def test_one_row_box_has_the_post_and_times_in_one_cell():
    """A shift of one half hour shows post and times together in its only cell."""
    # Arrange
    # Idea: Tickets 14:00-14:30 (blocks 32-33).

    # Act

    # Assert
    # Idea: "Tickets 14:00-14:30".
    pytest.skip("not written yet")


def test_time_off_the_half_hour_is_bold():
    """A start on :15 or :45 is written in bold; the end on the half hour is not."""
    # Arrange
    # Idea: Tickets 14:15-15:00 (blocks 33-35).

    # Act

    # Assert
    # Idea: str(cell.value) == "14:15-15:00" and _bold_parts(cell) == ["14:15"].
    pytest.skip("not written yet")


def test_times_on_the_half_hour_are_not_bold():
    """A shift that starts and ends on the half hour has no bold text."""
    # Arrange

    # Act

    # Assert
    # Idea: _bold_parts(cell) == [].
    pytest.skip("not written yet")


def test_pushed_box_starts_one_row_lower_with_its_start_in_bold():
    """After a post switch on :45 the next box starts in the row below, its start time bold."""
    # Arrange
    # Idea: Tickets 14:00-14:45 (32-34), Infobooth 14:45-16:00 (35-39).

    # Act

    # Assert
    # Idea: "Infobooth" in the 15:00 row; the bottom cell "14:45-16:00", bold ["14:45"].
    pytest.skip("not written yet")


def test_box_has_an_outside_border():
    """The cells of a box have a border on its outside edges and none inside the box."""
    # Arrange
    # Idea: a box of three rows, e.g. Tickets 14:00-15:30.

    # Act

    # Assert
    # Idea: cell.border.top.style etc. is None or not. Top cell: top, left, right;
    # middle cell: left, right; bottom cell: bottom, left, right.
    pytest.skip("not written yet")


def test_one_row_box_has_a_border_on_all_four_sides():
    """A box of one row has a border at the top, bottom, left and right of its cell."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_box_pushed_past_the_end_of_its_day_still_gets_its_row():
    """A box pushed into the first row of the next day gets that row, so no shift is hidden."""
    # Arrange
    # Idea: Tickets Friday 05:00-05:45 (blocks 92-94), Infobooth 05:45-06:00 (block 95). The
    # Infobooth box is pushed to row 96 = Saturday 06:00, which has no demand (and the
    # margin stays within Friday).

    # Act

    # Assert
    # Idea: the last row of the tab is ("Saturday", "06:00") and holds
    # "Infobooth 05:45-06:00".
    pytest.skip("not written yet")


# Free cells

def test_free_cell_is_white_when_the_volunteer_could_work():
    """A free cell during convention hours of an available volunteer has no fill."""
    # Arrange
    # Idea: two volunteers, only one of them works.

    # Act

    # Assert
    # Idea: cell.fill.fill_type is None.
    pytest.skip("not written yet")


def test_free_cell_is_grey_when_the_volunteer_is_not_available():
    """A free cell of a volunteer who is not available then is filled grey."""
    # Arrange

    # Act

    # Assert
    # Idea: cell.fill.fill_type == "solid" and cell.fill.fgColor.rgb ends with GREY.
    pytest.skip("not written yet")


def test_margin_rows_are_grey():
    """The margin rows have no demand, so they are grey even for someone available all weekend."""
    # Arrange
    # Idea: a volunteer with ALL_DAYS who doesn't work.

    # Act

    # Assert
    pytest.skip("not written yet")

import openpyxl
import pytest

from scheduler.model import Post, Problem, Schedule, Settings
from scheduler.output import create_schedule_sheet


RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))


def _problem(post_names: list[str], demand: dict[tuple[str, int], int]) -> Problem:
    """A problem with these posts and this demand; volunteers don't matter for the output."""
    posts = []
    for name in post_names:
        posts.append(Post(name))
    return Problem(volunteers=[], posts=posts, demand=demand, settings=RULES)


def _works(name: str, post: str, first_block: int, block_after_last: int) -> set[tuple]:
    """The assignments for one volunteer at one post, from first_block up to block_after_last.

    Uses the same convention as range(): block_after_last itself is not included.
    """
    assignments = set()
    for block in range(first_block, block_after_last):
        assignments.add((name, post, block))
    return assignments


def test_sheet_is_called_schedule():
    """The function adds a tab called "Schedule" to the workbook."""
    # Arrange
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36))

    # Act
    create_schedule_sheet(workbook, problem, schedule)

    # Assert
    assert "Schedule" in workbook.sheetnames


def test_header_row_has_day_time_and_one_column_per_slot():
    """Row 1 holds Day, Time and a header per post slot, numbered only if a post has several."""
    # Arrange
    workbook = openpyxl.Workbook()
    # Friday 14:00-15:00: Tickets needs 2, Infobooth 1.
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 2
        demand[("Infobooth", block)] = 1
    problem = _problem(["Tickets", "Infobooth"], demand)
    # Who works doesn't matter for the headers.
    schedule = Schedule(assignments=set())

    # Act
    create_schedule_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Schedule"]
    headers = []
    for column in range(1, 6):
        headers.append(sheet.cell(row=1, column=column).value)
    assert headers == ["Day", "Time", "Tickets 1", "Tickets 2", "Infobooth"]


def test_each_row_shows_the_day_and_time_of_its_block():
    """From row 2 on, columns A and B hold the day and the time (as text) of each block."""
    # Arrange
    workbook = openpyxl.Workbook()
    # Friday 14:00-15:00
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36))

    expected_result = []
    for time in ["14:00", "14:15", "14:30", "14:45"]:
        expected_result.append(("Friday", time))

    # Act
    create_schedule_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Schedule"]
    result = []
    for row in range(2, 6):
        result.append((sheet.cell(row=row, column=1).value, sheet.cell(row=row, column=2).value))
    assert result == expected_result


def test_night_rows_show_their_convention_day():
    """A block after midnight is shown under the convention day before it."""
    # Arrange
    workbook = openpyxl.Workbook()
    # Saturday night 01:00 (block 172), on the calendar early Sunday morning.
    demand = {("Tickets", 172): 1}
    problem = _problem(["Tickets"], demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 172, 173))

    # Act
    create_schedule_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Schedule"]
    result = (sheet.cell(row=2, column=1).value, sheet.cell(row=2, column=2).value)
    assert result == ("Saturday", "01:00")


def test_nickname_is_in_the_column_of_their_slot():
    """Each volunteer's nickname appears in the column of their slot, in every row they work."""
    # Arrange
    workbook = openpyxl.Workbook()
    # Friday 14:00-15:00, Tickets needs 2.
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 2
    problem = _problem(["Tickets"], demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36)
                        | _works("Testy Hooves", "Tickets", 32, 36))

    expected_result = []
    for row in range(2, 6):
        expected_result.append(("Mock Mane", "Testy Hooves"))

    # Act
    create_schedule_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Schedule"]
    result = []
    for row in range(2, 6):
        result.append((sheet.cell(row=row, column=3).value, sheet.cell(row=row, column=4).value))
    assert result == expected_result


def test_cell_without_anyone_is_empty():
    """A slot that nobody sits in during a block gives an empty cell."""
    # Arrange
    workbook = openpyxl.Workbook()
    # Friday 14:00-15:00: Tickets needs 2 in the first half hour, then 1.
    demand = {}
    for block in range(32, 34):
        demand[("Tickets", block)] = 2
    for block in range(34, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36)
                        | _works("Testy Hooves", "Tickets", 32, 34))

    expected_result = []
    for row in range(2, 4):
        expected_result.append("Testy Hooves")
    for row in range(4, 6):
        expected_result.append(None)

    # Act
    create_schedule_sheet(workbook, problem, schedule)

    # Assert
    sheet = workbook["Schedule"]
    result = []
    for row in range(2, 6):
        result.append(sheet.cell(row=row, column=4).value)
    assert result == expected_result


def test_header_row_and_day_time_columns_are_frozen():
    """The header row and the Day and Time columns stay in view when scrolling."""
    # Arrange
    workbook = openpyxl.Workbook()
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36))

    # Act
    create_schedule_sheet(workbook, problem, schedule)

    # Assert
    # "C2" is the first cell that scrolls: everything above and to the left of it is frozen.
    assert workbook["Schedule"].freeze_panes == "C2"


def test_existing_schedule_sheet_raises_value_error():
    """A workbook that already has a "Schedule" tab is an error, e.g. when called twice."""
    # Arrange
    workbook = openpyxl.Workbook()
    workbook.create_sheet("Schedule")
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 32, 36))

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(ValueError, match="Schedule"):
        create_schedule_sheet(workbook, problem, schedule)

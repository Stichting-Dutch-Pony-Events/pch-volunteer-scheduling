from pathlib import Path

import openpyxl
import pytest

from scheduler.model import Post, Problem, Schedule, Settings
from scheduler.writing.output import write_output
from scheduler.solving.solver import solve
from scheduler.reading.workbook import read_problem


TEST_WORKBOOK = Path(__file__).parent.parent / "data" / "test_input.xlsx"

RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))


def _small_problem_and_schedule() -> tuple[Problem, Schedule]:
    """Tickets needs 1 person on Friday 14:00-15:00 (blocks 32-35), and Mock Mane does it."""
    demand = {}
    assignments = set()
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
        assignments.add(("Mock Mane", "Tickets", block))
    problem = Problem(volunteers=[], posts=[Post("Tickets")], demand=demand, settings=RULES)
    return problem, Schedule(assignments=assignments)


def test_writes_a_file_at_the_given_path(tmp_path):
    """After writing, the output file exists."""
    # Arrange
    problem, schedule = _small_problem_and_schedule()
    path = tmp_path / "output.xlsx"

    # Act
    write_output(problem, schedule, path)

    # Assert
    assert path.exists()


def test_file_has_only_the_schedule_tab(tmp_path):
    """The written workbook has just the "Schedule" tab, without openpyxl's default "Sheet"."""
    # Arrange
    problem, schedule = _small_problem_and_schedule()
    path = tmp_path / "output.xlsx"

    # Act
    write_output(problem, schedule, path)

    # Assert
    workbook = openpyxl.load_workbook(path)
    assert workbook.sheetnames == ["Schedule"]


def test_written_file_contains_the_schedule(tmp_path):
    """The header and the nicknames can be read back from the saved file."""
    # Arrange
    problem, schedule = _small_problem_and_schedule()
    path = tmp_path / "output.xlsx"

    expected_result = [("Day", "Time", "Tickets")]
    for time in ["14:00", "14:15", "14:30", "14:45"]:
        expected_result.append(("Friday", time, "Mock Mane"))

    # Act
    write_output(problem, schedule, path)

    # Assert
    sheet = openpyxl.load_workbook(path)["Schedule"]
    result = []
    for row in range(1, 6):
        result.append((sheet.cell(row=row, column=1).value,
                       sheet.cell(row=row, column=2).value,
                       sheet.cell(row=row, column=3).value))
    assert result == expected_result


def test_existing_file_is_overwritten(tmp_path):
    """An existing file at the path is replaced by the new output."""
    # Arrange
    problem, schedule = _small_problem_and_schedule()
    path = tmp_path / "output.xlsx"
    old_workbook = openpyxl.Workbook()
    old_workbook.active.title = "Old"
    old_workbook.save(path)

    # Act
    write_output(problem, schedule, path)

    # Assert
    workbook = openpyxl.load_workbook(path)
    assert workbook.sheetnames == ["Schedule"]


@pytest.mark.parametrize("file_name", ["output.ods", "output.xls", "output"])
def test_path_that_is_not_xlsx_raises_value_error(tmp_path, file_name):
    """Only .xlsx is written for now; any other extension is an error mentioning .xlsx."""
    # Arrange
    problem, schedule = _small_problem_and_schedule()
    path = tmp_path / file_name

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(ValueError, match=r"\.xlsx"):
        write_output(problem, schedule, path)


def test_test_workbook_goes_all_the_way_to_an_output_file(tmp_path):
    """Read the test workbook, solve it and write it: every person needed fills one cell."""
    # Arrange
    problem = read_problem(TEST_WORKBOOK)
    schedule = solve(problem)
    path = tmp_path / "output.xlsx"

    # Demand is met exactly, so the number of filled-in name cells is the total demand.
    expected_result = 0
    for needed in problem.demand.values():
        expected_result = expected_result + needed

    # Act
    write_output(problem, schedule, path)

    # Assert
    sheet = openpyxl.load_workbook(path)["Schedule"]
    result = 0
    for row in range(2, sheet.max_row + 1):          # row 1 is the header
        for column in range(3, sheet.max_column + 1):  # columns A and B are Day and Time
            if sheet.cell(row=row, column=column).value is not None:
                result = result + 1
    assert result == expected_result

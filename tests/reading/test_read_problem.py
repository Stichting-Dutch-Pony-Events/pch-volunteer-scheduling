from pathlib import Path

import openpyxl
import pytest
from openpyxl.workbook.workbook import Workbook

from scheduler.errors import WorkbookError
from scheduler.model import Post, Problem, Settings, Volunteer
from scheduler.reading.workbook import read_problem
from scheduler.solving.solver import solve

# The reader switches every soft rule on; update this when a soft rule is added.
ALL_SOFT_RULES = frozenset({"round_times", "skill_score"})

# The made-up workbook in tests/data, used by the end-to-end tests.
TEST_WORKBOOK = Path(__file__).parent.parent / "data" / "test_input.xlsx"

# What _good_workbook() should give. Friday = blocks 0-95, Saturday = 96-191.
GOOD_PROBLEM = Problem(
    volunteers=[
        Volunteer(name="Mock Mane", skills={"Tickets": 3},
                  available_blocks=set(range(0, 96)),         # all of Friday
                  max_minutes_per_day=480, max_minutes_total=960),   # the defaults
        Volunteer(name="Testy Hooves", skills={"Tickets": 1, "Infobooth": 3},
                  available_blocks=set(range(112, 128)),      # Saturday 10:00-14:00
                  max_minutes_per_day=480, max_minutes_total=960),
    ],
    posts=[Post(name="Tickets"), Post(name="Infobooth")],
    demand={("Tickets", 32): 1, ("Tickets", 33): 1,           # Friday 14:00-15:00
            ("Tickets", 34): 1, ("Tickets", 35): 1,
            ("Infobooth", 112): 1, ("Infobooth", 113): 1,     # Saturday 10:00-11:00
            ("Infobooth", 114): 1, ("Infobooth", 115): 1},
    settings=Settings(min_stretch_minutes=60, max_stretch_minutes=180,
                      min_break_minutes=30, days=("Friday", "Saturday"),
                      default_max_minutes_per_day=480, default_max_minutes_total=960,
                      soft_rules=ALL_SOFT_RULES))


def _add_sheet(workbook: Workbook, title: str, rows: list[tuple]) -> None:
    """Add a tab with this title to the workbook: the first row is the header."""
    sheet = workbook.create_sheet(title)
    for row in rows:
        sheet.append(row)


def _good_workbook() -> Workbook:
    """A small, complete and correct input workbook in memory (see GOOD_PROBLEM)."""
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)   # a new workbook starts with a tab "Sheet"
    _add_sheet(workbook, "Settings", [
        ("Setting", "Value"),
        ("Workbook format version", 1),
        ("Time step", 15),
        ("Day boundary", "06:00"),
        ("Days", "Friday, Saturday"),
        ("Minimum work stretch", 60),
        ("Maximum work stretch", 180),
        ("Minimum break", 30),
        ("Default maximum hours per day", 8),
        ("Default maximum hours total", 16)])
    _add_sheet(workbook, "Volunteers", [
        ("Nickname", "Team", "Friday", "Saturday", "Max hours per day", "Max hours total"),
        ("Mock Mane", "Ticketing", "yes", "no"),        # empty limits: the defaults
        ("Testy Hooves", "Infobooth", "no", "10:00-14:00")])
    _add_sheet(workbook, "Posts", [
        ("Post",),
        ("Tickets",),
        ("Infobooth",)])
    _add_sheet(workbook, "Skills", [
        ("Nickname", "Team", "Tickets", "Infobooth"),
        ("Mock Mane", "Ticketing", 3, None),
        ("Testy Hooves", "Infobooth", 1, 3)])
    _add_sheet(workbook, "Demand", [
        ("Day", "Time", "Tickets", "Infobooth"),
        ("Friday", "14:00", 1, None),
        ("Friday", "14:15", 1, None),
        ("Friday", "14:30", 1, None),
        ("Friday", "14:45", 1, None),
        ("Saturday", "10:00", None, 1),
        ("Saturday", "10:15", None, 1),
        ("Saturday", "10:30", None, 1),
        ("Saturday", "10:45", None, 1)])
    return workbook


def _save(workbook: Workbook, folder: Path, file_name: str = "input.xlsx") -> Path:
    """Save the workbook in folder (a test's tmp_path) and return the path of the file."""
    path = folder / file_name
    workbook.save(path)
    return path


def test_good_workbook_gives_the_matching_problem(tmp_path):
    """Volunteers get their skills and availability, together with posts, demand, settings."""
    # Arrange
    path = _save(_good_workbook(), tmp_path)

    # Act
    problem = read_problem(path)

    # Assert
    assert problem == GOOD_PROBLEM


def test_known_tabs_the_scheduler_does_not_use_yet_are_accepted(tmp_path):
    """The real workbook also has ReadMe, Events, Wishes and Fixed: they are no problem."""
    # Arrange
    workbook = _good_workbook()
    for title in ["ReadMe", "Events", "Wishes", "Fixed"]:
        workbook.create_sheet(title)
    path = _save(workbook, tmp_path)

    # Act
    problem = read_problem(path)

    # Assert
    assert problem == GOOD_PROBLEM


def test_unknown_tab_raises_workbook_error(tmp_path):
    """A tab the scheduler doesn't know, e.g. a typo or a scratch tab, is an error naming it."""
    # Arrange
    workbook = _good_workbook()
    workbook.create_sheet("Sheet2")
    path = _save(workbook, tmp_path)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Sheet2"):
        read_problem(path)


def test_file_that_is_not_xlsx_raises_workbook_error(tmp_path):
    """Only .xlsx files can be read; anything else says to save the workbook as .xlsx."""
    # Arrange
    path = _save(_good_workbook(), tmp_path, file_name="input.ods")

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="xlsx"):
        read_problem(path)


def test_file_that_does_not_exist_raises_workbook_error(tmp_path):
    """A path to a file that isn't there is an error naming the file."""
    # Arrange
    path = tmp_path / "input.xlsx"   # never saved

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="input.xlsx"):
        read_problem(path)


def test_file_that_is_not_a_real_workbook_raises_workbook_error(tmp_path):
    """A damaged file, or another file renamed to .xlsx, is an error naming the file."""
    # Arrange
    path = tmp_path / "input.xlsx"
    path.write_bytes(b"this is not a workbook")

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="input.xlsx"):
        read_problem(path)


@pytest.mark.parametrize("tab", ["Settings", "Volunteers", "Posts", "Skills", "Demand"])
def test_missing_tab_raises_workbook_error(tmp_path, tab):
    """Each required tab must be there; a missing one is an error naming it."""
    # Arrange
    workbook = _good_workbook()
    workbook.remove(workbook[tab])
    path = _save(workbook, tmp_path)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match=tab):
        read_problem(path)


def test_volunteer_without_a_skills_row_raises_workbook_error(tmp_path):
    """Every volunteer needs a row on the Skills tab."""
    # Arrange
    workbook = _good_workbook()
    workbook["Skills"].delete_rows(3)   # row 3 is Testy Hooves
    path = _save(workbook, tmp_path)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Skills.*Testy Hooves"):
        read_problem(path)


def test_name_on_skills_that_is_not_a_volunteer_raises_workbook_error(tmp_path):
    """A row on the Skills tab for someone who is not on the Volunteers tab is an error."""
    # Arrange
    workbook = _good_workbook()
    workbook["Skills"].append(("Dummy Dash", "Ticketing", 2, None))
    path = _save(workbook, tmp_path)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Dummy Dash"):
        read_problem(path)


def test_skills_column_that_is_not_a_post_raises_workbook_error(tmp_path):
    """A Skills column whose header is not on the Posts tab (e.g. a typo) is an error."""
    # Arrange
    workbook = _good_workbook()
    workbook["Skills"]["D1"] = "Infobooht"   # column D is Infobooth
    path = _save(workbook, tmp_path)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Skills.*Infobooht"):
        read_problem(path)


def test_post_without_a_skills_column_raises_workbook_error(tmp_path):
    """Every post on the Posts tab needs a column on the Skills tab."""
    # Arrange
    workbook = _good_workbook()
    workbook["Skills"].delete_cols(4)   # column 4 (D) is Infobooth
    path = _save(workbook, tmp_path)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Skills.*Infobooth"):
        read_problem(path)


def test_demand_column_that_is_not_a_post_raises_workbook_error(tmp_path):
    """A Demand column whose header is not on the Posts tab (e.g. a typo) is an error."""
    # Arrange
    workbook = _good_workbook()
    workbook["Demand"]["D1"] = "Infobooht"   # column D is Infobooth
    path = _save(workbook, tmp_path)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Demand.*Infobooht"):
        read_problem(path)


def test_post_without_a_demand_column_raises_workbook_error(tmp_path):
    """Every post on the Posts tab needs a column on the Demand tab."""
    # Arrange
    workbook = _good_workbook()
    workbook["Demand"].delete_cols(4)   # column 4 (D) is Infobooth
    path = _save(workbook, tmp_path)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Demand.*Infobooth"):
        read_problem(path)


def test_the_test_workbook_can_be_read():
    """The made-up workbook in tests/data reads without errors (spot checks)."""
    # Arrange
    # (Nothing to arrange: the test workbook is TEST_WORKBOOK.)

    # Act
    problem = read_problem(TEST_WORKBOOK)

    # Assert
    assert len(problem.volunteers) == 5
    assert problem.posts == [Post(name="Tickets"), Post(name="Infobooth"),
                             Post(name="Security - Downstairs")]
    assert problem.settings.days == ("Friday", "Saturday", "Sunday")


def test_the_test_workbook_gives_a_schedule():
    """From workbook to schedule: the whole chain runs and the solver finds a schedule."""
    # Arrange
    problem = read_problem(TEST_WORKBOOK)

    # Act
    schedule = solve(problem)

    # Assert
    assert len(schedule.assignments) > 0


def test_read_problem_gives_each_volunteer_their_hour_limits():
    """In the test workbook, Testy Hooves has their own limits (4 per day, none in total)."""
    # Arrange
    # (Nothing to arrange: the test workbook is TEST_WORKBOOK.)

    # Act
    problem = read_problem(TEST_WORKBOOK)

    # Assert
    volunteers = {}
    for volunteer in problem.volunteers:
        volunteers[volunteer.name] = volunteer
    assert volunteers["Testy Hooves"].max_minutes_per_day == 240    # 4 hours
    assert volunteers["Testy Hooves"].max_minutes_total is None     # "none" = no limit
    assert volunteers["Mock Mane"].max_minutes_per_day == 480       # empty: the defaults
    assert volunteers["Mock Mane"].max_minutes_total == 960         # (8 and 16 hours)

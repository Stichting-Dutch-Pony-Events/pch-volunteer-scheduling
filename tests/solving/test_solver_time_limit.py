import pytest
from ortools.sat.python import cp_model

from scheduler.errors import NoScheduleFound, TimeLimitReached
from scheduler.model import Volunteer, Post, Problem, Settings, all_blocks
from scheduler.solving.solver import solve, make_solver, raise_if_no_schedule


RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))

ALL_DAYS = all_blocks(RULES)


def test_solver_gets_the_time_limit_in_seconds():
    """A time limit of 600 seconds is set as CP-SAT's maximum time."""
    # Arrange
    # Nothing to set up: the time limit is the only input.

    # Act
    solver = make_solver(time_limit_seconds=600)

    # Assert
    assert solver.parameters.max_time_in_seconds == 600


def test_without_a_time_limit_the_solver_keeps_its_default():
    """Without a time limit, CP-SAT's maximum time stays as on a fresh solver."""
    # Arrange
    # A solver straight from OR-Tools shows the default, whatever that value is.
    fresh_solver = cp_model.CpSolver()

    # Act
    solver = make_solver(time_limit_seconds=None)

    # Assert
    assert solver.parameters.max_time_in_seconds == fresh_solver.parameters.max_time_in_seconds


def test_status_unknown_raises_time_limit_reached():
    """CP-SAT stopping before it found anything (UNKNOWN) raises TimeLimitReached."""
    # Arrange
    # Nothing to set up: the statuses are plain numbers in cp_model.

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(TimeLimitReached):
        raise_if_no_schedule(status=cp_model.UNKNOWN, time_limit_seconds=600)


def test_status_infeasible_raises_no_schedule_found():
    """CP-SAT proving there is no schedule (INFEASIBLE) raises NoScheduleFound."""
    # Arrange
    # Nothing to set up: the statuses are plain numbers in cp_model.

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        raise_if_no_schedule(status=cp_model.INFEASIBLE, time_limit_seconds=600)


@pytest.mark.parametrize("status", [cp_model.OPTIMAL, cp_model.FEASIBLE],
                         ids=["optimal", "feasible"])
def test_found_schedule_status_raises_nothing(status):
    """OPTIMAL and FEASIBLE mean a schedule was found: nothing is raised."""
    # Arrange
    # Nothing to set up: the status comes from parametrize.

    # Act
    raise_if_no_schedule(status=status, time_limit_seconds=600)

    # Assert
    # Nothing to check: the test fails if the call above raises.


def test_time_limit_reached_message_names_the_limit():
    """The message says how long the time limit was, in minutes."""
    # Arrange
    # Nothing to set up: 600 seconds should show as 10 minutes.

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(TimeLimitReached, match="10 minutes"):
        raise_if_no_schedule(status=cp_model.UNKNOWN, time_limit_seconds=600)


def test_time_limit_reached_is_not_a_kind_of_no_schedule_found():
    """After a timeout a schedule may still exist, so it is no NoScheduleFound."""
    # Arrange
    # Nothing to set up: this checks how the two error classes relate.

    # Act
    result = issubclass(TimeLimitReached, NoScheduleFound)

    # Assert
    assert result is False


def test_solve_with_a_time_limit_still_finds_a_schedule():
    """A small problem solved with a time limit still gives its schedule."""
    # Arrange
    # Only Mock Mane, Tickets needs one person in blocks 0-3 (one hour): one possible schedule.
    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS)],
                      posts=[Post(name="Tickets")],
                      demand={("Tickets", 0): 1, ("Tickets", 1): 1,
                              ("Tickets", 2): 1, ("Tickets", 3): 1},
                      settings=RULES)

    expected = set()
    for block in range(0, 4):
        expected.add(("Mock Mane", "Tickets", block))

    # Act
    schedule = solve(problem=problem, time_limit_seconds=60)

    # Assert
    assert schedule.assignments == expected

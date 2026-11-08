import pytest

from scheduler.checks import check_problem
from scheduler.errors import NoScheduleFound, NotEnoughQualified, NotEnoughVolunteers
from scheduler.model import Volunteer, Post, Problem, Settings, all_blocks, block_of
from scheduler.solver import solve


RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))

ALL_DAYS = all_blocks(RULES)
SATURDAY = set(range(96, 192))


def test_post_needing_more_people_than_qualified_raises_not_enough_qualified():
    """A post that needs more people than are qualified raises NotEnoughQualified."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    problem = Problem(volunteers=volunteers,
                      posts=[Post(name="Tickets"), Post(name="Infobooth")],
                      demand={("Tickets", 0): 2},
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughQualified):
        check_problem(problem)


def test_not_enough_qualified_message_names_the_post_day_and_time():
    """The message says which post, on which day and at what time."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    problem = Problem(volunteers=volunteers,
                      posts=[Post(name="Tickets"), Post(name="Infobooth")],
                      demand={("Tickets", 0): 2},
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughQualified, match="Tickets.*Friday.*06:00"):
        check_problem(problem)


def test_not_enough_qualified_message_lists_who_is_qualified_and_available():
    """The message names the volunteers who are qualified and available then."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=SATURDAY),
                  Volunteer(name="Dummy Dash", skills={"Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    problem = Problem(volunteers=volunteers,
                      posts=[Post(name="Tickets"), Post(name="Infobooth")],
                      demand={("Tickets", 0): 2},
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughQualified, match=r"qualified and available \(Mock Mane\)"):
        check_problem(problem)


def test_qualified_but_unavailable_volunteers_do_not_count_and_are_listed_separately():
    """Qualified volunteers who are not there then don't count, and are named separately."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=SATURDAY),
                  Volunteer(name="Dummy Dash", skills={"Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    problem = Problem(volunteers=volunteers,
                      posts=[Post(name="Tickets"), Post(name="Infobooth")],
                      demand={("Tickets", 0): 2},
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughQualified, match=r"qualified but not available: Testy Hooves"):
        check_problem(problem)


def test_consecutive_blocks_with_the_same_shortage_become_one_time_range():
    """Several quarter-hours in a row with the same shortage make one line with a range."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=SATURDAY),
                  Volunteer(name="Dummy Dash", skills={"Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 2

    problem = Problem(volunteers=volunteers,
                      posts=[Post(name="Tickets"), Post(name="Infobooth")],
                      demand=demand,
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughQualified, match="06:00-07:00"):
        check_problem(problem)


def test_every_shortage_is_listed_not_just_the_first():
    """Shortages at two time ranges both appear in the message."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=SATURDAY),
                  Volunteer(name="Dummy Dash", skills={"Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 4):      # 06:00-07:00
        demand[("Tickets", block)] = 2
    for block in range(8, 12):     # 08:00-09:00
        demand[("Tickets", block)] = 2

    problem = Problem(volunteers=volunteers,
                      posts=[Post(name="Tickets"), Post(name="Infobooth")],
                      demand=demand,
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughQualified, match="(?s)06:00-07:00.*08:00-09:00"):
        check_problem(problem)


def test_posts_together_needing_more_people_than_available_raise_not_enough_volunteers():
    """Two posts that each have enough qualified people, but not both at once, raise."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1, "Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    problem = Problem(volunteers=volunteers,
                      posts=[Post(name="Tickets"), Post(name="Infobooth")],
                      demand={("Tickets", 0): 2, ("Infobooth", 0): 1},
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughVolunteers):
        check_problem(problem)


@pytest.mark.parametrize("error", [NotEnoughQualified, NotEnoughVolunteers])
def test_both_check_errors_are_a_kind_of_no_schedule_found(error):
    """Code that catches NoScheduleFound also catches the errors from the checks."""
    # Arrange
    # Nothing to set up: the error class comes from parametrize

    # Act
    result = issubclass(error, NoScheduleFound)

    # Assert
    assert result


def test_a_conflict_between_rules_still_raises_plain_no_schedule_found():
    """When no check finds a cause, solve() raises NoScheduleFound itself, not a child."""
    # Arrange
    # Lets go for a classic maximum stretch scheduling issue.
    demand = {}
    for block in range(0, 16):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS)],
                      posts=[Post(name="Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    with pytest.raises(NoScheduleFound) as caught:
        solve(problem)

    # Assert
    assert type(caught.value) is NoScheduleFound

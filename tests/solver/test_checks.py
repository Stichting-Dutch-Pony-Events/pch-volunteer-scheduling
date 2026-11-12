import pytest

from scheduler import checks
from scheduler.checks import check_problem
from scheduler.errors import NoScheduleFound, NotEnoughHours, NotEnoughQualified
from scheduler.errors import NotEnoughVolunteers
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


def test_different_shortages_on_consecutive_blocks_give_separate_lines():
    """Consecutive blocks with a different shortage are not merged into one time range."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 2):      # 06:00-06:30
        demand[("Tickets", block)] = 3
    for block in range(2, 4):      # 06:30-07:00
        demand[("Tickets", block)] = 2

    problem = Problem(volunteers=volunteers,
                      posts=[Post(name="Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughQualified,
                       match="(?s)06:00-06:30: needs 3.*06:30-07:00: needs 2"):
        check_problem(problem)


def test_message_stops_after_the_maximum_number_of_lines_and_counts_the_rest(monkeypatch):
    """With more shortages than the maximum, the first ones are listed and the rest counted."""
    # Arrange
    monkeypatch.setattr(checks, "MAX_LINES", 10)

    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    # 12 separate shortages: Tickets needs 2 every other quarter-hour, 06:00 to 11:30.
    demand = {}
    for block in range(0, 24, 2):
        demand[("Tickets", block)] = 2

    problem = Problem(volunteers=volunteers,
                      posts=[Post(name="Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    with pytest.raises(NotEnoughQualified) as caught:
        check_problem(problem)
    message = str(caught.value)

    # Assert
    assert "and 2 more" in message
    assert "11:00-11:15" not in message  # the 11th shortage is only counted


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


@pytest.mark.parametrize("error", [NotEnoughQualified, NotEnoughVolunteers, NotEnoughHours])
def test_every_check_error_is_a_kind_of_no_schedule_found(error):
    """Code that catches NoScheduleFound also catches the errors from the checks."""
    # Arrange
    # Nothing to set up: the error class comes from parametrize

    # Act
    result = issubclass(error, NoScheduleFound)

    # Assert
    assert result


def test_solve_runs_the_checks_and_raises_not_enough_qualified():
    """solve() runs the checks first, so a shortage gives NotEnoughQualified."""
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
        solve(problem)


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


# --- Hours ---

def test_post_needing_more_hours_than_its_qualified_volunteers_can_work_raises_not_enough_hours():
    """A post needing more hours than its qualified volunteers' total limits raises."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_total=120),
                  Volunteer(name="Testy Hooves", skills={"Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 8):  # for 2 hours on Friday
        demand[("Tickets", block)] = 1
    for block in range(96, 104):  # for 2 hours on Saturday
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets"), Post("Infobooth")],
                      demand=demand,
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughHours, match="Tickets.*over all days"):
        check_problem(problem)


def test_post_needing_exactly_the_hours_its_qualified_volunteers_can_work_is_fine():
    """A post needing exactly what its qualified volunteers can work in total raises nothing."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_total=240),
                  Volunteer(name="Testy Hooves", skills={"Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 8):  # for 2 hours on Friday
        demand[("Tickets", block)] = 1
    for block in range(96, 104):  # for 2 hours on Saturday
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets"), Post("Infobooth")],
                      demand=demand,
                      settings=RULES)

    # Act
    check_problem(problem)

    # Assert
    # (Nothing to assert: the test passes as long as check_problem raises nothing)


def test_post_short_of_hours_on_one_day_raises_not_enough_hours():
    """A post needing more hours on one day than its volunteers' daily limits raises."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_per_day=120),
                  Volunteer(name="Testy Hooves", skills={"Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 12):  # for 3 hours on Friday
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets"), Post("Infobooth")],
                      demand=demand,
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughHours, match="Tickets.*Friday"):
        check_problem(problem)


def test_post_needing_exactly_the_hours_its_qualified_volunteers_can_work_that_day_is_fine():
    """A post needing exactly what its volunteers can work that day raises nothing."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_per_day=180),
                  Volunteer(name="Testy Hooves", skills={"Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 12):  # for 3 hours on Friday
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets"), Post("Infobooth")],
                      demand=demand,
                      settings=RULES)

    # Act
    check_problem(problem)

    # Assert
    # (Nothing to assert: the test passes as long as check_problem raises nothing)


# Tests 5-8: two posts, Mock Mane and Testy Hooves both qualified for both. Each post fits
# on its own, only both posts together are short ("All posts, ...").

def test_posts_together_needing_more_hours_than_all_volunteers_can_work_raises_not_enough_hours():
    """Two posts that each fit, but together need more hours than everyone can work, raise."""
    # Arrange
    # 1 hour each in total: 2 hours together. Each post needs 2 hours (fits), both need 4.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_total=60),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1, "Infobooth": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_total=60)]

    demand = {}
    for block in range(0, 8):  # Tickets: 2 hours on Friday
        demand[("Tickets", block)] = 1
    for block in range(96, 104):  # Infobooth: 2 hours on Saturday
        demand[("Infobooth", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets"), Post("Infobooth")],
                      demand=demand,
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughHours, match="All posts.*over all days"):
        check_problem(problem)


def test_posts_together_needing_exactly_the_hours_all_volunteers_can_work_is_fine():
    """Two posts that together need exactly what everyone can work raise nothing."""
    # Arrange
    # 2 hours each in total: 4 hours together, exactly what both posts need.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_total=120),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1, "Infobooth": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_total=120)]

    demand = {}
    for block in range(0, 8):  # Tickets: 2 hours on Friday
        demand[("Tickets", block)] = 1
    for block in range(96, 104):  # Infobooth: 2 hours on Saturday
        demand[("Infobooth", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets"), Post("Infobooth")],
                      demand=demand,
                      settings=RULES)

    # Act
    check_problem(problem)

    # Assert
    # (Nothing to assert: the test passes as long as check_problem raises nothing)


def test_posts_together_short_of_hours_on_one_day_raise_not_enough_hours():
    """Two posts that each fit, but together need too many hours on one day, raise."""
    # Arrange
    # 1 hour each per day: 2 hours together on Friday, while both posts need 4 that day.
    # Over all days they can work 3 days * 2 hours = 6 hours, so only Friday is short.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_per_day=60),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1, "Infobooth": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_per_day=60)]

    demand = {}
    for block in range(0, 8):  # Tickets: 2 hours on Friday, 06:00-08:00
        demand[("Tickets", block)] = 1
    for block in range(8, 16):  # Infobooth: 2 hours on Friday, 08:00-10:00
        demand[("Infobooth", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets"), Post("Infobooth")],
                      demand=demand,
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughHours, match="All posts.*Friday"):
        check_problem(problem)


def test_posts_together_needing_exactly_the_hours_all_volunteers_can_work_that_day_is_fine():
    """Two posts that together need exactly what everyone can work that day raise nothing."""
    # Arrange
    # 2 hours each per day: 4 hours together on Friday, exactly what both posts need.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_per_day=120),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1, "Infobooth": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_per_day=120)]

    demand = {}
    for block in range(0, 8):  # Tickets: 2 hours on Friday, 06:00-08:00
        demand[("Tickets", block)] = 1
    for block in range(8, 16):  # Infobooth: 2 hours on Friday, 08:00-10:00
        demand[("Infobooth", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets"), Post("Infobooth")],
                      demand=demand,
                      settings=RULES)

    # Act
    check_problem(problem)

    # Assert
    # (Nothing to assert: the test passes as long as check_problem raises nothing)


def test_volunteer_counts_for_at_most_the_hours_they_are_available():
    """A volunteer without limits who is only there for 2 hours counts as 2 hours."""
    # Arrange
    # Tickets needs 4 hours. Mock Mane has no limits but is only there 06:00-08:00 (2 hours),
    # Testy Hooves is there all weekend but may work 1 hour: 3 hours together. Without the
    # cap by availability Mock Mane would count as unlimited and nothing would be short.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=set(range(0, 8))),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_total=60)]

    demand = {}
    for block in range(0, 16):  # Tickets: 4 hours on Friday, 06:00-10:00
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughHours, match="Tickets"):
        check_problem(problem)


def test_volunteer_counts_for_at_most_their_total_limit_on_one_day():
    """With 8 hours per day but 6 in total, a volunteer counts as 6 hours on one day."""
    # Arrange
    # Tickets needs 7 hours on Friday. With only the daily limit Mock Mane could do 8 that
    # day; the total limit of 6 makes Friday short as well (not only "over all days").
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_per_day=480,
                            max_minutes_total=360)]

    demand = {}
    for block in range(0, 28):  # Tickets: 7 hours on Friday, 06:00-13:00
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughHours, match="Tickets, Friday"):
        check_problem(problem)


def test_not_enough_hours_message_names_the_post_the_day_and_both_numbers_of_hours():
    """The message names the post, the day, the hours needed and the hours available."""
    # Arrange
    # As test 3: Tickets needs 3 hours on Friday, Mock Mane may work 2 hours per day.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_per_day=120)]

    demand = {}
    for block in range(0, 12):  # Tickets: 3 hours on Friday
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    with pytest.raises(NotEnoughHours) as caught:
        check_problem(problem)
    message = str(caught.value)

    # Assert
    assert "Tickets, Friday" in message
    assert "3 hours" in message      # needed
    assert "2 hours" in message      # what Mock Mane can work that day


def test_hours_checks_only_run_when_checks_one_and_two_find_nothing():
    """A problem short of both people and hours raises NotEnoughQualified, not NotEnoughHours."""
    # Arrange
    # Tickets needs 2 people for 2 hours, only Mock Mane is qualified (check 1), and they
    # may only work 1 hour (the hours check would be short too).
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS,
                            max_minutes_total=60)]

    demand = {}
    for block in range(0, 8):  # Tickets: 2 people for 2 hours on Friday
        demand[("Tickets", block)] = 2

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(NotEnoughQualified):
        check_problem(problem)

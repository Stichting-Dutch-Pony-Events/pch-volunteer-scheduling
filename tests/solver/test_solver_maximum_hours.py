import pytest

from scheduler.model import Volunteer, Post, Problem, Settings, all_blocks, block_of
from scheduler.solver import solve, NoScheduleFound


# The tests below pass the stretch and break limits explicitly (in blocks: 4, 12 and 2)
# instead of relying on the defaults in model.py. The hour limits are on the volunteers,
# in minutes (None = no limit).
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))

ALL_DAYS = all_blocks(RULES)


# --- Maximum hours per day ---

def test_work_beyond_the_daily_maximum_raises_no_schedule_found():
    """With a daily maximum of 2 hours, 3 hours of work on one day is not allowed."""
    # Arrange
    demand = {}
    for block in range(0, 12):     # Friday 06:00-09:00, 3 hours (one allowed stretch)
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS, max_minutes_per_day=120)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_work_up_to_the_daily_maximum_is_allowed():
    """With a daily maximum of 2 hours, exactly 2 hours of work is fine."""
    # Arrange
    demand = {}
    for block in range(0, 8):      # Friday 06:00-08:00, 2 hours
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS, max_minutes_per_day=120)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    expected = set()
    for block in range(0, 8):
        expected.add(("Mock Mane", "Tickets", block))
    assert schedule.assignments == expected


def test_daily_maximum_applies_to_each_day_separately():
    """A daily maximum of 2 hours allows 2 hours on Friday and another 2 on Saturday."""
    # Arrange
    demand = {}
    for block in range(0, 8):      # Friday 06:00-08:00, 2 hours
        demand[("Tickets", block)] = 1
    for block in range(96, 104):   # Saturday 06:00-08:00, 2 hours
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS, max_minutes_per_day=120)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    expected = set()
    for block in range(0, 8):
        expected.add(("Mock Mane", "Tickets", block))
    for block in range(96, 104):
        expected.add(("Mock Mane", "Tickets", block))
    assert schedule.assignments == expected


def test_night_work_counts_toward_the_convention_day_it_belongs_to():
    """Friday 22:00-23:00 and Friday night 01:00-02:00 are both Friday: 2 hours on one day."""
    # Arrange
    # On the calendar, 01:00 is already Saturday; counted per calendar day, each would be
    # 1 hour on a different day and the schedule would (wrongly) be allowed.
    evening = block_of("Friday", "22:00", RULES)     # 64
    night = block_of("Friday", "01:00", RULES)       # 76

    demand = {}
    for block in range(evening, evening + 4):        # Friday 22:00-23:00, 1 hour
        demand[("Tickets", block)] = 1
    for block in range(night, night + 4):            # Friday night 01:00-02:00, 1 hour
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS, max_minutes_per_day=60)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


# --- Maximum hours in total ---

def test_work_beyond_the_total_maximum_raises_no_schedule_found():
    """With a total maximum of 3 hours, 2 hours on Friday plus 2 on Saturday is too much."""
    # Arrange
    demand = {}
    for block in range(0, 8):      # Friday 06:00-08:00, 2 hours
        demand[("Tickets", block)] = 1
    for block in range(96, 104):   # Saturday 06:00-08:00, 2 hours
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS, max_minutes_total=180)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_work_up_to_the_total_maximum_is_allowed():
    """With a total maximum of 4 hours, 2 hours on Friday plus 2 on Saturday is fine."""
    # Arrange
    demand = {}
    for block in range(0, 8):      # Friday 06:00-08:00, 2 hours
        demand[("Tickets", block)] = 1
    for block in range(96, 104):   # Saturday 06:00-08:00, 2 hours
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS, max_minutes_total=240)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    expected = set()
    for block in range(0, 8):
        expected.add(("Mock Mane", "Tickets", block))
    for block in range(96, 104):
        expected.add(("Mock Mane", "Tickets", block))
    assert schedule.assignments == expected


# --- No limit, and limits per volunteer ---

def test_volunteer_without_limits_may_work_any_number_of_hours():
    """A volunteer without hour limits may work 3 hours on each of the three days."""
    # Arrange
    demand = {}
    for block in range(0, 12):     # Friday 06:00-09:00
        demand[("Tickets", block)] = 1
    for block in range(96, 108):   # Saturday 06:00-09:00
        demand[("Tickets", block)] = 1
    for block in range(192, 204):  # Sunday 06:00-09:00
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert len(schedule.assignments) == 36


def test_each_volunteer_has_their_own_limit():
    """A daily maximum of 2 hours for one volunteer is not shared with someone without limit."""
    # Arrange
    # Tickets needs 2 people for 3 hours, so both must work all 3 hours.
    demand = {}
    for block in range(0, 12):     # Friday 06:00-09:00
        demand[("Tickets", block)] = 2

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS, max_minutes_per_day=120),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


# --- Together with the maximum work stretch ---

def test_hour_limit_and_maximum_stretch_together_leave_a_gap_raises_no_schedule_found():
    """8 hours at Tickets: Testy Hooves can do 3 + 3, Mock Mane (max 1 hour) only one gap."""
    # Arrange
    # Testy Hooves needs a break between two stretches of at most 3 hours; Mock Mane covers
    # it with their 1 hour. That is 7 hours: the 8th hour has nobody left. Without the hour
    # limit, Mock Mane would simply cover it.
    demand = {}
    for block in range(0, 32):     # Friday 06:00-14:00, 8 hours
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS, max_minutes_total=60),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_hour_limit_and_maximum_stretch_together_can_still_be_met():
    """8 hours at Tickets works when Mock Mane may work 2 hours: 3 + 1 + 3 + 1."""
    # Arrange
    demand = {}
    for block in range(0, 32):     # Friday 06:00-14:00, 8 hours
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS, max_minutes_total=120),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=ALL_DAYS)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    mock_mane_blocks = 0
    for (name, post, block) in schedule.assignments:
        if name == "Mock Mane":
            mock_mane_blocks += 1
    assert mock_mane_blocks <= 8   # at most 2 hours

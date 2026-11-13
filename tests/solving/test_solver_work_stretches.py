import pytest

from scheduler.model import (Volunteer, Post, Problem, Settings, block_of, all_blocks,
                             MINUTES_PER_BLOCK)
from scheduler.errors import NoScheduleFound
from scheduler.solving.solver import solve


# Most tests below are built around these exact limits (in blocks: 4, 12 and 2), so they
# pass them (and the days, which block_of and all_blocks need) explicitly instead of
# relying on the defaults in model.py. Tests that need different limits make their own
# Settings.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))


def test_work_stretch_longer_than_the_maximum_raises_no_schedule_found():
    """With a 180 min maximum, 4 hours of work in a row is not allowed."""
    # Arrange
    demand = {}
    for block in range(16):       # blocks 0-15, so 4 hours
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_work_stretch_across_the_day_boundary_is_at_most_the_maximum():
    """Saturday night into Sunday morning is one stretch, so 4 hours across 06:00 is too long."""
    # Arrange
    # Saturday night 03:00 (calendar: early Sunday) up to Sunday 07:00, straight across 06:00.
    first_block = block_of("Saturday", "03:00", RULES)        # 96 + 84 = 180
    block_after_last = block_of("Sunday", "07:00", RULES)     # 192 + 4 = 196

    demand = {}
    for block in range(first_block, block_after_last):  # 16 blocks = 4 hours at Tickets
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_continuous_work_across_two_posts_is_at_most_the_maximum():
    """Switching post does not reset the clock: 4 hours across two posts is too long."""
    # Arrange
    demand = {}
    for block in range(8):        # blocks 0-7: 2 hours at Tickets
        demand[("Tickets", block)] = 1
    for block in range(8, 16):    # blocks 8-15: then 2 hours at Infobooth
        demand[("Infobooth", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_break_shorter_than_the_minimum_raises_no_schedule_found():
    """With a 30 min minimum break, a 15-minute break between two stretches is not allowed."""
    # Arrange
    demand = {}
    for block in range(8):        # blocks 0-7: 2 hours at Tickets
        demand[("Tickets", block)] = 1
    for block in range(9, 17):    # blocks 9-16: then 2 hours at Tickets, after 15 minute break
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_break_across_the_day_boundary_is_at_least_the_minimum():
    """A 15-minute break around 06:00 (Saturday night into Sunday) is still too short."""
    # Arrange
    # Saturday night 04:00-06:00 (calendar: early Sunday), then 15 minutes off at 06:00,
    # then Sunday 06:15-08:15. Only Mock Mane can do it, so the break can't be avoided.
    demand = {}
    for block in range(block_of("Saturday", "04:00", RULES),
                       block_of("Saturday", "05:45", RULES) + 1):   # blocks 184-191, 2 hours
        demand[("Tickets", block)] = 1
    for block in range(block_of("Sunday", "06:15", RULES),
                       block_of("Sunday", "08:15", RULES)):         # blocks 193-200, 2 hours
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_break_of_exactly_the_minimum_is_allowed():
    """With a 30 min minimum break, a 30-minute break between two stretches is long enough."""
    # Arrange
    demand = {}
    for block in range(8):        # blocks 0-7: 2 hours at Tickets
        demand[("Tickets", block)] = 1
    for block in range(10, 18):   # blocks 10-17: 2 hours more, after 30 minute break
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Tickets", 10) == {"Mock Mane"}


def test_extra_person_needed_for_less_than_the_minimum_may_work_just_that_time():
    """A second person needed for only 30 minutes (minimum 60) may work just those 30 minutes."""
    # Arrange
    # Tickets needs 2 people in blocks 0-1 and 1 in blocks 2-7. Whoever takes the
    # second spot can only work those 30 minutes: a short piece of demand, so allowed.
    demand = {}
    for block in range(2):        # blocks 0-1: half hour at Tickets
        demand[("Tickets", block)] = 2
    for block in range(2, 8):     # blocks 2-7: then 1.5 hours at Tickets
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Tickets", 1) == {"Mock Mane", "Testy Hooves"}


def test_two_posts_together_can_make_up_the_minimum():
    """30 minutes at one post followed by 30 minutes at another is a valid 60-minute stretch."""
    # Arrange
    demand = {}
    for block in range(2):        # blocks 0-1: half hour at Tickets
        demand[("Tickets", block)] = 2
    for block in range(2, 8):     # blocks 2-7: then 1.5 hours at Tickets
        demand[("Tickets", block)] = 1
    for block in range(2, 4):     # blocks 2-3: additionally 0.5 hours at Infobooth
        demand[("Infobooth", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Tickets", 1) == {"Mock Mane", "Testy Hooves"}
    assert schedule.people_at("Tickets", 2) == {"Mock Mane"}
    assert schedule.people_at("Infobooth", 2) == {"Testy Hooves"}


def test_post_open_less_than_the_minimum_can_be_worked():
    """A post open only 30 minutes in a row (minimum 60) may be worked for just that time."""
    # Arrange
    demand = {}
    for block in range(2):        # blocks 0-1: half hour at Tickets
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Tickets", 1) == {"Mock Mane"}


def test_work_stretch_shorter_than_minimum_raises_no_schedule_found():
    """A short stretch in the middle of a longer piece of demand is not allowed."""
    # Arrange
    # Own settings: with a 150 min minimum and a 180 min maximum, nobody can do the 4 hours
    # alone, and any split leaves a piece under 150 min.
    demand = {}
    for block in range(16):       # blocks 0-15: 4 hours at Tickets
        demand[("Tickets", block)] = 1

    settings = Settings(min_stretch_minutes=150, max_stretch_minutes=180,
                        days=("Friday", "Saturday", "Sunday"))

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=all_blocks(settings)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=all_blocks(settings))],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=settings)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_minimum_stretch_can_be_changed_in_the_settings():
    """With the minimum set to 30 minutes, a 30-minute stretch is allowed."""
    # Arrange
    # Own settings: nobody can do 90 min alone (max 60), so it must be split, e.g. 60 + 30.
    # With a 60 min minimum that would be impossible.
    demand = {}
    for block in range(6):        # blocks 0-5: 1.5 hours at Tickets
        demand[("Tickets", block)] = 1

    settings = Settings(min_stretch_minutes=30, max_stretch_minutes=60,
                        days=("Friday", "Saturday", "Sunday"))

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=all_blocks(settings)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=all_blocks(settings))],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=settings)

    # Act
    schedule = solve(problem)

    # Assert
    assert len(schedule.assignments) == 6


def test_long_opening_is_split_into_stretches_of_allowed_length():
    """A 4-hour opening is split so that every work stretch is between the minimum and maximum."""
    # Arrange
    demand = {}
    for block in range(16):       # blocks 0-15: 4 hours at Tickets
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    for volunteer in ("Mock Mane", "Testy Hooves"):
        for first_block, block_after_last in schedule.work_stretches_of(volunteer):
            length_in_minutes = (block_after_last - first_block) * MINUTES_PER_BLOCK
            assert RULES.min_stretch_minutes <= length_in_minutes <= RULES.max_stretch_minutes

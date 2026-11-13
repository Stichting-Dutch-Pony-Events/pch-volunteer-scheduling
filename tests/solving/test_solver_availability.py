import pytest

from scheduler.model import Volunteer, Post, Problem, Settings, block_of, all_blocks
from scheduler.solving.solver import solve, NoScheduleFound


# The stretch and break rules also apply here, and block_of depends on the days, so the
# tests pass these limits and days explicitly instead of relying on the defaults in model.py.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))


def test_volunteer_cannot_work_on_a_day_they_are_not_available():
    """Someone available only on Friday cannot cover demand on Saturday."""
    # Arrange
    # Saturday 10:00-12:00: 2 hours at Tickets
    demand = {}
    for block in range(block_of("Saturday", "10:00", RULES),
                       block_of("Saturday", "12:00", RULES)):
        demand[("Tickets", block)] = 1

    # Mock Mane is there all of Friday (06:00 up to Saturday 06:00), not on Saturday.
    friday = set(range(block_of("Friday", "06:00", RULES),
                       block_of("Saturday", "06:00", RULES)))

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=friday)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_work_goes_to_the_volunteer_who_is_available():
    """When one volunteer is away, the work goes to the one who is there."""
    # Arrange
    saturday_10_00 = block_of("Saturday", "10:00", RULES)
    saturday_12_00 = block_of("Saturday", "12:00", RULES)

    # Saturday 10:00-12:00: 2 hours at Tickets
    demand = {}
    for block in range(saturday_10_00, saturday_12_00):
        demand[("Tickets", block)] = 1

    # Mock Mane is there all of Friday (06:00 up to Saturday 06:00), not on Saturday.
    # Testy Hooves is there all weekend.
    friday = set(range(block_of("Friday", "06:00", RULES),
                       block_of("Saturday", "06:00", RULES)))

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=friday),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.work_stretches_of("Testy Hooves") == [(saturday_10_00, saturday_12_00)]


def test_volunteer_can_work_inside_their_available_blocks():
    """Demand that falls entirely inside someone's available blocks can be worked."""
    # Arrange
    friday_14_00 = block_of("Friday", "14:00", RULES)

    # Friday 14:00-16:00: 2 hours at Tickets
    demand = {}
    for block in range(friday_14_00, block_of("Friday", "16:00", RULES)):
        demand[("Tickets", block)] = 1

    # Mock Mane is there Friday 12:00-18:00, so the whole demand falls inside.
    friday_afternoon = set(range(block_of("Friday", "12:00", RULES),
                                 block_of("Friday", "18:00", RULES)))

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=friday_afternoon)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Tickets", friday_14_00) == {"Mock Mane"}


def test_one_block_outside_the_available_blocks_raises_no_schedule_found():
    """Being available until 18:00 means the block starting at 18:00 cannot be worked."""
    # Arrange
    # Friday 17:00-18:15: Tickets, so one block (18:00-18:15) sticks out past 18:00.
    demand = {}
    for block in range(block_of("Friday", "17:00", RULES),
                       block_of("Friday", "18:15", RULES)):
        demand[("Tickets", block)] = 1

    # Mock Mane is there Friday 12:00-18:00 (the last block they can work starts at 17:45).
    friday_afternoon = set(range(block_of("Friday", "12:00", RULES),
                                 block_of("Friday", "18:00", RULES)))

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=friday_afternoon)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_volunteer_with_no_available_blocks_cannot_work():
    """An empty set of available blocks means never available."""
    # Arrange
    # Friday 17:00-18:00: 1 hour at Tickets
    demand = {}
    for block in range(block_of("Friday", "17:00", RULES),
                       block_of("Friday", "18:00", RULES)):
        demand[("Tickets", block)] = 1

    # Mock Mane is never available.
    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=set())],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_shift_change_happens_when_availability_ends():
    """When one volunteer leaves halfway, the other takes over at exactly that moment."""
    # Arrange
    friday_14_00 = block_of("Friday", "14:00", RULES)
    friday_16_00 = block_of("Friday", "16:00", RULES)
    friday_18_00 = block_of("Friday", "18:00", RULES)

    # Friday 14:00-18:00: 4 hours at Tickets, more than the maximum for one person.
    demand = {}
    for block in range(friday_14_00, friday_18_00):
        demand[("Tickets", block)] = 1

    # Mock Mane is there 14:00-16:00, Testy Hooves 16:00-18:00.
    mock_mane_availability = set(range(friday_14_00, friday_16_00))
    testy_hooves_availability = set(range(friday_16_00, friday_18_00))

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=mock_mane_availability),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=testy_hooves_availability)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Tickets", block_of("Friday", "15:45", RULES)) == {"Mock Mane"}
    assert schedule.people_at("Tickets", friday_16_00) == {"Testy Hooves"}


def test_availability_does_not_allow_a_stretch_shorter_than_the_minimum():
    """Being available for only 30 minutes of a long opening is not a reason for a short stretch."""
    # Arrange
    # Mock Mane can do at most 3 of the 3.5 hours, so Testy Hooves would have to do just
    # the last 30 minutes: not a short piece of demand, so not allowed.
    friday_17_30 = block_of("Friday", "17:30", RULES)

    # Friday 14:00-17:30: 3.5 hours at Tickets, more than the maximum for one person.
    demand = {}
    for block in range(block_of("Friday", "14:00", RULES), friday_17_30):
        demand[("Tickets", block)] = 1

    # Mock Mane is there all of Friday (06:00 up to Saturday 06:00).
    friday = set(range(block_of("Friday", "06:00", RULES),
                       block_of("Saturday", "06:00", RULES)))

    # Testy Hooves is there only Friday 17:00-17:30.
    testy_hooves_availability = set(range(block_of("Friday", "17:00", RULES), friday_17_30))

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                              available_blocks=friday),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=testy_hooves_availability)],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)

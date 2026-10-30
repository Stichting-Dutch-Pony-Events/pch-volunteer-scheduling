import pytest

from scheduler.model import Volunteer, Post, Problem, Schedule, Settings
from scheduler.solver import solve, NoScheduleFound


def test_work_stretch_longer_than_180_minutes_raises_no_schedule_found():
    """A work stretch longer than 180 minutes is not allowed, so no schedule can be found."""
    # Arrange
    demand = {}
    for block in range(16):       # blocks 0-15, so 4 hours
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1})],
        posts=[Post(name="Tickets")],
        demand=demand)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_continuous_work_across_two_posts_is_at_most_180_minutes():
    """Switching post does not reset the clock: 4 hours across two posts is not allowed."""
    # Arrange
    demand = {}
    for block in range(8):        # blocks 0-7: 2 hours at Tickets
        demand[("Tickets", block)] = 1
    for block in range(8, 16):    # blocks 8-15: then 2 hours at Infobooth
        demand[("Infobooth", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1})],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_break_of_15_minutes_raises_no_schedule_found():
    """A break of only 15 minutes between two work stretches is not allowed."""
    # Arrange
    demand = {}
    for block in range(8):        # blocks 0-7: 2 hours at Tickets
        demand[("Tickets", block)] = 1
    for block in range(9, 17):    # blocks 9-16: then 2 hours at Tickets, after 15 minute break
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1})],
        posts=[Post(name="Tickets")],
        demand=demand)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_break_of_30_minutes_is_allowed():
    """A break of 30 minutes between two work stretches is long enough."""
    # Arrange
    demand = {}
    for block in range(8):        # blocks 0-7: 2 hours at Tickets
        demand[("Tickets", block)] = 1
    for block in range(10, 18):   # blocks 10-17: 2 hours more, after 30 minute break
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1})],
        posts=[Post(name="Tickets")],
        demand=demand)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Tickets", 10) == {"Mock Mane"}


def test_extra_person_needed_for_30_minutes_may_work_just_those_30_minutes():
    """A second person needed for only 30 minutes may work a 30-minute stretch."""
    # Arrange
    demand = {}
    for block in range(2):        # blocks 0-1: half hour at Tickets
        demand[("Tickets", block)] = 2
    for block in range(2, 8):     # blocks 2-7: then 1.5 hours at Tickets
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1}),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1})],
        posts=[Post(name="Tickets")],
        demand=demand)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Tickets", 1) == {"Mock Mane", "Testy Hooves"}


def test_two_posts_together_can_make_up_the_60_minutes():
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
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1}),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1, "Infobooth": 1})],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Tickets", 1) == {"Mock Mane", "Testy Hooves"}
    assert schedule.people_at("Tickets", 2) == {"Mock Mane"}
    assert schedule.people_at("Infobooth", 2) == {"Testy Hooves"}


def test_post_open_less_than_60_minutes_can_be_worked():
    """A post open less than 60 minutes in a row may be worked for just that opening."""
    # Arrange
    demand = {}
    for block in range(2):        # blocks 0-1: half hour at Tickets
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1})],
        posts=[Post(name="Tickets")],
        demand=demand)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Tickets", 1) == {"Mock Mane"}


def test_work_stretch_shorter_than_minimum_raises_no_schedule_found():
    """A short stretch in the middle of a longer piece of demand is not allowed."""
    # Arrange
    demand = {}
    for block in range(16):       # blocks 0-15: 4 hours at Tickets
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1}),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1})],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=Settings(min_stretch_minutes=150, max_stretch_minutes=180))

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_minimum_stretch_can_be_changed_in_the_settings():
    """With the minimum set to 30 minutes, a 30-minute stretch is allowed."""
    # Arrange
    demand = {}
    for block in range(6):        # blocks 0-5: 1.5 hours at Tickets
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1}),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1})],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=Settings(min_stretch_minutes=30, max_stretch_minutes=60))


    # Act
    schedule = solve(problem)

    # Assert
    assert len(schedule.assignments) == 6



def test_long_opening_is_split_into_stretches_of_allowed_length():
    """A 4-hour opening is split so that every work stretch is 60 to 180 minutes."""
    # Arrange
    min_minutes = 60
    max_minutes = 180

    demand = {}
    for block in range(16):       # blocks 0-15: 4 hours at Tickets
        demand[("Tickets", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1}),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1})],
        posts=[Post(name="Tickets")],
        demand=demand,
        settings=Settings(min_stretch_minutes=min_minutes, max_stretch_minutes=max_minutes))

    # Act
    schedule = solve(problem)

    # Assert
    for volunteer in ("Mock Mane", "Testy Hooves"):
        for first_block, block_after_last in schedule.work_stretches_of(volunteer):
            length = block_after_last - first_block
            assert min_minutes <= (length * 15) <= max_minutes

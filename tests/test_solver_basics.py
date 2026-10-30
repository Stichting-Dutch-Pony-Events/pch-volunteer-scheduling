import pytest

from scheduler.model import Volunteer, Post, Problem, Schedule
from scheduler.solver import solve, NoScheduleFound


def test_single_volunteer_fills_single_post():
    """One qualified volunteer and one open block: the volunteer is scheduled there."""
    # Arrange
    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1})],
        posts=[Post(name="Tickets")],
        demand={("Tickets", 0): 1})

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Tickets", 0) == {"Mock Mane"}


def test_post_gets_exactly_the_number_needed():
    """A post needing two people gets exactly two, even when three are qualified."""
    # Arrange
    problem = Problem(
        volunteers=[
            Volunteer(name="Mock Mane", skills={"Tickets": 1}),
            Volunteer(name="Testy Hooves", skills={"Tickets": 1}),
            Volunteer(name="Dummy Dash", skills={"Tickets": 1}),
        ],
        posts=[Post(name="Tickets")],
        demand={("Tickets", 0): 2})

    # Act
    schedule = solve(problem)

    # Assert
    assert len(schedule.people_at("Tickets", 0)) == 2


def test_nobody_works_a_closed_post():
    """A post that is not in the demand for a block gets nobody in that block."""
    # Arrange
    problem = Problem(
        volunteers=[
            Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1}),
            Volunteer(name="Testy Hooves", skills={"Tickets": 1, "Infobooth": 1}),
        ],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand={("Tickets", 0): 1})  # Infobooth is closed in block 0

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Infobooth", 0) == set()


def test_volunteer_without_skill_is_never_scheduled():
    """A volunteer with no skill score for a post is never put on that post."""
    # Arrange
    problem = Problem(
        volunteers=[
            Volunteer(name="Mock Mane", skills={"Tickets": 1}),
            Volunteer(name="Testy Hooves", skills={"Infobooth": 1}),
        ],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand={("Tickets", 0): 1})

    # Act
    schedule = solve(problem)

    # Assert
    assert "Testy Hooves" not in schedule.people_at("Tickets", 0)


def test_nobody_is_in_two_places_at_once():
    """One volunteer cannot fill two posts in the same block, so no schedule exists."""
    # Arrange
    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1})],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand={("Tickets", 0): 1, ("Infobooth", 0): 1})

    # Act
    # (Act and Assert are combined: pytest.raises checks the exception while solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_too_few_volunteers_raises_no_schedule_found():
    """When a post needs more people than are qualified, solving raises NoScheduleFound."""
    # Arrange
    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1})],
        posts=[Post(name="Tickets")],
        demand={("Tickets", 0): 2})

    # Act
    # (Act and Assert are combined: pytest.raises checks the exception while solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_nobody_qualified_raises_no_schedule_found():
    """When nobody has a skill score for an open post, solving raises NoScheduleFound."""
    # Arrange
    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Infobooth": 1})],
        posts=[Post(name="Tickets")],
        demand={("Tickets", 0): 1})

    # Act
    # (Act and Assert are combined: pytest.raises checks the exception while solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)

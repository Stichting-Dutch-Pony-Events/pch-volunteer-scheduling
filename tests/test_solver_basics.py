from scheduler.model import Volunteer, Post, Problem, Schedule
from scheduler.solver import solve


def test_single_volunteer_fills_single_post():
    """One qualified volunteer and one open block: the volunteer is scheduled there."""
    # Arrange
    mock_mane = Volunteer(name="Mock Mane", skills={"Tickets": 1})
    problem = Problem(
        volunteers=[mock_mane],
        posts=[Post(name="Tickets")],
        demand={("Tickets", 0): 1})

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.people_at("Tickets", 0) == {"Mock Mane"}
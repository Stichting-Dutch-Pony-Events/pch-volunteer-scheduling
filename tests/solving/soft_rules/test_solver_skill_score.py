import pytest

from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks
from scheduler.solving.solver import solve


# Passed explicitly instead of relying on the defaults in model.py, including the skill
# score weights (penalty points per block worked; lower = preferred).
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"),
                 weight_skill_score_1=6, weight_skill_score_2=2, weight_skill_score_3=0)

ALL_DAYS = all_blocks(RULES)

# Against a test that is green by luck (without an objective CP-SAT takes any valid
# schedule): one volunteer with the preferred score against several others, and the
# preferred one FIRST in the list. (Tried 2026-11-18: without an objective, CP-SAT picked
# the last volunteer in the list every time, so "preferred last" was green by luck.)


def test_volunteer_with_score_3_gets_the_post_over_score_1():
    """Of two qualified volunteers, the one with skill score 3 works, not the one with 1."""
    # Arrange
    volunteers = [Volunteer(name="Star Fixture", skills={"Tickets": 3}, available_blocks=ALL_DAYS),
                  Volunteer(name="Mock Mane", skills={"Tickets": 1}, available_blocks=ALL_DAYS)]

    demand = {}
    expected = set()
    for block in range(0, 8):
        demand[("Tickets", block)] = 1
        expected.add(("Star Fixture", "Tickets", block))

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected


def test_score_2_is_preferred_over_score_1():
    """Of two qualified volunteers, the one with skill score 2 works, not the one with 1."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_score_3_is_preferred_over_score_2():
    """Of two qualified volunteers, the one with skill score 3 works, not the one with 2."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_preference_is_per_post():
    """Each volunteer goes to the post where their own skill score is highest."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_weights_come_from_the_settings():
    """With the weights reversed, the volunteer with skill score 1 is preferred."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_lower_score_still_works_when_needed():
    """A post needing two people gets both, even though one has a lower score."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_equal_weights_still_give_a_schedule():
    """With all skill score weights 0, a schedule is still found."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_solver_minimises_the_penalty_with_a_time_limit():
    """With a time limit, the solver still prefers the volunteer with the higher score."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")

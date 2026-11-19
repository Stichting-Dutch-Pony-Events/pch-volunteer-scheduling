from dataclasses import replace

import pytest
from ortools.sat.python import cp_model

from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks
from scheduler.solving.soft_rules import add_round_times_penalty
from scheduler.solving.solver import solve
from scheduler.solving.variables import create_variables


# Passed explicitly instead of relying on the defaults in model.py. Only the round times
# soft rule is switched on, so no other soft rule can change the outcome; the skill score
# weights are here for the tests that switch both rules on.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"),
                 soft_rules=frozenset({"round_times"}),
                 weight_off_round_time=10,
                 weight_skill_score_1=6, weight_skill_score_2=2, weight_skill_score_3=0)

ALL_DAYS = all_blocks(RULES)

# Block 0 = Friday 06:00, so even blocks are on :00/:30 and odd blocks on :15/:45.
# Most tests force a choice between two hand-overs through availability: Tickets needs
# 1 person in blocks 0-11 (06:00-09:00), one volunteer is only there early, the other
# only late, so the minimum stretch of 60 minutes leaves just two hand-over moments.
# Without an objective CP-SAT takes either one; check afterwards with a few seeds that
# these tests go red without the rule.


def test_handover_on_the_half_hour_is_preferred_over_a_quarter_past():
    """Of a hand-over at 07:15 or 07:30, the solver picks 07:30."""
    # Arrange
    # Mock Mane available blocks 0-5, Testy Hooves blocks 5-11: hand-over at block 5
    # (07:15) or 6 (07:30). Expected: Mock Mane 0-5, Testy Hooves 6-11.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=set(range(0, 6))),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=set(range(5, 12)))]

    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    expected = set()
    for block in range(0, 6):
        expected.add(("Mock Mane", "Tickets", block))
    for block in range(6, 12):
        expected.add(("Testy Hooves", "Tickets", block))

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected


def test_handover_on_the_hour_is_preferred_over_a_quarter_past():
    """Of a hand-over at 07:00 or 07:15, the solver picks 07:00 (the hour is round too)."""
    # Arrange
    # Mock Mane available blocks 0-4, Testy Hooves blocks 4-11: hand-over at block 4
    # (07:00) or 5 (07:15). Expected: Mock Mane 0-3, Testy Hooves 4-11.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=set(range(0, 5))),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=set(range(4, 12)))]

    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    expected = set()
    for block in range(0, 4):
        expected.add(("Mock Mane", "Tickets", block))
    for block in range(4, 12):
        expected.add(("Testy Hooves", "Tickets", block))

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected


def test_switching_post_inside_a_stretch_is_not_a_start():
    """One volunteer going on from Tickets to Infobooth at 06:45 costs nothing extra."""
    # Arrange
    # Tickets needs 1 in blocks 0-2 (only Mock Mane), Infobooth 1 in blocks 3-6 (Mock Mane
    # and Testy Hooves). Mock Mane going on to Infobooth: no start or end at 06:45.
    # Testy Hooves taking Infobooth: Mock Mane ends and Testy Hooves starts at 06:45, two
    # penalties. Expected: Mock Mane works all of it, Testy Hooves nothing.
    # (Mock Mane worked only 45 minutes at Tickets, so the stay-at-post rule allows it.)
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                            available_blocks=set(range(0, 7))),
                  Volunteer(name="Testy Hooves", skills={"Infobooth": 1},
                            available_blocks=set(range(3, 7)))]

    demand = {}
    for block in range(0, 3):
        demand[("Tickets", block)] = 1
    for block in range(3, 7):
        demand[("Infobooth", block)] = 1

    expected = set()
    for block in range(0, 3):
        expected.add(("Mock Mane", "Tickets", block))
    for block in range(3, 7):
        expected.add(("Mock Mane", "Infobooth", block))

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets"), Post("Infobooth")],
                      demand=demand, settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected


def test_start_off_the_half_hour_that_cannot_be_avoided_still_gives_a_schedule():
    """A post that opens at 06:15 still gets its volunteer; the rule is only a preference."""
    # Arrange
    # Only Mock Mane, Tickets needs 1 in blocks 1-4 (06:15-07:15).
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=set(range(1, 5)))]

    demand = {}
    for block in range(1, 5):
        demand[("Tickets", block)] = 1

    expected = set()
    for block in range(1, 5):
        expected.add(("Mock Mane", "Tickets", block))

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected


# Together with the skill score rule: the weights decide which preference wins.
# Mock Mane (score 1, 6 points per block) available blocks 0-5, Star Fixture (score 3,
# 0 points) blocks 5-11; Tickets needs 1 in blocks 0-11.
#   hand-over at 07:15 (block 5): Mock Mane 5 blocks = 30, plus 2 x round times weight
#   hand-over at 07:30 (block 6): Mock Mane 6 blocks = 36, no round times penalty
# So weight 10 (30 + 20 = 50) gives 07:30, weight 2 (30 + 4 = 34) gives 07:15.

def test_round_times_win_over_the_skill_score_with_a_high_weight():
    """With weight 10 per start or end, the hand-over is at 07:30 despite the skill score."""
    # Arrange
    volunteers = [Volunteer(name="Starry Fixture", skills={"Tickets": 3},
                            available_blocks=set(range(5, 12))),
                  Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=set(range(0, 6)))]

    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    expected = set()
    for block in range(0, 6):
        expected.add(("Mock Mane", "Tickets", block))
    for block in range(6, 12):
        expected.add(("Starry Fixture", "Tickets", block))

    new_rules = replace(RULES, soft_rules=frozenset({"round_times", "skill_score"}))

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=new_rules)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected


def test_skill_score_wins_over_round_times_with_a_low_weight():
    """With weight 2 per start or end, the better score wins and the hand-over is at 07:15."""
    # Arrange
    volunteers = [Volunteer(name="Starry Fixture", skills={"Tickets": 3},
                            available_blocks=set(range(5, 12))),
                  Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=set(range(0, 6)))]

    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    expected = set()
    for block in range(0, 5):
        expected.add(("Mock Mane", "Tickets", block))
    for block in range(5, 12):
        expected.add(("Starry Fixture", "Tickets", block))

    new_rules = replace(RULES, soft_rules=frozenset({"round_times", "skill_score"}),
                        weight_off_round_time=2)

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=new_rules)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected


# Switching the rule on and off. The rule checks settings.soft_rules itself, so these
# tests call it directly (no solving needed); the tests above show that solve() uses it.

def test_round_times_penalty_that_is_off_returns_nothing():
    """With the round times rule switched off, add_round_times_penalty returns no terms."""
    # Arrange
    model = cp_model.CpModel()

    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=set(range(4)))],
                      posts=[Post("Tickets")],
                      demand={("Tickets", 0): 1, ("Tickets", 1): 1,
                              ("Tickets", 2): 1, ("Tickets", 3): 1},
                      settings=replace(RULES, soft_rules=frozenset()))

    works = create_variables(model, problem)

    # Act
    penalties = add_round_times_penalty(model, problem, works)

    # Assert
    assert penalties == []


def test_round_times_penalty_that_is_on_returns_terms():
    """With the rule on, a volunteer who could start at 06:15 gives penalty terms."""
    # Arrange
    model = cp_model.CpModel()

    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=set(range(4)))],
                      posts=[Post("Tickets")],
                      demand={("Tickets", 0): 1, ("Tickets", 1): 1,
                              ("Tickets", 2): 1, ("Tickets", 3): 1},
                      settings=replace(RULES, soft_rules=frozenset({"round_times"})))

    works = create_variables(model, problem)

    # Act
    penalties = add_round_times_penalty(model, problem, works)

    # Assert
    assert penalties

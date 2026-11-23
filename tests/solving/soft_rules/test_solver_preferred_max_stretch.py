from dataclasses import replace

import pytest
from ortools.sat.python import cp_model

from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks
from scheduler.solving.soft_rules import add_preferred_max_stretch_penalty
from scheduler.solving.solver import solve
from scheduler.solving.variables import Works, create_variables


# Passed explicitly instead of relying on the defaults in model.py. Only the preferred maximum
# stretch soft rule is switched on, so no other soft rule can change the outcome; the fewer
# stretches weight is here for the tests that switch both rules on.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"),
                 soft_rules=frozenset({"preferred_max_stretch"}),
                 preferred_max_stretch_minutes=120, weight_over_preferred_stretch=6,
                 weight_work_stretch=20)

ALL_DAYS = all_blocks(RULES)

# Without an objective CP-SAT takes any valid schedule, so after implementing, check with a
# few seeds that the preference tests go red without the rule.


def test_no_stretch_is_longer_than_the_preferred_maximum_when_it_can_be_avoided():
    """A 3-hour opening with two volunteers is split, so no stretch is over 2 hours."""
    # Arrange
    # Tickets needs 1 in blocks 0-11 (06:00-09:00), Mock Mane and Testy Hooves both
    # available. Assert with schedule.work_stretches_of that every stretch is at most 8
    # blocks.
    names = ["Mock Mane", "Testy Hooves"]
    volunteers = []
    for name in names:
        volunteers.append(Volunteer(name=name, skills={"Tickets": 1},
                                    available_blocks=ALL_DAYS))

    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    for name in names:
        for (first_block, block_after_last) in schedule.work_stretches_of(name):
            assert block_after_last - first_block <= 8


def test_stretch_longer_than_the_preferred_maximum_that_cannot_be_avoided_still_gives_a_schedule():
    """With only one volunteer for a 3-hour opening, the long stretch is still scheduled."""
    # Arrange
    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS)],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    expected = set()
    for block in range(0, 12):
        expected.add(("Mock Mane", "Tickets", block))

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected


# Together with the fewer stretches rule: the weights decide which preference wins.
# Tickets needs 1 in blocks 0-11 (3 hours), Mock Mane and Testy Hooves both available.
#   one stretch of 3 hours: 1 x 20 + 4 blocks over the preferred maximum x weight
#   split into two stretches of at most 2 hours: 2 x 20 = 40, nothing over
# So weight 6 (20 + 24 = 44 against 40) gives the split, weight 4 (20 + 16 = 36 against
# 40) gives one stretch.

def test_shorter_stretches_win_over_fewer_stretches_with_a_high_weight():
    """With weight 6 per block over the preferred maximum, the 3-hour opening is split."""
    # Arrange
    names = ["Mock Mane", "Testy Hooves"]
    volunteers = []
    for name in names:
        volunteers.append(Volunteer(name=name, skills={"Tickets": 1},
                                    available_blocks=ALL_DAYS))

    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    both_rules = replace(RULES, soft_rules=frozenset({"preferred_max_stretch",
                                                      "fewer_stretches"}))

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=both_rules)

    # Act
    schedule = solve(problem)

    # Assert
    number_of_stretches = 0
    for name in names:
        number_of_stretches += len(schedule.work_stretches_of(name))

    assert number_of_stretches == 2


def test_fewer_stretches_win_over_shorter_stretches_with_a_low_weight():
    """With weight 4 per block over the preferred maximum, one volunteer works all 3 hours."""
    # Arrange
    names = ["Mock Mane", "Testy Hooves"]
    volunteers = []
    for name in names:
        volunteers.append(Volunteer(name=name, skills={"Tickets": 1},
                                    available_blocks=ALL_DAYS))

    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    both_rules = replace(RULES, soft_rules=frozenset({"preferred_max_stretch",
                                                      "fewer_stretches"}),
                         weight_over_preferred_stretch=4)

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=both_rules)

    # Act
    schedule = solve(problem)

    # Assert
    number_of_stretches = 0
    for name in names:
        number_of_stretches += len(schedule.work_stretches_of(name))

    assert number_of_stretches == 1


# Counting blocks over the preferred maximum. Like in test_solver_fewer_stretches.py: one
# volunteer's work is fixed by hand and only this rule is added (no hard rules), so the
# penalty is exactly what the rule counts. Each case lists the pieces Mock Mane works as
# (post, first block, block after the last); Tickets and Infobooth are open in blocks 0-23.
# The preferred maximum is 8 blocks (120 minutes), the weight 6 per block over it.
STRETCH_CASES = [([("Tickets", 0, 8)], 0),            # exactly 2 hours: nothing over
                 ([("Tickets", 0, 9)], 6),            # 2h15: 1 block over
                 ([("Tickets", 0, 12)], 24),          # 3 hours: 4 blocks over
                 ([("Tickets", 0, 10),
                   ("Tickets", 12, 22)], 24),         # two stretches of 2.5 hours: 2 + 2
                 ([("Tickets", 0, 6),
                   ("Infobooth", 6, 12)], 24)]        # post switch: still one 3-hour stretch


def _model_with_fixed_work(pieces: list[tuple[str, int, int]]
                           ) -> tuple[cp_model.CpModel, Problem, Works]:
    """A model with only Mock Mane's variables, each fixed to 1 inside the pieces, else 0."""
    demand = {}
    for block in range(0, 24):
        demand[("Tickets", block)] = 1
        demand[("Infobooth", block)] = 1

    problem = Problem(volunteers=[Volunteer(name="Mock Mane",
                                            skills={"Tickets": 1, "Infobooth": 1},
                                            available_blocks=ALL_DAYS)],
                      posts=[Post("Tickets"), Post("Infobooth")],
                      demand=demand, settings=RULES)
    model = cp_model.CpModel()
    works = create_variables(model, problem)

    # Fix every variable by hand: 1 for the (post, block) pairs in the pieces, 0 for all
    # others. CP-SAT then has no choice left about the work, only about the helper
    # variables the rule makes.
    worked = set()
    for (post, first_block, block_after_last) in pieces:
        for block in range(first_block, block_after_last):
            worked.add((post, block))

    for (volunteer_name, post, block), variable in works.items():
        if (post, block) in worked:
            model.add(variable == 1)
        else:
            model.add(variable == 0)

    return (model, problem, works)


@pytest.mark.parametrize("pieces, expected_penalty", STRETCH_CASES)
def test_each_block_over_the_preferred_maximum_costs_the_weight(
        pieces: list[tuple[str, int, int]], expected_penalty: int):
    """Each block of a stretch beyond the preferred maximum costs the weight, across posts."""
    # Arrange
    model, problem, works = _model_with_fixed_work(pieces=pieces)
    penalties = add_preferred_max_stretch_penalty(model, problem, works)
    model.minimize(cp_model.LinearExpr.sum(penalties))
    solver = cp_model.CpSolver()

    # Act
    solver.solve(model)

    # Assert
    assert solver.objective_value == expected_penalty


@pytest.mark.parametrize("pieces, expected_penalty", STRETCH_CASES)
def test_penalty_counts_only_real_blocks_over_even_when_maximised(
        pieces: list[tuple[str, int, int]], expected_penalty: int):
    """Even when the solver makes the penalty as high as it can, it is the real count."""
    # Arrange
    model, problem, works = _model_with_fixed_work(pieces=pieces)
    penalties = add_preferred_max_stretch_penalty(model, problem, works)
    model.maximize(cp_model.LinearExpr.sum(penalties))  # Maximise instead of minimise
    solver = cp_model.CpSolver()

    # Act
    solver.solve(model)

    # Assert
    assert solver.objective_value == expected_penalty


# Switching the rule on and off. The rule checks settings.soft_rules itself, so these
# tests call it directly (no solving needed); the tests above show that solve() uses it.

def test_preferred_max_stretch_penalty_that_is_off_returns_nothing():
    """With the rule switched off, add_preferred_max_stretch_penalty returns []."""
    # Arrange
    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    soft_rule_turned_off = replace(RULES, soft_rules=frozenset())

    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS)],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=soft_rule_turned_off)

    model = cp_model.CpModel()
    works = create_variables(model, problem)

    # Act
    penalties = add_preferred_max_stretch_penalty(model, problem, works)

    # Assert
    assert penalties == []


def test_preferred_max_stretch_penalty_that_is_on_returns_terms():
    """With the rule on, a volunteer who could work over 2 hours gives penalty terms."""
    # Arrange
    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS)],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    model = cp_model.CpModel()
    works = create_variables(model, problem)

    # Act
    penalties = add_preferred_max_stretch_penalty(model, problem, works)

    # Assert
    assert len(penalties) > 0

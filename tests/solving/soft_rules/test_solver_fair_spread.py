from dataclasses import replace

import pytest
from ortools.sat.python import cp_model

from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks
from scheduler.solving.soft_rules import add_fair_spread_penalty
from scheduler.solving.solver import solve
from scheduler.solving.variables import Works, create_variables


# Passed explicitly instead of relying on the defaults in model.py. Only the fair spread
# soft rule is switched on, so no other soft rule can change the outcome; the fewer
# stretches weight is here for the tests that switch both rules on.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"),
                 soft_rules=frozenset({"fair_spread"}),
                 weight_over_fair_share=4, weight_work_stretch=20)

ALL_DAYS = all_blocks(RULES)

# Without an objective CP-SAT takes any valid schedule, so after implementing, check with a
# few seeds that the preference tests go red without the rule. The targets themselves are
# tested in test_fair_share_targets.py; here every volunteer is there all weekend, so the
# demand is shared equally.


def test_work_is_shared_by_volunteers_below_their_fair_share():
    """Two equal volunteers each work their fair share, not one of them everything."""
    # Arrange
    # Tickets needs 1 in blocks 0-7 (2 hours), Mock Mane and Testy Hooves both all
    # weekend -> targets 4 and 4. Expected: each works exactly 4 blocks (without the rule
    # CP-SAT gave this to one person in every seed tried).
    names = ["Mock Mane", "Testy Hooves"]
    volunteers = []
    for name in names:
        volunteers.append(Volunteer(name=name, skills={"Tickets": 1},
                                    available_blocks=ALL_DAYS))

    demand = {}
    for block in range(0, 8):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    for name in names:
        blocks = 0

        for (volunteer_name, post, block) in schedule.assignments:
            if volunteer_name == name:
                blocks += 1

        assert blocks == 4, name


def test_work_above_the_fair_share_that_cannot_be_avoided_still_gives_a_schedule():
    """When only one volunteer is qualified, they still get all the work."""
    # Arrange
    # Tickets needs 1 in blocks 0-7, Mock Mane qualified, Testy Hooves available but
    # not qualified (skills={"Infobooth": 1}) -> targets 4 and 4, but Mock Mane works all 8.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 8):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets"), Post("Infobooth")],
                      demand=demand,
                      settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    blocks_per_volunteer = {"Mock Mane": 0, "Testy Hooves": 0}
    for (volunteer_name, post, block) in schedule.assignments:
        blocks_per_volunteer[volunteer_name] += 1

    assert blocks_per_volunteer["Mock Mane"] == 8
    assert blocks_per_volunteer["Testy Hooves"] == 0


# Together with the fewer stretches rule: the weights decide which preference wins.
# Tickets needs 1 in blocks 0-11 (3 hours), Mock Mane and Testy Hooves both all weekend,
# so the targets are 6 and 6.
#   one person works all 3 hours: 1 stretch (20) + 6 blocks above the target x weight
#   split between the two:        2 stretches (40), nothing above the target
# So weight 4 (20 + 24 = 44 against 40) gives the split, weight 2 (20 + 12 = 32 against
# 40) gives one person.

def test_fair_spread_wins_over_fewer_stretches_with_a_high_weight():
    """With weight 4 per block above the fair share, the 3-hour opening is split."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    new_rules = replace(RULES, soft_rules=frozenset({"fair_spread", "fewer_stretches"}))

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=new_rules)

    # Act
    schedule = solve(problem)

    # Assert
    work_stretches = 0
    for volunteer in volunteers:
        work_stretches += len(schedule.work_stretches_of(volunteer.name))

    assert work_stretches == 2


def test_fewer_stretches_win_over_fair_spread_with_a_low_weight():
    """With weight 2 per block above the fair share, one volunteer works all 3 hours."""
    # Arrange
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    new_rules = replace(RULES, soft_rules=frozenset({"fair_spread", "fewer_stretches"}),
                        weight_over_fair_share=2)

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=new_rules)

    # Act
    schedule = solve(problem)

    # Assert
    work_stretches = 0
    for volunteer in volunteers:
        work_stretches += len(schedule.work_stretches_of(volunteer.name))

    assert work_stretches == 1


# Counting blocks above the fair share. Like in the stretch rule tests: the work is fixed
# by hand and only this rule is added (no hard rules), so the penalty is exactly what the
# rule counts. Tickets is open in blocks 0-31 (32 blocks), Mock Mane and Testy Hooves are
# both there all weekend, so both targets are 16. Each case lists the pieces Mock Mane
# works as (post, first block, block after the last); Testy Hooves works nothing (below
# the target costs nothing). The weight is 4 per block above the target.
FAIR_SHARE_CASES = [([], 0),                       # no work
                    ([("Tickets", 0, 10)], 0),     # 10 blocks: below the target
                    ([("Tickets", 0, 16)], 0),     # 16 blocks: exactly the target
                    ([("Tickets", 0, 20)], 16),    # 20 blocks: 4 above
                    ([("Tickets", 0, 32)], 64)]    # 32 blocks: 16 above


def _model_with_fixed_work(pieces: list[tuple[str, int, int]]
                           ) -> tuple[cp_model.CpModel, Problem, Works]:
    """A model with Mock Mane's variables fixed to 1 inside the pieces, all others to 0."""
    demand = {}
    for block in range(0, 32):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[Volunteer(name="Mock Mane",
                                            skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS),
                                  Volunteer(name="Testy Hooves",
                                            skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS)],
                      posts=[Post("Tickets")],
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
        if (post, block) in worked and volunteer_name == "Mock Mane":
            model.add(variable == 1)
        else:
            model.add(variable == 0)

    return (model, problem, works)


@pytest.mark.parametrize("pieces, expected_penalty", FAIR_SHARE_CASES)
def test_each_block_above_the_fair_share_costs_the_weight(
        pieces: list[tuple[str, int, int]], expected_penalty: int):
    """Each block a volunteer works above their fair share costs the weight."""
    # Arrange
    model, problem, works = _model_with_fixed_work(pieces=pieces)
    penalties = add_fair_spread_penalty(model, problem, works)
    model.minimize(cp_model.LinearExpr.sum(penalties))
    solver = cp_model.CpSolver()

    # Act
    solver.solve(model)

    # Assert
    assert solver.objective_value == expected_penalty


@pytest.mark.parametrize("pieces, expected_penalty", FAIR_SHARE_CASES)
def test_penalty_counts_only_real_blocks_above_even_when_maximised(
        pieces: list[tuple[str, int, int]], expected_penalty: int):
    """Even when the solver makes the penalty as high as it can, it is the real count."""
    # Arrange
    model, problem, works = _model_with_fixed_work(pieces=pieces)
    penalties = add_fair_spread_penalty(model, problem, works)
    model.maximize(cp_model.LinearExpr.sum(penalties))
    solver = cp_model.CpSolver()

    # Act
    solver.solve(model)

    # Assert
    assert solver.objective_value == expected_penalty


# Switching the rule on and off. The rule checks settings.soft_rules itself, so these
# tests call it directly (no solving needed); the tests above show that solve() uses it.

def test_fair_spread_penalty_that_is_off_returns_nothing():
    """With the rule switched off, add_fair_spread_penalty returns []."""
    # Arrange
    volunteers = [Volunteer(name="Star Fixture", skills={"Tickets": 3},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 8):
        demand[("Tickets", block)] = 1

    no_rules = replace(RULES, soft_rules=frozenset())

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=no_rules)

    model = cp_model.CpModel()
    works = create_variables(model, problem)

    # Act
    penalties = add_fair_spread_penalty(model, problem, works)

    # Assert
    assert penalties == []


def test_fair_spread_penalty_that_is_on_returns_terms():
    """With the rule on, a volunteer who could work above their fair share gives terms."""
    # Arrange
    volunteers = [Volunteer(name="Star Fixture", skills={"Tickets": 3},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 8):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    model = cp_model.CpModel()
    works = create_variables(model, problem)

    # Act
    penalties = add_fair_spread_penalty(model, problem, works)

    # Assert
    assert len(penalties) > 0

from dataclasses import replace

import pytest
from ortools.sat.python import cp_model

from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks
from scheduler.solving.soft_rules import add_fewer_stretches_penalty
from scheduler.solving.solver import solve
from scheduler.solving.variables import create_variables


# Passed explicitly instead of relying on the defaults in model.py. Only the fewer
# stretches soft rule is switched on, so no other soft rule can change the outcome; the
# skill score weights are here for the tests that switch both rules on.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"),
                 soft_rules=frozenset({"fewer_stretches"}),
                 weight_work_stretch=20,
                 weight_skill_score_1=6, weight_skill_score_2=2, weight_skill_score_3=0)

ALL_DAYS = all_blocks(RULES)

# Without an objective CP-SAT takes any valid schedule, so after implementing, check with a
# few seeds that the preference tests go red without the rule.


def test_one_volunteer_works_the_whole_opening_instead_of_two_splitting_it():
    """Tickets open for 3 hours goes to one volunteer, not split into two stretches."""
    # Arrange
    names = ["Mock Mane", "Testy Hooves", "Dummy Dash", "Sample Sparkle"]
    volunteers = []
    for name in names:
        volunteers.append(Volunteer(name=name, skills={"Tickets": 1},
                                    available_blocks=set(range(0, 12))))

    demand = {}
    for block in range(0, 12):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # One of the four works the whole opening
    possible_schedules = []
    for name in names:
        schedule_of_one = set()
        for block in range(0, 12):
            schedule_of_one.add((name, "Tickets", block))
        possible_schedules.append(schedule_of_one)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments in possible_schedules


def test_stretches_that_cannot_be_joined_still_give_a_schedule():
    """Two openings with a gap still give a schedule; the rule is only a preference."""
    # Arrange
    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 1
    for block in range(8, 12):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS)],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    expected = set()
    for block in range(0, 4):
        expected.add(("Mock Mane", "Tickets", block))
    for block in range(8, 12):
        expected.add(("Mock Mane", "Tickets", block))

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected


# Together with the skill score rule: the weights decide which preference wins.
# Tickets needs 1 in blocks 0-7. Mock Mane (score 1, 6 points per block) available all
# day, Star Fixture (score 3, 0 points) only blocks 0-3.
#   split, Star Fixture 0-3 and Mock Mane 4-7: 2 stretches, skill score 4 x 6 = 24
#   Mock Mane alone 0-7:                        1 stretch,  skill score 8 x 6 = 48
# So weight 30 (60 + 24 = 84 against 30 + 48 = 78) gives Mock Mane alone, weight 20
# (40 + 24 = 64 against 20 + 48 = 68) gives the split.


def test_fewer_stretches_win_over_the_skill_score_with_a_high_weight():
    """With weight 30 per stretch, Mock Mane works the whole opening despite the skill score."""
    # Arrange
    volunteers = [Volunteer(name="Star Fixture", skills={"Tickets": 3},
                            available_blocks=set(range(0, 4))),
                  Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 8):
        demand[("Tickets", block)] = 1

    both_rules = replace(RULES, weight_work_stretch=30,
                         soft_rules=frozenset({"fewer_stretches", "skill_score"}))

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=both_rules)

    expected = set()
    for block in range(0, 8):
        expected.add(("Mock Mane", "Tickets", block))

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected


def test_skill_score_wins_over_fewer_stretches_with_a_low_weight():
    """With weight 20 per stretch, Star Fixture takes the first hour and Mock Mane the rest."""
    # Arrange
    volunteers = [Volunteer(name="Star Fixture", skills={"Tickets": 3},
                            available_blocks=set(range(0, 4))),
                  Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 8):
        demand[("Tickets", block)] = 1

    both_rules = replace(RULES, weight_work_stretch=20,
                         soft_rules=frozenset({"fewer_stretches", "skill_score"}))

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=both_rules)

    expected = set()
    for block in range(0, 4):
        expected.add(("Star Fixture", "Tickets", block))
    for block in range(4, 8):
        expected.add(("Mock Mane", "Tickets", block))

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected


# Counting stretches. Like in test_solver_round_times.py: one volunteer's work is fixed by
# hand and only this rule is added (no hard rules), so the lowest penalty CP-SAT can reach
# is exactly what the rule counts. Each case lists the pieces Mock Mane works as
# (post, first block, block after the last); Tickets and Infobooth are open in blocks 0-15.

@pytest.mark.parametrize("pieces, expected_penalty",
                         [([], 0),                          # no work, no stretch
                          ([("Tickets", 0, 6)], 20),        # one stretch, from block 0
                          ([("Tickets", 0, 4),
                            ("Tickets", 8, 12)], 40),       # two stretches with a gap
                          ([("Tickets", 0, 4),
                            ("Infobooth", 4, 8)], 20)])     # post switch: still one stretch
def test_each_work_stretch_costs_the_weight(pieces: list[tuple[str, int, int]],
                                            expected_penalty: int):
    """Each work stretch costs the weight once, also when it switches post halfway."""
    # Arrange
    demand = {}
    for block in range(0, 16):
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

    penalties = add_fewer_stretches_penalty(model, problem, works)
    model.minimize(cp_model.LinearExpr.sum(penalties))
    solver = cp_model.CpSolver()

    # Act
    solver.solve(model)

    # Assert
    assert solver.objective_value == expected_penalty


# The penalty must be exact for every schedule, not only the best one: the same cases, but
# CP-SAT tries to make the penalty as HIGH as possible. Only helper variables bounded on
# both sides keep it at the real count.

@pytest.mark.parametrize("pieces, expected_penalty",
                         [([], 0),                          # no work, no stretch
                          ([("Tickets", 0, 6)], 20),        # one stretch, from block 0
                          ([("Tickets", 0, 4),
                            ("Tickets", 8, 12)], 40),       # two stretches with a gap
                          ([("Tickets", 0, 4),
                            ("Infobooth", 4, 8)], 20)])     # post switch: still one stretch
def test_penalty_counts_only_real_stretches_even_when_maximised(pieces: list[tuple[str, int, int]],
                                                                expected_penalty: int):
    """Even when the solver makes the penalty as high as it can, it is the real count."""
    # Arrange
    demand = {}
    for block in range(0, 16):
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

    penalties = add_fewer_stretches_penalty(model, problem, works)
    model.maximize(cp_model.LinearExpr.sum(penalties))  # Maximise instead of minimise
    solver = cp_model.CpSolver()

    # Act
    solver.solve(model)

    # Assert
    assert solver.objective_value == expected_penalty


# Switching the rule on and off. The rule checks settings.soft_rules itself, so these
# tests call it directly (no solving needed); the tests above show that solve() uses it.

def test_fewer_stretches_penalty_that_is_off_returns_nothing():
    """With the fewer stretches rule switched off, add_fewer_stretches_penalty returns []."""
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
    penalties = add_fewer_stretches_penalty(model, problem, works)

    # Assert
    assert penalties == []


def test_fewer_stretches_penalty_that_is_on_returns_terms():
    """With the rule on, a volunteer who could work gives penalty terms."""
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
    penalties = add_fewer_stretches_penalty(model, problem, works)

    # Assert
    assert len(penalties) > 0

from dataclasses import replace

from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks
from scheduler.solving.solver import solve


# Passed explicitly instead of relying on the defaults in model.py. Only the skill score
# soft rule is switched on, so the penalty of a schedule is easy to work out by hand:
# 6 points for every block worked at a post with skill score 1.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"),
                 soft_rules=frozenset({"skill_score"}),
                 weight_skill_score_1=6, weight_skill_score_2=2, weight_skill_score_3=0)

ALL_DAYS = all_blocks(RULES)

# The solver tells what it knows about the schedule it found: whether it is proven to be
# the best possible (CP-SAT's status OPTIMAL), its penalty, and the lowest penalty any
# schedule could have. A schedule that is not proven optimal (time limit reached) can't
# be made reliably in a test; the command line tests use a fake solve for that.


def test_schedule_found_without_a_time_limit_is_proven_optimal():
    """Without a time limit CP-SAT searches until it has proven the schedule is the best."""
    # Arrange
    # Two volunteers for Tickets in blocks 0-3, so CP-SAT has a choice to make: Star
    # Fixture (score 3, 0 points) or Mock Mane (score 1, 6 points per block).
    volunteers = [Volunteer(name="Star Fixture", skills={"Tickets": 3},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.proven_optimal is True


def test_schedule_reports_its_penalty():
    """The schedule's penalty is the sum of its soft rule penalties."""
    # Arrange
    # Only Mock Mane, skill score 1 for Tickets (6 points per block), Tickets needs 1 in
    # blocks 0-3: penalty 4 x 6 = 24.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.penalty == 24


def test_lowest_possible_penalty_of_an_optimal_schedule_is_its_own_penalty():
    """For a proven optimal schedule, the lowest possible penalty equals its penalty."""
    # Arrange
    # The same scenario as above: penalty 24, and no schedule can do better.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=RULES)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.lowest_possible_penalty == 24


def test_schedule_with_only_hard_rules_has_penalty_0():
    """With no soft rule switched on, every valid schedule is the best one: penalty 0."""
    # Arrange
    # Mock Mane has skill score 1, which would cost 24 points with the skill score rule
    # on; with no soft rule switched on it costs nothing.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 1

    hard_rules_only = replace(RULES, soft_rules=frozenset())

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=hard_rules_only)

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.penalty == 0

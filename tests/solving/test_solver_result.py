from dataclasses import replace

import pytest

from scheduler.errors import NoScheduleFound
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


# --- the first schedule ---
# solve() can tell its caller as soon as CP-SAT finds a first schedule, by calling the
# on_first_schedule function with the seconds searched so far and that schedule's penalty.
# Each test passes a small function that remembers every call in a list.

def test_solve_reports_the_first_schedule_once():
    """on_first_schedule is called exactly once, even if CP-SAT finds better schedules later."""
    # Arrange
    # Six volunteers with mixed skill scores, Tickets needs 2 and Infobooth 1 in blocks
    # 0-15: enough choice that CP-SAT finds several schedules on its way to the best (tried:
    # at least 5 in each of 20 runs). With fewer volunteers it finds the best one at once,
    # and the test would also pass if every schedule were reported.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 2},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 2, "Infobooth": 3},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Dummy Dash", skills={"Tickets": 3, "Infobooth": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Sample Sparkle", skills={"Tickets": 1, "Infobooth": 2},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Placeholder Pip", skills={"Tickets": 2, "Infobooth": 3},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Star Fixture", skills={"Tickets": 3, "Infobooth": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 16):
        demand[("Tickets", block)] = 2
        demand[("Infobooth", block)] = 1

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets"), Post("Infobooth")],
                      demand=demand, settings=RULES)

    calls = []

    def remember(seconds: float, penalty: int) -> None:
        calls.append((seconds, penalty))

    # Act
    solve(problem, on_first_schedule=remember)

    # Assert
    assert len(calls) == 1


def test_first_schedule_is_reported_with_its_penalty():
    """on_first_schedule gets the penalty of the first schedule CP-SAT found."""
    # Arrange
    # Only Mock Mane, skill score 1 for Tickets (6 points per block), Tickets needs 1 in
    # blocks 0-3: only one schedule is possible, so the first one has penalty 4 x 6 = 24.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=RULES)

    penalties = []

    def remember(seconds: float, penalty: int) -> None:
        penalties.append(penalty)

    # Act
    solve(problem, on_first_schedule=remember)

    # Assert
    assert penalties == [24]


def test_first_schedule_is_reported_with_the_seconds_since_solving_started():
    """on_first_schedule gets the seconds CP-SAT searched, as a number of at least 0."""
    # Arrange
    # The same scenario as above. How long CP-SAT takes can't be predicted, so the test only
    # checks that it is a float and not negative.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=RULES)

    seconds_reported = []

    def remember(seconds: float, penalty: int) -> None:
        seconds_reported.append(seconds)

    # Act
    solve(problem, on_first_schedule=remember)

    # Assert
    assert len(seconds_reported) == 1
    assert isinstance(seconds_reported[0], float)
    assert seconds_reported[0] >= 0


def test_nothing_is_reported_when_no_schedule_is_possible():
    """When CP-SAT finds no schedule at all, on_first_schedule is never called."""
    # Arrange
    # Only Mock Mane, Tickets needs 1 in blocks 0-15 (4 hours): longer than the maximum
    # work stretch. The checks before solving don't see this, CP-SAT does.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 16):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=RULES)

    calls = []

    def remember(seconds: float, penalty: int) -> None:
        calls.append((seconds, penalty))

    # Act
    with pytest.raises(NoScheduleFound):
        solve(problem, on_first_schedule=remember)

    # Assert
    assert calls == []

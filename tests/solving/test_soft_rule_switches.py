import pytest
from ortools.sat.python import cp_model

from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks
from scheduler.solving import soft_rules
from scheduler.solving.solver import solve
from scheduler.solving.variables import Works


def test_soft_rule_that_is_off_is_not_called(monkeypatch: pytest.MonkeyPatch):
    """A soft rule that is not in settings.soft_rules is not applied by solve()."""
    # Arrange
    # A fake rule that only remembers it was called; monkeypatch puts the real one back
    # after the test.
    calls: list[Problem] = []

    def fake_penalty(model: cp_model.CpModel, problem: Problem,
                     works: Works) -> list[cp_model.LinearExpr]:
        calls.append(problem)
        return []          # no penalty terms: solve() can carry on as normal

    monkeypatch.setattr(soft_rules, "add_skill_score_penalty", fake_penalty)

    # soft_rules is not given, so it is empty: every soft rule is off.
    settings = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                        days=("Friday", "Saturday", "Sunday"))

    # One volunteer and Tickets open in blocks 0-3: a schedule exists, so solve() runs
    # all the way to the soft rules.
    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 1
    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 3},
                                            available_blocks=all_blocks(settings))],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=settings)

    # Act
    solve(problem)

    # Assert
    assert calls == []


def test_soft_rule_that_is_on_is_called(monkeypatch: pytest.MonkeyPatch):
    """A soft rule that is in settings.soft_rules is applied by solve() exactly once."""
    # Arrange
    # A fake rule that only remembers it was called; monkeypatch puts the real one back
    # after the test.
    calls: list[Problem] = []

    def fake_penalty(model: cp_model.CpModel, problem: Problem,
                     works: Works) -> list[cp_model.LinearExpr]:
        calls.append(problem)
        return []          # no penalty terms: solve() can carry on as normal

    monkeypatch.setattr(soft_rules, "add_skill_score_penalty", fake_penalty)

    # Only the skill score soft rule is switched on.
    settings = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                        days=("Friday", "Saturday", "Sunday"),
                        soft_rules=frozenset({"skill_score"}))

    # One volunteer and Tickets open in blocks 0-3: a schedule exists, so solve() runs
    # all the way to the soft rules.
    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 1
    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 3},
                                            available_blocks=all_blocks(settings))],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=settings)

    # Act
    solve(problem)

    # Assert
    assert calls == [problem]

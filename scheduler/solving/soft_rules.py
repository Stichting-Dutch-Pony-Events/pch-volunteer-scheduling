"""Soft rules for the schedule, one function per rule.

A soft rule may be broken, but each time it costs penalty points; the solver looks for
the schedule with the fewest points in total. Each add_..._penalty function adds the
helper variables it needs to the model and returns its penalty terms, already multiplied
by the rule's weight from the settings; solve() adds them all up and asks CP-SAT to
minimise the sum. Weights are whole points per time block (15 minutes).

They all take the same arguments as the hard rules: the model, the problem, and the works
variables made by create_variables (see Works in variables.py). solve() only calls a rule
when its name is in settings.soft_rules; the valid names are SOFT_RULE_NAMES in model.py.
"""
from ortools.sat.python import cp_model

from scheduler.model import Problem
from scheduler.solving.variables import Works


def add_skill_score_penalty(model: cp_model.CpModel, problem: Problem,
                            works: Works) -> list[cp_model.LinearExpr]:
    """Soft rule: prefer volunteers with a higher skill score for the post.

    Every block a volunteer works at a post costs the weight of their skill score for that
    post (settings.weight_skill_score_1, _2 or _3).
    """
    raise NotImplementedError

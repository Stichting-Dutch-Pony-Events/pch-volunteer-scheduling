"""Soft rules for the schedule, one function per rule.

A soft rule may be broken, but each time it costs penalty points; the solver looks for
the schedule with the fewest points in total. Each add_..._penalty function adds the
helper variables it needs to the model and returns its penalty terms, already multiplied
by the rule's weight from the settings; solve() adds them all up and asks CP-SAT to
minimise the sum. Weights are whole points: per time block of 15 minutes (skill score)
or per start or end of a work stretch (round times).

They all take the same arguments as the hard rules: the model, the problem, and the works
variables made by create_variables (see Works in variables.py). solve() only calls a rule
when its name is in settings.soft_rules; the valid names are SOFT_RULE_NAMES in model.py.
"""
from ortools.sat.python import cp_model

from scheduler.debug import debug_print
from scheduler.model import Problem
from scheduler.solving.variables import (Works, blocks_of_convention,
                                         variables_by_volunteer_and_block, variables_of)


def add_skill_score_penalty(model: cp_model.CpModel, problem: Problem,
                            works: Works) -> list[cp_model.LinearExpr]:
    """Soft rule: prefer volunteers with a higher skill score for the post.

    Every block a volunteer works at a post costs the weight of their skill score for that
    post (settings.weight_skill_score_1, _2 or _3).
    """
    # if the rule is not added, then return nothing
    if "skill_score" not in problem.settings.soft_rules:
        debug_print("add_skill_score_penalty: skipping the rule")
        return []

    debug_print("add_skill_score_penalty: adding the rule")

    # create a dictionary of volunteers by name
    volunteers_by_name = {}
    for volunteer in problem.volunteers:
        volunteers_by_name[volunteer.name] = volunteer

    # create a dictionary of weight by scores
    weight_of_score = {1: problem.settings.weight_skill_score_1,
                       2: problem.settings.weight_skill_score_2,
                       3: problem.settings.weight_skill_score_3}

    # per work (block a volunteer can work), create a penalty
    penalties = []
    for (volunteer_name, post_name, block), variable in works.items():
        skill_score = volunteers_by_name[volunteer_name].skills[post_name]
        weight = weight_of_score[skill_score]

        if weight > 0:
            penalties.append(variable * weight)

    return penalties


def add_round_times_penalty(model: cp_model.CpModel, problem: Problem,
                            works: Works) -> list[cp_model.LinearExpr]:
    """Soft rule: work stretches start and end on the hour or half hour.

    Every work stretch (continuous work, also across posts) that starts or ends on :15 or
    :45 costs settings.weight_off_round_time, once for the start and once for the end.
    A switch to another post inside a stretch is not a start.
    """
    # if the rule is not added (or costs nothing), then return nothing
    weight = problem.settings.weight_off_round_time
    if "round_times" not in problem.settings.soft_rules or weight == 0:
        debug_print("add_round_times_penalty: skipping the rule")
        return []

    debug_print("add_round_times_penalty: adding the rule")

    lookup = variables_by_volunteer_and_block(works)

    penalties = []
    for block in blocks_of_convention(problem):
        if block % 2 == 0:  # Block is even, thus starts at :00 or :30
            continue

        for volunteer in problem.volunteers:
            # Collect the variables of every post this volunteer could work in this block,
            # and in the block before.
            works_before = variables_of(lookup, volunteer.name, block - 1, block)
            works_now = variables_of(lookup, volunteer.name, block, block + 1)
            if works_before == [] and works_now == []:
                continue

            # changes = 1 exactly when this volunteer starts or stops working at this
            # block (on :15 or :45). Each sum is 0 or 1 (nobody works two posts at once).
            # The two >= lines force changes to 1 on a start (free before, working now) or
            # an end (working before, free now).
            # The two <= lines force changes to 0 when nothing changes (free-free or
            # working-working). Minimising would do that anyway at the best schedule, but
            # a schedule found earlier (time limit, Ctrl+C) would otherwise report a
            # penalty that is too high.
            changes = model.new_bool_var(f"{volunteer.name} starts or ends at {block}")
            model.add(changes >= sum(works_before) - sum(works_now))
            model.add(changes >= sum(works_now) - sum(works_before))
            model.add(changes <= sum(works_before) + sum(works_now))
            model.add(changes <= 2 - sum(works_before) - sum(works_now))

            penalties.append(changes * weight)

    return penalties

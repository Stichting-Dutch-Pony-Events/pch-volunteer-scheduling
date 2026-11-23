"""Soft rules for the schedule, one function per rule.

A soft rule may be broken, but each time it costs penalty points; the solver looks for
the schedule with the fewest points in total. Each add_..._penalty function adds the
helper variables it needs to the model and returns its penalty terms, already multiplied
by the rule's weight from the settings; solve() adds them all up and asks CP-SAT to
minimise the sum. Weights are whole points: per time block of 15 minutes (skill score)
per start or end of a work stretch (round times), per work stretch (fewer stretches) or
per time block beyond the preferred maximum stretch (preferred maximum stretch) or per
time block above a volunteer's fair share of the work (fair spread).

They all take the same arguments as the hard rules: the model, the problem, and the works
variables made by create_variables (see Works in variables.py). solve() only calls a rule
when its name is in settings.soft_rules; the valid names are SOFT_RULE_NAMES in model.py.
"""
from ortools.sat.python import cp_model

from scheduler.debug import debug_print
from scheduler.model import BLOCKS_PER_DAY, MINUTES_PER_BLOCK, Problem
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


def add_fewer_stretches_penalty(model: cp_model.CpModel, problem: Problem,
                                works: Works) -> list[cp_model.LinearExpr]:
    """Soft rule: fewer, longer work stretches.

    Every work stretch (continuous work, also across posts) costs
    settings.weight_work_stretch, once, however long it is. A switch to another post
    inside a stretch is not a new stretch.
    """
    # if the rule is not added (or costs nothing), then return nothing
    weight = problem.settings.weight_work_stretch
    if "fewer_stretches" not in problem.settings.soft_rules or weight == 0:
        debug_print("add_fewer_stretches_penalty: skipping the rule")
        return []

    debug_print("add_fewer_stretches_penalty: adding the rule")

    lookup = variables_by_volunteer_and_block(works)

    penalties = []
    for block in blocks_of_convention(problem):
        for volunteer in problem.volunteers:
            works_before = variables_of(lookup, volunteer.name, block - 1, block)
            works_now = variables_of(lookup, volunteer.name, block, block + 1)
            if works_now == []:
                continue

            # Counting the number of starts of stretches
            starts = model.new_bool_var(f"{volunteer.name} starts at block {block}")
            model.add(starts >= sum(works_now) - sum(works_before))  # forced 1 at start stretch
            model.add(starts <= sum(works_now))  # forced 0 if not working now
            model.add(starts <= 1 - sum(works_before))  # forced 0 if working before

            penalties.append(starts * weight)

    return penalties


def add_preferred_max_stretch_penalty(model: cp_model.CpModel, problem: Problem,
                                      works: Works) -> list[cp_model.LinearExpr]:
    """Soft rule: work stretches of at most the preferred length.

    Every time block of a work stretch (continuous work, also across posts) beyond
    settings.preferred_max_stretch_minutes costs settings.weight_over_preferred_stretch.
    A stretch of 3 hours with a preferred maximum of 2 hours costs 4 times the weight.
    """
    # if the rule is not added (or costs nothing), then return nothing
    weight = problem.settings.weight_over_preferred_stretch
    if "preferred_max_stretch" not in problem.settings.soft_rules or weight == 0:
        debug_print("add_preferred_max_stretch_penalty: skipping the rule")
        return []

    debug_print("add_preferred_max_stretch_penalty: adding the rule")

    lookup = variables_by_volunteer_and_block(works)

    preferred_blocks = problem.settings.preferred_max_stretch_minutes // MINUTES_PER_BLOCK

    penalties = []
    for block in blocks_of_convention(problem):
        for volunteer in problem.volunteers:
            works_before = variables_of(lookup, volunteer.name, block - preferred_blocks, block)
            works_now = variables_of(lookup, volunteer.name, block, block + 1)

            # Cheap test, if the volunteer can't work now, no penalty is required.
            if works_now == []:
                continue

            # Anytime now and all blocks in preferred length before are working, thats over
            over = model.new_bool_var((f"{volunteer.name} worked longer than prefered length "
                                       f"{problem.settings.preferred_max_stretch_minutes} "
                                       f"minutes at block {block}"))

            # Force 1 if all blocks before and now are worked
            model.add(over >= sum(works_now) + sum(works_before) - preferred_blocks)
            # Force 0 if not working now
            model.add(over <= sum(works_now))
            # Force 0 if not working ALL of the works before
            model.add(over * preferred_blocks <= sum(works_before))

            penalties.append(over * weight)

    return penalties


def fair_share_targets(problem: Problem) -> dict[str, int]:
    """Every volunteer's fair share of the work, in blocks: {volunteer name: target}.

    A convention day lasts from its first to its last block with demand (gaps included). A
    volunteer's weight is the sum of the lengths of the days on which they are available
    during those hours, however long; the total demand (in person-blocks) is divided in
    proportion to the weights, rounded to whole blocks, and at most their total hour
    limit. Without any demand every target is 0. Used by add_fair_spread_penalty (later).
    """
    # 1. The convention hours of each day: its first and last block with demand.
    #    The day of a block is block // BLOCKS_PER_DAY (night blocks already belong to the
    #    day before, so Saturday 01:00 counts as Saturday).
    first_and_last = {}  # day number -> (first block, last block)
    for (post, block) in problem.demand:
        day = block // BLOCKS_PER_DAY
        if day not in first_and_last:
            first_and_last[day] = (block, block)
        else:
            first_block, last_block = first_and_last[day]
            first_and_last[day] = (min(first_block, block), max(last_block, block))

    # 2. Each volunteer's weight: the lengths of the days on which they are there during the
    #    convention hours, for however short a time.
    weights = {}  # volunteer name -> weight in blocks
    for volunteer in problem.volunteers:
        weights[volunteer.name] = 0
        for (first_block, last_block) in first_and_last.values():
            convention_hours = set(range(first_block, last_block + 1))
            if volunteer.available_blocks & convention_hours:  # at least one block in common
                weights[volunteer.name] += last_block - first_block + 1

    # 3. Without any weight (no demand, or nobody there) everyone's target is 0; this also
    #    avoids dividing by zero below.
    total_weight = sum(weights.values())
    targets = {}  # volunteer name -> target in blocks
    if total_weight == 0:
        for volunteer in problem.volunteers:
            targets[volunteer.name] = 0
        return targets

    # 4. Share the total demand (in person-blocks) in proportion to the weights, rounded to
    #    whole blocks; a total hour limit caps the target (the rest is not shared out again).
    total_demand = sum(problem.demand.values())
    for volunteer in problem.volunteers:
        targets[volunteer.name] = round(total_demand * weights[volunteer.name] / total_weight)

        if volunteer.max_minutes_total is not None:
            limit_in_blocks = volunteer.max_minutes_total // MINUTES_PER_BLOCK
            targets[volunteer.name] = min(targets[volunteer.name], limit_in_blocks)

    return targets


def add_fair_spread_penalty(model: cp_model.CpModel, problem: Problem,
                            works: Works) -> list[cp_model.LinearExpr]:
    """Soft rule: spread the work fairly over the volunteers.

    Every time block a volunteer works above their fair share (fair_share_targets) costs
    settings.weight_over_fair_share. Working less than the fair share costs nothing: the
    total work is fixed by the demand, so less above the target for one means more for
    the others below theirs.
    """
    # TODO: not yet called from solve(); add the line there once this works.
    raise NotImplementedError

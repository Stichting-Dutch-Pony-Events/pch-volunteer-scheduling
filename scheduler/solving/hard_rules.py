"""Hard rules for the schedule, one function per rule.

Each add_..._rule function adds its constraints to the CP-SAT model. They all take the
same arguments: the model, the problem, and the works variables made by
create_variables (see Works in variables.py, which also has the helpers to find them).
"""
from ortools.sat.python import cp_model

from scheduler.helpers import debug_print
from scheduler.model import Problem, runs_of_consecutive_blocks, block_of
from scheduler.model import MINUTES_PER_BLOCK, BLOCKS_PER_DAY
from scheduler.solving.variables import Works, variables_by_volunteer_and_block
from scheduler.solving.variables import variables_of, blocks_of_convention


def add_demand_rule(model: cp_model.CpModel, problem: Problem, works: Works) -> None:
    """Hard rule: every open block of a post gets exactly the number of people needed."""
    debug_print("add_demand_rule: adding the rule")
    # Group the variables per (post, block) once, instead of searching works every time.
    variables_by_post_and_block = {}
    for (volunteer_name, post, block), var in works.items():
        if (post, block) not in variables_by_post_and_block:
            variables_by_post_and_block[(post, block)] = []
        variables_by_post_and_block[(post, block)].append(var)

    for (post, block), needed in problem.demand.items():
        # The variables of everyone who could work this post in this block.
        people_here = variables_by_post_and_block.get((post, block), [])
        model.add(sum(people_here) == needed)


def add_no_double_booking_rule(model: cp_model.CpModel, problem: Problem, works: Works) -> None:
    """Hard rule: no volunteer works more than one post in the same block."""
    debug_print("add_no_double_booking_rule: adding the rule")
    lookup = variables_by_volunteer_and_block(works)

    for block in blocks_of_convention(problem):
        for volunteer in problem.volunteers:
            # Collect the variables of every post this volunteer could work in this block.
            posts_here = variables_of(lookup, volunteer.name, block, block + 1)

            # Only needed when there are two or more options; 0 or 1 can never clash.
            if len(posts_here) > 1:
                model.add(sum(posts_here) <= 1)


def add_maximum_stretch_rule(model: cp_model.CpModel, problem: Problem, works: Works) -> None:
    """Hard rule: no volunteer works longer than the maximum number of blocks in a row."""
    debug_print("add_maximum_stretch_rule: adding the rule")
    max_number_of_blocks = problem.settings.max_stretch_minutes // MINUTES_PER_BLOCK
    lookup = variables_by_volunteer_and_block(works)

    for volunteer in problem.volunteers:
        for window_start in blocks_of_convention(problem):
            # Collect this volunteer's variables (any post) inside the moving window.
            posts_in_window = variables_of(lookup, volunteer.name, window_start,
                                           window_start + max_number_of_blocks + 1)

            model.add(sum(posts_in_window) <= max_number_of_blocks)


def add_minimum_break_rule(model: cp_model.CpModel, problem: Problem, works: Works) -> None:
    """Hard rule: no volunteer has a break shorter than the minimum break."""
    debug_print("add_minimum_break_rule: adding the rule")
    min_break_blocks = problem.settings.min_break_minutes // MINUTES_PER_BLOCK
    if min_break_blocks <= 1:
        return
    lookup = variables_by_volunteer_and_block(works)

    for volunteer in problem.volunteers:
        for block in blocks_of_convention(problem):
            for gap_length in range(1, min_break_blocks):
                # We look at a gap in blocks block + 1 .. block_after_gap - 1.
                block_after_gap = block + gap_length + 1

                # This volunteer's variables in three groups by block number:
                # the block before the gap, the gap itself, and the block after it.
                first = variables_of(lookup, volunteer.name, block, block + 1)
                middle = variables_of(lookup, volunteer.name, block + 1, block_after_gap)
                last = variables_of(lookup, volunteer.name, block_after_gap, block_after_gap + 1)

                # The pattern "work, gap_length blocks free, work" can only happen if
                # the volunteer could work both before and after the gap.
                if first and last:
                    # Ends count +1, the middle -1: only "work, all free, work" reaches 2.
                    model.add(sum(first) - sum(middle) + sum(last) <= 1)


def add_minimum_stretch_rule(model: cp_model.CpModel, problem: Problem, works: Works) -> None:
    """Hard rule: no volunteer works a stretch shorter than the minimum.

    Exception: a shorter stretch is allowed if it is exactly one short piece of demand
    (see _short_pieces), worked entirely at that piece's post.
    """
    debug_print("add_minimum_stretch_rule: adding the rule")
    min_stretch_blocks = problem.settings.min_stretch_minutes // MINUTES_PER_BLOCK
    if min_stretch_blocks <= 1:
        return

    short_pieces = _short_pieces(problem)  # worked out once, used for every volunteer
    lookup = variables_by_volunteer_and_block(works)

    for volunteer in problem.volunteers:
        for block in blocks_of_convention(problem):
            for run_length in range(1, min_stretch_blocks):
                # We look at a run of work in blocks block .. block_after_run - 1.
                block_after_run = block + run_length

                # If the volunteer can't work every block of this run, the short run can
                # never happen, so there is no need for a rule.
                can_work_whole_run = True
                for run_block in range(block, block_after_run):
                    if not variables_of(lookup, volunteer.name, run_block, run_block + 1):
                        can_work_whole_run = False
                if not can_work_whole_run:
                    continue

                before = variables_of(lookup, volunteer.name, block - 1, block)
                run = variables_of(lookup, volunteer.name, block, block_after_run)
                after = variables_of(lookup, volunteer.name, block_after_run,
                                     block_after_run + 1)

                # Exception: if this run is exactly a short piece of demand at some post,
                # an "escape" variable may switch the rule off, but only if the volunteer
                # works that post in every block of the piece.
                escapes = []
                for post, first_block, block_after_last in short_pieces:
                    if first_block != block or block_after_last != block_after_run:
                        continue  # a different piece
                    if post not in volunteer.skills:
                        continue  # not qualified for this post, so no escape
                    label = f"{volunteer.name} works short piece {post} {block}-{block_after_run}"
                    escape = model.new_bool_var(label)
                    for piece_block in range(block, block_after_run):
                        model.add(escape <= works[(volunteer.name, post, piece_block)])
                    escapes.append(escape)

                # The run counts +1 per block, the blocks around it -1. Only "free, all
                # run_length blocks working, free" reaches run_length, and that is a stretch
                # shorter than the minimum: forbidden, unless an escape is 1.
                model.add(-sum(before) + sum(run) - sum(after) <= run_length - 1 + sum(escapes))


def add_stay_at_post_rule(model: cp_model.CpModel, problem: Problem, works: Works) -> None:
    """Hard rule: within a work stretch a volunteer stays at their post.

    A volunteer only moves on to another post at a moment their post needs fewer people
    than in the block before (closing counts too). Then at most that many people may move
    on, and everyone who stops working there at that moment (a break, or the end of their
    availability) uses up one of those places. The volunteers that are moving would otherwise
    have had too short work-stretches. Handovers (one stops, another starts while the post
    needs the same people) are not limited by this rule.
    """
    debug_print("add_stay_at_post_rule: adding the rule")
    min_stretch_blocks = problem.settings.min_stretch_minutes // MINUTES_PER_BLOCK

    # Look at every post at every moment it was open just before: previous_block -> block.
    for (post, previous_block), needed_before in problem.demand.items():
        block = previous_block + 1
        needed_now = problem.demand.get((post, block), 0)   # 0 = closed
        drop = needed_before - needed_now                   # how many people fewer

        movers = []    # per volunteer: 1 if they move from this post to another post
        stoppers = []  # per volunteer: 1 if they stop working here and go nowhere
        for volunteer in problem.volunteers:
            was_here = works.get((volunteer.name, post, previous_block))
            if was_here is None:
                continue  # could not work this post just before, so can't move on from it

            # This volunteer's variables in the new block: at other posts, and at any post.
            elsewhere_now = []
            for other_post in problem.posts:
                if other_post.name != post:
                    other = works.get((volunteer.name, other_post.name, block))
                    if other is not None:
                        elsewhere_now.append(other)
            working_now = list(elsewhere_now)
            here_now = works.get((volunteer.name, post, block))
            if here_now is not None:
                working_now.append(here_now)

            if drop <= 0:
                # The post needs the same or more people: nobody moves on to another post.
                # "Here before" + "elsewhere now" may not both be 1.
                if elsewhere_now:
                    model.add(was_here + sum(elsewhere_now) <= 1)
                continue

            # The post needs fewer people: count who moves on and who stops. Each count
            # variable is forced to 1 when it happens (here before and elsewhere now: the
            # sum reaches 2). Setting it to 1 without reason would only make the limit
            # below stricter, so the solver never gains anything by that.
            if elsewhere_now:
                moves = model.new_bool_var(f"{volunteer.name} moves on from {post} in {block}")
                model.add(moves >= was_here + sum(elsewhere_now) - 1)
                movers.append(moves)

                # Only someone who has not yet worked a full minimum stretch may move on.
                # Collect their work (any post) in the min_stretch_blocks blocks just before
                # this block: if all of those are 1, the sum alone already reaches
                # min_stretch_blocks, so moves has to be 0.
                worked_just_before = []
                for earlier_block in range(block - min_stretch_blocks, block):
                    for any_post in problem.posts:
                        earlier = works.get((volunteer.name, any_post.name, earlier_block))
                        if earlier is not None:
                            worked_just_before.append(earlier)
                model.add(moves + sum(worked_just_before) <= min_stretch_blocks)
            stops = model.new_bool_var(f"{volunteer.name} stops at {post} in {block}")
            model.add(stops >= was_here - sum(working_now))
            stoppers.append(stops)

        # Only when someone moves on: movers and stoppers together fit in the drop.
        # (Without anyone moving, stopping is free: that covers normal handovers.)
        if movers:
            someone_moves = model.new_bool_var(f"someone moves on from {post} in {block}")
            for moves in movers:
                model.add(someone_moves >= moves)
            model.add(sum(movers) + sum(stoppers) <= drop).only_enforce_if(someone_moves)


def add_maximum_hours_per_day_rule(model: cp_model.CpModel, problem: Problem,
                                   works: Works) -> None:
    """Hard rule: a volunteer works at most max_minutes_per_day on each convention day.

    A convention day runs from 06:00 to 06:00, so night work counts toward the day it
    belongs to. Only time at a post counts. No limit (None) = no rule for that volunteer.
    """
    debug_print("add_maximum_hours_per_day_rule: adding the rule")

    lookup = variables_by_volunteer_and_block(works)
    for volunteer in problem.volunteers:
        if volunteer.max_minutes_per_day is None:
            continue

        for day in problem.settings.days:
            # A convention day: from its 06:00 up to the next day's 06:00 (not included).
            start_block = block_of(day, "06:00", problem.settings)
            block_after_last = start_block + BLOCKS_PER_DAY

            variables = variables_of(lookup, volunteer.name, start_block, block_after_last)
            if not variables:
                continue  # can't work that day (not available, or no demand): nothing to limit

            # Each variable is one block of MINUTES_PER_BLOCK minutes, so compare in blocks.
            model.add(sum(variables) <= volunteer.max_minutes_per_day // MINUTES_PER_BLOCK)


def add_maximum_hours_total_rule(model: cp_model.CpModel, problem: Problem,
                                 works: Works) -> None:
    """Hard rule: a volunteer works at most max_minutes_total over the whole convention.

    Only time at a post counts. No limit (None) = no rule for that volunteer.
    """
    debug_print("add_maximum_hours_total_rule: adding the rule")

    lookup = variables_by_volunteer_and_block(works)
    for volunteer in problem.volunteers:
        if volunteer.max_minutes_total is None:
            continue

        # The whole convention: from block 0 up to the end of the last day (not included).
        start_block = 0
        block_after_last = start_block + BLOCKS_PER_DAY * len(problem.settings.days)

        variables = variables_of(lookup, volunteer.name, start_block, block_after_last)
        if not variables:
            continue  # can't work at all (no demand they qualify for): nothing to limit

        # Each variable is one block of MINUTES_PER_BLOCK minutes, so compare in blocks.
        model.add(sum(variables) <= volunteer.max_minutes_total // MINUTES_PER_BLOCK)


def _short_pieces(problem: Problem) -> set[tuple[str, int, int]]:
    """Pieces of demand shorter than the minimum stretch, as (post, first_block, block_after_last).

    Looks at each post's demand layer by layer: layer k is every block where the post
    needs at least k people. A run in a layer that is shorter than the minimum is a short
    piece. Example: Tickets needs 2, 2, 1, 1, 1, 1 in blocks 0-5. Layer 2 is blocks 0-1,
    so ("Tickets", 0, 2) is a short piece.
    """
    min_blocks = problem.settings.min_stretch_minutes // MINUTES_PER_BLOCK

    # Which posts have demand, and the most people each post ever needs.
    highest_demand = {}
    for (post, block), needed in problem.demand.items():
        if needed > highest_demand.get(post, 0):
            highest_demand[post] = needed

    pieces = set()  # a set, so a piece found in two layers only counts once
    for post, highest in highest_demand.items():
        for layer in range(1, highest + 1):
            # Every block where this post needs at least `layer` people.
            blocks_in_layer = []
            for (demand_post, block), needed in problem.demand.items():
                if demand_post == post and needed >= layer:
                    blocks_in_layer.append(block)

            for first_block, block_after_last in runs_of_consecutive_blocks(blocks_in_layer):
                if block_after_last - first_block < min_blocks:
                    pieces.add((post, first_block, block_after_last))
    return pieces

"""Hard rules for the schedule, one function per rule.

Each add_..._rule function adds its constraints to the CP-SAT model. They all take the
same arguments: the model, the problem, and the works variables from solver.py
(a dict: (volunteer_name, post, block) -> variable).
"""
from ortools.sat.python import cp_model

from scheduler.model import Problem


def add_demand_rule(model: cp_model.CpModel, problem: Problem, works: dict):
    """Hard rule: every open block of a post gets exactly the number of people needed."""
    for (post, block), needed in problem.demand.items():
        # Collect the variables of everyone who could work this post in this block.
        people_here = []
        for key, var in works.items():
            volunteer_name, assigned_post, assigned_block = key
            if assigned_post == post and assigned_block == block:
                people_here.append(var)

        model.add(sum(people_here) == needed)


def add_no_double_booking_rule(model: cp_model.CpModel, problem: Problem, works: dict):
    """Hard rule: no volunteer works more than one post in the same block."""
    for block in _blocks_of_day(problem):
        for volunteer in problem.volunteers:
            # Collect the variables of every post this volunteer could work in this block.
            posts_here = _variables_of(works, volunteer.name, block, block + 1)

            # Only needed when there are two or more options; 0 or 1 can never clash.
            if len(posts_here) > 1:
                model.add(sum(posts_here) <= 1)


def add_maximum_stretch_rule(model: cp_model.CpModel, problem: Problem, works: dict):
    """Hard rule: no volunteer works longer than the maximum number of blocks in a row."""
    max_number_of_blocks = problem.settings.max_stretch_minutes // 15

    for volunteer in problem.volunteers:
        for window_start in _blocks_of_day(problem):
            # Collect this volunteer's variables (any post) inside the moving window.
            posts_in_window = _variables_of(works, volunteer.name, window_start,
                                            window_start + max_number_of_blocks + 1)

            model.add(sum(posts_in_window) <= max_number_of_blocks)


def add_minimum_break_rule(model: cp_model.CpModel, problem: Problem, works: dict):
    """Hard rule: no volunteer has a break shorter than the minimum break."""
    min_break_blocks = problem.settings.min_break_minutes // 15
    if min_break_blocks <= 1:
        return

    for volunteer in problem.volunteers:
        for block in _blocks_of_day(problem):
            for gap_length in range(1, min_break_blocks):
                # We look at a gap in blocks block + 1 .. block_after_gap - 1.
                block_after_gap = block + gap_length + 1

                # This volunteer's variables in three groups by block number:
                # the block before the gap, the gap itself, and the block after it.
                first = _variables_of(works, volunteer.name, block, block + 1)
                middle = _variables_of(works, volunteer.name, block + 1, block_after_gap)
                last = _variables_of(works, volunteer.name, block_after_gap, block_after_gap + 1)

                # The pattern "work, gap_length blocks free, work" can only happen if
                # the volunteer could work both before and after the gap.
                if first and last:
                    # Ends count +1, the middle -1: only "work, all free, work" reaches 2.
                    model.add(sum(first) - sum(middle) + sum(last) <= 1)


def add_minimum_stretch_rule(model: cp_model.CpModel, problem: Problem, works: dict):
    """Hard rule: no volunteer works a stretch shorter than the minimum.

    Exception: a shorter stretch is allowed if it is exactly one short piece of demand
    (see _short_pieces), worked entirely at that piece's post.
    """
    min_stretch_blocks = problem.settings.min_stretch_minutes // 15
    if min_stretch_blocks <= 1:
        return

    short_pieces = _short_pieces(problem)  # worked out once, used for every volunteer

    for volunteer in problem.volunteers:
        for block in _blocks_of_day(problem):
            for run_length in range(1, min_stretch_blocks):
                # We look at a run of work in blocks block .. block_after_run - 1.
                block_after_run = block + run_length

                # If the volunteer can't work every block of this run, the short run can
                # never happen, so there is no need for a rule.
                can_work_whole_run = True
                for run_block in range(block, block_after_run):
                    if not _variables_of(works, volunteer.name, run_block, run_block + 1):
                        can_work_whole_run = False
                if not can_work_whole_run:
                    continue

                before = _variables_of(works, volunteer.name, block - 1, block)
                run = _variables_of(works, volunteer.name, block, block_after_run)
                after = _variables_of(works, volunteer.name, block_after_run, block_after_run + 1)

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


def _blocks_in_demand(problem: Problem):
    """Every block that appears in the demand, each only once."""
    blocks = set()
    for (post, block) in problem.demand:
        blocks.add(block)
    return blocks


def _blocks_of_day(problem: Problem) -> range:
    """All blocks from the first to the last block in the demand, in order.

    Returns an empty range when there is no demand, so loops over it simply don't run.
    """
    blocks = _blocks_in_demand(problem)
    if len(blocks) == 0:
        return range(0)
    return range(min(blocks), max(blocks) + 1)


def _variables_of(works: dict, volunteer_name: str, first_block: int,
                  block_after_last: int) -> list:
    """This volunteer's variables (at any post) in blocks first_block up to block_after_last.

    Uses the same convention as range(): block_after_last itself is not included.
    """
    variables = []
    for key, var in works.items():
        assigned_volunteer, assigned_post, assigned_block = key
        in_range = first_block <= assigned_block < block_after_last
        if assigned_volunteer == volunteer_name and in_range:
            variables.append(var)
    return variables


def _runs_of_consecutive_blocks(blocks) -> list[tuple[int, int]]:
    """Split blocks into runs of consecutive blocks, as (first_block, block_after_last).

    Example: {0, 1, 2, 5, 6} -> [(0, 3), (5, 7)]
    """
    runs = []
    start = None      # first block of the run we are building
    previous = None   # the block we looked at just before this one
    for block in sorted(blocks):
        if start is None:
            start = block
        elif block != previous + 1:
            runs.append((start, previous + 1))  # gap: close this run
            start = block                       # ...and start a new one
        previous = block

    if start is not None:
        runs.append((start, previous + 1))      # the last run has no gap after it
    return runs


def _short_pieces(problem: Problem) -> set[tuple[str, int, int]]:
    """Pieces of demand shorter than the minimum stretch, as (post, first_block, block_after_last).

    Looks at each post's demand layer by layer: layer k is every block where the post
    needs at least k people. A run in a layer that is shorter than the minimum is a short
    piece. Example: Tickets needs 2, 2, 1, 1, 1, 1 in blocks 0-5. Layer 2 is blocks 0-1,
    so ("Tickets", 0, 2) is a short piece.
    """
    min_blocks = problem.settings.min_stretch_minutes // 15

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

            for first_block, block_after_last in _runs_of_consecutive_blocks(blocks_in_layer):
                if block_after_last - first_block < min_blocks:
                    pieces.add((post, first_block, block_after_last))
    return pieces

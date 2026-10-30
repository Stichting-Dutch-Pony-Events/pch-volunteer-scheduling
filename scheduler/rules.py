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
    for block in _blocks_in_demand(problem):
        for volunteer in problem.volunteers:
            # Collect the variables of every post this volunteer could work in this block.
            posts_here = []
            for key, var in works.items():
                volunteer_name, assigned_post, assigned_block = key
                if assigned_block == block and volunteer_name == volunteer.name:
                    posts_here.append(var)

            # Only needed when there are two or more options; 0 or 1 can never clash.
            if len(posts_here) > 1:
                model.add(sum(posts_here) <= 1)


def add_maximum_stretch_rule(model: cp_model.CpModel, problem: Problem, works: dict):
    """Hard rule: no volunteer works longer than the maximum number of blocks in a row."""
    max_number_of_blocks = problem.settings.max_stretch_minutes // 15

    for volunteer in problem.volunteers:
        for window_start in _blocks_of_day(problem):
            # Collect the variables of every post inside a moving window
            posts_in_window = []

            for key, var in works.items():
                volunteer_name, assigned_post, assigned_block = key
                in_window = window_start <= assigned_block <= window_start + max_number_of_blocks
                if volunteer_name == volunteer.name and in_window:
                    posts_in_window.append(var)

            model.add(sum(posts_in_window) <= max_number_of_blocks)


def add_minimum_break_rule(model: cp_model.CpModel, problem: Problem, works: dict):
    """Hard rule: no volunteer has a break shorter than the minimum break."""
    min_break_blocks = problem.settings.min_break_minutes // 15
    if min_break_blocks <= 1:
        return

    for volunteer in problem.volunteers:
        for block in _blocks_of_day(problem):
            for gap_length in range(1, min_break_blocks):
                # Sort this volunteer's variables into three groups by block number:
                # the block before the gap, the gap itself, and the block after it.
                first = []
                middle = []
                last = []
                for key, var in works.items():
                    volunteer_name, assigned_post, assigned_block = key
                    if volunteer_name != volunteer.name:
                        continue  # not this volunteer: skip to the next variable
                    if assigned_block == block:
                        first.append(var)
                    elif block < assigned_block <= block + gap_length:
                        middle.append(var)
                    elif assigned_block == block + gap_length + 1:
                        last.append(var)

                # The pattern "work, gap_length blocks free, work" can only happen if
                # the volunteer could work both before and after the gap.
                if first and last:
                    # Ends count +1, the middle -1: only "work, all free, work" reaches 2.
                    model.add(sum(first) - sum(middle) + sum(last) <= 1)


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

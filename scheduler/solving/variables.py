"""The solver's yes/no variables: creating them and finding them again.

create_variables makes them (solver.py calls it); variables_by_volunteer_and_block,
variables_of and blocks_of_convention help the rules find them again. Shared by the hard
rules, and later by the soft rules too.
"""
from ortools.sat.python import cp_model

from scheduler.debug import debug_print
from scheduler.model import Problem

# The solver's yes/no variables: (volunteer_name, post, block) -> variable.
Works = dict[tuple[str, str, int], cp_model.IntVar]

# The same variables grouped per (volunteer_name, block): see variables_by_volunteer_and_block.
VariablesByVolunteerAndBlock = dict[tuple[str, int], list[cp_model.IntVar]]


def create_variables(model: cp_model.CpModel, problem: Problem) -> Works:
    """One yes/no variable per (volunteer, post, block) that could happen.

    Only for open blocks (in demand), only if the volunteer has a skill score for that
    post and is available in that block. 1 = the volunteer works there in that block, 0 = not.
    Returns a dict: (volunteer_name, post, block) -> variable (see Works above).
    """
    debug_print("create_variables: creating the yes/no variables")
    works: Works = {}
    for (post, block) in problem.demand:
        for volunteer in problem.volunteers:
            if post in volunteer.skills and block in volunteer.available_blocks:
                key = (volunteer.name, post, block)
                # The label is only for debugging; we find variables again via the key.
                label = f"{volunteer.name} at {post} in block {block}"
                works[key] = model.new_bool_var(label)
    return works


def variables_by_volunteer_and_block(works: Works) -> VariablesByVolunteerAndBlock:
    """The works variables grouped per volunteer and block: {(name, block): [variables]}.

    One list per block a volunteer could work, with one variable per post they could
    do then. Made once per rule, so variables_of can look blocks up directly instead of
    searching all of works on every call (that was what made building the model slow).
    """
    lookup = {}
    for (volunteer_name, post, block), var in works.items():
        if (volunteer_name, block) not in lookup:
            lookup[(volunteer_name, block)] = []
        lookup[(volunteer_name, block)].append(var)
    return lookup


def variables_of(lookup: VariablesByVolunteerAndBlock, volunteer_name: str, first_block: int,
                 block_after_last: int) -> list[cp_model.IntVar]:
    """This volunteer's variables (at any post) in blocks first_block up to block_after_last.

    Uses the same convention as range(): block_after_last itself is not included.
    lookup comes from variables_by_volunteer_and_block.
    """
    variables = []
    for block in range(first_block, block_after_last):
        # .get with an empty list: no variables when the volunteer can't work this block.
        variables.extend(lookup.get((volunteer_name, block), []))
    return variables


def blocks_of_convention(problem: Problem) -> range:
    """All blocks from the first to the last block in the demand, in order.

    This spans the whole convention, across days and nights: night blocks without demand
    have no variables, so the rules simply skip them. Returns an empty range when there
    is no demand, so loops over it simply don't run.
    """
    blocks = _blocks_in_demand(problem)
    if len(blocks) == 0:
        return range(0)
    return range(min(blocks), max(blocks) + 1)


def _blocks_in_demand(problem: Problem) -> set[int]:
    """Every block that appears in the demand, each only once."""
    blocks = set()
    for (post, block) in problem.demand:
        blocks.add(block)
    return blocks

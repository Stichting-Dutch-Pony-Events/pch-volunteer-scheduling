"""Hard rules for the schedule, one function per rule.

Each add_..._rule function adds its constraints to the CP-SAT model. They all take the
same arguments: the model, the problem, and the works variables from solver.py
(a dict: (volunteer_name, post, block) -> variable).
"""


def add_demand_rule(model, problem, works):
    """Hard rule: every open block of a post gets exactly the number of people needed."""
    for (post, block), needed in problem.demand.items():
        # Collect the variables of everyone who could work this post in this block.
        people_here = []
        for key, var in works.items():
            volunteer_name, assigned_post, assigned_block = key
            if assigned_post == post and assigned_block == block:
                people_here.append(var)

        model.add(sum(people_here) == needed)


def add_no_double_booking_rule(model, problem, works):
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


def _blocks_in_demand(problem):
    """Every block that appears in the demand, each only once."""
    blocks = set()
    for (post, block) in problem.demand:
        blocks.add(block)
    return blocks

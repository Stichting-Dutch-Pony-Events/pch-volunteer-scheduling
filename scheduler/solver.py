from ortools.sat.python import cp_model

from scheduler.model import Schedule, Problem


class NoScheduleFound(Exception):
    """Raised when no schedule can satisfy all the hard rules."""


def solve(problem: Problem) -> Schedule:
    """Find a schedule that meets all hard rules, using the OR-Tools CP-SAT solver."""
    model = cp_model.CpModel()
    works = _create_variables(model, problem)

    # Hard rules
    _add_demand_rule(model, problem, works)
    _add_no_double_booking_rule(model, problem, works)

    return _solve_and_read_schedule(model, works)


def _create_variables(model, problem):
    """One yes/no variable per (volunteer, post, block) that could happen.

    Only for open blocks (in demand) and only if the volunteer has a skill score
    for that post. 1 = the volunteer works there in that block, 0 = not.
    Returns a dict: (volunteer_name, post, block) -> variable.
    """
    works = {}
    for (post, block) in problem.demand:
        for volunteer in problem.volunteers:
            if post in volunteer.skills:
                key = (volunteer.name, post, block)
                # The label is only for debugging; we find variables again via the key.
                label = f"{volunteer.name} at {post} in block {block}"
                works[key] = model.new_bool_var(label)
    return works


def _add_demand_rule(model, problem, works):
    """Hard rule: every open block of a post gets exactly the number of people needed."""
    for (post, block), needed in problem.demand.items():
        # Collect the variables of everyone who could work this post in this block.
        people_here = []
        for key, var in works.items():
            volunteer_name, assigned_post, assigned_block = key
            if assigned_post == post and assigned_block == block:
                people_here.append(var)

        model.add(sum(people_here) == needed)


def _add_no_double_booking_rule(model, problem, works):
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


def _solve_and_read_schedule(model, works):
    """Run the solver and turn every variable set to 1 into an assignment."""
    solver = cp_model.CpSolver()
    status = solver.solve(model)

    # OPTIMAL or FEASIBLE means the solver found a schedule that obeys every rule.
    # Anything else (usually INFEASIBLE) means no such schedule exists.
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise NoScheduleFound("No schedule meets all the hard rules.")

    assignments = set()
    for key, var in works.items():
        if solver.value(var) == 1:
            assignments.add(key)
    return Schedule(assignments=assignments)


def _blocks_in_demand(problem):
    """Every block that appears in the demand, each only once."""
    blocks = set()
    for (post, block) in problem.demand:
        blocks.add(block)
    return blocks

from ortools.sat.python import cp_model

from scheduler.model import Schedule, Problem

class NoScheduleFound(Exception):
    """Raised when no schedule can satisfy all the hard rules."""


def solve(problem: Problem) -> Schedule:
    """Find a schedule that meets the demand, using the OR-Tools CP-SAT solver."""
    model = cp_model.CpModel()

    # One yes/no variable per (volunteer, post, block) that could happen:
    # only for open blocks (in demand) and only if the volunteer has a skill score
    # for that post. 1 = the volunteer works there in that block, 0 = not.
    works = {}
    for (post, block) in problem.demand:
        for volunteer in problem.volunteers:
            if post in volunteer.skills:
                key = (volunteer.name, post, block)
                works[key] = model.new_bool_var(f"{volunteer.name} at {post} in block {block}")

    # Hard rule: every open block of a post gets exactly the number of people needed.
    for (post, block), needed in problem.demand.items():
        # Collect the variables of everyone who could work this post in this block.
        people_here = []
        for key, var in works.items():
            volunteer_name, assigned_post, assigned_block = key
            if assigned_post == post and assigned_block == block:
                people_here.append(var)

        model.add(sum(people_here) == needed)

    # Solve the model
    solver = cp_model.CpSolver()
    solver.solve(model)

    # Read the answer: every variable the solver set to 1 becomes an assignment
    assignments = set()
    for key, var in works.items():
        if solver.Value(var) == 1:
            assignments.add(key)

    return Schedule(assignments=assignments)
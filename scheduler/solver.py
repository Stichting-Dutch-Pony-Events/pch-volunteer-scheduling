from ortools.sat.python import cp_model

from scheduler.model import Schedule, Problem
from scheduler import rules


class NoScheduleFound(Exception):
    """Raised when no schedule can satisfy all the hard rules."""


def solve(problem: Problem) -> Schedule:
    """Find a schedule that meets all hard rules, using the OR-Tools CP-SAT solver."""
    model = cp_model.CpModel()
    works = _create_variables(model, problem)

    # Hard rules (see rules.py)
    rules.add_demand_rule(model, problem, works)
    rules.add_no_double_booking_rule(model, problem, works)
    rules.add_maximum_stretch_rule(model, problem, works)
    rules.add_minimum_break_rule(model, problem, works)

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

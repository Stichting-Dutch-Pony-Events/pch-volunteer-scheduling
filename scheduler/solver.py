from ortools.sat.python import cp_model

from scheduler.errors import NoScheduleFound
from scheduler.helpers import debug_print
from scheduler.model import Schedule, Problem
from scheduler import checks, rules


def solve(problem: Problem) -> Schedule:
    """Find a schedule that meets all hard rules, using the OR-Tools CP-SAT solver."""
    # Check problem for obvious unsolvable situations
    checks.check_problem(problem)

    # Build the model
    model = cp_model.CpModel()
    works = _create_variables(model, problem)

    # Hard rules (see rules.py)
    rules.add_demand_rule(model, problem, works)
    rules.add_no_double_booking_rule(model, problem, works)
    rules.add_minimum_stretch_rule(model, problem, works)
    rules.add_maximum_stretch_rule(model, problem, works)
    rules.add_minimum_break_rule(model, problem, works)
    rules.add_stay_at_post_rule(model, problem, works)
    rules.add_maximum_hours_per_day_rule(model, problem, works)
    rules.add_maximum_hours_total_rule(model, problem, works)

    return _solve_and_read_schedule(model, works)


def _create_variables(model: cp_model.CpModel, problem: Problem) -> rules.Works:
    """One yes/no variable per (volunteer, post, block) that could happen.

    Only for open blocks (in demand), only if the volunteer has a skill score for that
    post and is available in that block. 1 = the volunteer works there in that block, 0 = not.
    Returns a dict: (volunteer_name, post, block) -> variable (see rules.Works).
    """
    debug_print("_create_variables: creating the yes/no variables")
    works: rules.Works = {}
    for (post, block) in problem.demand:
        for volunteer in problem.volunteers:
            if post in volunteer.skills and block in volunteer.available_blocks:
                key = (volunteer.name, post, block)
                # The label is only for debugging; we find variables again via the key.
                label = f"{volunteer.name} at {post} in block {block}"
                works[key] = model.new_bool_var(label)
    return works


def _solve_and_read_schedule(model: cp_model.CpModel, works: rules.Works) -> Schedule:
    """Run the solver and turn every variable set to 1 into an assignment."""
    # The gap between this line and the next output is CP-SAT's own search time.
    debug_print("_solve_and_read_schedule: running CP-SAT")
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

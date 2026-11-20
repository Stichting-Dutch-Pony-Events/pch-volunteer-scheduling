from collections.abc import Callable

from ortools.sat.python import cp_model

from scheduler.debug import debug_print
from scheduler.errors import NoScheduleFound, TimeLimitReached
from scheduler.model import Problem, Schedule
from scheduler.solving import checks, hard_rules, soft_rules, variables


def solve(problem: Problem, time_limit_seconds: int | None = None,
          on_first_schedule: Callable[[float, int], None] | None = None) -> Schedule:
    """Find a schedule that meets all hard rules, using the OR-Tools CP-SAT solver.

    time_limit_seconds: stop CP-SAT after this many seconds (None = no limit); if it found
    nothing by then, TimeLimitReached is raised.
    on_first_schedule: called once, as soon as CP-SAT finds its first schedule, with the
    seconds CP-SAT has been searching and that schedule's penalty (None = nobody to tell).
    solve() itself prints nothing; the caller decides what to do with it.
    """
    # TODO (step 3): pass on_first_schedule on to CP-SAT via a solution callback.
    # Check problem for obvious unsolvable situations
    checks.check_problem(problem)

    # Build the model
    model = cp_model.CpModel()
    works = variables.create_variables(model, problem)

    # Hard rules (see hard_rules.py)
    hard_rules.add_demand_rule(model, problem, works)
    hard_rules.add_no_double_booking_rule(model, problem, works)
    hard_rules.add_minimum_stretch_rule(model, problem, works)
    hard_rules.add_maximum_stretch_rule(model, problem, works)
    hard_rules.add_minimum_break_rule(model, problem, works)
    hard_rules.add_stay_at_post_rule(model, problem, works)
    hard_rules.add_maximum_hours_per_day_rule(model, problem, works)
    hard_rules.add_maximum_hours_total_rule(model, problem, works)

    # Soft rules (see soft_rules.py)
    penalties = []
    penalties += soft_rules.add_skill_score_penalty(model, problem, works)
    penalties += soft_rules.add_round_times_penalty(model, problem, works)
    model.minimize(cp_model.LinearExpr.sum(penalties))

    return _solve_and_read_schedule(model, works, time_limit_seconds)


def _solve_and_read_schedule(model: cp_model.CpModel, works: variables.Works,
                             time_limit_seconds: int | None = None) -> Schedule:
    """Run the solver and turn every variable set to 1 into an assignment;
    the Schedule also says whether CP-SAT proved it optimal, its penalty
    and lowest penalty possible.
    """
    # The gap between this line and the next output is CP-SAT's own search time.
    debug_print("_solve_and_read_schedule: running CP-SAT")
    solver = make_cp_sat_solver(time_limit_seconds=time_limit_seconds)
    status = solver.solve(model)

    # Stop here if CP-SAT found no schedule (see raise_if_no_schedule).
    raise_if_no_schedule(status=status, time_limit_seconds=time_limit_seconds)

    # Every variable CP-SAT set to 1 is an assignment.
    assignments = set()
    for key, var in works.items():
        if solver.value(var) == 1:
            assignments.add(key)

    return Schedule(assignments=assignments,
                    proven_optimal=(status == cp_model.OPTIMAL),
                    penalty=round(solver.objective_value),
                    lowest_possible_penalty=round(solver.best_objective_bound))


def make_cp_sat_solver(time_limit_seconds: int | None) -> cp_model.CpSolver:
    """A CP-SAT solver that stops after time_limit_seconds (None = no limit).

    A building block of solve(); public because it is tested on its own.
    """
    solver = cp_model.CpSolver()
    if time_limit_seconds is not None:
        solver.parameters.max_time_in_seconds = time_limit_seconds
    return solver


def raise_if_no_schedule(status: int, time_limit_seconds: int | None) -> None:
    """Raise if CP-SAT's status means it found no schedule; do nothing if it found one.

    INFEASIBLE (proven impossible) raises NoScheduleFound; UNKNOWN (stopped by the time
    limit before finding anything) raises TimeLimitReached, whose message names the limit.
    OPTIMAL and FEASIBLE mean a schedule was found. A building block of solve(); public
    because it is tested on its own (a real timeout can't be made reliably in a test).
    """
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return
    elif status == cp_model.UNKNOWN:
        # :g leaves out a ".0", so 600 seconds shows as "10" and 90 seconds as "1.5".
        raise TimeLimitReached(f"No schedule found within the time limit of "
                               f"{time_limit_seconds / 60:g} minutes; one may still exist.")
    else:
        raise NoScheduleFound("No schedule meets all the hard rules.")

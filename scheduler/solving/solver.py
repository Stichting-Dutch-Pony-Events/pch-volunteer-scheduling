import signal
import threading
from collections.abc import Callable

from ortools.sat.python import cp_model

from scheduler.debug import debug_print
from scheduler.errors import NoScheduleFound, TimeLimitReached
from scheduler.model import Problem, Schedule
from scheduler.solving import checks, hard_rules, soft_rules, variables


def solve(problem: Problem, time_limit_seconds: int | None = None,
          on_first_schedule: Callable[[float, int], None] | None = None,
          on_stopping: Callable[[], None] | None = None) -> Schedule:
    """Find a schedule that meets all hard rules, using the OR-Tools CP-SAT solver.

    time_limit_seconds: stop CP-SAT after this many seconds (None = no limit); if it found
    nothing by then, TimeLimitReached is raised.
    on_first_schedule: called once, as soon as CP-SAT finds its first schedule, with the
    seconds CP-SAT has been searching and that schedule's penalty (None = nobody to tell).
    on_stopping: called once, right when Ctrl+C asks CP-SAT to stop (it may need a few
    seconds to finish). A Ctrl+C before any schedule was found raises KeyboardInterrupt.
    solve() itself prints nothing; the caller decides what to do with it.
    """
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

    return _solve_and_read_schedule(model, works, time_limit_seconds,
                                    on_first_schedule, on_stopping)


def _solve_and_read_schedule(model: cp_model.CpModel, works: variables.Works,
                             time_limit_seconds: int | None = None,
                             on_first_schedule: Callable[[float, int], None] | None = None,
                             on_stopping: Callable[[], None] | None = None) -> Schedule:
    """Run the solver and turn every variable set to 1 into an assignment;
    the Schedule also says whether CP-SAT proved it optimal, its penalty
    and lowest penalty possible.
    """
    # The gap between this line and the next output is CP-SAT's own search time.
    debug_print("_solve_and_read_schedule: running CP-SAT")
    solver = make_cp_sat_solver(time_limit_seconds=time_limit_seconds)
    reporter = _FirstScheduleReporter(on_first_schedule)
    status = run_cp_sat(solver, model, reporter, on_stopping)

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

    # CP-SAT's own Ctrl+C handling ends the whole program on Windows (and stays behind
    # after the search); run_cp_sat handles Ctrl+C instead.
    solver.parameters.catch_sigint_signal = False

    return solver


def run_cp_sat(solver: cp_model.CpSolver, model: cp_model.CpModel,
               solution_callback: cp_model.CpSolverSolutionCallback | None,
               on_stopping: Callable[[], None] | None = None) -> int:
    """Run CP-SAT so that Ctrl+C stops the search but keeps the best schedule so far.

    Returns CP-SAT's status. CP-SAT searches in a background thread while the main thread
    waits. During the search, Ctrl+C runs our own handler instead of raising
    KeyboardInterrupt: it asks CP-SAT to stop, and CP-SAT returns as if the time limit was
    reached. (A KeyboardInterrupt could pop up at any line, also outside a try; and CP-SAT's
    own Ctrl+C handling ends the whole program on Windows, so make_cp_sat_solver switches it
    off.) on_stopping is called on the first Ctrl+C, right away (CP-SAT may need a few
    seconds to stop); a second Ctrl+C doesn't call it again. If the search was stopped
    before it found any schedule (UNKNOWN), KeyboardInterrupt is raised: a normal abort.
    A building block of solve(); public because it is tested on its own.
    """
    # A thread can't return a value, so the search puts CP-SAT's status in this dict.
    result = {}

    def search() -> None:
        """Run CP-SAT; this runs in the background thread."""
        result["status"] = solver.solve(model, solution_callback)

    thread = threading.Thread(target=search)

    stopped_by_user = False

    def on_ctrl_c(signal_number: int, frame: object) -> None:
        """Our Ctrl+C handler during the search: ask CP-SAT to stop."""
        nonlocal stopped_by_user   # change the variable of run_cp_sat, not make a new one
        solver.stop_search()
        if not stopped_by_user:
            stopped_by_user = True
            if on_stopping is not None:
                on_stopping()

    # During the search Ctrl+C calls on_ctrl_c instead of raising KeyboardInterrupt;
    # finally puts the previous handler back, whatever happens.
    previous_handler = signal.signal(signal.SIGINT, on_ctrl_c)
    try:
        thread.start()
        # Wait in short steps, so the main thread regularly runs Python code: Python only
        # runs a Ctrl+C handler there.
        while thread.is_alive():
            thread.join(timeout=0.2)
    finally:
        signal.signal(signal.SIGINT, previous_handler)

    status = result["status"]
    # Stopped before any schedule was found: nothing to keep, a normal abort.
    if stopped_by_user and status == cp_model.UNKNOWN:
        raise KeyboardInterrupt
    return status


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


class _FirstScheduleReporter(cp_model.CpSolverSolutionCallback):
    """Passes CP-SAT's first schedule on to on_first_schedule; later (better) ones are not
    reported.

    CP-SAT calls on_solution_callback for every schedule it finds while searching. It wants
    an object of this kind, not a plain function, so this class sits in between.
    """

    def __init__(self, on_first_schedule: Callable[[float, int], None] | None) -> None:
        super().__init__()   # CP-SAT's own part of the object must be set up as well
        self.on_first_schedule = on_first_schedule
        self.already_reported = False

    def on_solution_callback(self) -> None:
        """Called by CP-SAT for every schedule it finds."""
        if self.on_first_schedule is None or self.already_reported:
            return
        self.already_reported = True
        # wall_time = seconds since CP-SAT started; objective_value = this schedule's penalty.
        self.on_first_schedule(self.wall_time, round(self.objective_value))

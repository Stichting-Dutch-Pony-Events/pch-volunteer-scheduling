import signal
import threading

import pytest
from ortools.sat.python import cp_model

from scheduler.solving.solver import make_cp_sat_solver, run_cp_sat


# Ctrl+C while CP-SAT searches should stop the search and keep the best schedule so far,
# just like the time limit. CP-SAT's own Ctrl+C handling ends the whole program on Windows,
# so we switch it off and do it ourselves in run_cp_sat (see its docstring).


class _FakeSolver:
    """Stands in for CP-SAT's CpSolver: its search runs until stop_search is called.

    It waits at most 5 seconds, so a run_cp_sat that never calls stop_search gives a red
    test instead of a test that hangs.
    """

    def __init__(self) -> None:
        self.stopped = threading.Event()   # a flag one thread can set and another wait for

    def solve(self, model: cp_model.CpModel | None,
              solution_callback: cp_model.CpSolverSolutionCallback | None = None) -> int:
        """Search until stopped: FEASIBLE (a schedule was found), or UNKNOWN after 5 s."""
        if self.stopped.wait(timeout=5):
            return cp_model.FEASIBLE
        return cp_model.UNKNOWN

    def stop_search(self) -> None:
        """What CpSolver.stop_search does: ask the search to stop."""
        self.stopped.set()


def test_cp_sat_solver_leaves_ctrl_c_to_us():
    """The solver has CP-SAT's own Ctrl+C handling switched off (it ends the program)."""
    # Arrange
    # (nothing to arrange: we look at a fresh solver)

    # Act
    solver = make_cp_sat_solver(time_limit_seconds=None)

    # Assert
    assert solver.parameters.catch_sigint_signal is False


def test_run_cp_sat_returns_the_status_of_the_search():
    """run_cp_sat runs a real CP-SAT search and returns its status."""
    # Arrange
    # A tiny model: one yes/no variable, as low as possible. CP-SAT proves 0 is the best.
    model = cp_model.CpModel()
    variable = model.new_bool_var("x")
    model.minimize(variable)
    solver = make_cp_sat_solver(time_limit_seconds=None)

    # Act
    status = run_cp_sat(solver, model, solution_callback=None)

    # Assert
    assert status == cp_model.OPTIMAL


def test_ctrl_c_stops_the_search_and_returns_its_status():
    """A Ctrl+C during the search stops it, and run_cp_sat returns the search's status."""
    # Arrange
    # The fake search runs until stopped. After 0.2 s a timer sends a real Ctrl+C
    # (signal.raise_signal), just like pressing it in the terminal.
    # First Python's own Ctrl+C handling is put back (it raises KeyboardInterrupt): a CP-SAT
    # search with its own handling on (e.g. a plain cp_model.CpSolver() in an earlier test)
    # leaves CP-SAT's handler behind, and that one ends the whole test run on Windows.
    signal.signal(signal.SIGINT, signal.default_int_handler)
    fake_solver = _FakeSolver()
    ctrl_c_timer = threading.Timer(0.2, signal.raise_signal, args=(signal.SIGINT,))
    ctrl_c_timer.start()

    # Act
    # A Ctrl+C that gets out of run_cp_sat would make pytest stop the whole test run;
    # catching it here turns that into a normal red test. finally: a timer that has not
    # fired yet (e.g. run_cp_sat failed at once) is cancelled, so no late Ctrl+C can reach
    # pytest or the next test.
    try:
        status = run_cp_sat(fake_solver, model=None, solution_callback=None)
    except KeyboardInterrupt:
        pytest.fail("Ctrl+C reached the caller: run_cp_sat did not catch it")
    finally:
        ctrl_c_timer.cancel()

    # Assert
    assert fake_solver.stopped.is_set()
    assert status == cp_model.FEASIBLE

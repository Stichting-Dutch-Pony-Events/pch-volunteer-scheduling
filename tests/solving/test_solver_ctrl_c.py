import signal
import threading
import time
from collections.abc import Callable

import pytest
from ortools.sat.python import cp_model

from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks
from scheduler.solving import solver as solver_module
from scheduler.solving.solver import make_cp_sat_solver, run_cp_sat, solve


# Ctrl+C while CP-SAT searches should stop the search and keep the best schedule so far,
# just like the time limit. CP-SAT's own Ctrl+C handling ends the whole program on Windows,
# so we switch it off and do it ourselves in run_cp_sat (see its docstring).

RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))


class _FakeSolver:
    """Stands in for CP-SAT's CpSolver: its search runs until stop_search is called.

    Like CP-SAT, it needs a moment to finish after stop_search (0.5 s here), and then
    returns status_when_stopped: FEASIBLE = it had found a schedule, UNKNOWN = not yet. It
    waits at most 5 seconds, so a run_cp_sat that never calls stop_search gives a red test
    instead of a test that hangs.
    """

    def __init__(self, status_when_stopped: int = cp_model.FEASIBLE) -> None:
        self.status_when_stopped = status_when_stopped
        self.stopped = threading.Event()   # a flag one thread can set and another wait for
        self.finished = False

    def solve(self, model: cp_model.CpModel | None,
              solution_callback: cp_model.CpSolverSolutionCallback | None = None) -> int:
        """Search until stopped, then take a moment to finish."""
        if not self.stopped.wait(timeout=5):
            self.finished = True
            return cp_model.UNKNOWN
        time.sleep(0.5)   # finishing the current step, as CP-SAT does
        self.finished = True
        return self.status_when_stopped

    def stop_search(self) -> None:
        """What CpSolver.stop_search does: ask the search to stop."""
        self.stopped.set()


def _send_ctrl_c_after(seconds: float) -> threading.Timer:
    """Start a timer that sends a real Ctrl+C after this many seconds, like the terminal.

    First Python's own Ctrl+C handling is put back (it raises KeyboardInterrupt): a CP-SAT
    search with its own handling on (e.g. a plain cp_model.CpSolver() in an earlier test)
    leaves CP-SAT's handler behind, and that one ends the whole test run on Windows.
    The test must cancel the timer in a finally, so a Ctrl+C that has not been sent yet
    (e.g. run_cp_sat failed at once) can never reach pytest or the next test.
    """
    signal.signal(signal.SIGINT, signal.default_int_handler)
    timer = threading.Timer(seconds, signal.raise_signal, args=(signal.SIGINT,))
    timer.start()
    return timer


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
    # The fake search has found a schedule (FEASIBLE) and runs until stopped. After 0.2 s
    # a Ctrl+C comes.
    fake_solver = _FakeSolver(status_when_stopped=cp_model.FEASIBLE)
    ctrl_c_timer = _send_ctrl_c_after(0.2)

    # Act
    # A Ctrl+C that gets out of run_cp_sat would make pytest stop the whole test run;
    # catching it here turns that into a normal red test.
    try:
        status = run_cp_sat(fake_solver, model=None, solution_callback=None)
    except KeyboardInterrupt:
        pytest.fail("Ctrl+C reached the caller: run_cp_sat did not catch it")
    finally:
        ctrl_c_timer.cancel()

    # Assert
    assert fake_solver.stopped.is_set()
    assert status == cp_model.FEASIBLE


def test_ctrl_c_before_a_first_schedule_raises_keyboard_interrupt():
    """A Ctrl+C before CP-SAT found any schedule is a normal abort: KeyboardInterrupt."""
    # Arrange
    # The fake search has not found a schedule yet: stopped, it returns UNKNOWN (the same
    # status as "time limit reached with nothing found", which is why run_cp_sat must tell).
    fake_solver = _FakeSolver(status_when_stopped=cp_model.UNKNOWN)
    ctrl_c_timer = _send_ctrl_c_after(0.2)

    # Act
    # (Act and Assert are in the same expression: pytest.raises catches the
    # KeyboardInterrupt, so it never reaches pytest itself.)

    # Assert
    try:
        with pytest.raises(KeyboardInterrupt):
            run_cp_sat(fake_solver, model=None, solution_callback=None)
    finally:
        ctrl_c_timer.cancel()


def test_ctrl_c_calls_on_stopping_right_away():
    """on_stopping is called as soon as Ctrl+C comes, while CP-SAT is still finishing."""
    # Arrange
    # The fake needs 0.5 s to finish after stop_search. on_stopping notes whether the
    # search had finished yet when it was called.
    fake_solver = _FakeSolver(status_when_stopped=cp_model.FEASIBLE)
    search_finished_when_called = []

    def on_stopping() -> None:
        search_finished_when_called.append(fake_solver.finished)

    ctrl_c_timer = _send_ctrl_c_after(0.2)

    # Act
    try:
        run_cp_sat(fake_solver, model=None, solution_callback=None, on_stopping=on_stopping)
    except KeyboardInterrupt:
        pytest.fail("Ctrl+C reached the caller: run_cp_sat did not catch it")
    finally:
        ctrl_c_timer.cancel()

    # Assert
    # One call, made while the search was still finishing (finished was False).
    assert search_finished_when_called == [False]


def test_second_ctrl_c_does_not_call_on_stopping_again():
    """A second Ctrl+C while CP-SAT is stopping doesn't call on_stopping again."""
    # Arrange
    # Ctrl+C after 0.2 s and again after 0.4 s, while the fake still needs until 0.7 s to
    # finish.
    fake_solver = _FakeSolver(status_when_stopped=cp_model.FEASIBLE)
    calls = []

    def on_stopping() -> None:
        calls.append("stopping")

    first_ctrl_c = _send_ctrl_c_after(0.2)
    second_ctrl_c = _send_ctrl_c_after(0.4)

    # Act
    try:
        run_cp_sat(fake_solver, model=None, solution_callback=None, on_stopping=on_stopping)
    except KeyboardInterrupt:
        pytest.fail("Ctrl+C reached the caller: run_cp_sat did not catch it")
    finally:
        first_ctrl_c.cancel()
        second_ctrl_c.cancel()

    # Assert
    assert calls == ["stopping"]


def test_solve_passes_on_stopping_on_to_run_cp_sat(monkeypatch: pytest.MonkeyPatch):
    """solve() hands its on_stopping function to run_cp_sat, which calls it on Ctrl+C."""
    # Arrange
    # A real Ctrl+C on a real search can't be timed reliably in a test. So run_cp_sat is
    # replaced by a version that remembers what on_stopping it got and then searches as
    # usual (CP-SAT's own solve), so solve() can read the schedule afterwards.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=all_blocks(RULES))]
    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 1
    problem = Problem(volunteers=volunteers, posts=[Post("Tickets")],
                      demand=demand, settings=RULES)

    received = []

    def remembering_run_cp_sat(solver: cp_model.CpSolver, model: cp_model.CpModel,
                               solution_callback: cp_model.CpSolverSolutionCallback | None,
                               on_stopping: Callable[[], None] | None = None) -> int:
        received.append(on_stopping)
        return solver.solve(model, solution_callback)

    monkeypatch.setattr(solver_module, "run_cp_sat", remembering_run_cp_sat)

    def on_stopping() -> None:
        pass   # only passed on, never called here

    # Act
    solve(problem, on_stopping=on_stopping)

    # Assert
    assert received == [on_stopping]

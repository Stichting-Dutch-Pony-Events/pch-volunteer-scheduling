"""Small helpers that any part of the scheduler may use.

debug_print: timing output switched on with the command line's --debug-time flag, so calls
to it can stay in the code; while debugging is off they print nothing.
"""
import sys
from typing import TextIO

# Off unless the command line switches it on with set_debug_time(True).
debug_time_on = False


def set_debug_time(on: bool) -> None:
    """Switch debug_print on (True) or off (False) for the rest of the run."""
    raise NotImplementedError  # stub, so the tests can run and fail


def debug_print(message: str, destination: TextIO | None = None) -> None:
    """If debugging is on, print "[14:03:12.345] message" to destination (default: stdout).

    destination is looked up when called, not when Python reads this line, so a replaced
    sys.stdout (as pytest's capsys does) is used. Prints nothing while debugging is off.
    """
    raise NotImplementedError  # stub, so the tests can run and fail

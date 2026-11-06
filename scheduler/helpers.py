"""Small helpers that any part of the scheduler may use.

debug_print: timing output switched on with the command line's --debug-time flag, so calls
to it can stay in the code; while debugging is off they print nothing.
"""
import sys
from datetime import datetime
from typing import TextIO

# Off unless the command line switches it on with set_debug_time(True).
debug_time_on = False


def set_debug_time(on: bool) -> None:
    """Switch debug_print on (True) or off (False) for the rest of the run."""
    global debug_time_on
    debug_time_on = on


def debug_print(message: str, destination: TextIO | None = None) -> None:
    """If debugging is on, print a tab and "[14:03:12.345] message" to destination.

    The tab indents the debug lines under the normal progress lines of the command line.
    destination defaults to stdout; it is looked up when called, not when Python reads this
    line, so a replaced sys.stdout (as pytest's capsys does) is used. Prints nothing while
    debugging is off.
    """
    if not debug_time_on:
        return

    if destination is None:
        true_destination = sys.stdout
    else:
        true_destination = destination

    now = datetime.now().strftime("%H:%M:%S.%f")[:-3]   # %f = microseconds: keep 3 digits
    print(f"\t[{now}] {message}", flush=True, file=true_destination)

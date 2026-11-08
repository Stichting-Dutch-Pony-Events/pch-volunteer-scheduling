"""The error types of the scheduler, all in one place.

WorkbookError: a mistake in the input workbook (a typo, a missing column, ...).
NoScheduleFound: the input is fine, but no schedule can meet all the hard rules.

The other modules import them from here; workbook.py and solver.py also make them
available under their old place, so `from scheduler.solver import NoScheduleFound` works.
"""


class WorkbookError(Exception):
    """Raised when the input workbook has a mistake, e.g. a missing column or a typo.

    The message starts with the tab, so the user knows where to look.
    """


class NoScheduleFound(Exception):
    """Raised when no schedule can satisfy all the hard rules."""

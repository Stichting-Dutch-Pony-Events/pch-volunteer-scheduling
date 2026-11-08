"""The error types of the scheduler, all in one place.

WorkbookError: a mistake in the input workbook (a typo, a missing column, ...).
NoScheduleFound: the input is fine, but no schedule can meet all the hard rules. Its
children NotEnoughQualified and NotEnoughVolunteers say where, when a check before
solving finds a clear cause.

The other modules import them from here; workbook.py and solver.py also make them
available under their old place, so `from scheduler.solver import NoScheduleFound` works.
"""


class WorkbookError(Exception):
    """Raised when the input workbook has a mistake, e.g. a missing column or a typo.

    The message starts with the tab, so the user knows where to look.
    """


class NoScheduleFound(Exception):
    """Raised when no schedule can satisfy all the hard rules."""


# The children below are raised by the checks before solving (checks.py), when they find a
# clear cause. Code that catches NoScheduleFound also catches them.

class NotEnoughQualified(NoScheduleFound):
    """A post needs more people at some time than there are qualified volunteers available.

    The message lists every such post and time range, with who is qualified and available,
    and separately who is qualified but not available then.
    """


class NotEnoughVolunteers(NoScheduleFound):
    """At some time all posts together need more people than there are volunteers available.

    The message lists every such time with the numbers needed and available.
    """

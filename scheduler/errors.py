"""The error types of the scheduler, all in one place.

WorkbookError: a mistake in the input workbook (a typo, a missing column, ...).
NoScheduleFound: the input is fine, but no schedule can meet all the hard rules. Its
children NotEnoughQualified, NotEnoughVolunteers and NotEnoughHours say where, when a
check before solving finds a clear cause.
TimeLimitReached: the solver found no schedule within the time limit (one may still exist).

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


class NotEnoughHours(NoScheduleFound):
    """A post, or all posts together, need more hours than the volunteers can work.

    Per convention day or over the whole convention; what a volunteer can work is capped
    by their availability and their hour limits. The message says which kind it is and
    gives the hours needed and the hours the volunteers can work.
    """


class TimeLimitReached(Exception):
    """CP-SAT found no schedule within the time limit.

    Not a child of NoScheduleFound on purpose: after a timeout a schedule may still exist,
    the solver just didn't find one in time. The message names the limit.
    """

"""Quick checks before solving: find clear reasons why no schedule is possible.

If a check finds something, it raises a child of NoScheduleFound with a message that says
where (post, day, time) and why. If no check finds anything, the solver runs as usual; if
it still finds no schedule, the cause is the combination of rules (plain NoScheduleFound).

All problems of one kind are reported at once: the message is a list, at most
MAX_LINES lines, then "and N more".
"""
from scheduler.errors import NotEnoughQualified, NotEnoughVolunteers
from scheduler.model import Problem, all_blocks, runs_of_consecutive_blocks, day_of, time_of
from scheduler.helpers import debug_print

# At most this many problem lines in one message; the rest is counted ("and 12 more").
MAX_LINES = 10


def check_problem(problem: Problem) -> None:
    """Raise NotEnoughQualified or NotEnoughVolunteers if a check finds a clear cause.

    Check 1 (per post) comes first: its message is the most precise. Check 2 (all posts
    together) only runs when check 1 found nothing.
    """
    raise NotImplementedError  # stub, so the tests can run and fail


def _not_enough_qualified_lines(problem: Problem) -> list[str]:
    """One line per post and time range where the post needs more people than are
    qualified and available, e.g. "Tickets, Saturday 14:00-15:30: needs 3, only 2
    qualified and available (Mock Mane, Testy Hooves); qualified but not available:
    Dummy Dash". Consecutive blocks with the same problem make one line. Empty list = fine.
    """
    debug_print("_not_enough_qualified_lines: Checking before solving")

    # 1. For every demand, check who is qualified and available.
    unmet_demands = {}
    for (post, block) in problem.demand:
        qualified_and_available = []
        qualified_and_unavailable = []
        for v in problem.volunteers:
            if post in v.skills:
                if block in v.available_blocks:
                    qualified_and_available.append(v.name)
                else:
                    qualified_and_unavailable.append(v.name)

        if len(qualified_and_available) < problem.demand[(post, block)]:
            if post not in unmet_demands:
                unmet_demands[post] = {}

            unmet_demands[post][block] = {"needed": problem.demand[(post, block)],
                                        "qualified_and_available": qualified_and_available,
                                        "qualified_and_unavailable": qualified_and_unavailable}

    messages = []
    for post in unmet_demands:
        blocks = unmet_demands[post].keys()
        runs = runs_of_consecutive_blocks(blocks)

        for block, block_after_last in runs:
            day, start = time_of(block=block, settings=problem.settings)
            _, end = time_of(block=block_after_last, settings=problem.settings)
            needed = unmet_demands[post][block]["needed"]
            available = unmet_demands[post][block]["qualified_and_available"]
            unavailable = unmet_demands[post][block]["qualified_and_unavailable"]

            line = f"{post}, {day} {start}-{end}: needs {needed}, only {len(available)} qualified and available ({', '.join(available)})"
            if unavailable:
                line = line + f"; qualified but not available: {', '.join(unavailable)}"

            messages.append(line)


    return messages


def _not_enough_volunteers_lines(problem: Problem) -> list[str]:
    """One line per block where all posts together need more people than there are
    volunteers available, e.g. "Saturday 14:00: the posts need 30 people in total, only
    28 volunteers available". Empty list = fine.
    """
    raise NotImplementedError  # stub, so the tests can run and fail

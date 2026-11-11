"""Quick checks before solving: find clear reasons why no schedule is possible.

If a check finds something, it raises a child of NoScheduleFound with a message that says
where (post, day, time) and why. If no check finds anything, the solver runs as usual; if
it still finds no schedule, the cause is the combination of rules (plain NoScheduleFound).

All problems of one kind are reported at once: the message is a list, at most
MAX_LINES lines, then "and N more".
"""
from scheduler.errors import NotEnoughQualified, NotEnoughVolunteers
from scheduler.model import Problem, runs_of_consecutive_blocks, time_of
from scheduler.model import Settings, BLOCKS_PER_DAY
from scheduler.helpers import debug_print

# At most this many problem lines in one message; the rest is counted ("and 12 more").
MAX_LINES = 10


def check_problem(problem: Problem) -> None:
    """Raise NotEnoughQualified or NotEnoughVolunteers if a check finds a clear cause.

    Check 1 (per post) comes first: its message is the most precise. Check 2 (all posts
    together) only runs when check 1 found nothing.
    """

    lines = _not_enough_qualified_lines(problem=problem)
    if lines:
        raise NotEnoughQualified(_message(lines=lines))

    lines = _not_enough_volunteers_lines(problem=problem)
    if lines:
        raise NotEnoughVolunteers(_message(lines=lines))


def _message(lines: list[str]) -> str:
    """Join the lines into one message: at most MAX_LINES lines, then "and N more"."""
    error_text = "\n".join(lines[:MAX_LINES])
    if len(lines) > MAX_LINES:
        error_text = error_text + f"\nand {len(lines) - MAX_LINES} more"

    return error_text


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
        available = []
        unavailable = []
        for volunteer in problem.volunteers:
            if post in volunteer.skills:
                if block in volunteer.available_blocks:
                    available.append(volunteer.name)
                else:
                    unavailable.append(volunteer.name)

        # 2. Fewer qualified and available than needed: describe the shortage (the part of
        #    the line after the time).
        needed = problem.demand[(post, block)]
        if len(available) < needed:
            end_line = f": needs {needed}, only {len(available)} "
            end_line = end_line + f"qualified and available ({', '.join(available)})"
            if unavailable:
                end_line = end_line + f"; qualified but not available: {', '.join(unavailable)}"

            # Collect the blocks per post and description, so only blocks with exactly the
            # same shortage are merged into one time range below.
            if (post, end_line) not in unmet_demands:
                unmet_demands[(post, end_line)] = []
            unmet_demands[(post, end_line)].append(block)

    # 3. One line per run of consecutive blocks with the same shortage.
    messages = []
    for post, end_line in unmet_demands:
        runs = runs_of_consecutive_blocks(unmet_demands[(post, end_line)])

        for block, block_after_last in runs:
            day, start = time_of(block=block, settings=problem.settings)
            end = _end_time(block_after_last=block_after_last, settings=problem.settings)

            line = f"{post}, {day} {start}-{end}" + end_line

            messages.append(line)

    return messages


def _not_enough_volunteers_lines(problem: Problem) -> list[str]:
    """One line per time range where all posts together need more people than there are
    volunteers available, e.g. "Saturday 14:00-15:00: the posts need 30 people in total,
    only 28 volunteers available". Consecutive blocks with the same numbers make one line.
    Empty list = fine.
    """
    debug_print("_not_enough_volunteers_lines: Checking before solving")

    # 1. Add up how many people all posts together need, per block (only blocks with demand).
    total_needed = {}
    for (post, block) in problem.demand:
        if block not in total_needed:
            total_needed[block] = 0
        total_needed[block] += problem.demand[(post, block)]

    # 2. Count how many volunteers are available in each of those blocks.
    unmet_demands = {}
    for block in total_needed:
        available = 0
        for volunteer in problem.volunteers:
            if block in volunteer.available_blocks:
                available += 1

        # 3. More needed than available: describe the shortage (the part after the time) and
        #    collect the blocks per description, as in _not_enough_qualified_lines.
        if total_needed[block] > available:
            end_line = f": the posts need {total_needed[block]} people in total"
            end_line = end_line + f", only {available} volunteers available"

            if end_line not in unmet_demands:
                unmet_demands[end_line] = []
            unmet_demands[end_line].append(block)

    # 4. One line per run of consecutive blocks with the same shortage.
    messages = []
    for end_line in unmet_demands:
        runs = runs_of_consecutive_blocks(unmet_demands[end_line])

        for block, block_after_last in runs:
            day, start = time_of(block=block, settings=problem.settings)
            end = _end_time(block_after_last=block_after_last, settings=problem.settings)

            line = f"{day} {start}-{end}" + end_line

            messages.append(line)

    return messages


def _end_time(block_after_last: int, settings: Settings) -> str:
    """The end time ("HH:MM") of a time range that stops just before block_after_last.

    Usually that is simply the time of block_after_last. But a range that runs until the
    very end of the convention has a block_after_last that no longer exists, so time_of
    would raise; that range ends at the day boundary (06:00).
    """
    final_block = (len(settings.days) * BLOCKS_PER_DAY) - 1

    if block_after_last > final_block:
        # The convention ends at 06:00, the same time of day as block 0.
        _, end = time_of(block=0, settings=settings)
    else:
        _, end = time_of(block=block_after_last, settings=settings)

    return end

"""Quick checks before solving: find clear reasons why no schedule is possible.

If a check finds something, it raises a child of NoScheduleFound with a message that says
where (post, day, time) and why. If no check finds anything, the solver runs as usual; if
it still finds no schedule, the cause is the combination of rules (plain NoScheduleFound).

All problems of one kind are reported at once: the message is a list, at most
MAX_LINES lines, then "and N more".
"""
from scheduler.errors import NotEnoughQualified, NotEnoughVolunteers, NotEnoughHours
from scheduler.model import Problem, runs_of_consecutive_blocks, time_of, day_of, block_of
from scheduler.model import Volunteer
from scheduler.model import Settings, BLOCKS_PER_DAY, MINUTES_PER_BLOCK
from scheduler.helpers import debug_print

# At most this many problem lines in one message; the rest is counted ("and 12 more").
MAX_LINES = 10


def check_problem(problem: Problem) -> None:
    """Raise NotEnoughQualified, NotEnoughVolunteers or NotEnoughHours if a check finds a
    clear cause.

    Check 1 (per post) comes first: its message is the most precise. Check 2 (all posts
    together) only runs when check 1 found nothing. The hours checks (per post, then all
    posts together) only run when checks 1 and 2 found nothing.
    """

    lines = _not_enough_qualified_lines(problem=problem)
    if lines:
        raise NotEnoughQualified(_message(lines=lines))

    lines = _not_enough_volunteers_lines(problem=problem)
    if lines:
        raise NotEnoughVolunteers(_message(lines=lines))

    lines = _not_enough_hours_at_post_lines(problem=problem)
    if lines:
        raise NotEnoughHours(_message(lines=lines))

    lines = _not_enough_hours_in_total_lines(problem=problem)
    if lines:
        raise NotEnoughHours(_message(lines=lines))


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


def _not_enough_hours_at_post_lines(problem: Problem) -> list[str]:
    """One line per post and day where the post needs more hours than its qualified
    volunteers can work that day, plus one line per post that is short over the whole
    convention. What a volunteer can work: on one day the lowest of their hours available
    that day, their limit per day and their limit in total; over the whole convention the
    lowest of their limit in total and the sum of their days. Empty list = fine.
    """
    debug_print("_not_enough_hours_at_post_lines: Checking before solving")

    lines = []
    for post in problem.posts:
        # Only the volunteers qualified for this post count.
        qualified = []
        for volunteer in problem.volunteers:
            if post.name in volunteer.skills:
                qualified.append(volunteer)

        lines += _hours_lines(problem=problem, label=post.name, posts={post.name},
                              volunteers=qualified, who="the qualified volunteers",
                              show_names=True)

    return lines


def _not_enough_hours_in_total_lines(problem: Problem) -> list[str]:
    """Like _not_enough_hours_at_post_lines, but for all posts together and all
    volunteers: one line per day where the posts need more hours than everyone can work
    that day, plus one line if they are short over the whole convention. Empty list = fine.
    """
    debug_print("_not_enough_hours_in_total_lines: Checking before solving")

    # All posts that need someone at some time; every volunteer counts (no names in the
    # line: that would list everybody).
    all_posts = set()
    for (post, block) in problem.demand:
        all_posts.add(post)

    return _hours_lines(problem=problem, label="All posts", posts=all_posts,
                        volunteers=problem.volunteers, who="the volunteers",
                        show_names=False)


def _hours_lines(problem: Problem, label: str, posts: set[str], volunteers: list[Volunteer],
                 who: str, show_names: bool) -> list[str]:
    """The lines of both hours checks: compare the hours the given posts need with the
    hours the given volunteers can work, per day and over all days.

    label starts each line ("Tickets" or "All posts"), who names the volunteers in it
    ("the qualified volunteers"), show_names adds their names in brackets. Everything is
    counted in minutes; only the text of a line shows hours.
    """
    settings = problem.settings
    lines = []

    # 1. What each volunteer can work per day (the same for every day loop below).
    minutes_per_day = {}  # (volunteer name, day) -> minutes they can work that day
    for day in settings.days:
        start_block = block_of(day, "06:00", settings)
        blocks_of_day = set(range(start_block, start_block + BLOCKS_PER_DAY))
        for volunteer in volunteers:
            minutes_per_day[(volunteer.name, day)] = _minutes_can_work_on_day(volunteer,
                                                                              blocks_of_day)

    # 2. Per day: what the posts need against what the volunteers can work that day.
    for day in settings.days:
        needed = 0
        for (post, block), people in problem.demand.items():
            if post in posts and day_of(block, settings) == day:
                needed += people * MINUTES_PER_BLOCK

        can_work = 0
        names = []
        for volunteer in volunteers:
            minutes = minutes_per_day[(volunteer.name, day)]
            if minutes > 0:
                can_work += minutes
                names.append(volunteer.name)

        if needed > can_work:
            lines.append(_hours_line(f"{label}, {day}", needed, who, can_work, names,
                                     show_names))

    # 3. Over all days: the sum of a volunteer's days, but their total limit counts only
    #    once (each day above used it as a cap, so the sum of the days can be higher).
    needed = 0
    for (post, block), people in problem.demand.items():
        if post in posts:
            needed += people * MINUTES_PER_BLOCK

    can_work = 0
    names = []
    for volunteer in volunteers:
        minutes = 0
        for day in settings.days:
            minutes += minutes_per_day[(volunteer.name, day)]
        if volunteer.max_minutes_total is not None:
            minutes = min(minutes, volunteer.max_minutes_total)
        if minutes > 0:
            can_work += minutes
            names.append(volunteer.name)

    if needed > can_work:
        lines.append(_hours_line(f"{label}, over all days", needed, who, can_work, names,
                                 show_names))

    return lines


def _hours_line(start: str, needed: int, who: str, can_work: int, names: list[str],
                show_names: bool) -> str:
    """One line of an hours check, e.g. "Tickets, Friday: needs 3 hours, the qualified
    volunteers can work 2 hours (Mock Mane)". needed and can_work are in minutes.
    """
    line = f"{start}: needs {_hours_text(needed)}, {who} can work {_hours_text(can_work)}"
    if show_names:
        line += " (" + ", ".join(names) + ")"

    return line


def _minutes_can_work_on_day(volunteer: Volunteer, blocks_of_day: set[int]) -> int:
    """The minutes a volunteer can work on one day: the lowest of the time they are
    available that day, their limit per day and their limit in total (None = no limit).
    """
    minutes = len(volunteer.available_blocks & blocks_of_day) * MINUTES_PER_BLOCK
    if volunteer.max_minutes_per_day is not None:
        minutes = min(minutes, volunteer.max_minutes_per_day)
    if volunteer.max_minutes_total is not None:
        minutes = min(minutes, volunteer.max_minutes_total)

    return minutes


def _hours_text(minutes: int) -> str:
    """Minutes as hours for a message: 180 -> "3 hours", 150 -> "2.5 hours"."""
    if minutes % 60 == 0:
        return f"{minutes // 60} hours"

    return f"{minutes / 60:g} hours"


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

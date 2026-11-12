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

    # Everything below is counted in minutes; only the text of a line shows hours.

    # 1. How much work is needed per day per post.
    demand = {}  # (day, post) -> minutes needed
    for (post, block), needed in problem.demand.items():
        day = day_of(block, problem.settings)

        if (day, post) not in demand:
            demand[(day, post)] = 0

        demand[(day, post)] += needed * MINUTES_PER_BLOCK

    # 2. The blocks of each day, made once (the same for every volunteer).
    blocks_of_day = {}  # day -> set of blocks
    for day in problem.settings.days:
        start_block = block_of(day, "06:00", problem.settings)
        blocks_of_day[day] = set(range(start_block, start_block + BLOCKS_PER_DAY))

    # 3. How much work the qualified volunteers can do per post: per day, and over all days.
    supply = {}  # (day, post) -> minutes the qualified volunteers can work that day
    supply_volunteers = {}  # (day, post) -> names of those volunteers
    supply_over_all_days = {}  # post -> minutes the qualified volunteers can work in total
    supply_volunteers_over_all_days = {}  # post -> names of those volunteers
    for volunteer in problem.volunteers:
        minutes_over_all_days = 0
        for day in problem.settings.days:
            minutes_can_work = _minutes_can_work_on_day(volunteer, blocks_of_day[day])
            if minutes_can_work == 0:
                continue
            minutes_over_all_days += minutes_can_work

            for post in volunteer.skills:
                if (day, post) not in supply:
                    supply[(day, post)] = 0
                    supply_volunteers[(day, post)] = []
                supply[(day, post)] += minutes_can_work
                supply_volunteers[(day, post)].append(volunteer.name)

        # Over all days their total limit counts only once (each day above used it as a
        # cap, so the sum of the days can be higher than the limit).
        if volunteer.max_minutes_total is not None:
            minutes_over_all_days = min(minutes_over_all_days, volunteer.max_minutes_total)
        if minutes_over_all_days == 0:
            continue

        for post in volunteer.skills:
            if post not in supply_over_all_days:
                supply_over_all_days[post] = 0
                supply_volunteers_over_all_days[post] = []
            supply_over_all_days[post] += minutes_over_all_days
            supply_volunteers_over_all_days[post].append(volunteer.name)

    # 4. Compare per post per day.
    lines = []
    for (day, post) in demand:
        can_work = supply.get((day, post), 0)
        if demand[(day, post)] > can_work:
            names = supply_volunteers.get((day, post), [])
            line = f"{post}, {day}: needs {_hours_text(demand[(day, post)])}, "
            line += f"the qualified volunteers can work {_hours_text(can_work)} "
            line += "(" + ", ".join(names) + ")"
            lines.append(line)

    # 5. Compare per post over the whole convention.
    for post in problem.posts:
        total_demand = 0
        for day in problem.settings.days:
            total_demand += demand.get((day, post.name), 0)

        can_work = supply_over_all_days.get(post.name, 0)
        if total_demand > can_work:
            names = supply_volunteers_over_all_days.get(post.name, [])
            line = f"{post.name}, over all days: needs {_hours_text(total_demand)}, "
            line += f"the qualified volunteers can work {_hours_text(can_work)} "
            line += "(" + ", ".join(names) + ")"
            lines.append(line)

    return lines


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


def _not_enough_hours_in_total_lines(problem: Problem) -> list[str]:
    """Like _not_enough_hours_at_post_lines, but for all posts together and all
    volunteers: one line per day where the posts need more hours than everyone can work
    that day, plus one line if they are short over the whole convention. Empty list = fine.
    """
    debug_print("_not_enough_hours_in_total_lines: Checking before solving")

    # 1. How much work is needed per day.
    demand = {}  # (day) -> minutes needed
    for (post, block), needed in problem.demand.items():
        day = day_of(block, problem.settings)

        if day not in demand:
            demand[day] = 0

        demand[day] += needed * MINUTES_PER_BLOCK

    # 2. The blocks of each day, made once (the same for every volunteer).
    blocks_of_day = {}  # day -> set of blocks
    for day in problem.settings.days:
        start_block = block_of(day, "06:00", problem.settings)
        blocks_of_day[day] = set(range(start_block, start_block + BLOCKS_PER_DAY))

    # 3. How much work the qualified volunteers can do: per day, and over all days.
    supply = {}  # day -> minutes the qualified volunteers can work that day
    supply_over_all_days = 0  # minutes the qualified volunteers can work in total
    for volunteer in problem.volunteers:
        minutes_over_all_days = 0
        for day in problem.settings.days:
            minutes_can_work = _minutes_can_work_on_day(volunteer, blocks_of_day[day])
            if minutes_can_work == 0:
                continue
            minutes_over_all_days += minutes_can_work

            if day not in supply:
                supply[day] = 0
            supply[day] += minutes_can_work

        # Over all days their total limit counts only once (each day above used it as a
        # cap, so the sum of the days can be higher than the limit).
        if volunteer.max_minutes_total is not None:
            minutes_over_all_days = min(minutes_over_all_days, volunteer.max_minutes_total)
        if minutes_over_all_days == 0:
            continue

        supply_over_all_days += minutes_over_all_days

    # 4. Compare per day.
    lines = []
    for day in demand:
        can_work = supply.get(day, 0)
        if demand[day] > can_work:
            line = f"All posts, {day}: needs {_hours_text(demand[day])}, "
            line += f"the volunteers can work {_hours_text(can_work)}"
            lines.append(line)

    # 5. Compare per post over the whole convention.
    total_demand = 0
    for day in problem.settings.days:
        total_demand += demand.get(day, 0)

    if total_demand > supply_over_all_days:
        line = f"All posts, over all days: needs {_hours_text(total_demand)}, "
        line += f"the volunteers can work {_hours_text(supply_over_all_days)}"
        lines.append(line)

    return lines


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

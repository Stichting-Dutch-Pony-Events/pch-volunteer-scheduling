"""The tab "Schedule" of the output workbook: one row per block, one column per post slot.

create_schedule_sheet first, then the helpers it uses. The helpers are plain functions
without openpyxl, so they can be tested without writing a file.
"""
from openpyxl import Workbook

from scheduler.debug import debug_print
from scheduler.model import BLOCKS_PER_DAY, Problem, Schedule, day_and_time_of


def create_schedule_sheet(workbook: Workbook, problem: Problem, schedule: Schedule) -> None:
    """Add the tab "Schedule" to the workbook: one row per block, one column per post slot.

    Row 1 is the header: Day, Time, then one column per (post, slot) from slot_columns.
    Below it one row per block from rows_to_show, with the day and time as text (night rows
    under their convention day) and the nickname of whoever sits in that slot, or an empty
    cell. The header row and the Day and Time columns are frozen. A workbook that already
    has a "Schedule" tab is a ValueError (e.g. the function was called twice).
    """
    debug_print("create_schedule_sheet: creating tab Schedule")
    # 1. Guard against duplicate sheets
    if "Schedule" in workbook.sheetnames:
        raise ValueError("The workbook already has a 'Schedule' tab.")
    sheet = workbook.create_sheet("Schedule")

    # 2. Collect columns and names before the loops
    columns = slot_columns(problem)      # [("Tickets", 1), ("Tickets", 2), ("Infobooth", 1)]
    names = assign_slots(schedule)       # {("Tickets", 1, 32): "Mock Mane", ...}
    slot_count_per_post = {}             # {"Tickets": 2, "Infobooth": 1}
    for post, slot in columns:
        if post not in slot_count_per_post:
            slot_count_per_post[post] = 0
        slot_count_per_post[post] = slot_count_per_post[post] + 1

    # 3. The header row: Day, Time, then one header per column.
    header = ["Day", "Time"]
    for post, slot in columns:
        header.append(column_header(post, slot, slot_count_per_post[post]))
    sheet.append(header)

    # 4. One row per block. The cells follow the same columns list as the header, so each
    #    nickname lands under the right header. .get gives None (an empty cell) when nobody
    #    sits in that slot during this block.
    for block in rows_to_show(problem):
        day, time = day_and_time_of(block, problem.settings)
        row = [day, time]
        for post, slot in columns:
            row.append(names.get((post, slot, block)))
        sheet.append(row)

    # 5. Keep the header row and the Day and Time columns in view when scrolling.
    sheet.freeze_panes = "C2"


def slot_columns(problem: Problem) -> list[tuple[str, int]]:
    """The columns of the Schedule tab after Day and Time: [(post, slot), ...], slots from 1.

    Posts in the order of problem.posts; each post gets as many columns as its highest
    demand at any block. A post without any demand gets no columns.
    Example: Tickets needs at most 2, Infobooth 1 -> [("Tickets", 1), ("Tickets", 2),
    ("Infobooth", 1)]
    """
    # 1. Check what the maximum demand per post is.
    max_demand_per_post = {}
    for post in problem.posts:
        for post_and_block, demand in problem.demand.items():
            if post.name == post_and_block[0] and demand > 0:
                if post.name not in max_demand_per_post:
                    max_demand_per_post[post.name] = demand
                elif max_demand_per_post[post.name] < demand:
                    max_demand_per_post[post.name] = demand

    # 2. Generate the required output
    slot_columns = []
    for post, max_demand in max_demand_per_post.items():
        for slot in range(1, max_demand + 1):
            slot_columns.append((post, slot))

    return slot_columns


def column_header(post: str, slot: int, slot_count: int) -> str:
    """The header text of one column: "Tickets 2", or just "Infobooth" if it has one slot."""
    # 1. Various checks
    if slot_count < 1:
        raise ValueError(f"Slotcount {slot_count} invalid. Needs to be at least 1.")
    if slot < 1:
        raise ValueError(f"Slot {slot} invalid. Needs to be at least 1.")
    if slot > slot_count:
        raise ValueError(f"Slot {slot} greater than slot_count {slot_count}.")
    if post == "":
        raise ValueError("Post can't be an empty string")

    # 2. return the header text
    if slot_count == 1:
        return post
    else:
        return post + " " + str(slot)


def rows_to_show(problem: Problem, margin: int = 0) -> list[int]:
    """The blocks that get a row on the Schedule tab, in time order.

    Per convention day: every block from the first to the last block with demand that day,
    gaps included, plus `margin` blocks before the first and after the last demand of that
    day, but never outside that day (so the margins of two days cannot overlap). A day
    without any demand gets no rows.
    """

    min_max_per_day = {}  # day: str -> (min_block: int, max_block: int)

    for post, block in problem.demand:
        day_number = block // BLOCKS_PER_DAY
        day = problem.settings.days[day_number]

        if day not in min_max_per_day:
            min_max_per_day[day] = (block, block)
            continue

        min_block, max_block = min_max_per_day[day]
        if block < min_block:
            min_max_per_day[day] = (block, max_block)
        elif block > max_block:
            min_max_per_day[day] = (min_block, block)

    # Add the margins, but stay within the day itself. A margin of 0 changes nothing.
    for day in min_max_per_day:
        old_min, old_max = min_max_per_day[day]
        day_number = problem.settings.days.index(day)

        minimum = max(old_min - margin, day_number * BLOCKS_PER_DAY)
        maximum = min(old_max + margin, (day_number + 1) * BLOCKS_PER_DAY - 1)

        min_max_per_day[day] = (minimum, maximum)

    blocks_to_show = []
    for day in problem.settings.days:          # Friday, Saturday, Sunday: time order
        if day in min_max_per_day:             # a day without demand gets no rows
            min_to_show, max_to_show = min_max_per_day[day]
            blocks_to_show.extend(range(min_to_show, max_to_show + 1))

    return blocks_to_show


def assign_slots(schedule: Schedule) -> dict[tuple[str, int, int], str]:
    """Who sits in which column of a post: {(post, slot, block): nickname}, slots from 1.

    Per post, block by block in time order: someone who also worked at this post in the
    previous block keeps their slot; everyone else is a newcomer and gets the lowest slot
    that is still free in this block (newcomers in the same block in name order). So a
    volunteer stays in one column for their whole shift at that post.
    """
    # 1. Per post, per block: who works there. {"Tickets": {0: ["Mock Mane", ...], ...}}
    people = {}
    for name, post, block in schedule.assignments:
        if post not in people:
            people[post] = {}
        if block not in people[post]:
            people[post][block] = []
        people[post][block].append(name)

    slots = {}
    for post, people_per_block in people.items():
        previous_slots = {}   # name -> slot, in the block just before this one
        previous_block = None
        for block in sorted(people_per_block):
            # Only the block directly before counts: after a gap everyone is new.
            if previous_block != block - 1:
                previous_slots = {}

            names = sorted(people_per_block[block])   # name order for the newcomers
            current_slots = {}

            # 2. Who was here in the previous block keeps their slot.
            for name in names:
                if name in previous_slots:
                    current_slots[name] = previous_slots[name]

            # 3. Everyone else gets the lowest slot that is still free in this block.
            for name in names:
                if name not in current_slots:
                    slot = 1
                    while slot in current_slots.values():
                        slot = slot + 1
                    current_slots[name] = slot

            for name, slot in current_slots.items():
                slots[(post, slot, block)] = name
            previous_slots = current_slots
            previous_block = block

    return slots

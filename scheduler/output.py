"""Writes the schedule to an output workbook (.xlsx).

Layout of this file (like workbook.py): write_output first (the table of contents), then
one create_<name>_sheet function per tab, then the helpers they use. The helpers are
plain functions without openpyxl, so they can be tested without writing a file.
"""
from openpyxl import Workbook

from scheduler.model import Problem, Schedule, BLOCKS_PER_DAY


def create_schedule_sheet(workbook: Workbook, problem: Problem, schedule: Schedule) -> None:
    """Add the tab "Schedule" to the workbook: one row per block, one column per post slot.

    Row 1 is the header: Day, Time, then one column per (post, slot) from slot_columns.
    Below it one row per block from rows_to_show, with the day and time as text (night rows
    under their convention day) and the nickname of whoever sits in that slot, or an empty
    cell. The header row and the Day and Time columns are frozen. A workbook that already
    has a "Schedule" tab is a ValueError (e.g. the function was called twice).
    """
    raise NotImplementedError  # stub, so the tests can run and fail


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


def rows_to_show(problem: Problem) -> list[int]:
    """The blocks that get a row on the Schedule tab, in time order.

    Per convention day: every block from the first to the last block with demand that day,
    gaps included. A day without any demand gets no rows.
    """

    min_max_per_day = {} # day: str -> (min_block: int, max_block: int)

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

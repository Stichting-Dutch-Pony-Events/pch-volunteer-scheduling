"""Writes the schedule to an output workbook (.xlsx).

Layout of this file (like workbook.py): write_output first (the table of contents), then
one create_<name>_sheet function per tab, then the helpers they use. The helpers are
plain functions without openpyxl, so they can be tested without writing a file.
"""
from scheduler.model import Schedule


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

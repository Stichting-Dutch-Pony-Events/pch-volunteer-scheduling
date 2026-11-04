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
    raise NotImplementedError  # stub, so the tests can run and fail

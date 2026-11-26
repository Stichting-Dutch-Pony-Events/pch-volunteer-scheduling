"""Writes the schedule to an output workbook (.xlsx).

write_output is the table of contents: a new workbook, one create_<name>_sheet call per
tab, then save. Each tab has its own module in this folder (now only schedule_sheet.py).
"""
from pathlib import Path

from openpyxl import Workbook

from scheduler.model import Problem, Schedule
from scheduler.writing.individual_schedules_sheet import create_individual_schedules_sheet
from scheduler.writing.schedule_sheet import create_schedule_sheet


def write_output(problem: Problem, schedule: Schedule, path: str | Path) -> None:
    """Write the schedule to a new .xlsx workbook at path, overwriting an existing file.

    The table of contents of the output: a new workbook, one create_<name>_sheet call per
    tab (now only "Schedule"), then save. A path that does not end in .xlsx is a ValueError.
    """
    # 1. Only .xlsx for now (like read_problem); other file types maybe later.
    if Path(path).suffix.lower() != ".xlsx":
        raise ValueError(f"Cannot write {path}: the output must be an .xlsx file.")

    # 2. A new workbook starts with an empty tab called "Sheet"; we don't need it.
    workbook = Workbook()
    workbook.remove(workbook.active)

    # 3. One line per tab. Later tabs (e.g. "No double check") are added here.
    create_schedule_sheet(workbook, problem, schedule)
    create_individual_schedules_sheet(workbook, problem, schedule)

    # 4. Save. An existing file at path is overwritten without asking.
    workbook.save(path)

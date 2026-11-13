"""Reads the input workbook (.xlsx) into a Problem the solver can work with.

read_problem is the table of contents: it checks the file and the tabs, calls one
reader per tab (each in its own module in this folder) and checks across tabs.
"""
import zipfile
from pathlib import Path

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.errors import WorkbookError
from scheduler.model import Problem
from scheduler.reading.cells import find_post_columns
from scheduler.reading.demand import read_demand
from scheduler.reading.posts import read_posts
from scheduler.reading.settings import read_settings
from scheduler.reading.skills import read_skills
from scheduler.reading.volunteers import read_volunteers

# The tabs read_problem needs, and the ones it knows but does not read yet.
REQUIRED_TABS = ["Settings", "Volunteers", "Posts", "Skills", "Demand"]
TABS_NOT_USED_YET = ["ReadMe", "Events", "Wishes", "Fixed"]


def read_problem(path: str | Path) -> Problem:
    """Read the input workbook at path into a Problem the solver can work with.

    Checks the file (.xlsx, exists) and the tabs (Settings, Volunteers, Posts, Skills and
    Demand are required; ReadMe, Events, Wishes and Fixed are known and ignored for now;
    any other tab is an error), calls the tab readers, checks across tabs (every
    volunteer has a Skills row and every Skills row is a volunteer; Posts, the Skills
    columns and the Demand columns name the same posts) and combines it all.
    Raises WorkbookError for the first problem it finds.
    """
    # 1. The file: an .xlsx that exists and can be opened.
    path = Path(path)
    if path.suffix.lower() != ".xlsx":
        raise WorkbookError(f"{path.name}: the scheduler reads .xlsx files only. Save the "
                            f"workbook as Excel (.xlsx), e.g. File > Save As in LibreOffice.")
    if not path.exists():
        raise WorkbookError(f"{path.name}: file not found ({path}).")

    try:
        workbook = openpyxl.load_workbook(path)
    except zipfile.BadZipFile:
        # An .xlsx is a zip file inside, so a damaged one fails as "not a zip file".
        raise WorkbookError(f"{path.name}: not a readable .xlsx workbook (damaged, or another "
                            "file type renamed to .xlsx). "
                            "Save it again from Excel or LibreOffice.") from None

    # 2. The tabs: every required one, and nothing unknown.
    for tab in REQUIRED_TABS:
        if tab not in workbook.sheetnames:
            raise WorkbookError(f"{path.name}: no tab {tab!r}. The workbook needs the tabs "
                                f"{', '.join(REQUIRED_TABS)}.")
    for tab in workbook.sheetnames:
        if tab not in REQUIRED_TABS and tab not in TABS_NOT_USED_YET:
            raise WorkbookError(f"{path.name}: unknown tab {tab!r}.")

    # 3. Each tab on its own. Settings first: the other readers need the days.
    settings = read_settings(workbook["Settings"])
    volunteers = read_volunteers(workbook["Volunteers"], settings)
    posts = read_posts(workbook["Posts"])
    skills = read_skills(workbook["Skills"])
    demand = read_demand(workbook["Demand"], settings)

    # 4. Across tabs: the same volunteers on Volunteers and Skills...
    for nickname in volunteers:
        if nickname not in skills:
            raise WorkbookError(f"Skills: no row for {nickname} (from the Volunteers tab).")
    for nickname in skills:
        if nickname not in volunteers:
            raise WorkbookError(f"Skills: {nickname} is not on the Volunteers tab.")

    # ...and the same posts on Posts, Skills and Demand.
    post_names = []
    for post in posts:
        post_names.append(post.name)
    _check_same_posts(workbook["Skills"], ["Nickname", "Team", "Notes"], post_names)
    _check_same_posts(workbook["Demand"], ["Day", "Time", "Notes"], post_names)

    # 5. Combine: each volunteer gets their skills (the dict keeps the order of the sheet).
    for nickname, volunteer in volunteers.items():
        volunteer.skills = skills[nickname]

    return Problem(volunteers=list(volunteers.values()),
                   posts=posts,
                   demand=demand,
                   settings=settings)


def _check_same_posts(sheet: Worksheet, not_posts: list[str], post_names: list[str]) -> None:
    """Check that the post columns of this tab are exactly the posts on the Posts tab."""
    columns = find_post_columns(sheet, not_posts)
    for header in columns:
        if header not in post_names:
            raise WorkbookError(f"{sheet.title}: column {header!r} is not a post on the "
                                f"Posts tab.")
    for name in post_names:
        if name not in columns:
            raise WorkbookError(f"{sheet.title}: no column for the post {name!r} (from the "
                                f"Posts tab).")

"""Reads the input workbook (.xlsx) into a Problem the solver can work with.

Layout of this file: read_problem first (the table of contents), then one reader per
tab in the order read_problem calls them, then the helpers they share.

Functions that read a tab take an openpyxl sheet; the tests build small sheets in
memory. Helpers like cell_text are plain functions without openpyxl, so they can be
tested with simple values instead of a workbook file.
"""
from datetime import time
from pathlib import Path

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.errors import WorkbookError
from scheduler.helpers import debug_print
from scheduler.model import Post, Problem, Settings, Volunteer, block_of
from scheduler.model import MINUTES_PER_BLOCK, DAY_STARTS_AT_HOUR, BLOCKS_PER_DAY

# The layout of the input workbook this scheduler reads (the "Workbook format version"
# setting). Raise it only when the workbook layout changes, e.g. a renamed setting or a
# new required column, not for every new version of the scheduler.
WORKBOOK_FORMAT_VERSION = 1

# The tabs read_problem needs, and the ones it knows but does not read yet.
REQUIRED_TABS = ["Settings", "Volunteers", "Posts", "Skills", "Demand"]
TABS_NOT_USED_YET = ["ReadMe", "Events", "Wishes", "Fixed"]

KNOWN_SETTINGS = {"Workbook format version", "Time step", "Day boundary", "Days",
                  "Shift start step", "Minimum work stretch", "Preferred maximum shift length",
                  "Maximum work stretch", "Minimum break", "Lunch window start",
                  "Lunch window end", "Lunch break length", "Dinner window start",
                  "Dinner window end", "Dinner break length", "Default maximum hours per day",
                  "Default maximum hours total", "Weight: miss a REALLY-want event",
                  "Weight: miss a like-to-attend event", "Weight: skill score 3",
                  "Weight: skill score 2", "Weight: skill score 1",
                  "Weight: shift longer than preferred", "Weight: unfair spread of hours"}

REQUIRED_SETTINGS = {"Workbook format version", "Time step", "Day boundary", "Days",
                     "Minimum work stretch", "Maximum work stretch", "Minimum break"}


def read_problem(path: str | Path) -> Problem:
    """Read the input workbook at path into a Problem the solver can work with.

    Checks the file (.xlsx, exists) and the tabs (Settings, Volunteers, Posts, Skills and
    Demand are required; ReadMe, Events, Wishes and Fixed are known and ignored for now;
    any other tab is an error), calls the tab readers, checks across tabs (every
    volunteer has a Skills row and every Skills row is a volunteer; Posts, the Skills
    columns and the Demand columns name the same posts) and combines it all.
    Raises WorkbookError for the first problem it finds.
    """
    # 1. The file: an .xlsx that exists.
    path = Path(path)
    if path.suffix.lower() != ".xlsx":
        raise WorkbookError(f"{path.name}: the scheduler reads .xlsx files only. Save the "
                            f"workbook as Excel (.xlsx), e.g. File > Save As in LibreOffice.")
    if not path.exists():
        raise WorkbookError(f"{path.name}: file not found ({path}).")
    workbook = openpyxl.load_workbook(path)

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
    availability = read_volunteers(workbook["Volunteers"], settings)
    posts = read_posts(workbook["Posts"])
    skills = read_skills(workbook["Skills"])
    demand = read_demand(workbook["Demand"], settings)

    # 4. Across tabs: the same volunteers on Volunteers and Skills...
    for nickname in availability:
        if nickname not in skills:
            raise WorkbookError(f"Skills: no row for {nickname} (from the Volunteers tab).")
    for nickname in skills:
        if nickname not in availability:
            raise WorkbookError(f"Skills: {nickname} is not on the Volunteers tab.")

    # ...and the same posts on Posts, Skills and Demand.
    post_names = []
    for post in posts:
        post_names.append(post.name)
    _check_same_posts(workbook["Skills"], ["Nickname", "Team", "Notes"], post_names)
    _check_same_posts(workbook["Demand"], ["Day", "Time", "Notes"], post_names)

    # 5. Combine: each volunteer with their skills and availability.
    volunteers = []
    for nickname, available_blocks in availability.items():
        volunteers.append(Volunteer(name=nickname, skills=skills[nickname],
                                    available_blocks=available_blocks))

    return Problem(volunteers=volunteers, posts=posts, demand=demand, settings=settings)


def read_settings(sheet: Worksheet) -> Settings:
    """The Settings tab as Settings: one setting per row, in the columns Setting and Value.

    The order of the rows is free. Required: Workbook format version (must be
    WORKBOOK_FORMAT_VERSION), Time step (must be 15), Day boundary (must be 06:00), Days
    (comma separated, no duplicates), Minimum work stretch, Maximum work stretch and
    Minimum break (whole numbers, in minutes). Settings the scheduler does not use yet
    (meals, maximum hours, weights) are accepted and ignored. Raises WorkbookError for a
    missing, empty, duplicate or unknown setting, or a value that is not allowed.
    """
    debug_print(f"read_settings: reading tab {sheet.title}")
    # 1. Isolate the headers and their respective column numbers
    columns = find_columns(sheet, ["Setting", "Value"])

    # 2. Fetch all (unparsed) settings from the Settings sheet
    unparsed_settings = dict()
    for rownumber in range(2, sheet.max_row + 1):
        setting_name = cell_text(sheet.cell(row=rownumber, column=columns["Setting"]).value)
        if setting_name == "":
            continue

        if setting_name in unparsed_settings:
            raise WorkbookError(f"Settings: two settings with name {setting_name!r}.")
        else:
            unparsed_value = cell_text(sheet.cell(row=rownumber, column=columns["Value"]).value)
            unparsed_settings[setting_name] = unparsed_value

    # 3. Check for unknown settings
    for key, value in unparsed_settings.items():
        if key not in KNOWN_SETTINGS:
            raise WorkbookError(f"Settings: unknown setting {key!r}")

    # 4. Check for presence of all required settings
    for required_setting in REQUIRED_SETTINGS:
        if required_setting not in unparsed_settings:
            raise WorkbookError(f"Settings: Missing required setting {required_setting!r}")

    # 5. Check the required settings one by one and turn them into Settings
    version = _whole_number(unparsed_settings, "Workbook format version")
    if version != WORKBOOK_FORMAT_VERSION:
        raise WorkbookError(f"Settings, 'Workbook format version': this workbook is version "
                            f"{version}, this scheduler reads version {WORKBOOK_FORMAT_VERSION}.")

    time_step = _whole_number(unparsed_settings, "Time step")
    if time_step != MINUTES_PER_BLOCK:
        raise WorkbookError(f"Settings, 'Time step': the scheduler only supports "
                            f"{MINUTES_PER_BLOCK} minutes for now, not {time_step}.")

    # cell_text already turned a time typed into Excel into text, so compare as text.
    day_boundary = unparsed_settings["Day boundary"]
    expected_day_boundary = f"{DAY_STARTS_AT_HOUR:02d}:00"
    if day_boundary != expected_day_boundary:
        raise WorkbookError(f"Settings, 'Day boundary': the scheduler only supports "
                            f"{expected_day_boundary} for now, not {day_boundary}.")

    # Days: "Friday, Saturday, Sunday" -> ["Friday", "Saturday", "Sunday"]
    days = []
    for day in unparsed_settings["Days"].split(","):
        day = day.strip()
        if day in days:
            raise WorkbookError(f"Settings, 'Days': {day!r} appears more than once.")
        days.append(day)

    return Settings(
        min_stretch_minutes=_whole_number(unparsed_settings, "Minimum work stretch"),
        max_stretch_minutes=_whole_number(unparsed_settings, "Maximum work stretch"),
        min_break_minutes=_whole_number(unparsed_settings, "Minimum break"),
        days=tuple(days))  # a tuple, like the default in Settings


def read_volunteers(sheet: Worksheet, settings: Settings) -> dict[str, set[int]]:
    """The Volunteers tab as {nickname: available blocks}, in the order of the sheet.

    Reads the Nickname column and one availability column per day in settings.days (a
    missing day column is an error); other columns are ignored. Each day's cell goes
    through parse_availability and the days are combined. A completely empty row is
    skipped. Raises WorkbookError (naming row, volunteer and day where possible) for a
    missing column, a nickname used twice, a row with availability but no nickname, an
    invalid availability, or a volunteer who is not available on any day.
    """
    debug_print(f"read_volunteers: reading tab {sheet.title}")
    # 1. The Nickname column and one column per convention day.
    columns = find_columns(sheet, ["Nickname"] + list(settings.days))

    volunteers = {}
    for row in range(2, sheet.max_row + 1):
        nickname = cell_text(sheet.cell(row=row, column=columns["Nickname"]).value)

        # 2. The availability cells of this row, per day: {"Friday": "yes", ...}
        availability = {}
        for day in settings.days:
            availability[day] = cell_text(sheet.cell(row=row, column=columns[day]).value)

        # 3. A row without nickname is only fine when it is completely empty.
        if nickname == "":
            for day in settings.days:
                if availability[day] != "":
                    raise WorkbookError(f"Volunteers, row {row}: availability but no nickname.")
            continue  # an empty row: skip it

        if nickname in volunteers:
            raise WorkbookError(f"Volunteers, row {row}: the nickname {nickname!r} is used "
                                f"more than once.")

        # 4. All days together; | combines two sets.
        blocks = set()
        for day in settings.days:
            try:
                blocks = blocks | parse_availability(availability[day], day, settings)
            except ValueError as error:
                # Put row, volunteer and day in front of the message from parse_availability.
                raise WorkbookError(f"Volunteers, row {row} ({nickname}), {day}: {error}") from None

        if len(blocks) == 0:
            raise WorkbookError(f"Volunteers, row {row}: {nickname} is not available on any day. "
                                f"Remove the row if they are not coming.")

        volunteers[nickname] = blocks

    return volunteers


def read_posts(sheet: Worksheet) -> list[Post]:
    """The Posts tab as a list of Post, in the order of the sheet.

    Reads only the Post column for now (Group and Colour are for the output later).
    An empty row is skipped. Raises WorkbookError for a missing Post column, a post
    that appears twice, or a tab without any posts.
    """
    debug_print(f"read_posts: reading tab {sheet.title}")
    columns = find_columns(sheet, ["Post"])

    posts = []
    names = []   # the names seen so far, to spot a post that appears twice
    for row in range(2, sheet.max_row + 1):
        name = cell_text(sheet.cell(row=row, column=columns["Post"]).value)
        if name == "":
            continue  # an empty row: skip it
        if name in names:
            raise WorkbookError(f"Posts, row {row}: the post {name!r} appears more than once.")
        names.append(name)
        posts.append(Post(name=name))

    if len(posts) == 0:
        raise WorkbookError("Posts: there are no posts. Add one row per post.")

    return posts


def read_skills(sheet: Worksheet) -> dict[str, dict[str, int]]:
    """The Skills tab as {nickname: {post: score}}, in the order of the sheet.

    Every column except Nickname, Team and Notes is a post column (empty headers are
    skipped). A score is 1 (can), 2 (good at it / likes it) or 3 (main role); an empty
    cell means never and is left out. An empty row is skipped. Raises WorkbookError for a
    missing Nickname column, a post column or nickname that appears twice, a row with
    scores but no nickname, a score that is not empty, 1, 2 or 3, or a volunteer without
    any score.
    """
    debug_print(f"read_skills: reading tab {sheet.title}")
    nickname_column = find_columns(sheet, ["Nickname"])["Nickname"]

    # 1. The post columns: every column except these.
    post_columns = _post_columns(sheet, not_posts=["Nickname", "Team", "Notes"])

    # 2. One row per volunteer.
    skills = {}
    for row in range(2, sheet.max_row + 1):
        nickname = cell_text(sheet.cell(row=row, column=nickname_column).value)

        # The scores of this row: {"Tickets": 3, ...}, empty cells left out.
        scores = {}
        for post, column in post_columns.items():
            text = cell_text(sheet.cell(row=row, column=column).value)
            if text == "":
                continue  # empty = never
            if text not in ("1", "2", "3"):
                raise WorkbookError(f"Skills, row {row} ({nickname}), {post}: {text!r} is not a "
                                    f"score. Use 1, 2, 3 or leave it empty.")
            scores[post] = int(text)

        # A row without nickname is only fine when it is completely empty.
        if nickname == "":
            if len(scores) > 0:
                raise WorkbookError(f"Skills, row {row}: scores but no nickname.")
            continue  # an empty row: skip it

        if nickname in skills:
            raise WorkbookError(f"Skills, row {row}: the nickname {nickname!r} is used "
                                f"more than once.")
        if len(scores) == 0:
            raise WorkbookError(f"Skills, row {row}: {nickname} has no score for any post. "
                                f"Give them at least one, or remove the row.")

        skills[nickname] = scores

    return skills


def read_demand(sheet: Worksheet, settings: Settings) -> dict[tuple[str, int], int]:
    """The Demand tab as {(post, block): number of people needed}, like Problem.demand.

    Each row is one block, given by its Day and Time (night times belong to the day
    before, as in block_of); every other column except Notes is a post. Empty or 0 means
    closed and is left out, so a row with a Day and Time but no number means everything
    is closed then. A completely empty row is skipped. Raises WorkbookError for a missing
    Day or Time column, a row with an invalid or missing Day or Time (also without
    numbers), the same Day and Time twice, or a number that is not a whole number of at
    least 0.
    """
    debug_print(f"read_demand: reading tab {sheet.title}")
    columns = find_columns(sheet, ["Day", "Time"])
    post_columns = _post_columns(sheet, not_posts=["Day", "Time", "Notes"])

    demand = {}
    rows_of_blocks = {}   # block -> the row it is on, to spot the same Day and Time twice
    for row in range(2, sheet.max_row + 1):
        day = cell_text(sheet.cell(row=row, column=columns["Day"]).value)
        time_text = cell_text(sheet.cell(row=row, column=columns["Time"]).value)

        # 1. The numbers of this row: {"Tickets": 2, ...}, empty and 0 left out.
        needed_per_post = {}
        for post, column in post_columns.items():
            text = cell_text(sheet.cell(row=row, column=column).value)
            if text == "":
                continue  # empty = closed
            try:
                needed = int(text)
            except ValueError:
                needed = -1   # not a whole number: reported just below
            if needed < 0:
                raise WorkbookError(f"Demand, row {row} ({day} {time_text}), {post}: {text!r} "
                                    f"is not a number of people (a whole number, 0 = closed).")
            if needed > 0:
                needed_per_post[post] = needed

        # 2. A completely empty row is skipped; any other row needs a valid Day and Time.
        if day == "" and time_text == "" and len(needed_per_post) == 0:
            continue

        # 3. Which block this row is, and not one we have seen already.
        try:
            block = block_of(day, time_text, settings)
        except ValueError as error:
            raise WorkbookError(f"Demand, row {row}: {error}") from None
        if block in rows_of_blocks:
            raise WorkbookError(f"Demand, row {row}: {day} {time_text} is already on row "
                                f"{rows_of_blocks[block]}.")
        rows_of_blocks[block] = row

        # 4. Only the open posts go into the demand.
        for post, needed in needed_per_post.items():
            demand[(post, block)] = needed

    return demand


def find_columns(sheet: Worksheet, names: list[str]) -> dict[str, int]:
    """The column number of each header in names, read from row 1 of the sheet.

    Example: header Setting, Value, Unit and names ["Setting", "Value"] gives
    {"Setting": 1, "Value": 2}. Spaces around a header are ignored. Raises WorkbookError
    (naming the tab) when a column is missing or a header appears twice.
    """
    # Row 1 as tidy text, e.g. ["Setting", "Value", "Unit"].
    headers = []
    for cell in sheet[1]:
        headers.append(cell_text(cell.value))

    columns = {}
    for name in names:
        # Every column with this header; enumerate counts from 1, like column A = 1.
        matching = []
        for column_number, header in enumerate(headers, start=1):
            if header == name:
                matching.append(column_number)

        if len(matching) == 0:
            raise WorkbookError(f"{sheet.title}: no column {name!r} in the header row (row 1).")
        if len(matching) > 1:
            raise WorkbookError(f"{sheet.title}: the header {name!r} is in more than one column.")
        columns[name] = matching[0]

    return columns


def _post_columns(sheet: Worksheet, not_posts: list[str]) -> dict[str, int]:
    """Every column in row 1 that is a post, as {post: column number}.

    A post column is any column whose header is not empty and not in not_posts (used by
    the Skills and Demand tabs, where the posts are the columns). Raises WorkbookError
    (naming the tab) when a post has more than one column.
    """
    post_columns = {}
    for column, cell in enumerate(sheet[1], start=1):
        header = cell_text(cell.value)
        if header == "" or header in not_posts:
            continue
        if header in post_columns:
            raise WorkbookError(f"{sheet.title}: the post {header!r} has more than one column.")
        post_columns[header] = column
    return post_columns


def _check_same_posts(sheet: Worksheet, not_posts: list[str], post_names: list[str]) -> None:
    """Check that the post columns of this tab are exactly the posts on the Posts tab."""
    columns = _post_columns(sheet, not_posts)
    for header in columns:
        if header not in post_names:
            raise WorkbookError(f"{sheet.title}: column {header!r} is not a post on the "
                                f"Posts tab.")
    for name in post_names:
        if name not in columns:
            raise WorkbookError(f"{sheet.title}: no column for the post {name!r} (from the "
                                f"Posts tab).")


def _whole_number(settings: dict[str, str], name: str) -> int:
    """The setting with this name as a whole number; WorkbookError if it isn't one."""
    try:
        return int(settings[name])
    except ValueError:
        # from None: show only our clear message, not the ValueError behind it
        raise WorkbookError(f"Settings, {name!r}: {settings[name]!r} is not a whole "
                            f"number.") from None


def cell_text(value: str | int | float | time | None) -> str:
    """The value of a cell as tidy text: spaces around it removed, empty cell = "".

    A time value (when someone types 14:00 into a cell) becomes "14:00".
    """
    if value is None:
        result = ""
    elif isinstance(value, time):
        result = value.strftime("%H:%M")
    else:  # str, int or float
        result = str(value).strip()

    return result


def parse_availability(text: str, day: str, settings: Settings) -> set[int]:
    """The blocks a volunteer is available on this convention day, from one Volunteers cell.

    text is the cell after cell_text, upper or lower case doesn't matter:
    "yes" = the whole convention day (06:00 to 06:00), "no" or "" = not that day,
    "08:00-18:00" = from 08:00 up to (not including) 18:00. A range may pass midnight
    (Saturday "20:00-02:00"); an end of "06:00" means until the end of the convention day.
    Anything else raises ValueError naming the value (the reader adds volunteer and row).
    """
    # The convention day starts at block_of(day, "06:00"); this also checks the day name.
    day_start = block_of(day, "06:00", settings)
    lowered = text.lower()

    # 1. The whole day, or not at all.
    if lowered == "yes":
        return set(range(day_start, day_start + BLOCKS_PER_DAY))
    if lowered == "no" or lowered == "":
        return set()

    # 2. Anything else must be one range "start-end".
    parts = lowered.split("-")
    if len(parts) != 2:
        raise ValueError(f"Availability {text!r} is not 'yes', 'no' or a time range "
                         f"like 08:00-18:00.")
    first_block = block_of(day, parts[0].strip(), settings)
    block_after_last = block_of(day, parts[1].strip(), settings)

    # An end of 06:00 gives the start of the day; as an end it means the end of the day.
    if block_after_last == day_start:
        block_after_last = day_start + BLOCKS_PER_DAY

    if block_after_last <= first_block:
        raise ValueError(f"Availability {text!r}: the end must be after the start.")

    return set(range(first_block, block_after_last))

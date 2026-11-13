"""Reads the Skills tab: read_skills."""
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.errors import WorkbookError
from scheduler.helpers import debug_print
from scheduler.reading.cells import cell_text, find_columns, find_post_columns


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
    post_columns = find_post_columns(sheet, not_posts=["Nickname", "Team", "Notes"])

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

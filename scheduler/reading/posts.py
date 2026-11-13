"""Reads the Posts tab: read_posts."""
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.debug import debug_print
from scheduler.errors import WorkbookError
from scheduler.model import Post
from scheduler.reading.cells import cell_text, find_columns


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

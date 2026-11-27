"""Reads the Posts tab: read_posts."""
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.debug import debug_print
from scheduler.errors import WorkbookError
from scheduler.model import Post
from scheduler.reading.cells import cell_text, find_columns, parse_colour


def read_posts(sheet: Worksheet) -> list[Post]:
    """The Posts tab as a list of Post, in the order of the sheet.

    Reads the columns Post, Group and Colour (a missing column is an error); other columns
    such as Notes are ignored. Group is free text; Colour goes through parse_colour, so it
    is stored as six hex digits in capitals, or "" when empty (no colour, white). A
    completely empty row is skipped. Raises WorkbookError (naming the row, and the post
    where possible) for a missing column, a row with a group or colour but no post name, a
    post that appears twice, an invalid colour, or a tab without any posts.
    """
    debug_print(f"read_posts: reading tab {sheet.title}")
    columns = find_columns(sheet, ["Post", "Group", "Colour"])

    posts = []
    names = []   # the names seen so far, to spot a post that appears twice
    for row in range(2, sheet.max_row + 1):
        # Read the values
        name = cell_text(sheet.cell(row=row, column=columns["Post"]).value)
        group = cell_text(sheet.cell(row=row, column=columns["Group"]).value)
        colour = cell_text(sheet.cell(row=row, column=columns["Colour"]).value)

        # A row without a post name is only fine when it is completely empty.
        if name == "":
            if group != "":
                raise WorkbookError(f"Posts, row {row}: Group but no post name.")
            if colour != "":
                raise WorkbookError(f"Posts, row {row}: Colour but no post name.")

            continue  # an empty row: skip it
        if name in names:
            raise WorkbookError(f"Posts, row {row}: the post {name!r} appears more than once.")

        # Parse colour
        try:
            parsed_colour = parse_colour("Colour", colour)
        except ValueError as error:
            raise WorkbookError(f"Posts, row {row} ({name}), {error}") from None

        # Record post
        names.append(name)
        posts.append(Post(name=name, group=group, colour=parsed_colour))

    if len(posts) == 0:
        raise WorkbookError("Posts: there are no posts. Add one row per post.")

    return posts

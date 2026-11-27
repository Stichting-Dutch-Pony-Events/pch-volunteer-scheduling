"""Reads the Teams tab: read_teams."""
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.debug import debug_print
from scheduler.errors import WorkbookError
from scheduler.reading.cells import cell_text, find_columns, parse_colour


def read_teams(sheet: Worksheet) -> dict[str, str]:
    """The Teams tab as {team: colour}, in the order of the sheet.

    Reads the columns Team and Colour (a missing column is an error); other columns such as
    Notes are ignored. Colour goes through parse_colour, so it is stored as six hex digits
    in capitals, or "" when empty (no colour, white). A completely empty row is skipped; a
    tab with only a header gives {} (a convention without teams). Raises WorkbookError
    (naming the row, and the team where possible) for a missing column, a row with a colour
    but no team name, a team that appears twice, or an invalid colour.
    """
    debug_print(f"read_teams: reading tab {sheet.title}")
    raise NotImplementedError("read_teams is not written yet")

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
    columns = find_columns(sheet, ["Team", "Colour"])

    team_colours = {}
    for row in range(2, sheet.max_row + 1):
        # Read the values
        name = cell_text(sheet.cell(row=row, column=columns["Team"]).value)
        colour = cell_text(sheet.cell(row=row, column=columns["Colour"]).value)

        # A row without a team name is only fine when it is completely empty.
        if name == "":
            if colour != "":
                raise WorkbookError(f"Teams, row {row}: Colour but no team name.")

            continue  # an empty row: skip it
        if name in team_colours:
            raise WorkbookError(f"Teams, row {row}: the team {name!r} appears more than once.")

        # Parse colour
        try:
            parsed_colour = parse_colour("Colour", colour)
        except ValueError as error:
            raise WorkbookError(f"Teams, row {row} ({name}), {error}") from None

        # Record the team
        team_colours[name] = parsed_colour

    return team_colours

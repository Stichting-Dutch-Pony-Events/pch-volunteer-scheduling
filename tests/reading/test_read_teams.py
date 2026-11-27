import openpyxl
import pytest
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.errors import WorkbookError
from scheduler.reading.teams import read_teams


# Like the real Teams tab: Team and Colour are read, Notes is ignored.
HEADER = ("Team", "Colour", "Notes")


def _teams_sheet(rows: list[tuple], header: tuple[str, ...] = HEADER) -> Worksheet:
    """A new in-memory sheet called Teams: the header in row 1, then one row per team."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Teams"            # so the error messages can name the tab
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    return sheet


def test_each_row_gives_a_team_and_its_colour():
    """Every row becomes an entry team -> colour, in the same order as on the tab."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_colour_is_stored_as_six_hex_digits_in_capitals():
    """A Colour cell "#f4cccc" is stored as "F4CCCC" (the value parse_colour gives)."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_empty_colour_gives_an_empty_string():
    """A team without a colour gets "" (no colour, white)."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_empty_rows_are_skipped():
    """A completely empty row between the teams is no problem."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_tab_with_only_a_header_gives_no_teams():
    """A Teams tab without any rows gives {}: a convention without teams is fine."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_the_same_team_twice_raises_workbook_error():
    """Two rows with the same team are an error naming the team."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_colour_but_no_team_name_raises_workbook_error():
    """A row with a colour but no team name is an error naming the row."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_invalid_colour_raises_workbook_error_naming_row_team_and_value():
    """A colour like "red" is an error naming the tab, row, team, column and value."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


@pytest.mark.parametrize("column", ["Team", "Colour"])
def test_missing_team_or_colour_column_raises_workbook_error(column: str):
    """A missing Team or Colour column is an error naming that column."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")

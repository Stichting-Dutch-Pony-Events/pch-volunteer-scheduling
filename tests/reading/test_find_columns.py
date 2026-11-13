import openpyxl
import pytest

from scheduler.errors import WorkbookError
from scheduler.reading.cells import find_columns


def test_columns_are_found_by_their_header():
    """Each asked-for header gives its column number (column A = 1)."""
    # Arrange
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Settings"         # so the error message can name the tab
    sheet.append(["Setting", "Value", "Unit"])   # the first append is row 1

    # Act
    result = find_columns(sheet, ["Setting", "Value"])

    # Assert
    assert result == {"Setting": 1, "Value": 2}


def test_column_order_does_not_matter():
    """The columns are found wherever they are in the header row."""
    # Arrange
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Settings"         # so the error message can name the tab
    sheet.append(["Unit", "Value", "Setting"])   # the first append is row 1

    # Act
    result = find_columns(sheet, ["Setting", "Value"])

    # Assert
    assert result == {"Setting": 3, "Value": 2}


def test_spaces_around_a_header_are_ignored():
    """A header " Value " is found when asking for "Value"."""
    # Arrange
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Settings"         # so the error message can name the tab
    sheet.append([" Value "])   # the first append is row 1

    # Act
    result = find_columns(sheet, ["Value"])

    # Assert
    assert result == {"Value": 1}


def test_missing_column_raises_workbook_error():
    """A missing column is an error that names the column and the tab."""
    # Arrange
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Settings"         # so the error message can name the tab
    sheet.append(["Unit", "Setting"])   # the first append is row 1

    # Act
    # Act done inside assert

    # Assert
    with pytest.raises(WorkbookError, match="Settings.*Value"):
        find_columns(sheet, ["Value"])


def test_the_same_header_twice_raises_workbook_error():
    """Two columns with the same header are an error: it is unclear which one is meant."""
    # Arrange
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Settings"         # so the error message can name the tab
    sheet.append(["Value", "Value"])   # the first append is row 1

    # Act
    # Act done inside assert

    # Assert
    with pytest.raises(WorkbookError, match="Settings.*Value"):
        find_columns(sheet, ["Value"])


def test_a_duplicate_header_that_is_not_asked_for_is_fine():
    """Only the asked-for headers must be unique; e.g. two Notes columns are no problem."""
    # Arrange
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Settings"         # so the error message can name the tab
    sheet.append(["Notes", "Notes", "Value"])   # the first append is row 1

    # Act
    result = find_columns(sheet, ["Value"])

    # Assert
    assert result == {"Value": 3}

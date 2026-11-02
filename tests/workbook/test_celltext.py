from datetime import time

from scheduler.workbook import cell_text


def test_empty_cell_gives_empty_text():
    """An empty cell (None from openpyxl) becomes an empty string."""
    # Arrange

    # Act

    # Assert


def test_text_is_returned_unchanged():
    """Plain text comes back as it is, including spaces inside it."""
    # Arrange

    # Act

    # Assert


def test_spaces_around_text_are_removed():
    """Spaces before and after the text are stripped."""
    # Arrange

    # Act

    # Assert


def test_text_of_only_spaces_counts_as_empty():
    """A cell with only spaces in it counts as an empty cell."""
    # Arrange

    # Act

    # Assert


def test_whole_number_becomes_text():
    """A number from Excel becomes its text, e.g. 15 -> "15"."""
    # Arrange

    # Act

    # Assert


def test_excel_time_becomes_hours_and_minutes():
    """A time value typed into Excel becomes "HH:MM"."""
    # Arrange

    # Act

    # Assert


def test_excel_time_before_ten_gets_a_leading_zero():
    """A morning time gets a leading zero, e.g. 08:15, just like in the workbook."""
    # Arrange

    # Act

    # Assert

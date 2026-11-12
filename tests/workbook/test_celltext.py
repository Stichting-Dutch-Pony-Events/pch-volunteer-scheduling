from datetime import time

import pytest

from scheduler.workbook import cell_text


def test_empty_cell_gives_empty_text():
    """An empty cell (None from openpyxl) becomes an empty string."""
    # Arrange
    # No arranging needed

    # Act
    result = cell_text(None)

    # Assert
    assert result == ""


def test_text_is_returned_unchanged():
    """Plain text comes back as it is, including spaces inside it."""
    # Arrange
    # No arranging needed

    # Act
    result = cell_text("Mock Mane")

    # Assert
    assert result == "Mock Mane"


def test_spaces_around_text_are_removed():
    """Spaces before and after the text are stripped."""
    # Arrange
    # No arranging needed

    # Act
    result = cell_text("  Friday ")

    # Assert
    assert result == "Friday"


def test_text_of_only_spaces_counts_as_empty():
    """A cell with only spaces in it counts as an empty cell."""
    # Arrange
    # No arranging needed

    # Act
    result = cell_text("   ")

    # Assert
    assert result == ""


# parametrize runs this test once for every (value, expected) pair in the list; pytest
# reports each one as its own test, named after the text in ids (e.g. "...[zero]").
@pytest.mark.parametrize(
    "whole_number, expected",
    [(15, "15"),
     (0, "0"),
     (123, "123"),
     (-2, "-2"),
     (1000000, "1000000")],
    ids=["fifteen", "zero", "three digits", "negative", "large"])
def test_whole_number_becomes_text(whole_number, expected):
    """A number from Excel becomes its text, e.g. 15 -> "15"."""
    # Arrange
    # (the number and the expected text come from parametrize)

    # Act
    result = cell_text(whole_number)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    "value, expected",
    [(time(11, 0), "11:00"),
     (time(14, 30), "14:30"),
     (time(23, 45), "23:45")],
    ids=["eleven", "half past two", "quarter to midnight"])
def test_excel_time_becomes_hours_and_minutes(value, expected):
    """A time value typed into Excel becomes "HH:MM"."""
    # Arrange
    # (the time and the expected text come from parametrize)

    # Act
    result = cell_text(value)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    "value, expected",
    [(time(8, 15), "08:15"),
     (time(0, 0), "00:00"),
     (time(1, 30), "01:30")],
    ids=["quarter past eight", "midnight", "half past one at night"])
def test_excel_time_before_ten_gets_a_leading_zero(value, expected):
    """A morning time gets a leading zero, e.g. 08:15, just like in the workbook."""
    # Arrange
    # (the time and the expected text come from parametrize)

    # Act
    result = cell_text(value)

    # Assert
    assert result == expected

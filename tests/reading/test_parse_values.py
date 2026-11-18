"""Tests of the functions that turn the text of one cell into a value (no sheets needed).

Whether a cell may be empty, and what an empty cell means, is up to the readers; those
rules are tested in test_read_settings.py and test_read_volunteers.py.
"""
import pytest
import re

from scheduler.reading.cells import parse_hour_limit, parse_whole_number
from scheduler.reading.settings import parse_days


# parse_whole_number

@pytest.mark.parametrize("text, minimum, expected", [("45", 0, 45), ("0", 0, 0), ("1", 1, 1)],
                         ids=["number", "zero at minimum 0", "one at minimum 1"])
def test_whole_number_text_is_read_as_a_number(text: str, minimum: int, expected: int):
    """A whole number of at least the minimum is read as that number."""
    # Arrange
    # (No arrangement required)

    # Act
    result = parse_whole_number("Test setting whole number", text, minimum)

    # Assert
    assert result == expected


@pytest.mark.parametrize("text", ["", "1.5", "six", "8h"],
                         ids=["empty", "decimal", "word", "unit"])
def test_text_that_is_not_a_whole_number_raises_value_error(text: str):
    """Text that is not a whole number raises ValueError naming the setting and the text."""
    # Arrange
    # (No arrangement required)

    # Act
    # (Act and assert on the same line)

    # Assert
    with pytest.raises(ValueError, match=f"Test setting whole number.*{re.escape(text)}"):
        parse_whole_number("Test setting whole number", text, 0)


@pytest.mark.parametrize("text, minimum", [("-1", 0), ("0", 1)],
                         ids=["negative at minimum 0", "zero at minimum 1"])
def test_whole_number_below_the_minimum_raises_value_error(text: str, minimum: int):
    """A whole number below the minimum raises ValueError naming the setting and the minimum."""
    # Arrange
    # (No arrangement required)

    # Act
    # (Act and assert on the same line)

    # Assert
    with pytest.raises(ValueError, match=f"Test setting whole number.*{text}.*minimum.*{minimum}"):
        parse_whole_number("Test setting whole number", text, minimum)


# parse_hour_limit

@pytest.mark.parametrize("text, max_hours, expected", [("8", 24, 480), ("24", 24, 1440)],
                         ids=["hours", "at the maximum"])
def test_hour_limit_is_read_in_minutes(text: str, max_hours: int, expected: int):
    """Whole hours from 1 up to the maximum are read as minutes."""
    # Arrange
    # (No arrangement required)

    # Act
    result = parse_hour_limit("Test setting hour limit", text, max_hours)

    # Assert
    assert result == expected


@pytest.mark.parametrize("text", ["none", "None", "NONE"],
                         ids=["lowercase", "capital", "all capitals"])
def test_none_means_no_hour_limit(text: str):
    """"none", in any case, gives None: no limit."""
    # Arrange
    # (No arrangement required)

    # Act
    result = parse_hour_limit("Test setting hour limit", text, 24)

    # Assert
    assert result is None


@pytest.mark.parametrize("text", ["", "7.5", "eight", "0", "-2", "25"],
                         ids=["empty", "decimal", "word", "zero", "negative", "above maximum"])
def test_invalid_hour_limit_raises_value_error(text: str):
    """An hour limit that is not a whole number from 1 up to the maximum raises ValueError."""
    # Arrange
    # (No arrangement required)

    # Act
    # (Act and assert on the same line)

    # Assert
    with pytest.raises(ValueError, match=f"Test setting hour limit.*{re.escape(text)}"):
        parse_hour_limit("Test setting hour limit", text, 24)


# parse_days

def test_days_are_split_on_commas_with_spaces_removed():
    """"Saturday ,Sunday" gives the days ("Saturday", "Sunday")."""
    # Arrange
    # (No arrangement required)

    # Act
    result = parse_days("Saturday ,Sunday")

    # Assert
    assert result == ("Saturday", "Sunday")


def test_the_same_day_twice_raises_value_error():
    """"Friday, Friday" raises ValueError naming the day."""
    # Arrange
    # (No arrangement required)

    # Act
    # (Act and assert on the same line)

    # Assert
    with pytest.raises(ValueError, match="Friday"):
        parse_days("Friday, Friday")


@pytest.mark.parametrize("text", ["Friday, , Saturday", "Friday, Saturday,"],
                         ids=["between commas", "comma at the end"])
def test_empty_day_name_raises_value_error(text: str):
    """An empty day name, between two commas or after the last one, raises ValueError."""
    # Arrange
    # (No arrangement required)

    # Act
    # (Act and assert on the same line)

    # Assert
    with pytest.raises(ValueError, match="empty"):
        parse_days(text)

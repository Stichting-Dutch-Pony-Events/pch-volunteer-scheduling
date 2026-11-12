import pytest

from scheduler.model import Settings
from scheduler.workbook import parse_availability


# The blocks depend on the days, so the tests pass them explicitly instead of relying on
# the defaults in model.py. Friday = blocks 0-95, Saturday = blocks 96-191.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))


def test_yes_means_the_whole_convention_day():
    """"yes" gives every block of that day, from 06:00 up to 06:00 the next morning."""
    # Arrange
    expected = set(range(0, 96))

    # Act
    result = parse_availability("yes", "Friday", RULES)

    # Assert
    assert result == expected


@pytest.mark.parametrize("text", ["Yes", "YES", "yes"],
                         ids=["capital", "all capitals", "lowercase"])
def test_yes_is_not_case_sensitive(text):
    """Case sensitivity of 'yes' should be ignored."""
    # Arrange
    expected = set(range(0, 96))

    # Act
    result = parse_availability(text, "Friday", RULES)

    # Assert
    assert result == expected


@pytest.mark.parametrize("text", ["no", "No", "", "NO"],
                         ids=["no", "capital", "empty", "all capitals"])
def test_no_or_empty_means_not_available(text):
    """"no" (any case) or an empty cell gives no blocks at all."""
    # Arrange
    expected = set()

    # Act
    result = parse_availability(text, "Friday", RULES)

    # Assert
    assert result == expected


def test_time_range_gives_the_blocks_from_start_up_to_end():
    """A range like 08:00-18:00 gives the blocks from 08:00 up to (not including) 18:00."""
    # Arrange
    expected = set(range(8, 48))

    # Act
    result = parse_availability("08:00-18:00", "Friday", RULES)

    # Assert
    assert result == expected


def test_spaces_around_the_dash_are_allowed():
    """"08:00 - 18:00" means the same as "08:00-18:00"."""
    # Arrange
    expected = set(range(8, 48))

    # Act
    result = parse_availability("08:00 - 18:00", "Friday", RULES)

    # Assert
    assert result == expected


def test_time_range_past_midnight_stays_on_the_same_convention_day():
    """Saturday 20:00-02:00 runs into the Saturday night, not back to Saturday morning."""
    # Arrange
    expected = set(range(152, 176))

    # Act
    result = parse_availability("20:00-02:00", "Saturday", RULES)

    # Assert
    assert result == expected


def test_range_ending_at_06_00_lasts_until_the_end_of_the_day():
    """An end of 06:00 means until the end of the convention day, not its start."""
    # Arrange
    expected = set(range(152, 192))

    # Act
    result = parse_availability("20:00-06:00", "Saturday", RULES)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    "text",
    ["yse", "maybe", "unavailable"],
    ids=["typo", "maybe", "unavailable"])
def test_unknown_word_raises_value_error(text):
    """Anything other than yes, no, empty or a range is an error that names the value."""
    # Arrange
    # No arrangement needed

    # Act
    # Act and Assert are in the same step

    # Assert
    with pytest.raises(ValueError, match=text):
        parse_availability(text, "Friday", RULES)


@pytest.mark.parametrize(
    "text",
    ["18:00-08:00", "12:00-12:00"],
    ids=["end before start", "end equals start"])
def test_range_whose_end_is_not_after_its_start_raises_value_error(text):
    """A reversed or empty range is an error, never a silent "not available"."""
    # Arrange
    # No arrangement needed

    # Act
    # Act and Assert are in the same step

    # Assert
    with pytest.raises(ValueError):
        parse_availability(text, "Friday", RULES)


def test_several_ranges_raise_value_error():
    """Only one range per cell for now, so "08:00-12:00, 14:00-18:00" is an error."""
    # Arrange
    # No arrangement needed

    # Act
    # Act and Assert are in the same step

    # Assert
    with pytest.raises(ValueError):
        parse_availability("08:00-12:00, 14:00-18:00", "Friday", RULES)


@pytest.mark.parametrize(
    "text",
    ["18:00-25:00", "12:11-12:45"],
    ids=["hour too high", "not on a 15-minute step"])
def test_invalid_time_in_range_raises_value_error(text):
    """A range with an impossible time like 25:00 or 12:11 is an error (passed on from block_of)."""
    # Arrange
    # No arrangement needed

    # Act
    # Act and Assert are in the same step

    # Assert
    with pytest.raises(ValueError):
        parse_availability(text, "Friday", RULES)

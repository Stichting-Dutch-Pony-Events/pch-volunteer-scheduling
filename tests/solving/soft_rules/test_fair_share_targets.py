import pytest

from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks, block_of
from scheduler.solving.soft_rules import fair_share_targets


# Passed explicitly instead of relying on the defaults in model.py. Two days keep the
# examples small: Friday = blocks 0-95, Saturday = blocks 96-191 (block 0 = Friday 06:00).
# fair_share_targets only looks at the demand, the availability and the hour limits, so
# no soft rule needs to be switched on.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday"))

ALL_DAYS = all_blocks(RULES)


def test_only_volunteer_gets_all_the_demand_as_target():
    """With one volunteer, their target is the whole demand."""
    # Arrange
    # Idea: only Mock Mane, Tickets needs 1 in blocks 0-7 -> target 8.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_volunteers_available_on_the_same_days_get_the_same_target():
    """Two volunteers who are there on the same days share the demand equally."""
    # Arrange
    # Idea: Mock Mane and Testy Hooves both all weekend, Tickets needs 1 in blocks 0-7
    # -> 4 and 4.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_volunteer_available_on_fewer_days_gets_a_smaller_target():
    """A volunteer there on one of two equally long days gets half the share of one on both."""
    # Arrange
    # Idea: Tickets needs 1 on Friday blocks 0-7 and Saturday blocks 96-103 (both days 8
    # blocks long, 16 in total). Mock Mane both days (weight 16), Testy Hooves only Friday
    # (weight 8) -> 16 x 16/24 and 16 x 8/24, rounded.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_being_available_later_in_the_day_does_not_raise_the_target():
    """Two volunteers there on the same day get the same target, however late they stay."""
    # Arrange
    # Idea: Saturday demand from 10:00 to 02:00 (block_of helps). Mock Mane available
    # until 22:00, Testy Hooves until 02:00 -> the same target.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_availability_outside_the_convention_hours_of_a_day_does_not_count():
    """A day counts only if the volunteer is there between its first and last demand."""
    # Arrange
    # Idea: Friday demand blocks 0-7. Mock Mane available Friday blocks 0-7, Testy Hooves
    # only Friday blocks 80-90 (after the last demand) -> Testy Hooves 0, Mock Mane 8.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_day_length_runs_from_the_first_to_the_last_demand_including_gaps():
    """A gap in a day's demand does not make the day shorter."""
    # Arrange
    # Idea: Friday demand blocks 0-3 and 12-15 (length 16, not 8), Saturday blocks 96-103
    # (length 8). Mock Mane both days (weight 24), Testy Hooves only Saturday (weight 8);
    # total demand 16 -> 12 and 4. With the gap left out it would be 10.67 and 5.33.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_demand_for_more_people_counts_once_per_person():
    """A block that needs two people adds two blocks to the work to share."""
    # Arrange
    # Idea: Mock Mane and Testy Hooves both all weekend, Tickets needs 2 in blocks 0-7
    # (16 person-blocks) -> 8 and 8.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_target_is_rounded_to_whole_blocks():
    """A share that is not a whole number of blocks is rounded."""
    # Arrange
    # Idea: Tickets needs 1 on Friday blocks 0-7 (length 8) and Saturday blocks 96-97
    # (length 2): 10 blocks in total. Mock Mane both days (weight 10), Testy Hooves only
    # Friday (weight 8) -> 10 x 10/18 = 5.56 and 10 x 8/18 = 4.44 -> 6 and 4.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_target_is_at_most_the_total_hour_limit():
    """A volunteer with a total hour limit never gets a target above it."""
    # Arrange
    # Idea: Mock Mane (max_minutes_total=60, 4 blocks) and Testy Hooves (no limit), both all
    # weekend, Tickets needs 1 in blocks 0-15 -> Mock Mane 4 (not 8), Testy Hooves 8.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_without_demand_every_target_is_0():
    """With no demand at all, every volunteer's target is 0 (no division by zero)."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")

import pytest

from scheduler.model import Post, Problem, Settings, Volunteer
from scheduler.writing.individual_schedules_sheet import free_cell_is_white, half_hour_rows


# Passed explicitly instead of relying on the defaults in model.py. Friday = blocks 0-95,
# Saturday = 96-191, Sunday = 192-287 (block 0 = Friday 06:00, block 32 = Friday 14:00).
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))


# half_hour_rows. It uses rows_to_show with the Schedule tab's margin of half an hour
# (2 blocks) before and after each day's demand, so the expected rows include it.

def test_demand_on_the_half_hour_gives_one_row_per_half_hour():
    """Demand from 14:00 to 15:00 gives the rows 13:30 to 15:00 (with the margin)."""
    # Arrange
    # Idea: Tickets needs 1 in blocks 32-35 -> rows_to_show 30-37 -> rows 30, 32, 34, 36.

    # Act

    # Assert
    pytest.skip("not written yet")


@pytest.mark.parametrize("first_block, block_after_last, expected_rows", [
    (33, 36, [30, 32, 34, 36]),         # 14:15-15:00: 14:15 falls in the row of 14:00
    (32, 37, [30, 32, 34, 36, 38]),     # 14:00-15:15: 15:15 falls in the row of 15:00
])
def test_quarter_hours_fall_in_the_row_of_their_half_hour(
        first_block: int, block_after_last: int, expected_rows: list[int]):
    """A block on :15 or :45 belongs to the row of the half hour it falls in."""
    # Arrange
    # Idea: Tickets needs 1 in range(first_block, block_after_last); the margin of 2 blocks
    # is added first, then each block goes to its even row.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_each_day_with_demand_gets_its_own_rows():
    """Two days with demand each get their own rows; a day without demand gets none."""
    # Arrange
    # Idea: Tickets needs 1 on Friday 14:00-15:00 (blocks 32-35) and Sunday 14:00-15:00
    # (blocks 224-227), nothing on Saturday -> rows 30-36 and 222-228 (even), no Saturday.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_without_demand_there_are_no_rows():
    """With no demand at all, the tab has no rows."""
    # Arrange
    # Idea: demand={} -> [].

    # Act

    # Assert
    pytest.skip("not written yet")


# free_cell_is_white. The row is named by its even block (32 = Friday 14:00-14:30, with
# blocks 32 and 33). In these tests Tickets needs 1 in blocks 32-35 unless said otherwise.

def test_cell_is_white_when_available_during_convention_hours():
    """Available in both blocks of a row with demand: white."""
    # Arrange
    # Idea: Mock Mane available in blocks 32-35, row 32 -> True.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_cell_is_grey_when_not_available():
    """Not available in either block of the row: grey, even during convention hours."""
    # Arrange
    # Idea: Mock Mane available only in blocks 34-35, row 32 -> False.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_cell_is_white_when_available_for_part_of_the_half_hour():
    """Available in only the second block of the row (arriving on :15): white."""
    # Arrange
    # Idea: Mock Mane available from block 33 (14:15), row 32 -> True.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_cell_is_grey_outside_convention_hours():
    """Available, but no post has demand in either block of the row: grey."""
    # Arrange
    # Idea: Mock Mane available all weekend, row 30 (13:30, a margin row without demand)
    # -> False.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_demand_at_any_post_counts_as_convention_hours():
    """Demand at a post the volunteer is not qualified for still makes the cell white."""
    # Arrange
    # Idea: Mock Mane qualified only for Tickets, available all weekend; only Infobooth
    # has demand in row 32 (blocks 32-33) -> True.

    # Act

    # Assert
    pytest.skip("not written yet")

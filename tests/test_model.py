import pytest

from scheduler.model import Schedule


def test_consecutive_blocks_form_one_work_stretch():
    """Blocks 0-3 at one post form a single work stretch (0, 4)."""
    # Arrange
    # (to do: Mock Mane at Tickets in blocks 0-3)

    # Act
    # (to do: work_stretches_of("Mock Mane"))

    # Assert
    pytest.skip("not written yet")


def test_a_gap_splits_work_into_two_stretches():
    """Blocks 0-3 and 6-9 with a gap in between form two work stretches."""
    # Arrange
    # (to do: Mock Mane at Tickets in blocks 0-3 and 6-9)

    # Act
    # (to do: work_stretches_of("Mock Mane"))

    # Assert
    pytest.skip("not written yet")  # expect [(0, 4), (6, 10)]


def test_switching_post_continues_the_same_stretch():
    """Moving straight from one post to another keeps it one work stretch."""
    # Arrange
    # (to do: Mock Mane at Tickets in blocks 0-3, then Infobooth in blocks 4-7)

    # Act
    # (to do: work_stretches_of("Mock Mane"))

    # Assert
    pytest.skip("not written yet")  # expect [(0, 8)]


def test_volunteer_without_assignments_has_no_stretches():
    """A volunteer who is not scheduled at all has no work stretches."""
    # Arrange
    # (to do: a schedule without any assignments for Mock Mane)

    # Act
    # (to do: work_stretches_of("Mock Mane"))

    # Assert
    pytest.skip("not written yet")  # expect []

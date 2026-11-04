import pytest

from scheduler.model import Schedule
from scheduler.output import assign_slots


def _works(name: str, post: str, first_block: int, block_after_last: int) -> set[tuple]:
    """The assignments for one volunteer at one post, from first_block up to block_after_last.

    Uses the same convention as range(): block_after_last itself is not included.
    Example: _works("Mock Mane", "Tickets", 0, 4) is Mock Mane at Tickets in blocks 0-3.
    """
    assignments = set()
    for block in range(first_block, block_after_last):
        assignments.add((name, post, block))
    return assignments


def test_one_volunteer_gets_slot_1():
    """A single volunteer at a post sits in slot 1 for every block they work."""
    # Arrange
    schedule = Schedule(assignments=_works("Mock Mane", "Tickets", 0, 4))

    expected_result = {}
    for b in range (0,4):
        expected_result[("Tickets", 1, b)] = "Mock Mane"

    # Act
    result = assign_slots(schedule)


    # Assert
    assert result == {}


def test_newcomers_in_the_same_block_get_slots_in_name_order():
    """Two volunteers who start together get slots 1 and 2 in name order."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_volunteer_keeps_their_slot_for_the_whole_shift():
    """Someone who keeps working at a post stays in the same slot, whoever comes and goes."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_volunteer_in_slot_2_stays_there_when_slot_1_becomes_free():
    """Staying in your column beats moving up: slot 2 stays slot 2, slot 1 stays empty."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_newcomer_gets_the_lowest_free_slot():
    """A volunteer who starts while others are working gets the lowest free slot."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_each_post_has_its_own_slots():
    """Slots are counted per post: two volunteers at two posts are both in slot 1."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_switching_post_makes_the_volunteer_a_newcomer_at_the_new_post():
    """After switching post, a volunteer gets a slot at the new post like any newcomer."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_after_a_break_a_volunteer_is_a_newcomer_again():
    """Coming back after a break counts as new, so the slot can differ from before."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_empty_schedule_gives_no_slots():
    """A schedule without assignments gives an empty result."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")

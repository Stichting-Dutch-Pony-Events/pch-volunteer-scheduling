import pytest

from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks
from scheduler.solving.solver import solve


def test_soft_rule_that_is_off_adds_no_penalty():
    """With the skill score rule off, the solver does not prefer the higher score."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")

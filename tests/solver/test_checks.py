import pytest

from scheduler.checks import check_problem
from scheduler.errors import NoScheduleFound, NotEnoughQualified, NotEnoughVolunteers
from scheduler.model import Volunteer, Post, Problem, Settings, all_blocks
from scheduler.solver import solve


RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))


def test_post_needing_more_people_than_qualified_raises_not_enough_qualified():
    """A post that needs more people than are qualified raises NotEnoughQualified."""
    # Arrange
    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Infobooth": 1},
                                            available_blocks=all_blocks(RULES))],
                      posts=["Tickets"],
                      demand={("Tickets", 0): 1},
                      settings=RULES)

    # Act
    # Act and Assert are done in the same line.

    # Assert
    with pytest.raises(NotEnoughQualified):
        solve(problem)


def test_not_enough_qualified_message_names_the_post_day_and_time():
    """The message says which post, on which day and at what time."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_not_enough_qualified_message_lists_who_is_qualified_and_available():
    """The message names the volunteers who are qualified and available then."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_qualified_but_unavailable_volunteers_do_not_count_and_are_listed_separately():
    """Qualified volunteers who are not there then don't count, and are named separately."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_consecutive_blocks_with_the_same_shortage_become_one_time_range():
    """Several quarter-hours in a row with the same shortage make one line with a range."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_every_shortage_is_listed_not_just_the_first():
    """Shortages at two posts both appear in the message."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_posts_together_needing_more_people_than_available_raise_not_enough_volunteers():
    """Two posts that each have enough qualified people, but not both at once, raise."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


@pytest.mark.parametrize("error", [NotEnoughQualified, NotEnoughVolunteers])
def test_both_check_errors_are_a_kind_of_no_schedule_found(error):
    """Code that catches NoScheduleFound also catches the errors from the checks."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_a_conflict_between_rules_still_raises_plain_no_schedule_found():
    """When no check finds a cause, solve() raises NoScheduleFound itself, not a child."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")

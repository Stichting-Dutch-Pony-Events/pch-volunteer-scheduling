from dataclasses import replace

import pytest
from ortools.sat.python import cp_model

from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks
from scheduler.solving.soft_rules import add_fewer_stretches_penalty
from scheduler.solving.solver import solve
from scheduler.solving.variables import create_variables


# Passed explicitly instead of relying on the defaults in model.py. Only the fewer
# stretches soft rule is switched on, so no other soft rule can change the outcome; the
# skill score weights are here for the tests that switch both rules on.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"),
                 soft_rules=frozenset({"fewer_stretches"}),
                 weight_work_stretch=20,
                 weight_skill_score_1=6, weight_skill_score_2=2, weight_skill_score_3=0)

ALL_DAYS = all_blocks(RULES)

# Without an objective CP-SAT takes any valid schedule, so after implementing, check with a
# few seeds that the preference tests go red without the rule.


def test_one_volunteer_works_the_whole_opening_instead_of_two_splitting_it():
    """Tickets open for 2 hours goes to one volunteer, not split into two stretches."""
    # Arrange
    # Idea: Tickets needs 1 in blocks 0-7 (06:00-08:00), Mock Mane and Testy Hooves both
    # available and equally qualified. Expected: exactly one of them works all 8 blocks.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_stretches_that_cannot_be_joined_still_give_a_schedule():
    """Two openings with a gap still give a schedule; the rule is only a preference."""
    # Arrange
    # Idea: only Mock Mane, Tickets needs 1 in blocks 0-3 and 8-11: two stretches are
    # unavoidable, and the schedule is still found.

    # Act

    # Assert
    pytest.skip("not written yet")


# Together with the skill score rule: the weights decide which preference wins.
# Idea: Tickets needs 1 in blocks 0-7. Mock Mane (score 1, 6 points per block) available
# all day, Star Fixture (score 3, 0 points) only blocks 0-3.
#   split, Star Fixture 0-3 and Mock Mane 4-7: 2 stretches, skill score 4 x 6 = 24
#   Mock Mane alone 0-7:                        1 stretch,  skill score 8 x 6 = 48
# So weight 30 (60 + 24 = 84 against 30 + 48 = 78) gives Mock Mane alone, weight 20
# (40 + 24 = 64 against 20 + 48 = 68) gives the split.

def test_fewer_stretches_win_over_the_skill_score_with_a_high_weight():
    """With weight 30 per stretch, Mock Mane works the whole opening despite the skill score."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_skill_score_wins_over_fewer_stretches_with_a_low_weight():
    """With weight 20 per stretch, Star Fixture takes the first hour and Mock Mane the rest."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


# Counting stretches. Like in test_solver_round_times.py: one volunteer's work is fixed by
# hand and only this rule is added (no hard rules), so the lowest penalty CP-SAT can reach
# is exactly what the rule counts. Idea for the cases (Tickets and Infobooth open in blocks
# 0-15): one stretch (20), two stretches with a gap (40), a stretch that switches from
# Tickets to Infobooth (20: a post switch is not a new stretch).

def test_each_work_stretch_costs_the_weight():
    """Each work stretch costs the weight once, also when it switches post halfway."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


# The penalty must be exact for every schedule, not only the best one: the same cases, but
# CP-SAT tries to make the penalty as HIGH as possible. Only helper variables bounded on
# both sides keep it at the real count.

def test_penalty_counts_only_real_stretches_even_when_maximised():
    """Even when the solver makes the penalty as high as it can, it is the real count."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


# Switching the rule on and off. The rule checks settings.soft_rules itself, so these
# tests call it directly (no solving needed); the tests above show that solve() uses it.

def test_fewer_stretches_penalty_that_is_off_returns_nothing():
    """With the fewer stretches rule switched off, add_fewer_stretches_penalty returns []."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_fewer_stretches_penalty_that_is_on_returns_terms():
    """With the rule on, a volunteer who could work gives penalty terms."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")

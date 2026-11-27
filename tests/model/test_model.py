import pytest

from scheduler.model import Schedule, Settings, Volunteer, runs_of_consecutive_blocks


def test_default_settings_match_the_agreed_rules():
    """The defaults are a 60-180 minute work stretch and a 30-minute break.

    If this fails, a default was changed: check that this was intended.
    """
    # Arrange
    # (nothing to arrange: we look at a fresh Settings with all defaults)

    # Act
    settings = Settings()

    # Assert
    assert (settings.min_stretch_minutes, settings.max_stretch_minutes,
            settings.min_break_minutes) == (60, 180, 30)


def test_default_skill_score_weights_match_the_workbook():
    """The default skill score weights are 6, 2 and 0 points per block for score 1, 2, 3."""
    # Arrange
    # (nothing to arrange: we look at a fresh Settings with all defaults)

    # Act
    settings = Settings()

    # Assert
    assert settings.weight_skill_score_3 == 0
    assert settings.weight_skill_score_2 == 2
    assert settings.weight_skill_score_1 == 6


def test_default_round_times_weight_is_10_per_start_or_end():
    """The default penalty for a start or end on :15 or :45 is 10 points."""
    # Arrange
    # (nothing to arrange: we look at a fresh Settings with all defaults)

    # Act
    settings = Settings()

    # Assert
    assert settings.weight_off_round_time == 10


def test_default_work_stretch_weight_is_20_per_stretch():
    """The default penalty for each work stretch is 20 points."""
    # Arrange
    # (nothing to arrange: we look at a fresh Settings with all defaults)

    # Act
    settings = Settings()

    # Assert
    assert settings.weight_work_stretch == 20


def test_default_preferred_maximum_stretch_is_120_minutes():
    """The default preferred maximum work stretch is 120 minutes."""
    # Arrange
    # (nothing to arrange: we look at a fresh Settings with all defaults)

    # Act
    settings = Settings()

    # Assert
    assert settings.preferred_max_stretch_minutes == 120


def test_default_weight_over_the_preferred_stretch_is_6_per_block():
    """The default penalty for each block beyond the preferred maximum stretch is 6 points."""
    # Arrange
    # (nothing to arrange: we look at a fresh Settings with all defaults)

    # Act
    settings = Settings()

    # Assert
    assert settings.weight_over_preferred_stretch == 6


def test_default_weight_over_the_fair_share_is_4_per_block():
    """The default penalty for each block above a volunteer's fair share is 4 points."""
    # Arrange
    # (nothing to arrange: we look at a fresh Settings with all defaults)

    # Act
    settings = Settings()

    # Assert
    assert settings.weight_over_fair_share == 4


def test_unknown_soft_rule_name_raises_value_error():
    """A name in Settings.soft_rules that is not a soft rule raises ValueError."""
    # Arrange
    # (nothing to arrange: the misspelled name is given straight to Settings)

    # Act
    # (Act and Assert are in the same expression)

    # Assert
    with pytest.raises(ValueError, match="skil_score.*Known:"):
        Settings(soft_rules=frozenset({"skil_score"}))


def test_volunteer_has_no_hour_limits_unless_given():
    """A Volunteer made without hour limits has none (None = no limit)."""
    # Arrange
    # (nothing to arrange: we make a Volunteer without the two limit fields)

    # Act
    volunteer = Volunteer(name="Mock Mane", skills={"Tickets": 1}, available_blocks={0})

    # Assert
    assert (volunteer.max_minutes_per_day, volunteer.max_minutes_total) == (None, None)


def test_volunteer_has_no_team_unless_given():
    """A Volunteer made without a team has team "" (none)."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_post_has_no_group_or_colour_unless_given():
    """A Post made with only a name has group "" and colour "" (no colour, white)."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")


def test_schedule_made_by_hand_is_not_proven_optimal_and_has_no_penalty():
    """A Schedule made without the solver's information: not proven optimal, no penalties."""
    # Arrange
    # (No arrange needed)

    # Act
    schedule = Schedule(assignments=set())

    # Assert
    assert schedule.proven_optimal is False
    assert schedule.penalty is None
    assert schedule.lowest_possible_penalty is None


def test_consecutive_blocks_form_one_work_stretch():
    """Blocks 0-3 at one post form a single work stretch (0, 4)."""
    # Arrange
    assignments = set()
    for block in range(4):        # blocks 0-3: 1 hour at Tickets
        assignments.add(("Mock Mane", "Tickets", block))
    schedule = Schedule(assignments=assignments)

    # Act
    stretches = schedule.work_stretches_of("Mock Mane")

    # Assert
    assert stretches == [(0, 4)]


def test_a_gap_splits_work_into_two_stretches():
    """Blocks 0-3 and 6-9 with a gap in between form two work stretches."""
    # Arrange
    assignments = set()
    for block in range(4):        # blocks 0-3: 1 hour at Tickets
        assignments.add(("Mock Mane", "Tickets", block))
    for block in range(6, 10):    # blocks 6-9: after a 30 min gap, 1 hour at Tickets
        assignments.add(("Mock Mane", "Tickets", block))

    schedule = Schedule(assignments=assignments)

    # Act
    stretches = schedule.work_stretches_of("Mock Mane")

    # Assert
    assert stretches == [(0, 4), (6, 10)]


def test_switching_post_continues_the_same_stretch():
    """Moving straight from one post to another keeps it one work stretch."""
    # Arrange
    assignments = set()
    for block in range(4):        # blocks 0-3: 1 hour at Tickets
        assignments.add(("Mock Mane", "Tickets", block))
    for block in range(4, 7):     # blocks 4-6: straight on, 45 min at Infobooth
        assignments.add(("Mock Mane", "Infobooth", block))

    schedule = Schedule(assignments=assignments)

    # Act
    stretches = schedule.work_stretches_of("Mock Mane")

    # Assert
    assert stretches == [(0, 7)]


def test_volunteer_without_assignments_has_no_stretches():
    """A volunteer who is not scheduled at all has no work stretches."""
    # Arrange
    schedule = Schedule(assignments=set())

    # Act
    stretches = schedule.work_stretches_of("Mock Mane")

    # Assert
    assert stretches == []


def test_consecutive_blocks_at_one_post_form_one_shift():
    """Blocks 0-3 at Tickets form a single shift ("Tickets", 0, 4)."""
    # Arrange
    assignments = set()
    for block in range(0, 4):
        assignments.add(("Mock Mane", "Tickets", block))

    schedule = Schedule(assignments=assignments)

    # Act
    shifts = schedule.shifts_of("Mock Mane")

    # Assert
    assert shifts == [("Tickets", 0, 4)]


def test_a_gap_splits_work_at_one_post_into_two_shifts():
    """Blocks 0-3 and 6-9 at Tickets, with a gap in between, form two shifts."""
    # Arrange
    assignments = set()
    # The * unpacks each range into one list: [0, 1, 2, 3, 6, 7, 8, 9]
    for block in [*range(0, 4), *range(6, 10)]:
        assignments.add(("Mock Mane", "Tickets", block))

    schedule = Schedule(assignments=assignments)

    # Act
    shifts = schedule.shifts_of("Mock Mane")

    # Assert
    assert shifts == [("Tickets", 0, 4), ("Tickets", 6, 10)]


def test_switching_post_starts_a_new_shift():
    """Tickets 0-3 and straight on Infobooth 4-7 form two shifts, without a gap."""
    # Arrange
    assignments = set()
    for block in range(0, 4):
        assignments.add(("Mock Mane", "Tickets", block))
    for block in range(4, 8):
        assignments.add(("Mock Mane", "Infobooth", block))

    schedule = Schedule(assignments=assignments)

    # Act
    shifts = schedule.shifts_of("Mock Mane")

    # Assert
    assert shifts == [("Tickets", 0, 4), ("Infobooth", 4, 8)]


def test_shifts_at_different_posts_are_in_time_order():
    """Tickets 0-3, Infobooth 4-7, Tickets 8-11 come out in that order, not grouped per post."""
    # Arrange
    assignments = set()
    # The * unpacks each range into one list: [0, 1, 2, 3, 8, 9, 10, 11]
    for block in [*range(0, 4), *range(8, 12)]:
        assignments.add(("Mock Mane", "Tickets", block))
    for block in range(4, 8):
        assignments.add(("Mock Mane", "Infobooth", block))

    schedule = Schedule(assignments=assignments)

    # Act
    shifts = schedule.shifts_of("Mock Mane")

    # Assert
    assert shifts == [("Tickets", 0, 4), ("Infobooth", 4, 8), ("Tickets", 8, 12)]


def test_shifts_of_other_volunteers_are_left_out():
    """Only the asked volunteer's shifts come out, not those of someone else."""
    # Arrange
    assignments = set()
    for block in range(0, 4):
        assignments.add(("Mock Mane", "Tickets", block))
    for block in range(4, 8):
        assignments.add(("Testy Hooves", "Infobooth", block))

    schedule = Schedule(assignments=assignments)

    # Act
    shifts = schedule.shifts_of("Mock Mane")

    # Assert
    assert shifts == [("Tickets", 0, 4)]


def test_volunteer_without_assignments_has_no_shifts():
    """A volunteer who is not scheduled at all has no shifts."""
    # Arrange
    assignments = set()
    for block in range(0, 4):
        assignments.add(("Mock Mane", "Tickets", block))
    for block in range(4, 8):
        assignments.add(("Mock Mane", "Infobooth", block))

    schedule = Schedule(assignments=assignments)

    # Act
    shifts = schedule.shifts_of("Testy Hooves")

    # Assert
    assert shifts == []


def test_a_shift_continues_across_the_day_boundary():
    """Saturday night 05:30 to Sunday 06:30 (blocks 190-193) at one post is one shift."""
    # Arrange
    assignments = set()
    for block in range(190, 194):
        assignments.add(("Mock Mane", "Tickets", block))

    schedule = Schedule(assignments=assignments)

    # Act
    shifts = schedule.shifts_of("Mock Mane")

    # Assert
    assert shifts == [("Tickets", 190, 194)]


def test_unsorted_blocks_are_split_into_runs_in_time_order():
    """Blocks given in any order still come out as runs sorted by time."""
    # Arrange
    blocks = [6, 0, 5, 1]         # blocks 0-1 and 5-6, shuffled

    # Act
    runs = runs_of_consecutive_blocks(blocks)

    # Assert
    assert runs == [(0, 2), (5, 7)]


def test_duplicate_blocks_count_once():
    """A block given twice does not split a run or make it longer."""
    # Arrange
    blocks = [0, 1, 1, 2]         # block 1 appears twice

    # Act
    runs = runs_of_consecutive_blocks(blocks)

    # Assert
    assert runs == [(0, 3)]


def test_single_block_is_a_run_of_one():
    """A single block forms a run that ends one block later."""
    # Arrange
    blocks = [3]

    # Act
    runs = runs_of_consecutive_blocks(blocks)

    # Assert
    assert runs == [(3, 4)]

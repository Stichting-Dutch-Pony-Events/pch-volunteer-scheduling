from scheduler.model import Schedule, Settings, runs_of_consecutive_blocks


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

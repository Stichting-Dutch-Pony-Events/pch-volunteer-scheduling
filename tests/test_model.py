from scheduler.model import Schedule


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

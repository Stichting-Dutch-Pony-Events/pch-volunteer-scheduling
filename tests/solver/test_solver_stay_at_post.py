import pytest

from scheduler.model import Volunteer, Post, Problem, Settings, all_blocks
from scheduler.solver import solve, NoScheduleFound


# The scenarios below fit these limits (in blocks: 4, 12 and 2), so they pass them (and
# the days, which all_blocks needs) explicitly instead of relying on the defaults.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))


def test_volunteer_may_not_leave_an_open_post_for_another_post():
    """Moving to another post while the old post still needs the same people is not allowed."""
    # Arrange
    # Tickets needs 1 in blocks 0-7, Infobooth 1 in blocks 4-7. Testy Hooves can only do
    # Tickets and is only there in blocks 4-7, so Mock Mane would have to do Tickets 0-3
    # and then move to Infobooth while Tickets stays open: forbidden.
    demand = {}
    for block in range(0, 8):
        demand[("Tickets", block)] = 1
    for block in range(4, 8):
        demand[("Infobooth", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=set(range(4, 8)))],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_volunteer_may_switch_post_when_the_old_post_closes():
    """When a post closes, the volunteer there may go on to another post in the same stretch."""
    # Arrange
    # Tickets in blocks 0-3, then Infobooth in blocks 4-7: one stretch of 2 hours.
    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 1
    for block in range(4, 8):
        demand[("Infobooth", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand,
        settings=RULES)

    expected_result = set()
    for block in range(0, 4):
        expected_result.add(("Mock Mane", "Tickets", block))
    for block in range(4, 8):
        expected_result.add(("Mock Mane", "Infobooth", block))

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected_result


def test_volunteer_may_switch_post_when_the_old_post_needs_fewer_people():
    """When a post needs one person fewer, one volunteer there may go on to another post."""
    # Arrange
    # Tickets needs 2 in blocks 0-3 and 1 in blocks 4-7; Infobooth needs 1 in blocks 4-7
    # and only Mock Mane can do it. So Mock Mane moves from Tickets to Infobooth at block 4,
    # just when Tickets needs one person fewer, and Testy Hooves stays at Tickets.
    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 2
    for block in range(4, 8):
        demand[("Tickets", block)] = 1
        demand[("Infobooth", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand,
        settings=RULES)

    expected_result = set()
    for block in range(0, 4):
        expected_result.add(("Mock Mane", "Tickets", block))
    for block in range(4, 8):
        expected_result.add(("Mock Mane", "Infobooth", block))
    for block in range(0, 8):
        expected_result.add(("Testy Hooves", "Tickets", block))

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected_result


def test_only_as_many_people_as_the_post_needs_fewer_may_switch():
    """When a post needs one person fewer, two volunteers may not both go on to another post."""
    # Arrange
    # Tickets needs 2 in blocks 0-3 and 1 in blocks 4-7; Infobooth needs 2 in blocks 4-7.
    # Only Mock Mane and Testy Hooves can do Infobooth; Dummy Dash can only do Tickets and
    # is only there in blocks 4-7. So both would have to move from Tickets to Infobooth at
    # block 4, while Tickets only needs one person fewer: forbidden.
    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 2
    for block in range(4, 8):
        demand[("Tickets", block)] = 1
        demand[("Infobooth", block)] = 2

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Dummy Dash", skills={"Tickets": 1},
                              available_blocks=set(range(4, 8)))],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_volunteer_may_switch_post_after_a_break():
    """After a break a new stretch starts, so the volunteer may start at another post."""
    # Arrange
    # Tickets needs 1 in blocks 0-9, Infobooth 1 in blocks 6-9 (only Mock Mane can do it).
    # Testy Hooves can only do Tickets and is only there from block 4. Mock Mane may not
    # move from Tickets to Infobooth while Tickets stays open, so the only way: Mock Mane
    # Tickets 0-3, a break in blocks 4-5, Infobooth 6-9; Testy Hooves takes over Tickets.
    demand = {}
    for block in range(0, 10):
        demand[("Tickets", block)] = 1
    for block in range(6, 10):
        demand[("Infobooth", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=set(range(4, 10)))],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand,
        settings=RULES)

    expected_result = set()
    for block in range(0, 4):
        expected_result.add(("Mock Mane", "Tickets", block))
    for block in range(6, 10):
        expected_result.add(("Mock Mane", "Infobooth", block))
    for block in range(4, 10):
        expected_result.add(("Testy Hooves", "Tickets", block))

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected_result


def test_a_volunteer_stopping_when_the_post_needs_fewer_people_uses_up_the_switch():
    """Someone stopping work as a post needs one fewer takes that spot; nobody may move on."""
    # Arrange
    # Tickets needs 2 in blocks 0-3 and 1 in blocks 4-7; Infobooth needs 1 in blocks 4-7
    # and only Mock Mane can do it. Testy Hooves (Tickets only) is there in blocks 0-3,
    # Dummy Dash (Tickets only) in blocks 4-7. At block 4 Testy Hooves stops, which already
    # uses up the one person fewer, so Mock Mane may not move to Infobooth: forbidden.
    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 2
    for block in range(4, 8):
        demand[("Tickets", block)] = 1
        demand[("Infobooth", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=set(range(0, 4))),
                    Volunteer(name="Dummy Dash", skills={"Tickets": 1},
                              available_blocks=set(range(4, 8)))],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_test_workbook_schedule_follows_the_stay_at_post_rule():
    """In the solved test workbook, every move to another post fits the drop in demand."""
    # Arrange

    # Act

    # Assert
    pytest.skip("not written yet")

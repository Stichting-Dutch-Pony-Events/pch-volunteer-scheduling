import pytest

from scheduler.model import Volunteer, Post, Problem, Settings, all_blocks
from scheduler.errors import NoScheduleFound
from scheduler.solving.solver import solve


# The scenarios below fit these limits (in blocks: 4, 12 and 2), so they pass them (and
# the days, which all_blocks needs) explicitly instead of relying on the defaults.
# Most moves happen at block 2, after 30 minutes: a volunteer may only move on before
# they have worked the minimum stretch (see the test with the move after 60 minutes).
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))


def test_volunteer_may_not_leave_an_open_post_for_another_post():
    """Moving to another post while the old post still needs the same people is not allowed."""
    # Arrange
    # Tickets needs 1 in blocks 0-5, Infobooth 1 in blocks 2-5. Testy Hooves can only do
    # Tickets and is only there in blocks 2-5, so Mock Mane would have to do Tickets 0-1
    # and then move to Infobooth while Tickets stays open: forbidden.
    demand = {}
    for block in range(0, 6):
        demand[("Tickets", block)] = 1
    for block in range(2, 6):
        demand[("Infobooth", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=set(range(2, 6)))],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_volunteer_may_switch_post_when_the_old_post_closes():
    """When a post closes before the minimum stretch is done, the volunteer may move on."""
    # Arrange
    # Tickets in blocks 0-1, then Infobooth in blocks 2-5: one stretch of 90 minutes, with
    # the move after 30 minutes.
    demand = {}
    for block in range(0, 2):
        demand[("Tickets", block)] = 1
    for block in range(2, 6):
        demand[("Infobooth", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES))],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand,
        settings=RULES)

    expected_result = set()
    for block in range(0, 2):
        expected_result.add(("Mock Mane", "Tickets", block))
    for block in range(2, 6):
        expected_result.add(("Mock Mane", "Infobooth", block))

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected_result


def test_volunteer_may_switch_post_when_the_old_post_needs_fewer_people():
    """When a post needs one person fewer, one volunteer there may go on to another post."""
    # Arrange
    # Tickets needs 2 in blocks 0-1 and 1 in blocks 2-5; Infobooth needs 1 in blocks 2-5
    # and only Mock Mane can do it. So Mock Mane moves from Tickets to Infobooth at block 2,
    # just when Tickets needs one person fewer, and Testy Hooves stays at Tickets.
    demand = {}
    for block in range(0, 2):
        demand[("Tickets", block)] = 2
    for block in range(2, 6):
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
    for block in range(0, 2):
        expected_result.add(("Mock Mane", "Tickets", block))
    for block in range(2, 6):
        expected_result.add(("Mock Mane", "Infobooth", block))
    for block in range(0, 6):
        expected_result.add(("Testy Hooves", "Tickets", block))

    # Act
    schedule = solve(problem)

    # Assert
    assert schedule.assignments == expected_result


def test_only_as_many_people_as_the_post_needs_fewer_may_switch():
    """When a post needs one person fewer, two volunteers may not both go on to another post."""
    # Arrange
    # Tickets needs 2 in blocks 0-1 and 1 in blocks 2-5; Infobooth needs 2 in blocks 2-5.
    # Only Mock Mane and Testy Hooves can do Infobooth; Dummy Dash can only do Tickets and
    # is only there in blocks 2-5. So both would have to move from Tickets to Infobooth at
    # block 2, while Tickets only needs one person fewer: forbidden.
    demand = {}
    for block in range(0, 2):
        demand[("Tickets", block)] = 2
    for block in range(2, 6):
        demand[("Tickets", block)] = 1
        demand[("Infobooth", block)] = 2

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Dummy Dash", skills={"Tickets": 1},
                              available_blocks=set(range(2, 6)))],
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
    # Tickets needs 2 in blocks 0-1 and 1 in blocks 2-5; Infobooth needs 1 in blocks 2-5
    # and only Mock Mane can do it. Testy Hooves (Tickets only) is there in blocks 0-1
    # (a short piece of demand, so 30 minutes is allowed), Dummy Dash (Tickets only) in
    # blocks 2-5. At block 2 Testy Hooves stops, which already uses up the one person
    # fewer, so Mock Mane may not move to Infobooth: forbidden.
    demand = {}
    for block in range(0, 2):
        demand[("Tickets", block)] = 2
    for block in range(2, 6):
        demand[("Tickets", block)] = 1
        demand[("Infobooth", block)] = 1

    problem = Problem(
        volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1, "Infobooth": 1},
                              available_blocks=all_blocks(RULES)),
                    Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                              available_blocks=set(range(0, 2))),
                    Volunteer(name="Dummy Dash", skills={"Tickets": 1},
                              available_blocks=set(range(2, 6)))],
        posts=[Post(name="Tickets"), Post(name="Infobooth")],
        demand=demand,
        settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)


def test_volunteer_who_already_worked_the_minimum_may_not_move_on():
    """Someone who has worked the minimum stretch stops when their post ends, no move on."""
    # Arrange
    # Tickets in blocks 0-3 (exactly the 60 minute minimum), then Tickets closes and
    # Infobooth needs 1 in blocks 4-7. Only Mock Mane can do either, so Mock Mane would
    # have to move on after 60 minutes: forbidden (stopping would not be too short).
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

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the solve runs.)

    # Assert
    with pytest.raises(NoScheduleFound):
        solve(problem)

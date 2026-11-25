import pytest

from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks
from scheduler.writing.individual_schedules_sheet import (ShiftBox, free_cell_is_white,
                                                          half_hour_rows, shift_boxes)


# Passed explicitly instead of relying on the defaults in model.py. Friday = blocks 0-95,
# Saturday = 96-191, Sunday = 192-287 (block 0 = Friday 06:00, block 32 = Friday 14:00).
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))

ALL_DAYS = all_blocks(RULES)


# half_hour_rows, first without a margin: only the half hours with demand.

def test_demand_on_the_half_hour_gives_one_row_per_half_hour():
    """Demand from 14:00 to 15:00 gives the rows 14:00 and 14:30."""
    # Arrange
    # Tickets needs 1 in blocks 32-35 (14:00-15:00).
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    expected = [32, 34]  # 14:00, 14:30

    # Act
    rows = half_hour_rows(problem, margin_rows=0)

    # Assert
    assert rows == expected


@pytest.mark.parametrize("first_block, block_after_last, expected_rows", [
    (33, 36, [32, 34]),         # 14:15-15:00: 14:15 falls in the row of 14:00
    (32, 37, [32, 34, 36]),     # 14:00-15:15: 15:00 gets a row of its own for 15:00-15:15
])
def test_quarter_hours_fall_in_the_row_of_their_half_hour(
        first_block: int, block_after_last: int, expected_rows: list[int]):
    """A block on :15 or :45 belongs to the row of the half hour it falls in."""
    # Arrange
    # Tickets needs 1 in range(first_block, block_after_last), margin_rows=0.
    demand = {}
    for block in range(first_block, block_after_last):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    rows = half_hour_rows(problem, margin_rows=0)

    # Assert
    assert rows == expected_rows


def test_each_day_with_demand_gets_its_own_rows():
    """Two days with demand each get their own rows; a day without demand gets none."""
    # Arrange
    # Tickets needs 1 on Friday 14:00-15:00 (blocks 32-35) and Sunday 14:00-15:00
    # (blocks 224-227), nothing on Saturday, margin_rows=0 -> [32, 34, 224, 226].
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    for block in range(224, 228):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    expected = [32, 34, 224, 226]  # Friday 14:00, 14:30; Sunday 14:00, 14:30

    # Act
    rows = half_hour_rows(problem, margin_rows=0)

    # Assert
    assert rows == expected


@pytest.mark.parametrize("margin_rows", [0, 1], ids=["no_margin", "with_margin"])
def test_without_demand_there_are_no_rows(margin_rows: int):
    """With no demand at all, the tab has no rows, with or without margin"""
    # Arrange
    problem = Problem(volunteers=[],
                      posts=[],
                      demand={},
                      settings=RULES)

    # Act
    result = half_hour_rows(problem, margin_rows=margin_rows)

    # Assert
    assert result == []


# half_hour_rows with a margin: margin_rows half-hour rows before the first and after the
# last row with demand of each day (1 = half an hour, like the Schedule tab), but never
# outside that day.

def test_margin_adds_rows_before_and_after_the_demand():
    """A margin of one row adds the half hour before and the half hour after the demand."""
    # Arrange
    # Tickets needs 1 in blocks 32-35 (14:00-15:00), margin_rows=1
    # -> [30, 32, 34, 36] (13:30 and 15:00 are the margin).
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    expected = [30, 32, 34, 36]  # (13:30 and 15:00 are the margin)

    # Act
    rows = half_hour_rows(problem, margin_rows=1)

    # Assert
    assert rows == expected


def test_margin_of_two_rows_adds_an_hour_on_each_side():
    """A margin of two rows adds a whole hour before and after the demand."""
    # Arrange
    # Tickets needs 1 in blocks 32-35, margin_rows=2 -> [28, 30, 32, 34, 36, 38]
    # (catches a margin that is always one row, or counted in blocks).
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    expected = [28, 30, 32, 34, 36, 38]  # (13:00, 13:30, 15:00 and 15:30 are the margin)

    # Act
    rows = half_hour_rows(problem, margin_rows=2)

    # Assert
    assert rows == expected


def test_margin_counts_whole_rows_from_a_quarter_hour():
    """Demand starting on :15 still gets exactly one whole margin row before its row."""
    # Arrange
    # Tickets needs 1 in blocks 33-36 (14:15-15:15), margin_rows=1
    # -> [30, 32, 34, 36, 38]: the margin is counted from the rows 14:00 and 15:00, not
    # from the blocks.
    demand = {}
    for block in range(33, 37):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    expected = [30, 32, 34, 36, 38]  # (13:30 and 15:30 are the margin)

    # Act
    rows = half_hour_rows(problem, margin_rows=1)

    # Assert
    assert rows == expected


@pytest.mark.parametrize("first_block, block_after_last, expected_rows", [
    (0, 4, [0, 2, 4]),          # Friday 06:00-07:00: no row before 06:00 (block 0)
    (92, 96, [90, 92, 94]),     # Friday 05:00-06:00 at night: no row after the day's end
])
def test_margin_stays_within_its_own_day(
        first_block: int, block_after_last: int, expected_rows: list[int]):
    """A margin row that would fall outside the demand's own convention day is left out."""
    # Arrange
    # Tickets needs 1 in range(first_block, block_after_last), margin_rows=1. (With
    # demand on Saturday too, a row after Friday's end would be Saturday's first row.)
    demand = {}
    for block in range(first_block, block_after_last):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    rows = half_hour_rows(problem, margin_rows=1)

    # Assert
    assert rows == expected_rows


# free_cell_is_white. The row is named by its even block (32 = Friday 14:00-14:30, with
# blocks 32 and 33). In these tests Tickets needs 1 in blocks 32-35 unless said otherwise.

def test_cell_is_white_when_available_during_convention_hours():
    """Available in both blocks of a row with demand: white."""
    # Arrange
    # Mock Mane available in blocks 32-35, row 32 -> True.
    mock_mane = Volunteer(name="Mock Mane", skills={"Tickets": 1},
                          available_blocks=set(range(32, 36)))

    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[mock_mane],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    cell_is_white = free_cell_is_white(mock_mane, 32, problem)

    # Assert
    assert cell_is_white is True


def test_cell_is_grey_when_not_available():
    """Not available in either block of the row: grey, even during convention hours."""
    # Arrange
    # Mock Mane available only in blocks 34-35, row 32 -> False.
    mock_mane = Volunteer(name="Mock Mane", skills={"Tickets": 1},
                          available_blocks=set(range(34, 36)))

    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[mock_mane],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    cell_is_white = free_cell_is_white(mock_mane, 32, problem)

    # Assert
    assert cell_is_white is False


@pytest.mark.parametrize("available_blocks", [
    {30, 31, 32},   # leaving at 14:15: available only in the row's first block
    {33, 34, 35},   # arriving at 14:15: available only in the row's second block
], ids=["leaving_on_a_quarter_past", "arriving_on_a_quarter_past"])
def test_cell_is_white_when_available_for_part_of_the_half_hour(available_blocks: set[int]):
    """Available in only one of the row's two blocks: white."""
    # Arrange
    # Mock Mane available in only one block of row 32 (14:00-14:30), Tickets needs 1 in
    # blocks 32-35 -> True. The mismatch is on purpose: the demand covers both blocks of
    # the row, the availability only one of them (arriving or leaving at 14:15), and
    # being there for part of the half hour is enough for a white cell.
    mock_mane = Volunteer(name="Mock Mane", skills={"Tickets": 1},
                          available_blocks=available_blocks)

    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[mock_mane],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    cell_is_white = free_cell_is_white(mock_mane, 32, problem)

    # Assert
    assert cell_is_white is True


def test_cell_is_grey_outside_convention_hours():
    """Available, but no post has demand in either block of the row: grey."""
    # Arrange
    # Mock Mane available all weekend, row 30 (13:30, a margin row without demand)
    mock_mane = Volunteer(name="Mock Mane", skills={"Tickets": 1},
                          available_blocks=ALL_DAYS)

    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[mock_mane],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    cell_is_white = free_cell_is_white(mock_mane, 30, problem)

    # Assert
    assert cell_is_white is False


@pytest.mark.parametrize("demand_blocks", [
    [30, 31, 32],  # closing on 14:15: demand only in the row's first block
    [33, 34, 35],  # opening on 14:15: demand only in the row's second block
], ids=["closing_on_a_quarter_past", "opening_on_a_quarter_past"])
def test_demand_in_one_block_of_the_row_makes_it_convention_hours(demand_blocks: list[int]):
    """Demand in only one of the row's two blocks still makes the cell white."""
    # Arrange
    mock_mane = Volunteer(name="Mock Mane", skills={"Tickets": 1},
                          available_blocks=ALL_DAYS)

    demand = {}
    for block in demand_blocks:
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[mock_mane],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    cell_is_white = free_cell_is_white(mock_mane, 32, problem)

    # Assert
    assert cell_is_white is True


def test_demand_at_any_post_counts_as_convention_hours():
    """Demand at a post the volunteer is not qualified for still makes the cell white."""
    # Arrange
    # Mock Mane qualified only for Tickets, available all weekend; only Infobooth
    # has demand in row 32 (blocks 32-33) -> True.
    mock_mane = Volunteer(name="Mock Mane", skills={"Tickets": 1},
                          available_blocks=ALL_DAYS)

    demand = {}
    for block in range(32, 36):
        demand[("Infobooth", block)] = 1

    problem = Problem(volunteers=[mock_mane],
                      posts=[Post("Infobooth")],
                      demand=demand,
                      settings=RULES)

    # Act
    cell_is_white = free_cell_is_white(mock_mane, 32, problem)

    # Assert
    assert cell_is_white is True


def test_row_that_is_not_on_the_half_hour_raises_value_error():
    """A row is named by its even block; an odd block (on :15 or :45) is an error."""
    # Arrange
    # Mock Mane available all weekend, Tickets needs 1 in blocks 32-35; row 33
    # (14:15) -> ValueError mentioning 33 (pytest.raises(ValueError, match="33")).
    mock_mane = Volunteer(name="Mock Mane", skills={"Tickets": 1},
                          available_blocks=ALL_DAYS)

    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[mock_mane],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(ValueError, match="33"):
        free_cell_is_white(mock_mane, 33, problem)


# shift_boxes. Each test gives one volunteer's shifts as (post, first_block,
# block_after_last), as Schedule.shifts_of gives them, and compares whole ShiftBoxes, so
# the kept times are checked too. Rows are named by their even block (32 = 14:00).

def test_shift_on_the_half_hour_fills_its_rows_without_bold():
    """A shift from 14:00 to 15:00 covers the rows 14:00 and 14:30, nothing bold."""
    # Arrange
    # Idea: [("Tickets", 32, 36)] -> [ShiftBox("Tickets", 32, 36, first_row=32, last_row=34,
    # start_bold=False, end_bold=False)].

    # Act

    # Assert
    pytest.skip("not written yet")


def test_start_on_a_quarter_past_is_bold():
    """A shift starting at 14:15 starts in the row of 14:00, with its start time bold."""
    # Arrange
    # Idea: [("Tickets", 33, 36)] -> rows 32-34, start_bold=True, end_bold=False.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_end_on_a_quarter_past_is_bold():
    """A shift ending at 15:15 ends in the row of 15:00, with its end time bold."""
    # Arrange
    # Idea: [("Tickets", 32, 37)] -> rows 32-36, start_bold=False, end_bold=True.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_half_hour_shift_is_one_row():
    """A shift of exactly one half hour is a box of one row, nothing bold."""
    # Arrange
    # Idea: [("Tickets", 32, 34)] -> first_row=32, last_row=32, both not bold.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_volunteer_without_shifts_has_no_boxes():
    """No shifts give no boxes."""
    # Arrange
    # Idea: [] -> [].

    # Act

    # Assert
    pytest.skip("not written yet")


def test_shifts_with_a_break_between_do_not_touch():
    """Two shifts with a break between get the same boxes as each on its own."""
    # Arrange
    # Idea: [("Tickets", 32, 36), ("Infobooth", 40, 44)] -> rows 32-34 and 40-42,
    # nothing bold.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_switch_on_the_half_hour_needs_no_push():
    """A switch at 15:00 puts the two boxes right under each other, without sharing a row."""
    # Arrange
    # Idea: [("Tickets", 32, 36), ("Infobooth", 36, 40)] -> rows 32-34 and 36-38,
    # nothing bold.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_switch_on_a_quarter_hour_pushes_the_second_box_down():
    """A switch at 14:45 starts the second box one row lower, with its start time bold."""
    # Arrange
    # Idea: [("Tickets", 32, 35), ("Infobooth", 35, 40)] -> Tickets rows 32-34, end bold
    # (14:45); Infobooth rows 36-38 (not 34), start bold, end not bold.

    # Act

    # Assert
    pytest.skip("not written yet")


def test_pushed_box_that_would_end_before_it_starts_becomes_one_row():
    """A pushed box with nothing left of its own rows becomes one row, both times bold."""
    # Arrange
    # Idea: [("Tickets", 32, 35), ("Infobooth", 35, 36)] -> Infobooth 14:45-15:00 would
    # be row 34, pushed to 36: first_row=36, last_row=36, start_bold=True, end_bold=True
    # (the box runs to 15:30, the shift ends at 15:00).

    # Act

    # Assert
    pytest.skip("not written yet")


def test_one_row_box_can_push_the_next_box_down():
    """A one-row box made by a push can push the box after it down in turn."""
    # Arrange
    # Idea: as the test above, plus ("Gopher", 36, 40) (15:00-16:00) -> Gopher rows 38-38
    # (not 36-38), start_bold=True, end_bold=False.

    # Act

    # Assert
    pytest.skip("not written yet")

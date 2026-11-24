import pytest

from scheduler.model import Post, Problem, Settings
from scheduler.writing.schedule_sheet import column_header, rows_to_show, slot_columns


RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))


def _problem(post_names: list[str], demand: dict[tuple[str, int], int]) -> Problem:
    """A problem with these posts and this demand; volunteers don't matter for the output."""
    posts = []
    for name in post_names:
        posts.append(Post(name))
    return Problem(volunteers=[], posts=posts, demand=demand, settings=RULES)


# --- slot_columns ---

def test_post_that_needs_one_person_gets_one_column():
    """A post that never needs more than one person gets a single column."""
    # Arrange
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)

    # Act
    result = slot_columns(problem)

    # Assert
    assert result == [("Tickets", 1)]


def test_post_gets_as_many_columns_as_its_highest_demand():
    """The number of columns of a post is the most people it needs at any block."""
    # Arrange
    demand = {("Tickets", 32): 1, ("Tickets", 33): 3, ("Tickets", 34): 2}
    problem = _problem(["Tickets"], demand)

    expected_result = []
    for slot in range(1, 4):
        expected_result.append(("Tickets", slot))

    # Act
    result = slot_columns(problem)

    # Assert
    assert result == expected_result


def test_columns_follow_the_order_of_the_posts():
    """Posts appear in the order of problem.posts, not in the order of the demand."""
    # Arrange
    # Tickets comes first in the demand, but Infobooth comes first in the posts.
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 2
        demand[("Infobooth", block)] = 1
    problem = _problem(["Infobooth", "Tickets"], demand)

    expected_result = [("Infobooth", 1)]
    for slot in range(1, 3):
        expected_result.append(("Tickets", slot))

    # Act
    result = slot_columns(problem)

    # Assert
    assert result == expected_result


def test_post_without_any_demand_gets_no_columns():
    """A post that is never open gets no column at all."""
    # Arrange
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets", "Infobooth"], demand)

    # Act
    result = slot_columns(problem)

    # Assert
    assert result == [("Tickets", 1)]


# --- column_header ---

def test_post_with_one_slot_keeps_its_plain_name():
    """A post with a single column is headed by just its name."""
    # Arrange
    # Nothing to set up: the function only takes plain values.

    # Act
    result = column_header("Infobooth", 1, 1)

    # Assert
    assert result == "Infobooth"


@pytest.mark.parametrize("slot, expected_header", [
    (1, "Tickets 1"),
    (2, "Tickets 2"),
    (3, "Tickets 3"),
])
def test_post_with_several_slots_gets_numbered_headers(slot, expected_header):
    """A post with several columns gets its name plus the slot number in each header."""
    # Arrange
    # Nothing to set up: the slot and the expected header come from parametrize.

    # Act
    result = column_header("Tickets", slot, 3)

    # Assert
    assert result == expected_header


def test_slot_count_below_1_raises_value_error():
    """A post with fewer than one column cannot get a header."""
    # Arrange
    # Nothing to set up: the function only takes plain values.

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(ValueError, match="Slotcount 0"):
        column_header("Tickets", 1, 0)


def test_slot_below_1_raises_value_error():
    """Slots are counted from 1, so slot 0 is an error."""
    # Arrange
    # Nothing to set up: the function only takes plain values.

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(ValueError, match="Slot 0"):
        column_header("Tickets", 0, 3)


def test_slot_above_the_slot_count_raises_value_error():
    """A slot number higher than the number of columns is an error naming both numbers."""
    # Arrange
    # Nothing to set up: the function only takes plain values.

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(ValueError, match="Slot 4.*3"):
        column_header("Tickets", 4, 3)


def test_empty_post_name_raises_value_error():
    """A header needs a post name."""
    # Arrange
    # Nothing to set up: the function only takes plain values.

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(ValueError, match="empty"):
        column_header("", 1, 1)


# --- rows_to_show ---

def test_rows_run_from_the_first_to_the_last_block_with_demand():
    """The rows of a day start at the first block with demand and end at the last one."""
    # Arrange
    # Friday 14:00-15:00
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)

    # Act
    result = rows_to_show(problem)

    # Assert
    assert result == list(range(32, 36))


def test_a_gap_within_a_day_gets_rows_too():
    """Blocks without demand between two open periods of the same day still get a row."""
    # Arrange
    # Friday 14:00-14:30 and 16:00-16:30
    demand = {}
    for block in range(32, 34):
        demand[("Tickets", block)] = 1
    for block in range(40, 42):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)

    # Act
    result = rows_to_show(problem)

    # Assert
    assert result == list(range(32, 42))


def test_rows_cover_the_demand_of_all_posts():
    """The rows run from the earliest to the latest demand of any post."""
    # Arrange
    # Tickets Friday 14:00-15:00, Infobooth Friday 14:30-16:00
    demand = {}
    for block in range(32, 36):
        demand[("Tickets", block)] = 1
    for block in range(34, 40):
        demand[("Infobooth", block)] = 1
    problem = _problem(["Tickets", "Infobooth"], demand)

    # Act
    result = rows_to_show(problem)

    # Assert
    assert result == list(range(32, 40))


def test_each_day_has_its_own_range():
    """The night between two days with demand gets no rows: each day has its own range."""
    # Arrange
    # Friday 14:00-14:30 and Saturday 10:00-10:30
    demand = {}
    for block in range(32, 34):
        demand[("Tickets", block)] = 1
    for block in range(112, 114):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)

    # Act
    result = rows_to_show(problem)

    # Assert
    assert result == list(range(32, 34)) + list(range(112, 114))


def test_night_blocks_belong_to_their_convention_day():
    """Demand after midnight extends the range of the convention day before it."""
    # Arrange
    # Saturday 22:00 (block 160) and Saturday night 01:00 (block 172)
    demand = {("Tickets", 160): 1, ("Tickets", 172): 1}
    problem = _problem(["Tickets"], demand)

    # Act
    result = rows_to_show(problem)

    # Assert
    assert result == list(range(160, 173))


def test_day_without_demand_gets_no_rows():
    """A convention day on which nothing is open is left out."""
    # Arrange
    # Friday 14:00-14:30 and Sunday 14:00-14:30, nothing on Saturday
    demand = {}
    for block in range(32, 34):
        demand[("Tickets", block)] = 1
    for block in range(224, 226):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)

    # Act
    result = rows_to_show(problem)

    # Assert
    assert result == list(range(32, 34)) + list(range(224, 226))


def test_no_demand_gives_no_rows():
    """Without any demand there are no rows at all."""
    # Arrange
    problem = _problem(["Tickets"], {})

    # Act
    result = rows_to_show(problem)

    # Assert
    assert result == []


# Half an hour of margin before and after the demand of each day, so the days are separated
# by rows without demand (grey on the individual schedules tab).

def test_rows_start_half_an_hour_before_the_first_demand_of_the_day():
    """Demand from Friday 08:00 gives a first row at 07:30."""
    # Arrange
    # Friday 08:00-09:00
    demand = {}
    for block in range(8, 12):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)

    # Act
    result = rows_to_show(problem)

    # Assert
    assert result[0] == 6           # Friday 07:30


def test_rows_end_half_an_hour_after_the_last_demand_of_the_day():
    """Demand until Friday 09:00 (last block 08:45) gives a last row at 09:15."""
    # Arrange
    # Friday 08:00-09:00
    demand = {}
    for block in range(8, 12):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)

    # Act
    result = rows_to_show(problem)

    # Assert
    assert result[-1] == 13         # Friday 09:15, the row that ends at 09:30


def test_rows_do_not_start_before_the_convention():
    """Demand from Friday 06:00 (block 0) gives no rows before block 0."""
    # Arrange
    # Friday 06:00-07:00
    demand = {}
    for block in range(0, 4):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)

    # Act
    result = rows_to_show(problem)

    # Assert
    assert result[0] == 0           # Friday 06:00


def test_rows_do_not_go_past_the_end_of_the_convention():
    """Demand until Sunday night 06:00 (last block 287) gives no rows after block 287."""
    # Arrange
    # Sunday night 05:00-06:00, the last hour of the convention
    demand = {}
    for block in range(284, 288):
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)

    # Act
    result = rows_to_show(problem)

    # Assert
    assert result[-1] == 287        # Sunday night 05:45


def test_margins_of_two_days_that_touch_give_each_row_once():
    """When Saturday's margin after and Sunday's margin before overlap, each row comes once."""
    # Arrange
    # Saturday night 05:00-05:30 (blocks 188-189) and Sunday 06:00-06:30 (blocks 192-193).
    # Both margins cover blocks 190-191 (Saturday night 05:30-06:00).
    demand = {}
    for block in [*range(188, 190), *range(192, 194)]:
        demand[("Tickets", block)] = 1
    problem = _problem(["Tickets"], demand)

    # Act
    result = rows_to_show(problem)

    # Assert
    assert result == list(range(186, 196))   # Saturday night 04:30 to Sunday 07:00

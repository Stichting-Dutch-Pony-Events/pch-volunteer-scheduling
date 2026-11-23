from scheduler.model import Post, Problem, Settings, Volunteer, all_blocks, block_of
from scheduler.solving.soft_rules import fair_share_targets


# Passed explicitly instead of relying on the defaults in model.py. Two days keep the
# examples small: Friday = blocks 0-95, Saturday = blocks 96-191 (block 0 = Friday 06:00).
# fair_share_targets only looks at the demand, the availability and the hour limits, so
# no soft rule needs to be switched on.
RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday"))

ALL_DAYS = all_blocks(RULES)
FRIDAY = set(range(0, 96))
SATURDAY = set(range(96, 192))


def test_only_volunteer_gets_all_the_demand_as_target():
    """With one volunteer, their target is the whole demand."""
    # Arrange
    # Only Mock Mane, Tickets needs 1 in blocks 0-7 -> target 8.
    demand = {}
    for block in range(0, 8):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS)],
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    result = fair_share_targets(problem)

    # Assert
    assert result == {"Mock Mane": 8}


def test_volunteers_available_on_the_same_days_get_the_same_target():
    """Two volunteers who are there on the same days share the demand equally."""
    # Arrange
    # Mock Mane and Testy Hooves both all weekend, Tickets needs 1 in blocks 0-7
    # -> 4 and 4.
    names = ["Mock Mane", "Testy Hooves"]
    volunteers = []
    for name in names:
        volunteers.append(Volunteer(name=name, skills={"Tickets": 1},
                                    available_blocks=ALL_DAYS))

    demand = {}
    for block in range(0, 8):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    expected = {}
    for name in names:
        expected[name] = 4

    # Act
    result = fair_share_targets(problem)

    # Assert
    assert result == expected


def test_volunteer_available_on_fewer_days_gets_a_smaller_target():
    """A volunteer there on one of two equally long days gets half the share of one on both."""
    # Arrange
    # Tickets needs 1 on Friday blocks 0-7 and Saturday blocks 96-103 (both days 8
    # blocks long, 16 in total). Mock Mane both days (weight 16), Testy Hooves only Friday
    # (weight 8) -> 16 x 16/24 and 16 x 8/24, rounded.
    # This also checks the rounding: 10.67 goes up to 11, 5.33 down to 5.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=FRIDAY)]

    demand = {}
    for block in [*range(0, 8), *range(96, 104)]:
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    result = fair_share_targets(problem)

    # Assert
    assert result["Mock Mane"] == 11  # 16 * 16/24, rounded
    assert result["Testy Hooves"] == 5  # 16 * 8/24, rounded


def test_being_available_later_in_the_day_does_not_raise_the_target():
    """Two volunteers there on the same day get the same target, however late they stay."""
    # Arrange
    # Saturday demand from 10:00 to 02:00 (block_of helps). Mock Mane available
    # until 22:00, Testy Hooves until 02:00 -> the same target.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=set(range(96,
                                                       block_of("Saturday", "22:00", RULES)))),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=SATURDAY)]

    demand = {}
    for block in range(block_of("Saturday", "10:00", RULES),
                       block_of("Saturday", "02:00", RULES)):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    expected = {}
    for volunteer in volunteers:
        expected[volunteer.name] = 32

    # Act
    result = fair_share_targets(problem)

    # Assert
    assert result == expected


def test_availability_outside_the_convention_hours_of_a_day_does_not_count():
    """A day counts only if the volunteer is there between its first and last demand."""
    # Arrange
    # Friday demand blocks 0-7. Mock Mane available Friday blocks 0-7, Testy Hooves
    # only Friday blocks 80-90 (after the last demand) -> Testy Hooves 0, Mock Mane 8.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=FRIDAY),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=set(range(80, 90)))]

    demand = {}
    for block in range(0, 8):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    result = fair_share_targets(problem)

    # Assert
    assert result == {"Mock Mane": 8, "Testy Hooves": 0}


def test_day_length_runs_from_the_first_to_the_last_demand_including_gaps():
    """A gap in a day's demand does not make the day shorter."""
    # Arrange
    # Friday demand blocks 0-3 and 12-15 (length 16, not 8), Saturday blocks 96-103
    # (length 8). Mock Mane both days (weight 24), Testy Hooves only Saturday (weight 8);
    # total demand 16 -> 12 and 4. With the gap left out it would be 10.67 and 5.33.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=SATURDAY)]

    demand = {}
    for block in [*range(0, 4), *range(12, 16), *range(96, 104)]:
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    result = fair_share_targets(problem)

    # Assert
    assert result["Mock Mane"] == 12
    assert result["Testy Hooves"] == 4


def test_demand_for_more_people_counts_once_per_person():
    """A block that needs two people adds two blocks to the work to share."""
    # Arrange
    # Mock Mane and Testy Hooves both all weekend, Tickets needs 2 in blocks 0-7
    # (16 person-blocks) -> 8 and 8.
    names = ["Mock Mane", "Testy Hooves"]
    volunteers = []
    for name in names:
        volunteers.append(Volunteer(name=name, skills={"Tickets": 1},
                                    available_blocks=ALL_DAYS))

    demand = {}
    for block in range(0, 8):
        demand[("Tickets", block)] = 2

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    expected = {}
    for name in names:
        expected[name] = 8

    # Act
    result = fair_share_targets(problem)

    # Assert
    assert result == expected


def test_target_is_at_most_the_total_hour_limit():
    """A volunteer with a total hour limit never gets a target above it."""
    # Arrange
    # Mock Mane (max_minutes_total=60, 4 blocks) and Testy Hooves (no limit), both all
    # weekend, Tickets needs 1 in blocks 0-15 -> Mock Mane 4 (not 8), Testy Hooves 8.
    volunteers = [Volunteer(name="Mock Mane", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS, max_minutes_total=60),
                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                            available_blocks=ALL_DAYS)]

    demand = {}
    for block in range(0, 16):
        demand[("Tickets", block)] = 1

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand=demand,
                      settings=RULES)

    # Act
    result = fair_share_targets(problem)

    # Assert
    assert result["Mock Mane"] == 4
    assert result["Testy Hooves"] == 8


def test_without_demand_every_target_is_0():
    """With no demand at all, every volunteer's target is 0 (no division by zero)."""
    # Arrange
    names = ["Mock Mane", "Testy Hooves"]
    volunteers = []
    for name in names:
        volunteers.append(Volunteer(name=name, skills={"Tickets": 1},
                                    available_blocks=ALL_DAYS))

    problem = Problem(volunteers=volunteers,
                      posts=[Post("Tickets")],
                      demand={},
                      settings=RULES)

    # Act
    result = fair_share_targets(problem)

    # Assert
    for name in names:
        assert result[name] == 0

from scheduler.solving.checks import find_warnings
from scheduler.model import Volunteer, Post, Problem, Settings, all_blocks


RULES = Settings(min_stretch_minutes=60, max_stretch_minutes=180, min_break_minutes=30,
                 days=("Friday", "Saturday", "Sunday"))

ALL_DAYS = all_blocks(RULES)
SATURDAY = set(range(96, 192))


def test_no_warnings_when_every_volunteer_can_be_scheduled():
    """When every volunteer can work somewhere, there are no warnings."""
    # Arrange
    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS)],
                      posts=[Post("Tickets")],
                      demand={("Tickets", 0): 1},
                      settings=RULES)

    # Act
    lines = find_warnings(problem=problem)

    # Assert
    assert lines == []


def test_volunteer_never_available_while_their_post_is_open_gets_a_warning():
    """A volunteer who is only there when their post is closed gets a warning."""
    # Arrange
    # Tickets is only open on Friday at 06:00 (block 0); Testy Hooves is only there Saturday.
    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS),
                                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                                            available_blocks=SATURDAY)],
                      posts=[Post("Tickets")],
                      demand={("Tickets", 0): 1},
                      settings=RULES)

    # Act
    lines = find_warnings(problem=problem)

    # Assert
    assert len(lines) == 1
    assert "Testy Hooves" in lines[0]


def test_volunteer_qualified_only_for_posts_that_are_never_open_gets_a_warning():
    """A volunteer qualified only for a post without demand gets a warning."""
    # Arrange
    # Infobooth is on the Posts tab but never needs anyone.
    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS),
                                  Volunteer(name="Testy Hooves", skills={"Infobooth": 1},
                                            available_blocks=ALL_DAYS)],
                      posts=[Post("Tickets"), Post("Infobooth")],
                      demand={("Tickets", 0): 1},
                      settings=RULES)

    # Act
    lines = find_warnings(problem=problem)

    # Assert
    assert len(lines) == 1
    assert "Testy Hooves" in lines[0]


def test_volunteer_available_for_one_block_of_their_post_gets_no_warning():
    """One block where their post is open while they are there is enough: no warning."""
    # Arrange
    # Tickets is open in blocks 0 and 1, Mock Mane is only there in block 0.
    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks={0})],
                      posts=[Post("Tickets")],
                      demand={("Tickets", 0): 1, ("Tickets", 1): 1},
                      settings=RULES)

    # Act
    lines = find_warnings(problem=problem)

    # Assert
    assert lines == []


def test_warning_names_the_volunteer_and_the_reason():
    """The warning says who can never be scheduled, and why."""
    # Arrange
    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS),
                                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                                            available_blocks=SATURDAY)],
                      posts=[Post("Tickets")],
                      demand={("Tickets", 0): 1},
                      settings=RULES)

    # Act
    lines = find_warnings(problem=problem)

    # Assert
    # The whole line, so the wording is pinned down exactly.
    assert lines == ["Testy Hooves can never be scheduled: no post they are qualified for "
                     "is open while they are available"]


def test_every_volunteer_who_can_never_be_scheduled_gets_their_own_warning():
    """Two volunteers who can never be scheduled give two lines, in volunteer order."""
    # Arrange
    # Mock Mane is fine; Testy Hooves is never there when Tickets is open, Dummy Dash is
    # only qualified for Infobooth, which never needs anyone.
    problem = Problem(volunteers=[Volunteer(name="Mock Mane", skills={"Tickets": 1},
                                            available_blocks=ALL_DAYS),
                                  Volunteer(name="Testy Hooves", skills={"Tickets": 1},
                                            available_blocks=SATURDAY),
                                  Volunteer(name="Dummy Dash", skills={"Infobooth": 1},
                                            available_blocks=ALL_DAYS)],
                      posts=[Post("Tickets"), Post("Infobooth")],
                      demand={("Tickets", 0): 1},
                      settings=RULES)

    # Act
    lines = find_warnings(problem=problem)

    # Assert
    assert len(lines) == 2
    assert "Testy Hooves" in lines[0]
    assert "Dummy Dash" in lines[1]

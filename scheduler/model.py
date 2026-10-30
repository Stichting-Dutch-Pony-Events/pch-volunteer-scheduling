"""The data the scheduler works with: volunteers, posts, settings, the problem to solve
and the schedule that comes out, plus small helpers for blocks of time.
"""
from dataclasses import dataclass

# Time is measured in blocks of 15 minutes. Block 0 is 06:00 on the first day; a day
# runs from 06:00 to 06:00 the next morning, so it has 24 * 4 = 96 blocks.
MINUTES_PER_BLOCK = 15
BLOCKS_PER_DAY = 96


def runs_of_consecutive_blocks(blocks) -> list[tuple[int, int]]:
    """Split blocks into runs of consecutive blocks, as (first_block, block_after_last).

    The blocks may be in any order; duplicates count once.
    Example: {0, 1, 2, 5, 6} -> [(0, 3), (5, 7)]
    """
    runs = []
    start = None      # first block of the run we are building
    previous = None   # the block we looked at just before this one
    for block in sorted(set(blocks)):
        if start is None:
            start = block
        elif block != previous + 1:
            runs.append((start, previous + 1))  # gap: close this run
            start = block                       # ...and start a new one
        previous = block

    if start is not None:
        runs.append((start, previous + 1))      # the last run has no gap after it
    return runs


@dataclass
class Volunteer:
    """A volunteer and the posts they may work."""
    name: str  # the nickname used in the schedule
    # post -> skill level: 1 can, 2 good at it / likes it, 3 main role (missing = never)
    skills: dict[str, int]


@dataclass
class Post:
    """A place or task that needs volunteers, e.g. Tickets or Infobooth."""
    name: str


# frozen=True: settings cannot be changed after creation. That also lets Python
# accept Settings() as the default value in Problem below.
@dataclass(frozen=True)
class Settings:
    """Limits and options for one scheduling run (later read from the Settings tab)."""
    # A work stretch is continuous work, also across posts.
    min_stretch_minutes: int = 60
    max_stretch_minutes: int = 180
    # Minimum break between two work stretches.
    min_break_minutes: int = 30
    # The convention days in order. The first one starts at block 0.
    days: tuple[str, ...] = ("Friday", "Saturday", "Sunday")


@dataclass
class Problem:
    """Everything the solver needs: who can work, where, and how many people when."""
    volunteers: list[Volunteer]
    posts: list[Post]
    # (post, block) -> number of volunteers needed (missing = closed)
    demand: dict[tuple[str, int], int]
    settings: Settings = Settings()


@dataclass
class Schedule:
    """The solver's answer: who works where in which block."""
    # (volunteer_name, post, block)
    assignments: set[tuple[str, str, int]]

    def people_at(self, post: str, block: int) -> set[str]:
        """Names of the volunteers working at this post during this block."""
        assigned_people = set()
        for assigned_volunteer_name, assigned_post, assigned_block in self.assignments:
            if assigned_post == post and assigned_block == block:
                assigned_people.add(assigned_volunteer_name)

        return assigned_people

    def work_stretches_of(self, volunteer_name: str) -> list[tuple[int, int]]:
        """Periods of continuous work for this volunteer, regardless of post.

        Each stretch is (first_block, block_after_last), sorted by time.
        """
        # Collect the blocks this volunteer works (a set, so no block can count twice).
        blocks = set()
        for assigned_volunteer_name, assigned_post, assigned_block in self.assignments:
            if assigned_volunteer_name == volunteer_name:
                blocks.add(assigned_block)

        return runs_of_consecutive_blocks(blocks)


def block_of(day: str, time: str, settings: Settings) -> int:
    """The block that starts at this time on this convention day, e.g. ("Saturday", "13:30").

    Times before 06:00 belong to the night after that day: ("Saturday", "01:00") is
    the Saturday night, in the early hours of Sunday.
    """
    return 0  # not implemented yet


def time_of(block: int, settings: Settings) -> tuple[str, str]:
    """The convention day and start time of a block, e.g. 172 -> ("Saturday", "01:00")."""
    return ("", "")  # not implemented yet


def day_of(block: int, settings: Settings) -> str:
    """The convention day a block belongs to, e.g. 172 -> "Saturday"."""
    return ""  # not implemented yet

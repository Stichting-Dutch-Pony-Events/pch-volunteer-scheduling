"""The data the scheduler works with: volunteers, posts, settings, the problem to solve
and the schedule that comes out, plus small helpers for blocks of time.
"""
from dataclasses import dataclass

# Time is measured in blocks of 15 minutes. Block 0 is 06:00 on the first day; a day
# runs from 06:00 to 06:00 the next morning, so it has 24 * 4 = 96 blocks.
MINUTES_PER_BLOCK = 15
BLOCKS_PER_DAY = 96
DAY_STARTS_AT_HOUR = 6

# The names that may be used in Settings.soft_rules to switch a soft rule on (each one is
# a function in solving/soft_rules.py). Settings refuses any other name, so a typo can't
# silently switch nothing on. Add the name here when adding a soft rule.
SOFT_RULE_NAMES = {"fair_spread", "fewer_stretches", "preferred_max_stretch", "round_times",
                   "skill_score"}


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
    # The blocks this volunteer can work (empty = never). For the whole weekend use
    # all_blocks(settings).
    available_blocks: set[int]
    # The most this volunteer may work per convention day and over the whole convention,
    # in minutes (None = no limit). The workbook gives whole hours.
    max_minutes_per_day: int | None = None
    max_minutes_total: int | None = None


@dataclass
class Post:
    """A place or task that needs volunteers, e.g. Tickets or Infobooth."""
    name: str


# frozen=True: settings cannot be changed after creation. That also lets Python
# accept Settings() as the default value in Problem below.
@dataclass(frozen=True)
class Settings:
    """Limits and options for one scheduling run, read from the Settings tab."""
    # A work stretch is continuous work, also across posts.
    min_stretch_minutes: int = 60
    max_stretch_minutes: int = 180
    # Minimum break between two work stretches.
    min_break_minutes: int = 30
    # The convention days in order. The first one starts at block 0.
    days: tuple[str, ...] = ("Friday", "Saturday", "Sunday")
    # The default hour limits in minutes (None = no limit), for volunteers who have no
    # limit of their own on the Volunteers tab. Only the reader uses these: the solver
    # looks at the limits on each Volunteer.
    default_max_minutes_per_day: int | None = None
    default_max_minutes_total: int | None = None
    # The soft rules that are switched on, by name (see SOFT_RULE_NAMES above).
    # Empty by default: Settings() means hard rules only, so a test switches on exactly the
    # soft rule it tests. A frozenset because Settings is frozen (a set could be changed).
    soft_rules: frozenset[str] = frozenset()
    # Soft rule weights: penalty points per time block (15 minutes) worked at a post where
    # the volunteer has this skill score. Lower = preferred, so score 3 costs the least.
    weight_skill_score_1: int = 6
    weight_skill_score_2: int = 2
    weight_skill_score_3: int = 0
    # Penalty points for each work stretch that starts or ends off the half-hour grid
    # (on :15 or :45). Per start or end, not per block.
    weight_off_round_time: int = 10
    # Penalty points for each work stretch, so the solver prefers fewer, longer stretches.
    # Per stretch, not per block.
    weight_work_stretch: int = 20
    # A work stretch longer than this costs weight_over_preferred_stretch for every time
    # block (15 minutes) beyond it.
    preferred_max_stretch_minutes: int = 120
    weight_over_preferred_stretch: int = 6
    # Penalty points for every time block (15 minutes) a volunteer works above their fair
    # share of the work (see fair_share_targets in solving/soft_rules.py).
    weight_over_fair_share: int = 4

    def __post_init__(self) -> None:
        """Check the settings right after initialisation."""
        for name in self.soft_rules:
            if name not in SOFT_RULE_NAMES:
                raise ValueError(f"Unknown soft rule {name!r}. Known: "
                                 + ", ".join(sorted(SOFT_RULE_NAMES)))


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
    # Filled in by the solver: True when CP-SAT proved no schedule has a lower penalty.
    proven_optimal: bool = False
    # The total penalty of this schedule (None = not made by the solver).
    penalty: int | None = None
    # No schedule can have a lower penalty than this (CP-SAT's best bound).
    lowest_possible_penalty: int | None = None

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

    def shifts_of(self, volunteer_name: str) -> list[tuple[str, int, int]]:
        """Shifts of this volunteer: runs of consecutive blocks at one post.

        Each shift is (post, first_block, block_after_last), sorted by time. Unlike a work
        stretch, moving straight on to another post starts a new shift.
        Example: Tickets 0-3, then Infobooth 4-6 -> [("Tickets", 0, 4), ("Infobooth", 4, 7)]
        """
        # Isolate what posts the volunteer is assigned, and what blocks
        blocks_per_post = {}  # dict(postname) -> set() blocks assigned
        for assigned_volunteer_name, assigned_post, assigned_block in self.assignments:
            if assigned_volunteer_name == volunteer_name:
                if assigned_post not in blocks_per_post:
                    blocks_per_post[assigned_post] = set()

                blocks_per_post[assigned_post].add(assigned_block)

        # Generate the shifts from those
        shifts = []  # [(post, first_block, block_after_last), ...]
        for post, blocks in blocks_per_post.items():
            for first_block, block_after_last in runs_of_consecutive_blocks(blocks):
                shifts.append((post, first_block, block_after_last))

        # Sort by the first block (time order), then by post name when two start together.
        shifts.sort(key=lambda shift: (shift[1], shift[0]))
        return shifts


def block_of(day: str, time: str, settings: Settings) -> int:
    """The block that starts at this time on this convention day, e.g. ("Saturday", "13:30").

    Times before 06:00 belong to the night after that day: ("Saturday", "01:00") is
    the Saturday night, in the early hours of Sunday.
    """
    # 1. The day must be one of the convention days.
    if day not in settings.days:
        raise ValueError(f"Unknown day {day!r}, expected one of {settings.days}.")
    day_number = settings.days.index(day)

    # 2. The time must look like "HH:MM", with valid hours and minutes.
    try:
        hours_text, minutes_text = time.split(":")
        hours = int(hours_text)
        minutes = int(minutes_text)
    except ValueError:
        raise ValueError(f"Time {time!r} is not in the format 'HH:MM'.") from None
    if not 0 <= hours < 24:
        raise ValueError(f"Time {time!r} has an invalid hour (expected 0-23).")
    if not 0 <= minutes < 60:
        raise ValueError(f"Time {time!r} has invalid minutes (expected 0-59).")

    # 3. The time must fall exactly on the start of a block.
    if minutes % MINUTES_PER_BLOCK != 0:
        raise ValueError(f"Time {time!r} is not on a {MINUTES_PER_BLOCK}-minute step.")

    # Minutes since the start of the convention day. % 24 wraps the night around:
    # 01:00 gives (1 - 6) % 24 = 19 hours after 06:00.
    hours_since_day_start = (hours - DAY_STARTS_AT_HOUR) % 24
    minutes_since_day_start = hours_since_day_start * 60 + minutes

    return day_number * BLOCKS_PER_DAY + minutes_since_day_start // MINUTES_PER_BLOCK


def day_and_time_of(block: int, settings: Settings) -> tuple[str, str]:
    """The convention day and start time of a block, e.g. 172 -> ("Saturday", "01:00")."""
    day = day_of(block, settings)   # also checks that the block is within the convention days

    # Minutes since the start of this convention day (06:00).
    block_in_day = block % BLOCKS_PER_DAY
    minutes_since_day_start = block_in_day * MINUTES_PER_BLOCK

    # Back to the clock: add the 6 hours and wrap around midnight.
    # Block 172 is 76 blocks into Saturday = 19 hours after 06:00, so (19 + 6) % 24 = 01:00.
    hours = (minutes_since_day_start // 60 + DAY_STARTS_AT_HOUR) % 24
    minutes = minutes_since_day_start % 60

    return (day, f"{hours:02d}:{minutes:02d}")


def end_time_of(block_after_last: int, settings: Settings) -> str:
    """The end time ("HH:MM") of a time range that stops just before block_after_last.

    Usually that is simply the time of block_after_last. But a range that runs until the
    very end of the convention has a block_after_last that no longer exists, so day_and_time_of
    would raise; that range ends at the day boundary (06:00).
    """
    final_block = (len(settings.days) * BLOCKS_PER_DAY) - 1

    if block_after_last > final_block:
        # The convention ends at 06:00, the same time of day as block 0.
        _, end = day_and_time_of(block=0, settings=settings)
    else:
        _, end = day_and_time_of(block=block_after_last, settings=settings)

    return end


def day_of(block: int, settings: Settings) -> str:
    """The convention day a block belongs to, e.g. 172 -> "Saturday"."""
    if block < 0 or block >= len(settings.days) * BLOCKS_PER_DAY:
        raise ValueError(f"Block {block} is out of convention days {settings.days}.")

    return settings.days[block // BLOCKS_PER_DAY]


def all_blocks(settings: Settings) -> set[int]:
    """Every block of the convention days, e.g. to make someone available all weekend."""
    # Same range as day_of accepts: block 0 up to (not including) the block after the last day.
    return set(range(len(settings.days) * BLOCKS_PER_DAY))

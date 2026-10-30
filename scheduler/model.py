from dataclasses import dataclass


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
    name: str
    # post -> skill level: 1 can, 2 good at it / likes it, 3 main role (missing = never)
    skills: dict[str, int]


@dataclass
class Post:
    name: str


# frozen=True: settings cannot be changed after creation. That also lets Python
# accept Settings() as the default value in Problem below.
@dataclass(frozen=True)
class Settings:
    # A work stretch is continuous work, also across posts.
    min_stretch_minutes: int = 60
    max_stretch_minutes: int = 180
    # Minimum break between two work stretches.
    min_break_minutes: int = 30


@dataclass
class Problem:
    volunteers: list[Volunteer]
    posts: list[Post]
    # (post, block) -> number of volunteers needed (missing = closed)
    demand: dict[tuple[str, int], int]
    settings: Settings = Settings()


@dataclass
class Schedule:
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

from dataclasses import dataclass


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

        # Walk through the blocks in time order. A stretch continues as long as each
        # block directly follows the previous one; a gap closes it and starts a new one.
        work_stretches = []
        start = None      # first block of the stretch we are building
        previous = None   # the block we looked at just before this one
        for block in sorted(blocks):
            if start is None:
                start = block                                 # very first block
            elif block != previous + 1:
                work_stretches.append((start, previous + 1))  # gap: close this stretch
                start = block                                 # ...and start a new one
            previous = block

        # The last stretch has no gap after it, so close it here (if there was any work).
        if start is not None:
            work_stretches.append((start, previous + 1))

        return work_stretches

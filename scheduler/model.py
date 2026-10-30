from dataclasses import dataclass


@dataclass
class Volunteer:
    name: str
    # post -> skill level: 1 can, 2 good at it / likes it, 3 main role (missing = never)
    skills: dict[str, int]


@dataclass
class Post:
    name: str


@dataclass
class Problem:
    volunteers: list[Volunteer]
    posts: list[Post]
    # (post, block) -> number of volunteers needed (missing = closed)
    demand: dict[tuple[str, int], int]


@dataclass
class Schedule:
    # (volunteer_name, post, block)
    assignments: set[tuple[str, str, int]]

    def people_at(self, post: str, block: int) -> set[str]:
        """Names of the volunteers working at this post during this block."""
        assigned_people = set()
        for volunteer_name, assigned_post, assigned_block in self.assignments:
            if assigned_post == post and assigned_block == block:
                assigned_people.add(volunteer_name)

        return assigned_people
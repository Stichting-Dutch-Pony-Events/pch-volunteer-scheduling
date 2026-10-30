from dataclasses import dataclass

@dataclass
class Volunteer:
    name: str
    skills: dict[str, int] # post -> skill level: 1 can, 2 good at it / likes it, 3 main role (missing = never)

@dataclass
class Post:
    name: str

@dataclass
class Problem:
    volunteers: list[Volunteer]
    posts: list[Post]
    demand: dict[tuple[str, int], int] # (post, block) -> number of volunteers needed

@dataclass
class Schedule:
    assignments: set[tuple[str, str, int]] # (volunteer_name, post, block)

    def people_at(self, post: str, block: int) -> set[str]:
        """Names of the volunteers working at this post during this block."""

        assigned_people = set()
        for assignment in self.assignments:
            if assignment[1] == post and assignment[2] == block:
                assigned_people.add(assignment[0])
                
        return assigned_people
"""A.D. Bugsworth progression model for Neon Shield.

Gamification only: levels and badges never alter security controls.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class BugsworthLevel:
    level: int
    title: str
    minimum_catches: int
    badge: str
    next_minimum: int | None


LEVELS: Tuple[BugsworthLevel, ...] = (
    BugsworthLevel(1, "Bug Spotter", 0, "🔎", 10),
    BugsworthLevel(2, "Bug Tracker", 10, "🐾", 25),
    BugsworthLevel(3, "Bug Buster", 25, "🪲", 50),
    BugsworthLevel(4, "Bug Hunter", 50, "🎯", 100),
    BugsworthLevel(5, "Bug Snare Specialist", 100, "🪤", 250),
    BugsworthLevel(6, "Shield Guardian", 250, "🛡️", 500),
    BugsworthLevel(7, "A.D. Bugsworth Elite", 500, "🏅", 1000),
    BugsworthLevel(8, "Master Bug Warden", 1000, "👑", None),
)


@dataclass(frozen=True)
class BugsworthProfile:
    catches: int = 0

    @property
    def level(self) -> BugsworthLevel:
        current = LEVELS[0]
        for level in LEVELS:
            if self.catches >= level.minimum_catches:
                current = level
            else:
                break
        return current

    @property
    def progress(self) -> dict[str, int | None]:
        current = self.level
        if current.next_minimum is None:
            return {"current": self.catches, "next": None, "remaining": 0}
        return {
            "current": self.catches,
            "next": current.next_minimum,
            "remaining": max(0, current.next_minimum - self.catches),
        }

    def record_catch(self, count: int = 1) -> "BugsworthProfile":
        if count < 1:
            raise ValueError("count must be at least 1")
        return BugsworthProfile(self.catches + count)

    def summary(self) -> dict[str, object]:
        current = self.level
        return {
            "name": "A.D. Bugsworth",
            "role": "Chief Bug Detection Officer",
            "level": current.level,
            "title": current.title,
            "badge": current.badge,
            "bugs_caught": self.catches,
            "progress": self.progress,
        }

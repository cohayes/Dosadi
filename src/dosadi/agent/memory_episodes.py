from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(slots=True)
class Episode:
    episode_id: str
    day: int
    kind: str
    salience: float
    payload: Dict[str, object]


@dataclass(slots=True)
class EpisodeBuffer:
    daily: List[Episode] = field(default_factory=list)

    def add(self, ep: Episode) -> None:
        self.daily.append(ep)


__all__ = ["Episode", "EpisodeBuffer"]

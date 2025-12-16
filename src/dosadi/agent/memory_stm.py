from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import json
from hashlib import sha256
from typing import List, Tuple

from .memory_episodes import Episode


@dataclass(slots=True)
class STMItem:
    episode_id: str
    score: float
    day: int


@dataclass(slots=True)
class STMBoringWinner:
    k: int
    items: List[STMItem] = field(default_factory=list)
    _heap: List[Tuple[float, str, STMItem]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.items and not self._heap:
            for itm in self.items:
                heapq.heappush(self._heap, (itm.score, itm.episode_id, itm))
        elif self._heap and not self.items:
            self.items = [entry[2] for entry in self._heap]

    def consider(self, ep: Episode) -> bool:
        item = STMItem(episode_id=ep.episode_id, score=float(ep.salience), day=ep.day)
        if len(self._heap) < self.k:
            heapq.heappush(self._heap, (item.score, item.episode_id, item))
            self.items = [entry[2] for entry in self._heap]
            return True

        weakest_score, _, _ = self._heap[0]
        if item.score < weakest_score:
            return False

        heapq.heapreplace(self._heap, (item.score, item.episode_id, item))
        self.items = [entry[2] for entry in self._heap]
        return True

    def signature(self) -> str:
        canonical = [
            {
                "episode_id": itm.episode_id,
                "score": round(float(itm.score), 6),
                "day": itm.day,
            }
            for _, _, itm in sorted(self._heap, key=lambda t: (t[0], t[1]))
        ]
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()


__all__ = ["STMItem", "STMBoringWinner"]

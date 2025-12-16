from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict


@dataclass(slots=True)
class CrumbCounter:
    count: int
    last_day: int


@dataclass(slots=True)
class CrumbStore:
    tags: Dict[str, CrumbCounter] = field(default_factory=dict)
    last_decay_day: int = 0

    def bump(self, tag: str, day: int, inc: int = 1, *, half_life_days: int = 30) -> None:
        self.maybe_decay(day, half_life_days=half_life_days)
        counter = self.tags.get(tag)
        if counter is None:
            self.tags[tag] = CrumbCounter(count=inc, last_day=day)
            return
        counter.count += inc
        counter.last_day = day

    def maybe_decay(self, day: int, half_life_days: int) -> None:
        if day <= self.last_decay_day:
            return
        if not self.tags:
            self.last_decay_day = day
            return

        elapsed = max(0, day - self.last_decay_day)
        if half_life_days <= 0 or elapsed <= 0:
            self.last_decay_day = day
            return

        decay_factor = 0.5 ** (elapsed / float(half_life_days))
        for key, counter in list(self.tags.items()):
            decayed = int(math.floor(counter.count * decay_factor))
            counter.count = max(0, decayed)
            counter.last_day = max(counter.last_day, day)
            if counter.count <= 0:
                del self.tags[key]
        self.last_decay_day = day

    def signature(self) -> str:
        parts = [f"{tag}:{counter.count}" for tag, counter in sorted(self.tags.items())]
        return ",".join(parts)


__all__ = ["CrumbCounter", "CrumbStore"]

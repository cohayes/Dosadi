from __future__ import annotations

from dataclasses import dataclass, field
import heapq
from typing import Dict, List, Tuple


@dataclass(slots=True)
class Belief:
    key: str
    value: float
    weight: float
    last_day: int


@dataclass(slots=True)
class BeliefStore:
    max_items: int
    items: Dict[str, Belief] = field(default_factory=dict)
    minheap: List[Tuple[float, str]] = field(default_factory=list)

    def upsert(self, belief: Belief) -> None:
        """Insert or update a belief while maintaining bounded retention."""

        self.items[belief.key] = belief
        heapq.heappush(self.minheap, (float(belief.weight), belief.key))
        self._rebalance()

    def _rebalance(self) -> None:
        if self.max_items <= 0:
            self.items.clear()
            self.minheap.clear()
            return

        while len(self.items) > self.max_items and self.minheap:
            weight, key = heapq.heappop(self.minheap)
            current = self.items.get(key)
            if current is None:
                continue
            if float(current.weight) != float(weight):
                # Outdated heap entry.
                continue
            del self.items[key]

        # Clean up excessive heap growth from outdated entries.
        if len(self.minheap) > max(self.max_items * 4, 32):
            fresh_heap: List[Tuple[float, str]] = [
                (float(b.weight), k) for k, b in self.items.items()
            ]
            heapq.heapify(fresh_heap)
            self.minheap = fresh_heap

    def get(self, key: str) -> Belief | None:
        return self.items.get(key)

    def signature(self) -> str:
        parts = [
            f"{key}:{val.value:.6f}:{val.weight:.6f}:{val.last_day}"
            for key, val in sorted(self.items.items(), key=lambda item: item[0])
        ]
        return ",".join(parts)


__all__ = ["Belief", "BeliefStore"]

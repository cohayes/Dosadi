from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Iterable, Iterator, Mapping, MutableMapping


@dataclass(slots=True)
class TopKEntry:
    key: str
    score: float
    payload: Mapping[str, object] | None = None


@dataclass(slots=True)
class TopK:
    k: int = 10
    entries: list[TopKEntry] = field(default_factory=list)

    def add(self, key: str, score: float, payload: Mapping[str, object] | None = None) -> None:
        entry = TopKEntry(key=key, score=float(score), payload=dict(payload or {}))
        self.entries.append(entry)
        self.entries.sort(key=lambda e: (-e.score, e.key))
        if len(self.entries) > max(1, int(self.k)):
            self.entries = self.entries[: int(self.k)]

    def snapshot(self) -> list[Mapping[str, object]]:
        return [
            {"key": entry.key, "score": entry.score, "payload": dict(entry.payload or {})}
            for entry in self.entries
        ]


@dataclass(slots=True)
class Metrics(MutableMapping[str, float]):
    counters: dict[str, float] = field(default_factory=dict)
    gauges: dict[str, Any] = field(default_factory=dict)
    topk: dict[str, TopK] = field(default_factory=dict)
    legacy: dict[str, float] = field(default_factory=dict)

    def __getitem__(self, key: str) -> float:
        return self.legacy[key]

    def __setitem__(self, key: str, value: float) -> None:
        self.legacy[key] = float(value)

    def __delitem__(self, key: str) -> None:
        if key in self.legacy:
            del self.legacy[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.legacy)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self.legacy)

    def inc(self, path: str, n: float = 1.0) -> float:
        self.counters[path] = self.counters.get(path, 0.0) + float(n)
        return self.counters[path]

    def set_gauge(self, path: str, value: Any) -> Any:
        self.gauges[path] = value
        return value

    def topk_add(self, path: str, key: str, score: float, payload: Mapping[str, object] | None = None) -> None:
        bucket = self.topk.get(path)
        if bucket is None:
            bucket = TopK()
            self.topk[path] = bucket
        bucket.add(key, score, payload=payload)

    def snapshot_signature(self) -> str:
        canonical = {
            "counters": {k: float(v) for k, v in sorted(self.counters.items())},
            "gauges": {k: self._to_jsonable(v) for k, v in sorted(self.gauges.items())},
            "topk": {k: bucket.snapshot() for k, bucket in sorted(self.topk.items())},
            "legacy": {k: float(v) for k, v in sorted(self.legacy.items())},
        }
        return json.dumps(canonical, sort_keys=True, separators=(",", ":"))

    def _to_jsonable(self, value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, Mapping):
            return {str(k): self._to_jsonable(v) for k, v in sorted(value.items(), key=lambda itm: str(itm[0]))}
        if isinstance(value, (list, tuple, set)):
            return [self._to_jsonable(v) for v in value]
        return str(value)


@dataclass(slots=True)
class EventRing:
    capacity: int = 200
    events: list[Mapping[str, object]] = field(default_factory=list)

    def append(self, event: Mapping[str, object]) -> None:
        self.events.append(dict(event))
        if len(self.events) > max(1, int(self.capacity)):
            self.events = self.events[-int(self.capacity) :]

    def tail(self, n: int = 10) -> list[Mapping[str, object]]:
        return list(self.events[-max(0, int(n)) :])


@dataclass(slots=True)
class DebugConfig:
    level: str = "minimal"

    def has_event_ring(self) -> bool:
        return self.level in {"standard", "verbose"}


def ensure_metrics(world: Any) -> Metrics:
    metrics = getattr(world, "metrics", None)
    if isinstance(metrics, Metrics):
        return metrics
    converted = Metrics()
    if isinstance(metrics, Mapping):
        for key, value in metrics.items():
            try:
                converted.legacy[str(key)] = float(value)
            except Exception:
                continue
    world.metrics = converted
    return converted


def ensure_event_ring(world: Any) -> EventRing:
    cfg: DebugConfig = getattr(world, "debug_cfg", DebugConfig())
    world.debug_cfg = cfg
    ring = getattr(world, "event_ring", None)
    if cfg.has_event_ring():
        if not isinstance(ring, EventRing):
            ring = EventRing()
            world.event_ring = ring
        return ring
    return ring if isinstance(ring, EventRing) else EventRing(capacity=0)


def record_event(world: Any, event: Mapping[str, object]) -> None:
    ring = ensure_event_ring(world)
    if ring.capacity <= 0:
        return
    payload = dict(event)
    if "day" not in payload:
        payload["day"] = getattr(world, "day", 0)
    ring.append(payload)


__all__ = [
    "DebugConfig",
    "EventRing",
    "Metrics",
    "TopK",
    "TopKEntry",
    "ensure_event_ring",
    "ensure_metrics",
    "record_event",
]

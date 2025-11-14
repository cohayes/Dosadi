"""Snapshot and journal helpers for deterministic state persistence."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple


@dataclass(frozen=True)
class TickJournalEntry:
    """Record a single state transition within a tick."""

    path: str
    before: Any
    after: Any


@dataclass(frozen=True)
class TickJournal:
    """Immutable journal describing mutations that occurred during a tick."""

    tick: int
    entries: Tuple[TickJournalEntry, ...]


@dataclass(frozen=True)
class Snapshot:
    """Full snapshot of the world state at a given tick."""

    tick: int
    state: Mapping[str, Any]


@dataclass(frozen=True)
class DeltaSnapshot:
    """Compressed representation referencing a base snapshot plus a journal."""

    base_tick: int
    journal: TickJournal


class SnapshotManager:
    """Manage a stream of full and delta snapshots for the runtime."""

    def __init__(self, *, full_interval: int = 250) -> None:
        self.full_interval = max(1, full_interval)
        self._last_state: Mapping[str, Any] | None = None
        self._last_full: Snapshot | None = None
        self._pending_since_full: int = 0
        self._journals: List[TickJournal] = []

    def prime(self, state: Mapping[str, Any], tick: int) -> Snapshot:
        """Record the baseline snapshot."""

        snapshot = Snapshot(tick=tick, state=dict(state))
        self._last_state = snapshot.state
        self._last_full = snapshot
        self._pending_since_full = 0
        self._journals.clear()
        return snapshot

    def capture_tick(self, state: Mapping[str, Any], tick: int) -> Tuple[TickJournal, DeltaSnapshot | Snapshot]:
        """Generate a journal (and potentially a new full snapshot)."""

        if self._last_state is None:
            full = self.prime(state, tick)
            empty = TickJournal(tick=tick, entries=tuple())
            return empty, full

        entries = tuple(_diff(self._last_state, state))
        journal = TickJournal(tick=tick, entries=entries)
        self._last_state = dict(state)
        self._pending_since_full += 1
        self._journals.append(journal)

        if self._pending_since_full >= self.full_interval:
            snapshot = self.prime(state, tick)
            return journal, snapshot

        return journal, DeltaSnapshot(base_tick=self._last_full.tick if self._last_full else tick, journal=journal)

    @property
    def journals(self) -> Iterable[TickJournal]:
        return tuple(self._journals)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def serialize_state(value: Any) -> Any:
    """Convert dataclasses and containers into deterministic primitives."""

    if is_dataclass(value):
        return {
            field.name: serialize_state(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): serialize_state(val) for key, val in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [serialize_state(val) for val in value]
    if isinstance(value, set):
        return sorted(serialize_state(val) for val in value)
    return value


def _diff(old: Mapping[str, Any], new: Mapping[str, Any], *, prefix: str = "") -> Iterable[TickJournalEntry]:
    old_keys = set(old.keys())
    new_keys = set(new.keys())
    for key in sorted(old_keys | new_keys):
        path = f"{prefix}.{key}" if prefix else str(key)
        if key not in old:
            yield TickJournalEntry(path=path, before=None, after=new[key])
            continue
        if key not in new:
            yield TickJournalEntry(path=path, before=old[key], after=None)
            continue
        old_val = old[key]
        new_val = new[key]
        if isinstance(old_val, Mapping) and isinstance(new_val, Mapping):
            yield from _diff(old_val, new_val, prefix=path)
            continue
        if isinstance(old_val, list) and isinstance(new_val, list):
            if old_val != new_val:
                yield TickJournalEntry(path=path, before=old_val, after=new_val)
            continue
        if old_val != new_val:
            yield TickJournalEntry(path=path, before=old_val, after=new_val)


__all__ = [
    "DeltaSnapshot",
    "Snapshot",
    "SnapshotManager",
    "TickJournal",
    "TickJournalEntry",
    "serialize_state",
]

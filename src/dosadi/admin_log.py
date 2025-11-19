"""Admin event log utilities derived from D-INTERFACE-0001.

The admin/debug dashboard spec (``docs/latest/09_interfaces/D-INTERFACE-0001...``)
identifies a lightweight event stream capturing key simulation happenings so
instrumentation (CLI, notebook, or future web tools) can reason about
"what just happened" without poking through world internals.  This module
implements the minimal v0 slice described in section 6 of that document:

* side-effect free event records tagged by tick and optional ward/facility
* helpers for the canonical event families (agent decisions, rumor spread,
  facility incidents)
* a ring buffer with filtering hooks so tooling can show recent activity

The log intentionally stays decoupled from any rendering/UI code to make it
usable from tests and batch simulations alike.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


@dataclass(slots=True)
class AdminEvent:
    """Structured record for a single admin/debug event."""

    tick: int
    event_type: str
    payload: MutableMapping[str, Any]
    ward_id: Optional[str] = None
    facility_id: Optional[str] = None
    agent_ids: Tuple[str, ...] = field(default_factory=tuple)
    tags: Tuple[str, ...] = field(default_factory=tuple)

    def summary(self) -> str:
        """Return a compact string summarising the payload."""

        if self.event_type == "AGENT_DECISION":
            action = self.payload.get("action", "?")
            score = self.payload.get("total_score")
            if score is not None:
                return f"{action} ({score:0.2f})"
            return str(action)
        if self.event_type == "RUMOR_SPREAD":
            topic = self.payload.get("topic", "?")
            delta = self.payload.get("credibility_delta")
            if delta is not None:
                return f"{topic} Δ{delta:0.2f}"
            return str(topic)
        if self.event_type == "FACILITY_EVENT":
            event_kind = self.payload.get("event_kind", "?")
            return f"{event_kind} @ {self.facility_id or '-'}"
        # fall back to payload repr
        return ", ".join(f"{k}={v}" for k, v in sorted(self.payload.items()))


class AdminEventLog:
    """Fixed-size event history suitable for admin dashboards."""

    def __init__(self, capacity: int = 1_000) -> None:
        self.capacity = max(1, capacity)
        self._events: Deque[AdminEvent] = deque(maxlen=self.capacity)

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------
    def record(
        self,
        *,
        tick: int,
        event_type: str,
        payload: Mapping[str, Any],
        ward_id: Optional[str] = None,
        facility_id: Optional[str] = None,
        agent_ids: Sequence[str] = (),
        tags: Sequence[str] = (),
    ) -> AdminEvent:
        event = AdminEvent(
            tick=tick,
            event_type=event_type,
            payload=dict(payload),
            ward_id=ward_id,
            facility_id=facility_id,
            agent_ids=tuple(agent_ids),
            tags=tuple(tags),
        )
        self._events.append(event)
        return event

    def log_agent_decision(
        self,
        *,
        tick: int,
        agent_id: str,
        ward_id: str,
        facility_id: Optional[str],
        action: str,
        survival_score: float,
        long_term_score: float,
        risk_score: float,
    ) -> AdminEvent:
        """Record a canonical AGENT_DECISION event."""

        total_score = survival_score + long_term_score - risk_score
        payload = {
            "action": action,
            "survival_score": survival_score,
            "long_term_score": long_term_score,
            "risk_score": risk_score,
            "total_score": total_score,
        }
        return self.record(
            tick=tick,
            event_type="AGENT_DECISION",
            payload=payload,
            ward_id=ward_id,
            facility_id=facility_id,
            agent_ids=[agent_id],
        )

    def log_rumor_spread(
        self,
        *,
        tick: int,
        speaker_id: str,
        listener_id: str,
        rumor_id: str,
        topic: str,
        credibility_before: float,
        credibility_after: float,
        ward_id: Optional[str] = None,
    ) -> AdminEvent:
        """Record a RUMOR_SPREAD event as suggested by the spec."""

        payload = {
            "rumor_id": rumor_id,
            "topic": topic,
            "credibility_before": credibility_before,
            "credibility_after": credibility_after,
            "credibility_delta": credibility_after - credibility_before,
        }
        return self.record(
            tick=tick,
            event_type="RUMOR_SPREAD",
            payload=payload,
            ward_id=ward_id,
            agent_ids=[speaker_id, listener_id],
        )

    def log_facility_event(
        self,
        *,
        tick: int,
        ward_id: str,
        facility_id: str,
        event_kind: str,
        impact: Optional[str] = None,
    ) -> AdminEvent:
        """Record a FACILITY_EVENT (crackdown, shortage, fight, etc.)."""

        payload: MutableMapping[str, Any] = {"event_kind": event_kind}
        if impact:
            payload["impact"] = impact
        return self.record(
            tick=tick,
            event_type="FACILITY_EVENT",
            payload=payload,
            ward_id=ward_id,
            facility_id=facility_id,
            tags=[event_kind],
        )

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------
    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._events)

    def get_recent(
        self,
        *,
        event_type: Optional[str] = None,
        ward_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AdminEvent]:
        """Return the newest events matching the optional filters."""

        selected: List[AdminEvent] = []
        for event in reversed(self._events):
            if event_type and event.event_type != event_type:
                continue
            if ward_id and event.ward_id != ward_id:
                continue
            selected.append(event)
            if len(selected) >= limit:
                break
        return list(reversed(selected))

    def iter_all(self) -> Iterable[AdminEvent]:
        """Iterate over events in chronological order."""

        return tuple(self._events)

    def clear(self) -> None:
        self._events.clear()


__all__ = ["AdminEvent", "AdminEventLog"]

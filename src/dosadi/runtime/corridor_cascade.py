from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping

from dosadi.runtime.events import EventKind, ensure_event_bus
from dosadi.runtime.rng_service import RNGService, ensure_rng_service
from dosadi.world.incidents import Incident, IncidentKind
from dosadi.world.incidents import IncidentLedger


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class CorridorCascadeConfig:
    enabled: bool = True
    update_cadence_days: int = 1
    risk_window_days: int = 7
    health_decay_base: float = 0.002
    health_repair_base: float = 0.004
    degraded_threshold: float = 0.55
    closed_threshold: float = 0.35
    collapse_threshold: float = 0.20
    collapse_days: int = 7
    abandonment_days: int = 14
    escort_effect: float = 0.20
    enforcement_effect: float = 0.15
    maintenance_effect: float = 0.25
    rng_stream_prefix: str = "corridor:"


@dataclass(slots=True)
class CorridorCascadeState:
    health: float = 1.0
    risk: float = 0.0
    pressure: float = 0.0
    maintenance_debt: float = 0.0
    collapse_status: str = "ACTIVE"
    days_degraded: int = 0
    days_closed: int = 0
    consecutive_collapse_days: int = 0
    abandonment_days: int = 0
    recent_failures_7d: float = 0.0
    recent_success_7d: float = 0.0
    last_event_day: int = -1

    def signature(self) -> tuple:
        return (
            round(self.health, 6),
            round(self.risk, 6),
            round(self.pressure, 6),
            round(self.maintenance_debt, 6),
            self.collapse_status,
            self.days_degraded,
            self.days_closed,
            self.consecutive_collapse_days,
            self.abandonment_days,
            round(self.recent_failures_7d, 4),
            round(self.recent_success_7d, 4),
        )


@dataclass(slots=True)
class CorridorCascadeLedger:
    corridors: dict[str, CorridorCascadeState] = field(default_factory=dict)

    def signature(self) -> tuple:
        return tuple(
            (cid, state.signature()) for cid, state in sorted(self.corridors.items())
        )


def ensure_cascade_config(world: Any) -> CorridorCascadeConfig:
    cfg = getattr(world, "corridor_cascade_cfg", None)
    if not isinstance(cfg, CorridorCascadeConfig):
        cfg = CorridorCascadeConfig()
        setattr(world, "corridor_cascade_cfg", cfg)
    return cfg


def ensure_cascade_ledger(world: Any) -> CorridorCascadeLedger:
    ledger = getattr(world, "corridor_cascade", None)
    if not isinstance(ledger, CorridorCascadeLedger):
        ledger = CorridorCascadeLedger()
        setattr(world, "corridor_cascade", ledger)
    return ledger


def corridor_state(world: Any, corridor_id: str) -> CorridorCascadeState:
    ledger = ensure_cascade_ledger(world)
    if corridor_id not in ledger.corridors:
        ledger.corridors[corridor_id] = CorridorCascadeState()
    return ledger.corridors[corridor_id]


def corridor_status(world: Any, corridor_id: str) -> str:
    state = ensure_cascade_ledger(world).corridors.get(corridor_id)
    return state.collapse_status if state else "ACTIVE"


def _maintenance_investment(world: Any, corridor_id: str) -> float:
    mapping = getattr(world, "corridor_maintenance_investment", {}) or {}
    return _clamp01(float(mapping.get(corridor_id, 0.0)))


def _escort_level(world: Any, corridor_id: str) -> float:
    mapping = getattr(world, "corridor_escort_level", {}) or {}
    return _clamp01(float(mapping.get(corridor_id, 0.0)))


def _enforcement_presence(world: Any, corridor_id: str) -> float:
    mapping = getattr(world, "corridor_enforcement", {}) or {}
    return _clamp01(float(mapping.get(corridor_id, 0.0)))


def _decay_window(value: float, window_days: int) -> float:
    if window_days <= 1:
        return value
    decay = (window_days - 1) / float(window_days)
    return max(0.0, value * decay)


def record_delivery_outcome(
    world: Any, corridor_id: str, *, day: int, success: bool
) -> None:
    state = corridor_state(world, corridor_id)
    cfg = ensure_cascade_config(world)
    state.recent_failures_7d = _decay_window(state.recent_failures_7d, cfg.risk_window_days)
    state.recent_success_7d = _decay_window(state.recent_success_7d, cfg.risk_window_days)
    if success:
        state.recent_success_7d = min(cfg.risk_window_days, state.recent_success_7d + 1.0)
    else:
        state.recent_failures_7d = min(cfg.risk_window_days, state.recent_failures_7d + 1.0)
    state.last_event_day = day


def _emit_status_event(
    world: Any, *, corridor_id: str, day: int, status: str, payload: Mapping[str, object]
) -> None:
    bus = ensure_event_bus(world)
    bus.publish(
        kind=status,
        tick=getattr(world, "tick", 0),
        day=day,
        subject_id=corridor_id,
        payload=payload,
    )


def _record_incident(world: Any, *, day: int, corridor_id: str, status: str, severity: float) -> None:
    ledger: IncidentLedger = getattr(world, "incidents", IncidentLedger())
    world.incidents = ledger
    kind = IncidentKind.CORRIDOR_COLLAPSE if status == EventKind.CORRIDOR_COLLAPSED else IncidentKind.CORRIDOR_CLOSED
    seq = len(ledger.incidents)
    inc_id = f"inc:corridor:{status}:{corridor_id}:{day}:{seq}"
    incident = Incident(
        incident_id=inc_id,
        kind=kind,
        day=day,
        target_kind="corridor",
        target_id=corridor_id,
        severity=severity,
        payload={"status": status, "corridor_id": corridor_id},
    )
    ledger.add(incident)


def _effective_pressure(world: Any, corridor_id: str) -> float:
    stress = getattr(world, "corridor_stress", {}) or {}
    base_pressure = _clamp01(stress.get(corridor_id, 0.0))
    ledger = getattr(world, "risk_ledger", None)
    if ledger is not None:
        rec = getattr(ledger, "edges", {}).get(corridor_id)
        if rec is not None:
            base_pressure = max(base_pressure, _clamp01(getattr(rec, "risk", 0.0)))
    enforcement = _enforcement_presence(world, corridor_id)
    cfg = ensure_cascade_config(world)
    return _clamp01(base_pressure * (1.0 - cfg.enforcement_effect * enforcement))


def update_corridor_cascades(world: Any, day: int) -> None:
    cfg = ensure_cascade_config(world)
    if not getattr(cfg, "enabled", False):
        return

    ledger = ensure_cascade_ledger(world)
    survey_map = getattr(world, "survey_map", None)
    corridor_ids = list(getattr(survey_map, "edges", {}).keys()) if survey_map else list(ledger.corridors.keys())
    rng_service: RNGService = ensure_rng_service(world)

    for corridor_id in sorted(set(corridor_ids)):
        state = corridor_state(world, corridor_id)
        prev_status = state.collapse_status
        state.recent_failures_7d = _decay_window(state.recent_failures_7d, cfg.risk_window_days)
        state.recent_success_7d = _decay_window(state.recent_success_7d, cfg.risk_window_days)

        maintenance = _maintenance_investment(world, corridor_id)
        escort = _escort_level(world, corridor_id)
        state.pressure = _effective_pressure(world, corridor_id)
        state.maintenance_debt = _clamp01(
            state.maintenance_debt + 0.1 * state.pressure - cfg.maintenance_effect * maintenance
        )
        state.risk = _clamp01(0.6 * state.pressure + 0.4 * state.maintenance_debt)
        state.health = _clamp01(
            state.health
            - cfg.health_decay_base * (1.0 + state.pressure + state.maintenance_debt)
            + cfg.health_repair_base * maintenance
        )

        escort_mitigation = cfg.escort_effect * escort
        if escort_mitigation > 0:
            state.risk = _clamp01(state.risk * (1.0 - escort_mitigation))

        if state.health < cfg.degraded_threshold:
            state.days_degraded += 1
        else:
            state.days_degraded = 0

        if state.health < cfg.closed_threshold:
            state.days_closed += 1
        else:
            state.days_closed = 0

        if state.health < cfg.collapse_threshold:
            state.consecutive_collapse_days += 1
        else:
            state.consecutive_collapse_days = 0

        abandonment = state.recent_success_7d <= 0.1 and state.risk >= 0.5
        state.abandonment_days = state.abandonment_days + 1 if abandonment else 0

        status = "ACTIVE"
        if state.health < cfg.degraded_threshold or state.days_degraded > 0:
            status = "DEGRADED"
        if state.health < cfg.closed_threshold or state.days_closed > 0:
            status = "CLOSED"
        if state.consecutive_collapse_days >= cfg.collapse_days or state.abandonment_days >= cfg.abandonment_days:
            status = "COLLAPSED"

        state.collapse_status = status
        collapsed_set: set[str] = getattr(world, "collapsed_corridors", set())
        if status == "COLLAPSED":
            collapsed_set.add(corridor_id)
        else:
            collapsed_set.discard(corridor_id)
        world.collapsed_corridors = collapsed_set

        if status != prev_status:
            reason = "PRESSURE" if state.pressure >= state.maintenance_debt else "MAINT_DEBT"
            if state.abandonment_days >= cfg.abandonment_days:
                reason = "ABANDONMENT"
            payload = {
                "corridor_id": corridor_id,
                "health": round(state.health, 4),
                "risk": round(state.risk, 4),
                "pressure": round(state.pressure, 4),
                "failures": round(state.recent_failures_7d, 4),
                "success": round(state.recent_success_7d, 4),
                "reason": reason,
            }
            event_kind = {
                "DEGRADED": EventKind.CORRIDOR_DEGRADED,
                "CLOSED": EventKind.CORRIDOR_CLOSED,
                "COLLAPSED": EventKind.CORRIDOR_COLLAPSED,
            }.get(status)
            if event_kind:
                _emit_status_event(world, corridor_id=corridor_id, day=day, status=event_kind, payload=payload)
                severity = max(0.1, 1.0 - state.health)
                if event_kind in {EventKind.CORRIDOR_CLOSED, EventKind.CORRIDOR_COLLAPSED}:
                    _record_incident(world, day=day, corridor_id=corridor_id, status=event_kind, severity=severity)

        rng_service.rand(
            f"{cfg.rng_stream_prefix}update",
            scope={"corridor_id": corridor_id, "day": day, "status": state.collapse_status},
        )


__all__ = [
    "CorridorCascadeConfig",
    "CorridorCascadeLedger",
    "CorridorCascadeState",
    "corridor_state",
    "corridor_status",
    "ensure_cascade_config",
    "ensure_cascade_ledger",
    "record_delivery_outcome",
    "update_corridor_cascades",
]

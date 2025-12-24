from __future__ import annotations

from dataclasses import dataclass
import heapq
import random
from hashlib import sha256
from typing import Any, Dict, Iterable, List, MutableMapping

from dosadi.world.facilities import FacilityLedger, ensure_facility_ledger
from dosadi.world.incidents import Incident, IncidentKind, IncidentLedger
from dosadi.world.logistics import DeliveryStatus, LogisticsLedger, release_courier
from dosadi.world.phases import WorldPhase
from dosadi.world.events import EventKind, WorldEvent, WorldEventLog


@dataclass(slots=True)
class IncidentConfig:
    enabled: bool = True
    max_incidents_per_day: int = 2
    history_limit: int = 2000
    p_delivery_loss_p0: float = 0.000
    p_delivery_loss_p1: float = 0.002
    p_delivery_loss_p2: float = 0.010
    p_delivery_delay_p2: float = 0.020
    p_facility_downtime_p2: float = 0.005
    delay_days_min: int = 1
    delay_days_max: int = 5
    downtime_days_min: int = 2
    downtime_days_max: int = 10


@dataclass(slots=True)
class IncidentState:
    last_run_day: int = -1
    next_incident_seq: int = 0


def _seed_int(*parts: object) -> int:
    blob = ":".join(str(part) for part in parts)
    return int(sha256(blob.encode("utf-8")).hexdigest(), 16) % (2**32)


def _derived_rng(*parts: object) -> random.Random:
    return random.Random(_seed_int(*parts))


def _ensure_ledger(world: Any) -> IncidentLedger:
    ledger: IncidentLedger = getattr(world, "incidents", None) or IncidentLedger()
    world.incidents = ledger
    return ledger


def _ensure_event_log(world: Any) -> WorldEventLog:
    log: WorldEventLog | None = getattr(world, "event_log", None)
    if not isinstance(log, WorldEventLog):
        log = WorldEventLog(max_len=5000)
        world.event_log = log
    return log


def _phase(world: Any) -> WorldPhase:
    state = getattr(world, "phase_state", None)
    if state is None:
        return WorldPhase.PHASE0
    phase = getattr(state, "phase", None)
    try:
        return WorldPhase(phase)
    except Exception:
        return WorldPhase.PHASE0


def _ticks_per_day(world: Any) -> int:
    cfg = getattr(world, "config", None)
    ticks = getattr(cfg, "ticks_per_day", None) if cfg is not None else None
    if ticks is None:
        ticks = getattr(world, "ticks_per_day", None)
    try:
        ticks_int = int(ticks)
    except Exception:
        ticks_int = None
    return max(1, ticks_int or 144_000)


def _bounded_candidates(candidates: Iterable[str], max_count: int, seed: int) -> List[str]:
    ids = list(sorted(set(candidates)))
    if not ids:
        return []
    rng = random.Random(seed)
    if len(ids) <= max_count:
        return ids
    return rng.sample(ids, max_count)


def _incident_id(day: int, *, seq: int) -> str:
    return f"inc:{day}:{seq}"


def _add_history(ledger: IncidentLedger, inc_id: str, *, history_limit: int) -> None:
    ledger.history.append(inc_id)
    if history_limit > 0 and len(ledger.history) > history_limit:
        ledger.history[:] = ledger.history[-history_limit:]


def _emit_event(world: Any, incident: Incident) -> None:
    log = _ensure_event_log(world)
    event = WorldEvent(
        event_id="",
        day=getattr(world, "day", 0),
        kind=EventKind.INCIDENT,
        subject_kind=incident.target_kind,
        subject_id=incident.target_id,
        severity=incident.severity,
        payload={
            "incident_id": incident.incident_id,
            "incident_kind": incident.kind.value,
            "target_kind": incident.target_kind,
            "target_id": incident.target_id,
            "severity": incident.severity,
        },
    )
    log.append(event)
    legacy_events = getattr(world, "events", None)
    if isinstance(legacy_events, list):
        legacy_events.append(
            {
                "day": event.day,
                "kind": event.kind.value,
                "incident_id": incident.incident_id,
                "incident_kind": incident.kind.value,
                "target_kind": incident.target_kind,
                "target_id": incident.target_id,
                "severity": incident.severity,
            }
        )
        world.events = legacy_events


def _emit_facility_state_event(world: Any, *, facility_id: str, kind: EventKind, payload: Dict[str, object]) -> None:
    log = _ensure_event_log(world)
    event = WorldEvent(
        event_id="",
        day=getattr(world, "day", 0),
        kind=kind,
        subject_kind="facility",
        subject_id=facility_id,
        severity=float(payload.get("severity", 0.0)),
        payload=payload,
    )
    log.append(event)


def _schedule_delivery_incidents(
    *,
    world: Any,
    cfg: IncidentConfig,
    ledger: IncidentLedger,
    state: IncidentState,
    day: int,
    phase: WorldPhase,
) -> int:
    logistics: LogisticsLedger | None = getattr(world, "logistics", None)
    if logistics is None:
        return 0

    active_status = {
        DeliveryStatus.REQUESTED,
        DeliveryStatus.ASSIGNED,
        DeliveryStatus.PICKED_UP,
        DeliveryStatus.IN_TRANSIT,
    }
    candidates = [
        delivery_id
        for delivery_id in logistics.active_ids
        if logistics.deliveries.get(delivery_id, None)
        and logistics.deliveries[delivery_id].status in active_status
    ]
    base_seed = getattr(world, "seed", 0)
    bound = max(1, cfg.max_incidents_per_day * 10)
    sampled = _bounded_candidates(candidates, bound, _seed_int(base_seed, day, "deliveries"))
    scheduled = 0

    for delivery_id in sampled:
        if scheduled >= cfg.max_incidents_per_day:
            break
        delivery = logistics.deliveries.get(delivery_id)
        if delivery is None:
            continue

        per_target_seed = _seed_int(base_seed, day, delivery_id)
        rng = _derived_rng(per_target_seed, "incident-engine", "delivery")
        severity = rng.random()

        if phase == WorldPhase.PHASE2:
            if rng.random() < cfg.p_delivery_delay_p2:
                state.next_incident_seq += 1
                inc = Incident(
                    incident_id=_incident_id(day, seq=state.next_incident_seq),
                    kind=IncidentKind.DELIVERY_DELAY,
                    day=day,
                    target_kind="delivery",
                    target_id=delivery_id,
                    severity=severity,
                    created_day=day,
                )
                ledger.add(inc)
                scheduled += 1
                continue

        prob_loss = {
            WorldPhase.PHASE0: cfg.p_delivery_loss_p0,
            WorldPhase.PHASE1: cfg.p_delivery_loss_p1,
            WorldPhase.PHASE2: cfg.p_delivery_loss_p2,
        }.get(phase, cfg.p_delivery_loss_p0)

        if rng.random() < prob_loss:
            state.next_incident_seq += 1
            inc = Incident(
                incident_id=_incident_id(day, seq=state.next_incident_seq),
                kind=IncidentKind.DELIVERY_LOSS,
                day=day,
                target_kind="delivery",
                target_id=delivery_id,
                severity=severity,
                created_day=day,
            )
            ledger.add(inc)
            scheduled += 1

    return scheduled


def _schedule_facility_incidents(
    *,
    world: Any,
    cfg: IncidentConfig,
    ledger: IncidentLedger,
    state: IncidentState,
    day: int,
    phase: WorldPhase,
    remaining_budget: int,
) -> int:
    if phase != WorldPhase.PHASE2 or remaining_budget <= 0:
        return 0

    facilities: FacilityLedger = ensure_facility_ledger(world)
    candidates = [fid for fid, fac in facilities.items() if getattr(fac, "status", "ACTIVE") == "ACTIVE"]
    base_seed = getattr(world, "seed", 0)
    bound = max(1, cfg.max_incidents_per_day * 10)
    sampled = _bounded_candidates(candidates, bound, _seed_int(base_seed, day, "facilities"))
    scheduled = 0

    for facility_id in sampled:
        if scheduled >= remaining_budget:
            break
        rng = _derived_rng(base_seed, day, facility_id, "facility")
        severity = rng.random()
        if rng.random() >= cfg.p_facility_downtime_p2:
            continue

        state.next_incident_seq += 1
        inc = Incident(
            incident_id=_incident_id(day, seq=state.next_incident_seq),
            kind=IncidentKind.FACILITY_DOWNTIME,
            day=day,
            target_kind="facility",
            target_id=facility_id,
            severity=severity,
            created_day=day,
        )
        ledger.add(inc)
        scheduled += 1

    return scheduled


def _update_delivery_queue(world: Any, delivery: DeliveryRequest) -> None:
    queue: List[tuple[int, str]] = getattr(world, "delivery_due_queue", []) or []
    filtered = [(tick, did) for tick, did in queue if did != delivery.delivery_id]
    heapq.heapify(filtered)
    due_tick = delivery.next_edge_complete_tick or delivery.deliver_tick
    if due_tick is not None:
        heapq.heappush(filtered, (due_tick, delivery.delivery_id))
    world.delivery_due_queue = filtered


def _resolve_delivery_loss(world: Any, *, incident: Incident, day: int) -> None:
    logistics: LogisticsLedger | None = getattr(world, "logistics", None)
    if logistics is None:
        return

    delivery = logistics.deliveries.get(incident.target_id)
    if delivery is None:
        return

    if delivery.status in {DeliveryStatus.ASSIGNED, DeliveryStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT}:
        if delivery.assigned_carrier_id:
            release_courier(world, delivery.assigned_carrier_id)
        delivery.status = DeliveryStatus.FAILED
        delivery.deliver_tick = None
        fraction = max(0.0, min(1.0, incident.severity))
        incident.payload["lost_items"] = {
            item: qty * fraction for item, qty in delivery.items.items()
        }
        delivery.notes["incident"] = "delivery_loss"


def _resolve_delivery_delay(
    world: Any, *, incident: Incident, day: int, cfg: IncidentConfig
) -> None:
    logistics: LogisticsLedger | None = getattr(world, "logistics", None)
    if logistics is None:
        return

    delivery = logistics.deliveries.get(incident.target_id)
    if delivery is None:
        return

    if delivery.status not in {DeliveryStatus.ASSIGNED, DeliveryStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT}:
        return

    ticks_per_day = _ticks_per_day(world)
    delay_range = max(0, cfg.delay_days_max - cfg.delay_days_min)
    delay_days = cfg.delay_days_min + int(incident.severity * delay_range)
    delay_days = max(cfg.delay_days_min, min(cfg.delay_days_max, delay_days))
    incident.payload["delay_days"] = delay_days
    if delivery.deliver_tick is None:
        delivery.deliver_tick = getattr(world, "tick", 0)
    delivery.deliver_tick += delay_days * ticks_per_day
    delivery.notes["incident"] = "delivery_delay"
    _update_delivery_queue(world, delivery)


def _resolve_facility_downtime(
    world: Any, *, incident: Incident, day: int, cfg: IncidentConfig
) -> None:
    facilities: FacilityLedger = ensure_facility_ledger(world)
    facility = facilities.get(incident.target_id)
    if facility is None:
        return

    downtime_range = max(0, cfg.downtime_days_max - cfg.downtime_days_min)
    downtime_days = cfg.downtime_days_min + int(incident.severity * downtime_range)
    downtime_days = max(cfg.downtime_days_min, min(cfg.downtime_days_max, downtime_days))
    incident.payload["downtime_days"] = downtime_days
    down_until = day + downtime_days
    facility.status = "INACTIVE"
    facility.is_operational = False
    facility.down_until_day = down_until
    facility.state["reactivate_day"] = down_until
    _emit_facility_state_event(
        world,
        facility_id=facility.facility_id,
        kind=EventKind.FACILITY_DOWNTIME,
        payload={
            "incident_id": incident.incident_id,
            "downtime_days": downtime_days,
            "severity": incident.severity,
            "target_id": facility.facility_id,
        },
    )


def _reactivate_facilities(world: Any, *, day: int) -> None:
    facilities: FacilityLedger = ensure_facility_ledger(world)
    for facility in facilities.values():
        reactivate_day = facility.state.get("reactivate_day") if isinstance(facility.state, dict) else None
        down_until = facility.down_until_day
        should_reactivate = False
        if reactivate_day is not None and day >= reactivate_day:
            should_reactivate = True
        if down_until >= 0 and day > down_until:
            should_reactivate = True
        if should_reactivate:
            facility.state.pop("reactivate_day", None)
            facility.status = "ACTIVE"
            facility.is_operational = True
            facility.down_until_day = -1
            _emit_facility_state_event(
                world,
                facility_id=facility.facility_id,
                kind=EventKind.FACILITY_REACTIVATED,
                payload={"target_id": facility.facility_id, "severity": 0.0},
            )


def run_incident_engine_for_day(world: Any, *, day: int) -> None:
    cfg: IncidentConfig = getattr(world, "incident_cfg", None) or IncidentConfig()
    state: IncidentState = getattr(world, "incident_state", None) or IncidentState()
    world.incident_cfg = cfg
    world.incident_state = state
    ledger = _ensure_ledger(world)

    if not cfg.enabled:
        return
    if state.last_run_day == day:
        return

    _reactivate_facilities(world, day=day)
    phase = _phase(world)

    # Slice B: scheduling
    scheduled = _schedule_delivery_incidents(
        world=world, cfg=cfg, ledger=ledger, state=state, day=day, phase=phase
    )
    remaining = max(0, cfg.max_incidents_per_day - scheduled)
    _schedule_facility_incidents(
        world=world,
        cfg=cfg,
        ledger=ledger,
        state=state,
        day=day,
        phase=phase,
        remaining_budget=remaining,
    )

    due_ids = ledger.due_ids(day)
    for inc_id in due_ids:
        incident = ledger.incidents.get(inc_id)
        if incident is None or incident.resolved:
            continue

        match incident.kind:
            case IncidentKind.DELIVERY_LOSS:
                _resolve_delivery_loss(world, incident=incident, day=day)
            case IncidentKind.DELIVERY_DELAY:
                _resolve_delivery_delay(world, incident=incident, day=day, cfg=cfg)
            case IncidentKind.FACILITY_DOWNTIME:
                _resolve_facility_downtime(world, incident=incident, day=day, cfg=cfg)
            case _:
                pass

        incident.resolved = True
        incident.resolved_day = day
        _add_history(ledger, inc_id, history_limit=cfg.history_limit)
        _emit_event(world, incident)

    state.last_run_day = day


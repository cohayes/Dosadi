from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import heapq
from hashlib import sha256
from typing import Any, Iterable, MutableMapping

from typing import TYPE_CHECKING

from dosadi.world.events import EventKind, WorldEvent, WorldEventLog
from dosadi.world.workforce import AssignmentKind, WorkforceLedger, ensure_workforce

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from dosadi.world.logistics import DeliveryStatus


class InteractionKind(Enum):
    HELP = "HELP"
    CONFLICT = "CONFLICT"
    SABOTAGE = "SABOTAGE"
    ESCORT = "ESCORT"


@dataclass(slots=True)
class InteractionConfig:
    enabled: bool = False
    max_interactions_per_day: int = 50
    max_candidates_per_opportunity: int = 12
    escort_enabled: bool = True
    theft_enabled: bool = True
    delay_ticks_min: int = 200
    delay_ticks_max: int = 2000
    sabotage_fail_chance: float = 0.35
    help_reduce_delay_factor: float = 0.50
    conflict_delay_factor: float = 1.25


@dataclass(slots=True)
class InteractionOpportunity:
    day: int
    tick: int
    kind: str
    node_id: str | None
    edge_key: str | None
    primary_agent_id: str | None
    subject_id: str | None
    severity: float = 0.0
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class InteractionResult:
    interaction_id: str
    kind: InteractionKind
    actors: list[str]
    node_id: str | None
    edge_key: str | None
    subject_id: str | None
    delay_ticks: int = 0
    delivery_failed: bool = False
    stolen_units: int = 0
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class InteractionState:
    last_run_day: int = -1
    count_today: int = 0


def hashed_unit_float(*parts: str) -> float:
    blob = "|".join(str(p) for p in parts)
    digest = sha256(blob.encode("utf-8")).hexdigest()[:8]
    value = int(digest, 16)
    return value / float(2**32)


def _interaction_metrics(world: Any) -> MutableMapping[str, float]:
    metrics: MutableMapping[str, float] = getattr(world, "metrics", {})
    world.metrics = metrics
    return metrics.setdefault("interactions", {})  # type: ignore[arg-type]


def ensure_interaction_config(world: Any) -> InteractionConfig:
    cfg = getattr(world, "interaction_cfg", None)
    if not isinstance(cfg, InteractionConfig):
        cfg = InteractionConfig()
        setattr(world, "interaction_cfg", cfg)
    return cfg


def ensure_interaction_state(world: Any) -> InteractionState:
    state = getattr(world, "interaction_state", None)
    if not isinstance(state, InteractionState):
        state = InteractionState()
        setattr(world, "interaction_state", state)
    return state


def _ensure_queue(world: Any) -> list[InteractionOpportunity]:
    queue = getattr(world, "interaction_queue", None)
    if not isinstance(queue, list):
        queue = []
        setattr(world, "interaction_queue", queue)
    return queue


def _maybe_enqueue_site_opportunities(world: Any, *, day: int, cfg: InteractionConfig) -> None:
    if not cfg.enabled:
        return

    queue = _ensure_queue(world)
    existing = {(opp.kind, opp.subject_id) for opp in queue if opp.day == day}
    ledger = ensure_workforce(world)

    projects = getattr(getattr(world, "projects", None), "projects", {}) or {}
    facilities = getattr(getattr(world, "facilities", None), "facilities", {}) or {}

    for assignment in ledger.assignments.values():
        if assignment.target_id is None:
            continue
        kind: str | None = None
        node_id: str | None = None
        if assignment.kind is AssignmentKind.PROJECT_WORK:
            kind = "project_site"
            project = projects.get(assignment.target_id)
            node_id = getattr(project, "site_node_id", None)
        elif assignment.kind is AssignmentKind.FACILITY_STAFF:
            kind = "facility_site"
            facility = facilities.get(assignment.target_id)
            node_id = getattr(facility, "site_node_id", None)
        if kind is None:
            continue
        key = (kind, assignment.target_id)
        if key in existing:
            continue
        if len(queue) >= cfg.max_interactions_per_day:
            break
        existing.add(key)
        opp = InteractionOpportunity(
            day=day,
            tick=getattr(world, "tick", 0),
            kind=kind,
            node_id=node_id,
            edge_key=None,
            primary_agent_id=assignment.agent_id,
            subject_id=str(assignment.target_id),
            severity=0.0,
            payload={},
        )
        queue.append(opp)


def enqueue_interaction_opportunity(world: Any, opp: InteractionOpportunity) -> None:
    cfg = ensure_interaction_config(world)
    if not cfg.enabled:
        return

    queue = _ensure_queue(world)
    if len(queue) >= max(1, cfg.max_interactions_per_day * 2):
        return
    queue.append(opp)
    metrics = _interaction_metrics(world)
    metrics["opportunities"] = metrics.get("opportunities", 0.0) + 1


def _candidate_agents_from_assignments(
    ledger: WorkforceLedger, subject_id: str | None, target_kinds: set[AssignmentKind]
) -> set[str]:
    if subject_id is None:
        return set()
    return {
        agent_id
        for agent_id, assignment in ledger.assignments.items()
        if assignment.kind in target_kinds and assignment.target_id == subject_id
    }


def resolve_candidates(world: Any, opp: InteractionOpportunity, cfg: InteractionConfig | None = None) -> list[str]:
    cfg = cfg or ensure_interaction_config(world)
    ledger = ensure_workforce(world)
    candidates: set[str] = set()

    if opp.primary_agent_id:
        candidates.add(str(opp.primary_agent_id))

    target_kinds: set[AssignmentKind] = set()
    if opp.kind == "project_site":
        target_kinds.add(AssignmentKind.PROJECT_WORK)
    elif opp.kind == "facility_site":
        target_kinds.add(AssignmentKind.FACILITY_STAFF)
    elif opp.kind in {"courier_edge", "courier_arrival"}:
        target_kinds.add(AssignmentKind.LOGISTICS_COURIER)

    candidates.update(_candidate_agents_from_assignments(ledger, opp.subject_id, target_kinds))

    if opp.node_id:
        agents = getattr(world, "agents", {}) or {}
        for agent_id, agent in agents.items():
            if getattr(agent, "location_id", None) == opp.node_id:
                candidates.add(str(agent_id))
                if len(candidates) >= cfg.max_candidates_per_opportunity:
                    break

    ordered = sorted(candidates)
    return ordered[: cfg.max_candidates_per_opportunity]


def _pick_roles(candidates: list[str]) -> tuple[str | None, list[str], str | None]:
    if not candidates:
        return None, [], None
    actor = candidates[0]
    others = candidates[1:]
    adversary = None
    if others:
        draw = hashed_unit_float("adversary", actor, *others)
        adversary = others[int(draw * len(others))]
    return actor, others, adversary


def _bounded_delay(cfg: InteractionConfig, draw: float, *, factor: float = 1.0) -> int:
    span = max(0, cfg.delay_ticks_max - cfg.delay_ticks_min)
    base = cfg.delay_ticks_min + int(draw * span)
    delay = int(base * factor)
    return max(cfg.delay_ticks_min, min(cfg.delay_ticks_max, delay))


def _apply_delivery_delay(world: Any, delivery_id: str, delay_ticks: int) -> None:
    if delay_ticks == 0:
        return

    from dosadi.world.logistics import ensure_logistics

    logistics = ensure_logistics(world)
    delivery = logistics.deliveries.get(delivery_id)
    if delivery is None:
        return

    if delivery.next_edge_complete_tick is not None:
        delivery.next_edge_complete_tick = max(0, delivery.next_edge_complete_tick + delay_ticks)
    delivery.remaining_edge_ticks = max(0, delivery.remaining_edge_ticks + delay_ticks)
    if delivery.deliver_tick is not None:
        delivery.deliver_tick = max(0, delivery.deliver_tick + delay_ticks)

    queue = getattr(world, "delivery_due_queue", [])
    new_queue = []
    found = False
    for due_tick, did in queue:
        if did == delivery_id:
            found = True
            new_queue.append((max(0, due_tick + delay_ticks), did))
        else:
            new_queue.append((due_tick, did))
    if not found and delivery.next_edge_complete_tick is not None:
        new_queue.append((delivery.next_edge_complete_tick, delivery_id))
    heapq.heapify(new_queue)
    world.delivery_due_queue = new_queue


def _fail_delivery(world: Any, delivery_id: str, *, tick: int, reason: str) -> None:
    from dosadi.world.logistics import DeliveryStatus, ensure_logistics, release_courier

    logistics = ensure_logistics(world)
    delivery = logistics.deliveries.get(delivery_id)
    if delivery is None:
        return

    delivery.status = DeliveryStatus.FAILED
    delivery.deliver_tick = tick
    delivery.notes["failure"] = reason
    delivery.next_edge_complete_tick = None
    delivery.remaining_edge_ticks = 0
    release_courier(world, delivery.assigned_carrier_id)

    queue = getattr(world, "delivery_due_queue", [])
    queue = [(due, did) for due, did in queue if did != delivery_id]
    heapq.heapify(queue)
    world.delivery_due_queue = queue


def _apply_theft(world: Any, delivery_id: str, units: int) -> int:
    if units <= 0:
        return 0

    from dosadi.world.logistics import ensure_logistics

    logistics = ensure_logistics(world)
    delivery = logistics.deliveries.get(delivery_id)
    if delivery is None:
        return 0

    remaining = units
    for item in sorted(delivery.items.keys()):
        if remaining <= 0:
            break
        available = delivery.items.get(item, 0.0)
        take = min(available, float(remaining))
        delivery.items[item] = max(0.0, available - take)
        remaining -= int(take)
    return units - remaining


def _subject_kind_for(opp: InteractionOpportunity) -> str:
    if opp.kind.startswith("courier"):
        return "delivery"
    if opp.kind.startswith("project"):
        return "project"
    if opp.kind.startswith("facility"):
        return "facility"
    return "unknown"


def _resolve_interaction(
    world: Any, opp: InteractionOpportunity, candidates: list[str], cfg: InteractionConfig
) -> InteractionResult | None:
    actor, others, adversary = _pick_roles(candidates)
    if actor is None:
        return None

    escort_present = bool(opp.payload.get("escort_present"))
    hazard = 0.0
    survey_map = getattr(world, "survey_map", None)
    if opp.edge_key and survey_map and hasattr(survey_map, "edges"):
        edge = survey_map.edges.get(opp.edge_key)
        if edge is not None:
            hazard = max(0.0, float(getattr(edge, "hazard", 0.0) or 0.0))

    draw = hashed_unit_float("interaction", opp.day, opp.kind, opp.subject_id or "-", opp.edge_key or "-", actor)
    hazard_boost = min(0.2, hazard * 0.1)
    sabotage_thresh = 0.10 + hazard_boost
    conflict_thresh = 0.25 + hazard_boost
    help_thresh = 0.45
    if escort_present:
        sabotage_thresh = max(0.0, sabotage_thresh - 0.05)
        conflict_thresh = max(sabotage_thresh + 0.05, conflict_thresh - 0.05)

    chosen: InteractionKind | None = None
    if draw < sabotage_thresh:
        chosen = InteractionKind.SABOTAGE
    elif draw < conflict_thresh:
        chosen = InteractionKind.CONFLICT
    elif draw < help_thresh:
        chosen = InteractionKind.HELP
    elif cfg.escort_enabled and escort_present:
        chosen = InteractionKind.ESCORT

    if chosen is None:
        return None

    result = InteractionResult(
        interaction_id=f"iact:{opp.day}:{opp.tick}:{opp.subject_id or 'none'}",
        kind=chosen,
        actors=[actor, *others],
        node_id=opp.node_id,
        edge_key=opp.edge_key,
        subject_id=opp.subject_id,
    )

    delay_draw = hashed_unit_float("delay", opp.day, opp.kind, opp.subject_id or "-", opp.edge_key or "-", actor)
    if chosen is InteractionKind.HELP:
        base_delay = _bounded_delay(cfg, delay_draw)
        result.delay_ticks = -int(base_delay * cfg.help_reduce_delay_factor)
        if others:
            result.payload["helper_id"] = others[0]
    elif chosen is InteractionKind.CONFLICT:
        result.delay_ticks = _bounded_delay(cfg, delay_draw, factor=cfg.conflict_delay_factor)
    elif chosen is InteractionKind.SABOTAGE:
        result.delay_ticks = _bounded_delay(cfg, delay_draw)
        success_draw = hashed_unit_float("sabotage", opp.day, opp.kind, opp.subject_id or "-", actor)
        if success_draw < cfg.sabotage_fail_chance:
            fail_draw = hashed_unit_float("sabotage_fail", opp.day, opp.subject_id or "-", actor)
            if fail_draw < 0.5:
                result.delivery_failed = True
            elif cfg.theft_enabled:
                result.stolen_units = max(1, int(1 + fail_draw * 2))
    elif chosen is InteractionKind.ESCORT:
        result.payload["escort_tag"] = f"escort:{opp.edge_key}" if opp.edge_key else "escort"

    return result


def _emit_event(
    world: Any, *, day: int, opp: InteractionOpportunity, result: InteractionResult, cfg: InteractionConfig
) -> None:
    log: WorldEventLog | None = getattr(world, "event_log", None)
    if not isinstance(log, WorldEventLog):
        log = WorldEventLog(max_len=5000)
        setattr(world, "event_log", log)

    subject_kind = _subject_kind_for(opp)
    payload = {
        "interaction_kind": result.kind.value,
        "incident_kind": result.kind.value,
        "target_kind": subject_kind,
        "target_id": opp.subject_id or "unknown",
        "edge_key": opp.edge_key,
        "node_id": opp.node_id,
        "actors": list(result.actors),
        "delay_ticks": result.delay_ticks,
        "stolen_units": result.stolen_units,
        "delivery_failed": result.delivery_failed,
    }
    payload.update(result.payload)

    event = WorldEvent(
        event_id=result.interaction_id,
        day=day,
        kind=EventKind.INCIDENT,
        subject_kind=subject_kind,
        subject_id=opp.subject_id or "unknown",
        severity=min(1.0, max(0.0, abs(result.delay_ticks) / max(1.0, cfg.delay_ticks_max))),
        payload=payload,
    )
    log.append(event)


def run_interactions_for_day(world: Any, *, day: int) -> None:
    cfg = ensure_interaction_config(world)
    if not cfg.enabled:
        return

    state = ensure_interaction_state(world)
    if state.last_run_day != day:
        state.last_run_day = day
        state.count_today = 0

    _maybe_enqueue_site_opportunities(world, day=day, cfg=cfg)
    queue = [opp for opp in _ensure_queue(world) if opp.day == day]
    queue.sort(key=lambda opp: (opp.tick, opp.kind, opp.subject_id or "", opp.edge_key or "", opp.primary_agent_id or ""))
    world.interaction_queue = []

    metrics = _interaction_metrics(world)

    for opp in queue:
        if state.count_today >= cfg.max_interactions_per_day:
            break
        candidates = resolve_candidates(world, opp, cfg)
        result = _resolve_interaction(world, opp, candidates, cfg)
        if result is None:
            continue

        state.count_today += 1
        metrics["resolved"] = metrics.get("resolved", 0.0) + 1
        metrics_key = result.kind.value.lower()
        metrics[metrics_key] = metrics.get(metrics_key, 0.0) + 1

        if result.delay_ticks != 0 and opp.subject_id:
            _apply_delivery_delay(world, opp.subject_id, result.delay_ticks)
            metrics["delays_total_ticks"] = metrics.get("delays_total_ticks", 0.0) + result.delay_ticks
        if result.delivery_failed and opp.subject_id:
            _fail_delivery(world, opp.subject_id, tick=getattr(world, "tick", 0), reason="interaction")
            metrics["deliveries_failed"] = metrics.get("deliveries_failed", 0.0) + 1
        if result.stolen_units > 0 and opp.subject_id:
            actual = _apply_theft(world, opp.subject_id, result.stolen_units)
            result.stolen_units = actual

        _emit_event(world, day=day, opp=opp, result=result, cfg=cfg)

    world.interaction_state = state


__all__ = [
    "InteractionKind",
    "InteractionConfig",
    "InteractionOpportunity",
    "InteractionResult",
    "InteractionState",
    "hashed_unit_float",
    "enqueue_interaction_opportunity",
    "resolve_candidates",
    "run_interactions_for_day",
    "ensure_interaction_config",
    "ensure_interaction_state",
]

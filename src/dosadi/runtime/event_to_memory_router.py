from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Set

from dosadi.agent.memory_crumbs import CrumbStore
from dosadi.agent.memory_episodes import Episode, EpisodeBuffer
from dosadi.agent.memory_stm import STMBoringWinner
from dosadi.world.events import EventKind, WorldEvent, WorldEventLog
from dosadi.world.workforce import AssignmentKind, WorkforceLedger, ensure_workforce


@dataclass(slots=True)
class RouterConfig:
    enabled: bool = True
    max_events_per_day: int = 500
    episode_salience_threshold: float = 0.65
    stm_k: int = 24
    crumb_half_life_days: int = 30
    max_stakeholders_per_event: int = 20


@dataclass(slots=True)
class RouterState:
    cursor_seq: int = 0
    last_run_day: int = -1


def _ensure_event_log(world: Any, *, max_len: int = 5000) -> WorldEventLog:
    log: WorldEventLog | None = getattr(world, "event_log", None)
    if not isinstance(log, WorldEventLog):
        log = WorldEventLog(max_len=max_len)
        setattr(world, "event_log", log)
    return log


def _ensure_router_state(world: Any) -> RouterState:
    state: RouterState | None = getattr(world, "router_state", None)
    if not isinstance(state, RouterState):
        state = RouterState()
        setattr(world, "router_state", state)
    return state


def _ensure_router_config(world: Any) -> RouterConfig:
    cfg: RouterConfig | None = getattr(world, "router_config", None)
    if not isinstance(cfg, RouterConfig):
        cfg = RouterConfig()
        setattr(world, "router_config", cfg)
    return cfg


def _bounded(items: Iterable[str], limit: int) -> List[str]:
    unique = sorted(set(items))
    return unique[: max(0, limit)]


def _ensure_agents_with_new_signals(world: Any) -> set[str]:
    signaled = getattr(world, "agents_with_new_signals", None)
    if not isinstance(signaled, set):
        signaled = set(signaled or [])
        setattr(world, "agents_with_new_signals", signaled)
    return signaled


def _resolve_delivery_stakeholders(
    *,
    world: Any,
    workforce: WorkforceLedger,
    subject_id: str,
    max_count: int,
) -> List[str]:
    stakeholders: Set[str] = set()
    for assignment in workforce.assignments.values():
        if assignment.kind is AssignmentKind.LOGISTICS_COURIER and assignment.target_id == subject_id:
            stakeholders.add(assignment.agent_id)
        if assignment.kind is AssignmentKind.PROJECT_WORK and assignment.target_id:
            stakeholders.add(assignment.agent_id)
    steward_ids = getattr(world, "ward_stewards", None)
    if isinstance(steward_ids, Sequence):
        stakeholders.update(str(s) for s in steward_ids)
    return _bounded(stakeholders, max_count)


def _resolve_project_stakeholders(
    *, workforce: WorkforceLedger, project_id: str, max_count: int
) -> List[str]:
    stakeholders: Set[str] = set()
    for assignment in workforce.assignments.values():
        if assignment.kind is AssignmentKind.PROJECT_WORK and assignment.target_id == project_id:
            stakeholders.add(assignment.agent_id)
    return _bounded(stakeholders, max_count)


def _resolve_facility_stakeholders(
    *, workforce: WorkforceLedger, facility_id: str, max_count: int
) -> List[str]:
    stakeholders: Set[str] = set()
    for assignment in workforce.assignments.values():
        if assignment.kind is AssignmentKind.FACILITY_STAFF and assignment.target_id == facility_id:
            stakeholders.add(assignment.agent_id)
    return _bounded(stakeholders, max_count)


def _resolve_phase_stakeholders(*, world: Any, max_count: int) -> List[str]:
    leaders = getattr(world, "council_members", None)
    if isinstance(leaders, Sequence) and leaders:
        return _bounded((str(member) for member in leaders), max_count)
    agents = getattr(world, "agents", {}) or {}
    return _bounded(agents.keys(), max_count)


def _incident_stakeholders(
    *, world: Any, workforce: WorkforceLedger, event: WorldEvent, cfg: RouterConfig
) -> List[str]:
    stakeholders: Set[str] = set()
    actors = event.payload.get("actors") if isinstance(event.payload, dict) else []
    if isinstance(actors, Sequence):
        stakeholders.update(str(actor) for actor in actors)
    target_kind = event.payload.get("target_kind") or event.subject_kind
    target_id = event.payload.get("target_id") or event.subject_id
    if target_kind == "delivery":
        stakeholders.update(
            _resolve_delivery_stakeholders(
                world=world, workforce=workforce, subject_id=str(target_id), max_count=cfg.max_stakeholders_per_event
            )
        )
    if target_kind == "facility":
        stakeholders.update(
            _resolve_facility_stakeholders(
                workforce=workforce, facility_id=str(target_id), max_count=cfg.max_stakeholders_per_event
            )
        )
    if target_kind == "agent":
        stakeholders.add(str(target_id))
    return _bounded(stakeholders, cfg.max_stakeholders_per_event)


def _resolve_stakeholders(world: Any, event: WorldEvent, cfg: RouterConfig) -> List[str]:
    workforce = ensure_workforce(world)
    if event.kind in {
        EventKind.DELIVERY_DELAYED,
        EventKind.DELIVERY_FAILED,
        EventKind.DELIVERY_DELIVERED,
    }:
        return _resolve_delivery_stakeholders(
            world=world, workforce=workforce, subject_id=event.subject_id, max_count=cfg.max_stakeholders_per_event
        )
    if event.kind in {EventKind.PROJECT_APPROVED, EventKind.PROJECT_STAGED, EventKind.PROJECT_COMPLETE}:
        return _resolve_project_stakeholders(
            workforce=workforce, project_id=event.subject_id, max_count=cfg.max_stakeholders_per_event
        )
    if event.kind in {
        EventKind.STOCKPILE_PULL_REQUESTED,
        EventKind.STOCKPILE_PULL_COMPLETED,
        EventKind.STOCKPILE_SHORTAGE,
    }:
        return _resolve_facility_stakeholders(
            workforce=workforce, facility_id=event.subject_id, max_count=cfg.max_stakeholders_per_event
        )
    if event.kind in {EventKind.FACILITY_DOWNTIME, EventKind.FACILITY_REACTIVATED}:
        return _resolve_facility_stakeholders(
            workforce=workforce, facility_id=event.subject_id, max_count=cfg.max_stakeholders_per_event
        )
    if event.kind is EventKind.INCIDENT:
        return _incident_stakeholders(world=world, workforce=workforce, event=event, cfg=cfg)
    if event.kind is EventKind.PHASE_TRANSITION:
        return _resolve_phase_stakeholders(world=world, max_count=cfg.max_stakeholders_per_event)
    if event.kind in {
        EventKind.SUIT_WEAR_WARN,
        EventKind.SUIT_REPAIR_NEEDED,
        EventKind.SUIT_CRITICAL,
        EventKind.SUIT_REPAIR_STARTED,
        EventKind.SUIT_REPAIRED,
    }:
        return _bounded([event.subject_id], cfg.max_stakeholders_per_event)
    return []


def _base_salience(event: WorldEvent) -> float:
    if event.kind is EventKind.DELIVERY_FAILED:
        return 0.8
    if event.kind is EventKind.FACILITY_DOWNTIME:
        return 0.7
    if event.kind is EventKind.INCIDENT:
        try:
            return max(0.0, min(1.0, float(event.severity)))
        except Exception:
            return 0.0
    if event.kind is EventKind.PROJECT_COMPLETE:
        return 0.5
    return 0.3


def _assigned_to_target(agent_id: str, workforce: WorkforceLedger, target_id: str) -> bool:
    assignment = workforce.assignments.get(agent_id)
    if assignment is None:
        return False
    if assignment.target_id is None:
        return False
    return str(assignment.target_id) == str(target_id)


def _salience_for(agent_id: str, workforce: WorkforceLedger, event: WorldEvent) -> float:
    score = _base_salience(event)
    if _assigned_to_target(agent_id, workforce, event.subject_id):
        score += 0.1
    if event.severity >= 0.7:
        score += 0.1
    return max(0.0, min(1.0, score))


def _crumb_tags(event: WorldEvent) -> List[str]:
    tags: List[str] = []
    if event.kind is EventKind.DELIVERY_FAILED:
        tags.append(f"delivery-fail:{event.subject_id}")
        edge_key = event.payload.get("edge_key") if isinstance(event.payload, dict) else None
        if edge_key:
            tags.append(f"route-risk:{edge_key}")
    elif event.kind is EventKind.FACILITY_DOWNTIME:
        tags.append(f"facility-down:{event.subject_id}")
    elif event.kind is EventKind.INCIDENT:
        incident_kind = event.payload.get("incident_kind") if isinstance(event.payload, dict) else "unknown"
        target_id = event.payload.get("target_id") if isinstance(event.payload, dict) else event.subject_id
        tags.append(f"incident:{incident_kind}:{target_id}")
        edge_key = event.payload.get("edge_key") if isinstance(event.payload, dict) else None
        node_id = event.payload.get("node_id") if isinstance(event.payload, dict) else None
        if incident_kind in {"CONFLICT", "SABOTAGE"} and edge_key:
            tags.append(f"route-risk:{edge_key}")
        if incident_kind in {"THEFT_CARGO", "THEFT_DEPOT", "SABOTAGE_PROJECT"} and edge_key:
            tags.append(f"route-risk:{edge_key}")
        if incident_kind == "SABOTAGE" and event.payload.get("delivery_failed"):
            tags.append(f"delivery-fail:{target_id}")
        if incident_kind == "SABOTAGE_PROJECT" and node_id:
            tags.append(f"site-trouble:{node_id}")
        if node_id and event.subject_kind in {"project", "facility"}:
            tags.append(f"site-trouble:{node_id}")
        helper_id = event.payload.get("helper_id") if isinstance(event.payload, dict) else None
        if helper_id:
            tags.append(f"helped-by:{helper_id}")
    elif event.kind is EventKind.PHASE_TRANSITION:
        from_phase = event.payload.get("from") if isinstance(event.payload, dict) else "?"
        to_phase = event.payload.get("to") if isinstance(event.payload, dict) else "?"
        tags.append(f"phase:{from_phase}->{to_phase}")
    elif event.kind in {EventKind.SUIT_WEAR_WARN, EventKind.SUIT_REPAIR_NEEDED}:
        tags.append("repair-needed")
    elif event.kind is EventKind.SUIT_CRITICAL:
        tags.append("suit-critical")
    elif event.kind is EventKind.SUIT_REPAIRED:
        facility_id = event.payload.get("facility_id") if isinstance(event.payload, dict) else None
        if facility_id:
            tags.append(f"workshop-reliability:{facility_id}")
    elif event.kind in {
        EventKind.STOCKPILE_PULL_REQUESTED,
        EventKind.STOCKPILE_PULL_COMPLETED,
        EventKind.STOCKPILE_SHORTAGE,
    }:
        material = event.payload.get("material") if isinstance(event.payload, dict) else None
        depot_id = event.subject_id
        if event.kind is EventKind.STOCKPILE_SHORTAGE and material and depot_id:
            tags.append(f"depot-short:{material}:{depot_id}")
        if event.kind is EventKind.STOCKPILE_PULL_COMPLETED:
            source_owner = event.payload.get("source_owner") if isinstance(event.payload, dict) else None
            if source_owner:
                tags.append(f"source-reliable:{source_owner}")
    return tags


def _ensure_agent_memory(agent: Any, cfg: RouterConfig) -> tuple[CrumbStore, EpisodeBuffer, STMBoringWinner]:
    crumbs = getattr(agent, "crumbs", None)
    if not isinstance(crumbs, CrumbStore):
        crumbs = CrumbStore()
        setattr(agent, "crumbs", crumbs)

    episodes_daily = getattr(agent, "episodes_daily", None)
    if not isinstance(episodes_daily, EpisodeBuffer):
        episodes_daily = EpisodeBuffer()
        setattr(agent, "episodes_daily", episodes_daily)

    stm = getattr(agent, "stm", None)
    if not isinstance(stm, STMBoringWinner):
        stm = STMBoringWinner(k=cfg.stm_k)
        setattr(agent, "stm", stm)

    return crumbs, episodes_daily, stm


def _process_event_for_agent(
    *,
    world: Any,
    agent_id: str,
    agent: Any,
    event: WorldEvent,
    day: int,
    cfg: RouterConfig,
    workforce: WorkforceLedger,
) -> None:
    crumbs, episodes_daily, stm = _ensure_agent_memory(agent, cfg)
    tags = _crumb_tags(event)
    for tag in tags:
        crumbs.bump(tag, day, half_life_days=cfg.crumb_half_life_days)

    salience = _salience_for(agent_id, workforce, event)
    if salience >= cfg.episode_salience_threshold:
        episode = Episode(
            episode_id=f"ep:{agent_id}:{event.event_id}",
            day=day,
            kind=event.kind.value,
            salience=salience,
            payload={
                "event_kind": event.kind.value,
                "subject_id": event.subject_id,
                "severity": float(event.severity),
                "day": event.day,
            },
        )
        episodes_daily.add(episode)
        stm.consider(episode)

    signaled = _ensure_agents_with_new_signals(world)
    signaled.add(agent_id)


def run_router_for_day(world: Any, *, day: int) -> None:
    cfg = _ensure_router_config(world)
    if not cfg.enabled:
        return

    state = _ensure_router_state(world)
    event_log = _ensure_event_log(world)
    if state.cursor_seq < event_log.base_seq:
        state.cursor_seq = event_log.base_seq

    events = event_log.since(state.cursor_seq)
    if not events:
        state.last_run_day = day
        world.router_state = state
        return

    workforce = ensure_workforce(world)
    processed = 0
    for event in events:
        if processed >= cfg.max_events_per_day:
            break
        stakeholders = _resolve_stakeholders(world, event, cfg)
        stakeholders = stakeholders[: cfg.max_stakeholders_per_event]
        for agent_id in stakeholders:
            agent = getattr(world, "agents", {}).get(agent_id)
            if agent is None:
                continue
            _process_event_for_agent(
                world=world,
                agent_id=agent_id,
                agent=agent,
                event=event,
                day=day,
                cfg=cfg,
                workforce=workforce,
            )
        processed += 1

    state.cursor_seq = event_log.base_seq + len(event_log.events)
    state.last_run_day = day
    world.router_state = state


__all__ = ["RouterConfig", "RouterState", "run_router_for_day"]

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, MutableMapping

from dosadi.runtime.belief_queries import belief_score, planner_perspective_agent
from dosadi.world.phases import WorldPhase
from dosadi.world.survey_map import SurveyMap
from dosadi.world.workforce import Assignment, AssignmentKind, WorkforceLedger, ensure_workforce


@dataclass(slots=True)
class EscortConfig:
    enabled: bool = False
    risk_threshold: float = 0.65
    max_escorts_per_delivery: int = 1
    escort_candidate_cap: int = 200
    escort_speed_penalty: float = 0.05
    escort_interaction_shift: float = 0.12
    phase2_threshold_delta: float = -0.05
    min_idle_reserve: int = 2


@dataclass(slots=True)
class EscortState:
    last_run_day: int = -1
    requested_today: int = 0
    assigned_today: int = 0


def ensure_escort_config(world: Any) -> EscortConfig:
    cfg = getattr(world, "escort_cfg", None)
    if not isinstance(cfg, EscortConfig):
        cfg = EscortConfig()
        setattr(world, "escort_cfg", cfg)
    return cfg


def ensure_escort_state(world: Any) -> EscortState:
    state = getattr(world, "escort_state", None)
    if not isinstance(state, EscortState):
        state = EscortState()
        setattr(world, "escort_state", state)
    return state


def _escort_metrics(world: Any) -> MutableMapping[str, float]:
    metrics: MutableMapping[str, float] = getattr(world, "metrics", {})
    world.metrics = metrics
    return metrics.setdefault("escort", {})  # type: ignore[arg-type]


def _edge_hazard(world: Any, edge_key: str) -> float:
    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    edge = survey_map.edges.get(edge_key)
    if edge is None:
        return 0.5
    try:
        return float(getattr(edge, "hazard", 0.0) or 0.0)
    except Exception:
        return 0.5


def delivery_route_risk(world: Any, delivery_id: str, perspective_agent_id: str | None) -> float:
    logistics = getattr(world, "logistics", None)
    if logistics is None:
        return 0.5
    delivery = getattr(logistics, "deliveries", {}).get(delivery_id)
    if delivery is None:
        return 0.5

    edge_keys: Iterable[str] = getattr(delivery, "route_edge_keys", [])
    edge_keys = list(edge_keys)
    if not edge_keys:
        return 0.5

    hazards: list[float] = []
    beliefs: list[float] = []
    agent = perspective_agent_id or planner_perspective_agent(world)

    for edge_key in edge_keys:
        hazards.append(_edge_hazard(world, edge_key))
        beliefs.append(belief_score(agent, f"route-risk:{edge_key}", 0.5))

    hazard_mean = sum(hazards) / max(1, len(hazards))
    belief_mean = sum(beliefs) / max(1, len(beliefs))
    return 0.5 * hazard_mean + 0.5 * belief_mean


def _idle_agents(ledger: WorkforceLedger, ordered_ids: list[str]) -> list[str]:
    idle: list[str] = []
    for agent_id in ordered_ids:
        try:
            if ledger.is_idle(agent_id):
                idle.append(agent_id)
        except Exception:
            continue
    return idle


def choose_escort_agents(
    world: Any, *, day: int, max_n: int, cap: int, min_idle_reserve: int
) -> list[str]:
    agents = getattr(world, "agents", {}) or {}
    if not agents or max_n <= 0:
        return []

    ledger = ensure_workforce(world)
    ordered_ids = sorted(agents.keys())[: max(0, cap)]
    idle = _idle_agents(ledger, ordered_ids)
    if len(idle) <= max(0, min_idle_reserve):
        return []

    take = max(0, min(max_n, len(idle) - max(0, min_idle_reserve)))
    return idle[:take]


def _reset_daily_state(state: EscortState, *, day: int) -> None:
    if state.last_run_day != day:
        state.last_run_day = day
        state.requested_today = 0
        state.assigned_today = 0


def _phase_adjusted_threshold(world: Any, cfg: EscortConfig) -> float:
    phase_state = getattr(world, "phase_state", None)
    phase = getattr(phase_state, "phase", None)
    if phase is WorldPhase.PHASE2:
        return cfg.risk_threshold + cfg.phase2_threshold_delta
    return cfg.risk_threshold


def assign_escorts_for_delivery(world: Any, delivery_id: str, *, day: int) -> list[str]:
    cfg = ensure_escort_config(world)
    if not cfg.enabled:
        return []

    state = ensure_escort_state(world)
    _reset_daily_state(state, day=day)
    metrics = _escort_metrics(world)

    logistics = getattr(world, "logistics", None)
    delivery = getattr(logistics, "deliveries", {}).get(delivery_id) if logistics else None
    if delivery is None:
        return []

    carrier_id = getattr(delivery, "assigned_carrier_id", None)
    if carrier_id is None or carrier_id.startswith("carrier:"):
        return []

    risk = delivery_route_risk(world, delivery_id, carrier_id)
    threshold = _phase_adjusted_threshold(world, cfg)
    if risk < threshold:
        return []

    state.requested_today += 1
    metrics["requested"] = metrics.get("requested", 0.0) + 1

    escorts = choose_escort_agents(
        world,
        day=day,
        max_n=cfg.max_escorts_per_delivery,
        cap=cfg.escort_candidate_cap,
        min_idle_reserve=cfg.min_idle_reserve,
    )
    if not escorts:
        metrics["unavailable"] = metrics.get("unavailable", 0.0) + 1
        return []

    ledger = ensure_workforce(world)
    assigned: list[str] = []
    for escort_id in escorts:
        try:
            ledger.assign(
                Assignment(
                    agent_id=escort_id,
                    kind=AssignmentKind.LOGISTICS_ESCORT,
                    target_id=delivery_id,
                    start_day=day,
                    notes={"role": "escort"},
                )
            )
            assigned.append(escort_id)
        except ValueError:
            continue

    if assigned:
        state.assigned_today += len(assigned)
        metrics["assigned"] = metrics.get("assigned", 0.0) + len(assigned)
        delivery.escort_agent_ids = assigned
    return assigned


def release_escorts(world: Any, delivery_id: str) -> None:
    logistics = getattr(world, "logistics", None)
    delivery = getattr(logistics, "deliveries", {}).get(delivery_id) if logistics else None
    if delivery is None:
        return

    escort_ids = list(getattr(delivery, "escort_agent_ids", []) or [])
    if not escort_ids:
        return

    ledger = ensure_workforce(world)
    for agent_id in escort_ids:
        assignment = ledger.get(agent_id)
        if assignment.kind is AssignmentKind.LOGISTICS_ESCORT and assignment.target_id == delivery_id:
            ledger.unassign(agent_id)
    delivery.escort_agent_ids = []

    metrics = _escort_metrics(world)
    metrics["missions_completed"] = metrics.get("missions_completed", 0.0) + 1


def has_escort(world: Any, delivery_id: str) -> bool:
    logistics = getattr(world, "logistics", None)
    delivery = getattr(logistics, "deliveries", {}).get(delivery_id) if logistics else None
    if delivery is None:
        return False
    escorts = getattr(delivery, "escort_agent_ids", None)
    if escorts:
        return True
    return False


__all__ = [
    "EscortConfig",
    "EscortState",
    "ensure_escort_config",
    "ensure_escort_state",
    "delivery_route_risk",
    "choose_escort_agents",
    "assign_escorts_for_delivery",
    "release_escorts",
    "has_escort",
]

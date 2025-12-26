from __future__ import annotations

"""Escort policy v2 driven by corridor risk."""

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .corridor_risk import ensure_corridor_risk_config, ensure_corridor_risk_ledger, risk_for_edge
from .defense import DefenseConfig, ensure_defense_config, ensure_ward_defense
from dosadi.world.survey_map import SurveyMap


@dataclass(slots=True)
class EscortPolicyV2Config:
    enabled: bool = False
    risk_threshold_warn: float = 0.35
    risk_threshold_high: float = 0.60
    risk_threshold_critical: float = 0.80
    base_escort_count: int = 0
    warn_escort_count: int = 1
    high_escort_count: int = 2
    critical_escort_count: int = 3
    max_escorts_per_delivery: int = 3
    max_escort_missions_per_day: int = 20
    deterministic_salt: str = "escort-v2"


@dataclass(slots=True)
class EscortPolicyV2State:
    last_run_day: int = -1
    escorts_scheduled_today: int = 0
    next_mission_seq: int = 0


def ensure_escort_policy_v2_config(world) -> EscortPolicyV2Config:
    cfg = getattr(world, "escort2_cfg", None)
    if not isinstance(cfg, EscortPolicyV2Config):
        cfg = EscortPolicyV2Config()
        world.escort2_cfg = cfg
    return cfg


def ensure_escort_policy_v2_state(world) -> EscortPolicyV2State:
    state = getattr(world, "escort2_state", None)
    if not isinstance(state, EscortPolicyV2State):
        state = EscortPolicyV2State()
        world.escort2_state = state
    return state


def _reset_daily_state(state: EscortPolicyV2State, day: int) -> None:
    if day != state.last_run_day:
        state.last_run_day = day
        state.escorts_scheduled_today = 0


def required_escorts_for_route(world, route_edges: Sequence[str]) -> int:
    cfg = ensure_escort_policy_v2_config(world)
    ensure_corridor_risk_config(world)
    ensure_corridor_risk_ledger(world)
    if not getattr(cfg, "enabled", False):
        return max(0, int(cfg.base_escort_count))

    if not route_edges:
        return max(0, int(cfg.base_escort_count))

    max_risk = 0.0
    for edge in route_edges:
        max_risk = max(max_risk, risk_for_edge(world, edge))

    defense_cfg: DefenseConfig = ensure_defense_config(world)
    if defense_cfg.enabled:
        survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
        ward_ids: set[str] = set()
        for edge_key in route_edges:
            edge = survey_map.edges.get(edge_key)
            if edge is None:
                continue
            for node_id in (edge.a, edge.b):
                ward_id = getattr(survey_map.nodes.get(node_id, None), "ward_id", None)
                if ward_id:
                    ward_ids.add(str(ward_id))
        readiness: list[float] = []
        for ward_id in sorted(ward_ids):
            state = ensure_ward_defense(world, ward_id)
            readiness.append(state.militia_ready * state.militia_strength)
        if readiness:
            max_risk *= max(0.0, 1.0 - 0.25 * max(readiness))

    if max_risk >= cfg.risk_threshold_critical:
        return min(cfg.max_escorts_per_delivery, cfg.critical_escort_count)
    if max_risk >= cfg.risk_threshold_high:
        return min(cfg.max_escorts_per_delivery, cfg.high_escort_count)
    if max_risk >= cfg.risk_threshold_warn:
        return min(cfg.max_escorts_per_delivery, cfg.warn_escort_count)
    return max(0, min(cfg.max_escorts_per_delivery, cfg.base_escort_count))


def schedule_escorts_for_delivery(
    world,
    delivery,
    *,
    available_guard_ids: Iterable[str],
    day: int,
) -> None:
    cfg = ensure_escort_policy_v2_config(world)
    state = ensure_escort_policy_v2_state(world)
    _reset_daily_state(state, day)

    if not getattr(cfg, "enabled", False):
        return
    if getattr(delivery, "escort_mission_ids", None):
        return

    required = required_escorts_for_route(world, getattr(delivery, "route_edge_keys", []) or [])
    if required <= 0:
        return

    remaining_daily = max(0, cfg.max_escort_missions_per_day - state.escorts_scheduled_today)
    if remaining_daily <= 0:
        return

    guard_pool = sorted(set(available_guard_ids))
    if not guard_pool:
        return

    count = min(required, len(guard_pool), cfg.max_escorts_per_delivery, remaining_daily)
    selected = guard_pool[:count]
    missions = []
    for guard_id in selected:
        mission_id = f"esc:{delivery.delivery_id}:{state.next_mission_seq}"
        missions.append(mission_id)
        state.next_mission_seq += 1
        state.escorts_scheduled_today += 1
        delivery.escort_agent_ids.append(guard_id)

    if missions:
        delivery.escort_mission_ids.extend(missions)


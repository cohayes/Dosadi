"""Deterministic war and raid operations (v1).

This module implements a lightweight, deterministic raid planner and resolver
that stresses corridors, blocks collapsed edges, and records outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping, MutableMapping

from dosadi.runtime.crackdown import CrackdownTarget
from dosadi.runtime.defense import DefenseConfig, ensure_defense_config, ensure_ward_defense
from dosadi.runtime.ledger import (
    LedgerConfig,
    LedgerState,
    get_or_create_account,
    transfer,
)
from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.world.corridor_infrastructure import level_for_edge
from dosadi.world.facilities import FacilityKind, ensure_facility_ledger
from dosadi.world.factions import (
    Faction,
    FactionSystemConfig,
    ensure_faction_territory,
    update_claim,
)
from dosadi.world.survey_map import SurveyEdge, SurveyMap


@dataclass(slots=True)
class WarConfig:
    enabled: bool = False
    max_ops_per_day: int = 3
    candidate_topk: int = 24
    raid_duration_days: int = 3
    deterministic_salt: str = "war-v1"
    collapse_threshold: float = 1.0
    stress_decay_per_day: float = 0.05
    raid_stress_per_success: float = 0.12
    territory_pressure_per_week: float = 0.05


@dataclass(slots=True)
class RaidPlan:
    op_id: str
    aggressor_faction: str
    target_kind: str
    target_id: str
    start_day: int
    end_day: int
    intensity: float
    objective: str
    expected_loot: dict[str, float] = field(default_factory=dict)
    expected_cost: dict[str, float] = field(default_factory=dict)
    reason: str = ""
    score_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class RaidOutcome:
    op_id: str
    day: int
    status: str
    loot: dict[str, float] = field(default_factory=dict)
    losses: dict[str, float] = field(default_factory=dict)
    corridor_stress_delta: float = 0.0
    territory_delta: dict[str, object] = field(default_factory=dict)
    notes: dict[str, object] = field(default_factory=dict)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _stable_rand(*parts: object, salt: str = "war-v1") -> float:
    payload = "|".join(str(p) for p in parts)
    digest = sha256(f"{salt}|{payload}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


def ensure_war_config(world: Any) -> WarConfig:
    cfg = getattr(world, "war_cfg", None)
    if not isinstance(cfg, WarConfig):
        cfg = WarConfig()
        world.war_cfg = cfg
    return cfg


def ensure_war_state(world: Any) -> tuple[dict[str, RaidPlan], list[RaidOutcome], dict[str, float]]:
    active = getattr(world, "raid_active", None)
    if not isinstance(active, dict):
        active = {}
    history = getattr(world, "raid_history", None)
    if not isinstance(history, list):
        history = []
    stress = getattr(world, "corridor_stress", None)
    if not isinstance(stress, dict):
        stress = {}
    collapsed = getattr(world, "collapsed_corridors", None)
    if not isinstance(collapsed, set):
        collapsed = set()
    world.raid_active = active
    world.raid_history = history
    world.corridor_stress = stress
    world.collapsed_corridors = collapsed
    return active, history, stress


def _bounded_append(history: list[RaidOutcome], outcome: RaidOutcome, limit: int = 200) -> None:
    history.append(outcome)
    if len(history) > max(1, limit):
        overflow = len(history) - limit
        history[:] = history[overflow:]


def _aggressor_pool(world: Any) -> list[Faction]:
    factions: Mapping[str, Faction] = getattr(world, "factions", {}) or {}
    raiders: list[Faction] = [
        factions[fid]
        for fid in sorted(factions.keys())
        if getattr(factions[fid], "kind", "").upper() == "RAIDERS"
    ]
    return raiders


def _edge_defense_penalty(world: Any, edge: SurveyEdge) -> float:
    if edge is None:
        return 0.0
    level = level_for_edge(world, edge.key)
    penalty = 0.08 * float(level)
    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    wards: list[str] = []
    for node_id in (edge.a, edge.b):
        ward = getattr(survey_map.nodes.get(node_id, None), "ward_id", None)
        if ward:
            wards.append(str(ward))
    if wards:
        avg_legitimacy = sum(getattr(world.wards.get(w, None), "legitimacy", 0.5) for w in wards) / len(wards)
        penalty += max(0.0, avg_legitimacy - 0.5) * 0.15
    cfg: DefenseConfig = ensure_defense_config(world)
    if cfg.enabled:
        ledger = ensure_facility_ledger(world)
        for facility in ledger.values():
            if getattr(facility, "site_node_id", None) not in {edge.a, edge.b}:
                continue
            if facility.kind in {FacilityKind.OUTPOST_L1, FacilityKind.OUTPOST}:
                penalty += 0.05
            if facility.kind == FacilityKind.FORT_L2:
                penalty += 0.12
            if facility.kind == FacilityKind.GARRISON_L2:
                penalty += 0.1
        for ward_id in wards:
            state = ensure_ward_defense(world, ward_id)
            militia_factor = float(state.militia_strength) * float(state.militia_ready)
            if militia_factor > 0:
                penalty += 0.08 * militia_factor
    return penalty


def _candidate_corridors(world: Any, cfg: WarConfig) -> list[tuple[float, SurveyEdge, dict[str, float]]]:
    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    stress = getattr(world, "corridor_stress", {}) or {}
    risk_ledger = getattr(world, "risk_ledger", None)
    candidates: list[tuple[float, SurveyEdge, dict[str, float]]] = []
    for edge_key_str, edge in sorted(survey_map.edges.items()):
        risk = 0.0
        if risk_ledger is not None:
            rec = getattr(risk_ledger, "edges", {}).get(edge_key_str)
            risk = getattr(rec, "risk", 0.0)
        stress_score = float(stress.get(edge_key_str, 0.0))
        defense_penalty = _edge_defense_penalty(world, edge)
        base_value = max(0.1, float(edge.travel_cost) + 0.5 * float(edge.hazard) + 1.0)
        score = base_value + 0.75 * risk + 0.6 * stress_score - defense_penalty
        breakdown = {
            "base": round(base_value, 4),
            "risk": round(risk, 4),
            "stress": round(stress_score, 4),
            "defense": round(defense_penalty, 4),
        }
        candidates.append((score, edge, breakdown))

    candidates.sort(key=lambda row: (-round(row[0], 6), row[1].key))
    return candidates[: cfg.candidate_topk]


def propose_raid_ops_for_day(world: Any, day: int) -> list[RaidPlan]:
    cfg = ensure_war_config(world)
    if not cfg.enabled:
        return []
    aggressors = _aggressor_pool(world)
    if not aggressors:
        return []

    candidates = _candidate_corridors(world, cfg)
    plans: list[RaidPlan] = []
    for idx, (score, edge, breakdown) in enumerate(candidates):
        if len(plans) >= cfg.max_ops_per_day:
            break
        faction = aggressors[idx % len(aggressors)]
        intensity = _clamp01(0.35 + 0.25 * score)
        op_id = f"raid:{cfg.deterministic_salt}:{day}:{edge.key}:{idx}"
        plan = RaidPlan(
            op_id=op_id,
            aggressor_faction=faction.faction_id,
            target_kind="corridor",
            target_id=edge.key,
            start_day=day,
            end_day=day + cfg.raid_duration_days,
            intensity=intensity,
            objective="disrupt",
            expected_loot={"credits": round(max(score, 0.0) * 5.0, 3)},
            expected_cost={"capacity": round(0.5 + 0.15 * intensity, 3)},
            reason=f"Corridor value {round(score, 3)} with stress {breakdown['stress']}",
            score_breakdown=breakdown,
        )
        plans.append(plan)

    return plans


def _crackdown_penalty(world: Any, target_id: str) -> float:
    active = getattr(world, "crackdown_active", {}) or {}
    penalty = 0.0
    for tgt in active.values():
        if not isinstance(tgt, CrackdownTarget):
            continue
        if tgt.target_id == target_id:
            penalty += 0.15 * float(getattr(tgt, "intensity", 0.0))
    return penalty


def _treaty_penalty(world: Any, target_id: str) -> float:
    treaties: Mapping[str, Any] = getattr(world, "treaties", {}) or {}
    penalty = 0.0
    for treaty in treaties.values():
        if getattr(treaty, "status", "active") != "active":
            continue
        protected = getattr(treaty, "protected_edges", set()) or set()
        if target_id in protected:
            penalty += 0.1
    return penalty


def success_probability(world: Any, plan: RaidPlan) -> float:
    cfg = ensure_war_config(world)
    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    edge = survey_map.edges.get(plan.target_id)
    defense_penalty = _edge_defense_penalty(world, edge) if edge else 0.0
    crackdown = _crackdown_penalty(world, plan.target_id)
    treaty = _treaty_penalty(world, plan.target_id)
    base = 0.35 + 0.5 * float(plan.intensity)
    prob = _clamp01(base - defense_penalty - crackdown - treaty)
    return prob


def deterministic_roll(world: Any, plan: RaidPlan, day: int) -> float:
    cfg = ensure_war_config(world)
    return _stable_rand(cfg.deterministic_salt, day, plan.op_id, salt=cfg.deterministic_salt)


def _territory_delta(world: Any, plan: RaidPlan, *, success: bool, day: int) -> dict[str, object]:
    if not success:
        return {}
    territory = ensure_faction_territory(world, plan.aggressor_faction)
    cfg: FactionSystemConfig = getattr(world, "faction_cfg", FactionSystemConfig())
    world.faction_cfg = cfg
    delta = update_claim(
        territory=territory,
        bucket="edge",
        key=plan.target_id,
        delta=ensure_war_config(world).territory_pressure_per_week / 7.0,
        day=day,
        cfg=cfg,
    )
    record_event(
        world,
        {
            "type": "TERRITORY_PRESSURE_CHANGED",
            "faction": plan.aggressor_faction,
            "target": plan.target_id,
            "day": day,
            "strength": delta,
        },
    )
    return {plan.target_id: delta}


def _apply_loot(world: Any, plan: RaidPlan, day: int, *, loot: Mapping[str, float]) -> dict[str, float]:
    if not loot:
        return {}
    cfg: LedgerConfig = getattr(world, "ledger_cfg", LedgerConfig())
    state: LedgerState = getattr(world, "ledger_state", LedgerState())
    world.ledger_cfg = cfg
    world.ledger_state = state
    if not getattr(cfg, "enabled", False):
        return {}

    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    edge = survey_map.edges.get(plan.target_id)
    wards = []
    for node_id in (getattr(edge, "a", None), getattr(edge, "b", None)):
        ward_id = getattr(survey_map.nodes.get(node_id, None), "ward_id", None)
        if ward_id:
            wards.append(f"acct:ward:{ward_id}")
    payer = wards[0] if wards else "acct:ward:unknown"
    receiver = f"acct:fac:{plan.aggressor_faction}"
    get_or_create_account(world, payer)
    get_or_create_account(world, receiver)

    transferred: dict[str, float] = {}
    for key, amount in loot.items():
        if amount <= 0:
            continue
        posted = transfer(
            world,
            day=day,
            from_acct=payer,
            to_acct=receiver,
            amount=float(amount),
            reason="RAID_TRIBUTE",
            meta={"op_id": plan.op_id, "target": plan.target_id, "resource": key},
        )
        if posted:
            transferred[key] = transferred.get(key, 0.0) + float(amount)
    return transferred


def _resolve_plan(world: Any, plan: RaidPlan, day: int) -> RaidOutcome:
    prob = success_probability(world, plan)
    roll = deterministic_roll(world, plan, day)
    succeeded = roll <= prob
    stress_delta = ensure_war_config(world).raid_stress_per_success * plan.intensity if succeeded else 0.0
    loot = _apply_loot(world, plan, day, loot=plan.expected_loot if succeeded else {})
    territory_delta = _territory_delta(world, plan, success=succeeded, day=day)
    treaty_penalty = _treaty_penalty(world, plan.target_id)
    outcome = RaidOutcome(
        op_id=plan.op_id,
        day=day,
        status="succeeded" if succeeded else "failed",
        loot=loot,
        corridor_stress_delta=stress_delta,
        territory_delta=territory_delta,
        notes={"prob": prob, "roll": roll},
    )
    if treaty_penalty > 0.0:
        record_event(
            world,
            {
                "type": "TREATY_BREACH",
                "op_id": plan.op_id,
                "target": plan.target_id,
                "day": day,
                "penalty": treaty_penalty,
            },
        )
    return outcome


def _decay_stress(world: Any, cfg: WarConfig, stress: MutableMapping[str, float]) -> None:
    for edge_key, value in list(stress.items()):
        updated = max(0.0, float(value) - cfg.stress_decay_per_day)
        if updated <= 0.0:
            stress.pop(edge_key, None)
        else:
            stress[edge_key] = updated


def _collapse_tracking(world: Any, day: int, cfg: WarConfig, stress: Mapping[str, float]) -> None:
    survey_map: SurveyMap = getattr(world, "survey_map", SurveyMap())
    collapsed: set[str] = getattr(world, "collapsed_corridors", set())
    metrics = ensure_metrics(world)
    for edge_key, value in stress.items():
        edge = survey_map.edges.get(edge_key)
        if value >= cfg.collapse_threshold:
            if edge_key not in collapsed:
                collapsed.add(edge_key)
                if edge is not None:
                    edge.closed_until_day = day + cfg.raid_duration_days
                metrics.inc("war.corridor_collapses", 1.0)
                record_event(
                    world,
                    {"type": "CORRIDOR_COLLAPSED", "edge": edge_key, "day": day, "stress": round(value, 4)},
                )
        else:
            if edge_key in collapsed and value < cfg.collapse_threshold:
                collapsed.remove(edge_key)
                if edge is not None:
                    edge.closed_until_day = None
                record_event(world, {"type": "CORRIDOR_REOPENED", "edge": edge_key, "day": day})
    world.collapsed_corridors = collapsed


def _emit_metrics(world: Any) -> None:
    metrics = ensure_metrics(world)
    metrics.set_gauge("war", metrics.get("war", {}))
    war_bucket = metrics.gauges.get("war")
    if isinstance(war_bucket, dict):
        war_bucket["ops_active"] = len(getattr(world, "raid_active", {}) or {})
        war_bucket["ops_started"] = metrics.counters.get("war.ops_started", 0.0)
        war_bucket["ops_success"] = metrics.counters.get("war.ops_success", 0.0)
        war_bucket["corridor_collapses"] = metrics.counters.get("war.corridor_collapses", 0.0)
        war_bucket["loot_total"] = metrics.counters.get("war.loot_total", 0.0)


def run_war_for_day(world: Any, *, day: int) -> None:
    cfg = ensure_war_config(world)
    if not cfg.enabled:
        return
    active, history, stress = ensure_war_state(world)
    _decay_stress(world, cfg, stress)

    # Resolve existing operations
    for op_id in sorted(list(active.keys())):
        plan = active.get(op_id)
        if plan is None:
            continue
        if day < plan.start_day:
            continue
        if day > plan.end_day:
            outcome = RaidOutcome(op_id=plan.op_id, day=day, status="expired")
            _bounded_append(history, outcome)
            active.pop(op_id, None)
            continue
        outcome = _resolve_plan(world, plan, day)
        if outcome.status == "succeeded":
            stress[plan.target_id] = stress.get(plan.target_id, 0.0) + outcome.corridor_stress_delta
            ensure_metrics(world).inc("war.ops_success", 1.0)
            ensure_metrics(world).inc("war.loot_total", sum(outcome.loot.values()))
        _bounded_append(history, outcome)
        active.pop(op_id, None)
        record_event(
            world,
            {
                "type": "RAID_RESOLVED",
                "op_id": plan.op_id,
                "status": outcome.status,
                "day": day,
                "target": plan.target_id,
            },
        )

    # Plan new operations
    new_ops = propose_raid_ops_for_day(world, day)
    metrics = ensure_metrics(world)
    for plan in new_ops:
        active[plan.op_id] = plan
        metrics.inc("war.ops_started", 1.0)
        record_event(
            world,
            {
                "type": "RAID_STARTED",
                "op_id": plan.op_id,
                "target": plan.target_id,
                "aggressor": plan.aggressor_faction,
                "day": plan.start_day,
                "reason": plan.reason,
            },
        )

    _collapse_tracking(world, day, cfg, stress)
    _emit_metrics(world)


__all__ = [
    "WarConfig",
    "RaidPlan",
    "RaidOutcome",
    "deterministic_roll",
    "ensure_war_config",
    "ensure_war_state",
    "propose_raid_ops_for_day",
    "run_war_for_day",
    "success_probability",
]

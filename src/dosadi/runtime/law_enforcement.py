"""Ward-level law enforcement planning and interdiction hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Dict, Iterable, Mapping

from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.runtime.institutions import WardInstitutionPolicy
from dosadi.world.corridor_infrastructure import predation_multiplier_for_edge
from dosadi.world.phases import WorldPhase


@dataclass(slots=True)
class EnforcementConfig:
    enabled: bool = False
    phase_budget_multiplier: dict[str, float] = field(
        default_factory=lambda: {"P0": 0.4, "P1": 1.0, "P2": 1.4}
    )
    max_patrols_per_ward: int = 12
    max_checkpoints_per_ward: int = 6
    traffic_lookback_days: int = 7
    incident_lookback_days: int = 14
    base_interdiction_prob: float = 0.05
    patrol_interdiction_bonus: float = 0.03
    checkpoint_interdiction_bonus: float = 0.06
    escort_synergy_bonus: float = 0.10
    max_interdiction_prob: float = 0.85
    risk_suppression_per_day: float = 0.03
    deterministic_salt: str = "enforcement-v1"


@dataclass(slots=True)
class WardSecurityPolicy:
    ward_id: str
    budget_points: float = 10.0
    posture: str = "balanced"  # balanced|patrol-heavy|checkpoint-heavy
    priority_edges: list[str] = field(default_factory=list)
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class WardSecurityState:
    ward_id: str
    patrol_edges: dict[str, int] = field(default_factory=dict)
    checkpoints: dict[str, int] = field(default_factory=dict)
    last_updated_day: int = -1
    events_today: int = 0


def _clamp01(val: float) -> float:
    return max(0.0, min(1.0, float(val)))


def _phase(world: Any) -> WorldPhase:
    phase_state = getattr(world, "phase_state", None)
    phase = getattr(phase_state, "phase", WorldPhase.PHASE0)
    try:
        return WorldPhase(phase)
    except Exception:
        return WorldPhase.PHASE0


def pseudo_rand01(key: str) -> float:
    digest = sha256(key.encode("utf-8")).digest()
    sample = int.from_bytes(digest[:8], "big")
    return sample / float(2**64)


def ensure_enforcement_config(world: Any) -> EnforcementConfig:
    cfg = getattr(world, "enf_cfg", None)
    if not isinstance(cfg, EnforcementConfig):
        cfg = EnforcementConfig()
        world.enf_cfg = cfg
    return cfg


def ensure_policy_for_ward(world: Any, ward_id: str) -> WardSecurityPolicy:
    policies: Dict[str, WardSecurityPolicy] = getattr(world, "enf_policy_by_ward", None) or {}
    if not isinstance(policies, dict):
        policies = {}
    policy = policies.get(ward_id)
    if not isinstance(policy, WardSecurityPolicy):
        policy = WardSecurityPolicy(ward_id=ward_id)
        policies[ward_id] = policy
    inst_policies = getattr(world, "inst_policy_by_ward", {}) or {}
    inst_policy = inst_policies.get(ward_id)
    if isinstance(inst_policy, WardInstitutionPolicy):
        policy.budget_points = float(getattr(inst_policy, "enforcement_budget_points", policy.budget_points))
    world.enf_policy_by_ward = policies
    return policy


def ensure_state_for_ward(world: Any, ward_id: str) -> WardSecurityState:
    states: Dict[str, WardSecurityState] = getattr(world, "enf_state_by_ward", None) or {}
    if not isinstance(states, dict):
        states = {}
    state = states.get(ward_id)
    if not isinstance(state, WardSecurityState):
        state = WardSecurityState(ward_id=ward_id)
        states[ward_id] = state
    world.enf_state_by_ward = states
    return state


def _ward_for_edge(world: Any, edge_key: str) -> str:
    survey_map = getattr(world, "survey_map", None)
    if survey_map is None:
        return "unknown"
    edge = getattr(survey_map, "edges", {}).get(edge_key)
    node_ids: Iterable[str] = ()
    if edge is not None:
        node_ids = (edge.a, edge.b)
    else:
        node_ids = tuple(edge_key.split("|"))
    for node_id in node_ids:
        node = getattr(survey_map, "nodes", {}).get(node_id)
        ward_id = getattr(node, "ward_id", None)
        if ward_id:
            return str(ward_id)
    return "unknown"


def _edge_stats(world: Any, edge_key: str) -> tuple[float, float]:
    from dosadi.runtime.corridor_risk import risk_for_edge

    risk = risk_for_edge(world, edge_key)
    incidents = 0.0
    ledger = getattr(world, "risk_ledger", None)
    if ledger is not None:
        rec = getattr(ledger, "edges", {}).get(edge_key)
        incidents = float(getattr(rec, "incidents_lookback", 0.0) or 0.0)
    return risk, incidents


def _traffic_score(world: Any, edge_key: str) -> float:
    ledger = getattr(world, "logistics", None)
    if ledger is None or not hasattr(ledger, "active_ids"):
        return 0.0
    score = 0.0
    for delivery_id in getattr(ledger, "active_ids", ()):  # type: ignore[assignment]
        delivery = getattr(ledger, "deliveries", {}).get(delivery_id)
        if delivery is None:
            continue
        for ek in getattr(delivery, "route_edge_keys", ()) or ():
            if ek == edge_key:
                score += 1.0
    return score


def interdiction_prob_for_edge(world: Any, edge_key: str, ward_id: str | None = None) -> float:
    cfg = ensure_enforcement_config(world)
    if not cfg.enabled:
        return 0.0
    ward = ward_id or _ward_for_edge(world, edge_key)
    states: Mapping[str, WardSecurityState] = getattr(world, "enf_state_by_ward", {}) or {}
    state = states.get(ward)
    if not isinstance(state, WardSecurityState):
        return _clamp01(cfg.base_interdiction_prob)
    patrols = int(state.patrol_edges.get(edge_key, 0))
    checkpoints = int(state.checkpoints.get(edge_key, 0))
    prob = cfg.base_interdiction_prob
    prob += cfg.patrol_interdiction_bonus * patrols
    prob += cfg.checkpoint_interdiction_bonus * checkpoints
    return _clamp01(min(cfg.max_interdiction_prob, prob))


def apply_interdiction(world: Any, *, edge_key: str, ward_id: str | None, day: int, severity: float) -> tuple[bool, float]:
    cfg = ensure_enforcement_config(world)
    if not cfg.enabled:
        return False, severity
    ward = ward_id or _ward_for_edge(world, edge_key)
    severity *= predation_multiplier_for_edge(world, edge_key)
    prob = interdiction_prob_for_edge(world, edge_key, ward)
    if prob <= 0.0:
        return False, severity
    key = f"{cfg.deterministic_salt}|day:{day}|edge:{edge_key}|ward:{ward}|severity:{round(severity, 3)}"
    roll = pseudo_rand01(key)
    if roll < prob:
        metrics = ensure_metrics(world)
        metrics.inc("enforcement.interdictions", 1.0)
        record_event(
            world,
            {
                "kind": "ENF_INTERDICTION_SUCCESS",
                "day": day,
                "edge_key": edge_key,
                "ward_id": ward,
            },
        )
        return True, 0.0
    return False, severity


def escort_synergy_multiplier(world: Any, edge_key: str, ward_id: str | None = None) -> float:
    cfg = ensure_enforcement_config(world)
    prob = interdiction_prob_for_edge(world, edge_key, ward_id)
    return 1.0 + cfg.escort_synergy_bonus * prob


def _coverage_factor(patrols: int, checkpoints: int) -> float:
    return _clamp01(min(1.0, 0.25 * max(0, patrols) + 0.5 * max(0, checkpoints)))


def _apply_risk_suppression(world: Any, *, day: int, cfg: EnforcementConfig) -> None:
    ledger = getattr(world, "risk_ledger", None)
    if ledger is None:
        return
    states: Mapping[str, WardSecurityState] = getattr(world, "enf_state_by_ward", {}) or {}
    for state in states.values():
        for edge_key, patrols in state.patrol_edges.items():
            checkpoints = int(state.checkpoints.get(edge_key, 0))
            factor = _coverage_factor(patrols, checkpoints)
            if factor <= 0.0:
                continue
            rec = getattr(ledger, "edges", {}).get(edge_key)
            if rec is None:
                continue
            rec.risk = max(0.0, rec.risk - cfg.risk_suppression_per_day * factor)
            rec.last_updated_day = max(day, getattr(rec, "last_updated_day", -1))


def run_enforcement_for_day(world: Any, *, day: int) -> None:
    cfg = ensure_enforcement_config(world)
    if not cfg.enabled:
        return
    metrics = ensure_metrics(world)
    phase = _phase(world)
    multiplier = cfg.phase_budget_multiplier.get(phase.name, 1.0)

    candidates_by_ward: Dict[str, Dict[str, float]] = {}
    ledger = getattr(world, "risk_ledger", None)
    if ledger is not None:
        for edge_key in list(getattr(ledger, "edges", {}).keys()):
            ward_id = _ward_for_edge(world, edge_key)
            risk, incidents = _edge_stats(world, edge_key)
            traffic = _traffic_score(world, edge_key)
            score = 0.6 * risk + 0.3 * traffic + 0.4 * incidents
            if score <= 0.0:
                continue
            ward_bucket = candidates_by_ward.setdefault(ward_id, {})
            ward_bucket[edge_key] = max(score, ward_bucket.get(edge_key, 0.0))

    active_wards = sorted(candidates_by_ward.keys())
    total_patrols = 0
    total_checkpoints = 0
    for ward_id in active_wards:
        policy = ensure_policy_for_ward(world, ward_id)
        state = ensure_state_for_ward(world, ward_id)
        edges = candidates_by_ward.get(ward_id, {})
        ranked = sorted(edges.items(), key=lambda item: (-round(item[1], 6), item[0]))
        priority_edges = [ek for ek, _ in ranked[: min(20, len(ranked))]]
        policy.priority_edges = priority_edges[:10]

        budget = max(0.0, float(policy.budget_points)) * multiplier
        if policy.posture == "patrol-heavy":
            patrol_budget = 0.7 * budget
        elif policy.posture == "checkpoint-heavy":
            patrol_budget = 0.3 * budget
        else:
            patrol_budget = 0.5 * budget
        patrol_count = min(cfg.max_patrols_per_ward, int(patrol_budget))
        remaining = max(0.0, budget - patrol_count)
        checkpoint_count = min(cfg.max_checkpoints_per_ward, int(remaining // 2))

        patrol_edges: Dict[str, int] = {}
        checkpoint_edges: Dict[str, int] = {}
        if priority_edges:
            for idx in range(patrol_count):
                edge_key = priority_edges[idx % len(priority_edges)]
                patrol_edges[edge_key] = patrol_edges.get(edge_key, 0) + 1
            for idx in range(checkpoint_count):
                edge_key = priority_edges[idx % len(priority_edges)]
                checkpoint_edges[edge_key] = checkpoint_edges.get(edge_key, 0) + 1

        # Enforce caps deterministically
        if sum(patrol_edges.values()) > cfg.max_patrols_per_ward:
            patrol_edges = dict(sorted(patrol_edges.items())[: cfg.max_patrols_per_ward])
        if sum(checkpoint_edges.values()) > cfg.max_checkpoints_per_ward:
            checkpoint_edges = dict(sorted(checkpoint_edges.items())[: cfg.max_checkpoints_per_ward])

        state.patrol_edges = patrol_edges
        state.checkpoints = checkpoint_edges
        state.last_updated_day = day
        state.events_today = 0
        total_patrols += sum(patrol_edges.values())
        total_checkpoints += sum(checkpoint_edges.values())

    metrics.set_gauge("enforcement.patrols_total", total_patrols)
    metrics.set_gauge("enforcement.checkpoints_total", total_checkpoints)
    _apply_risk_suppression(world, day=day, cfg=cfg)


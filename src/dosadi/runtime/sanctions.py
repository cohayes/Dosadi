from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable

from dosadi.runtime.shadow_state import apply_capture_modifier
from dosadi.runtime.telemetry import ensure_metrics, record_event


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class SanctionsConfig:
    enabled: bool = False
    update_cadence_days: int = 1
    deterministic_salt: str = "sanctions-v1"
    max_rules_active: int = 200
    max_goods_restricted_per_rule: int = 8
    base_leak_rate: float = 0.10
    enforcement_effect: float = 0.6
    comms_penalty_scale: float = 0.3
    penalty_scale: float = 0.25


@dataclass(slots=True)
class SanctionRule:
    rule_id: str
    issuer_id: str
    treaty_id: str | None
    kind: str
    target_kind: str
    target_id: str
    goods: list[str]
    severity: float
    start_day: int
    end_day: int
    enforcement_required: float
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SanctionsCompliance:
    entity_id: str
    violations_lookback: int = 0
    leak_rate_est: float = 0.0
    penalties_applied: float = 0.0
    last_update_day: int = -1


def ensure_sanctions_config(world: Any) -> SanctionsConfig:
    cfg = getattr(world, "sanctions_cfg", None)
    if not isinstance(cfg, SanctionsConfig):
        cfg = SanctionsConfig()
        world.sanctions_cfg = cfg
    return cfg


def ensure_sanction_rules(world: Any) -> dict[str, SanctionRule]:
    rules = getattr(world, "sanction_rules", None)
    if not isinstance(rules, dict):
        rules = {}
        world.sanction_rules = rules
    return rules


def ensure_sanctions_compliance(world: Any) -> dict[str, SanctionsCompliance]:
    compliance = getattr(world, "sanctions_compliance", None)
    if not isinstance(compliance, dict):
        compliance = {}
        world.sanctions_compliance = compliance
    return compliance


def ensure_sanctions_events(world: Any) -> list[dict[str, object]]:
    events = getattr(world, "sanctions_events", None)
    if not isinstance(events, list):
        events = []
        world.sanctions_events = events
    return events


def _normalize_goods(goods: Iterable[str]) -> list[str]:
    return sorted({str(item).upper() for item in goods})


def register_sanction_rule(world: Any, rule: SanctionRule) -> None:
    cfg = ensure_sanctions_config(world)
    rules = ensure_sanction_rules(world)
    normalized_goods = _normalize_goods(rule.goods)[: max(0, int(cfg.max_goods_restricted_per_rule))]
    rule.goods = normalized_goods
    rules[rule.rule_id] = rule
    if len(rules) > max(1, int(cfg.max_rules_active)):
        for rule_id in sorted(rules.keys())[: len(rules) - cfg.max_rules_active]:
            rules.pop(rule_id, None)


def _active_rules(world: Any, *, day: int, kinds: set[str] | None = None) -> list[SanctionRule]:
    rules = ensure_sanction_rules(world)
    active: list[SanctionRule] = []
    for rule in rules.values():
        if kinds and rule.kind not in kinds:
            continue
        if rule.start_day <= day <= rule.end_day:
            active.append(rule)
    active.sort(key=lambda r: (r.start_day, r.rule_id))
    return active


def _comms_reliability(world: Any, rule: SanctionRule) -> float:
    if rule.target_kind != "WARD":
        return 1.0
    mod = getattr(world, "comms_mod_by_ward", {}).get(rule.target_id)
    reliability = getattr(mod, "reliability", None)
    if reliability is None:
        reliability = getattr(mod, "uptime", 1.0)
    return _clamp01(reliability if reliability is not None else 1.0)


def enforcement_capacity(world: Any, rule: SanctionRule, *, day: int) -> float:
    cfg = ensure_sanctions_config(world)
    customs_bias = getattr(getattr(world, "customs_cfg", None), "base_inspection_rate", 0.0)
    crackdown_bias = 0.0
    ward_state = getattr(world, "enf_state_by_ward", {}).get(rule.target_id)
    if ward_state is not None:
        crackdown_bias = float(getattr(ward_state, "posture", 0.0))
    base = 0.2 + 0.4 * float(rule.enforcement_required) + customs_bias * 0.5 + crackdown_bias * 0.25
    comms_penalty = (1.0 - _comms_reliability(world, rule)) * cfg.comms_penalty_scale
    return _clamp01(base - comms_penalty)


def compute_leak_rate(
    world: Any,
    rule: SanctionRule,
    *,
    day: int,
    smuggling_strength: float | None = None,
    enforcement_override: float | None = None,
) -> float:
    cfg = ensure_sanctions_config(world)
    enforcement = enforcement_override if enforcement_override is not None else enforcement_capacity(world, rule, day=day)
    smuggling = smuggling_strength
    if smuggling is None:
        smuggling = 0.0
        smuggling_cfg = getattr(world, "smuggling_cfg", None)
        if getattr(smuggling_cfg, "enabled", False):
            smuggling = 0.25
    leak = cfg.base_leak_rate * (1.0 + smuggling) * (1.0 - enforcement * cfg.enforcement_effect)
    if getattr(getattr(world, "shadow_cfg", None), "enabled", False):
        enforcement_score = _clamp01(1.0 - leak)
        ward_id = rule.target_id if rule.target_kind == "WARD" else None
        adjusted_enforcement, audit_flags = apply_capture_modifier(world, ward_id, "CUSTOMS", enforcement_score)
        if audit_flags:
            record_event(world, {"type": "CAPTURE_APPLIED", "ward_id": ward_id, "domain": "CUSTOMS", "flags": audit_flags})
        leak = _clamp01(1.0 - adjusted_enforcement)
    return _clamp01(leak)


def _edge_ward(world: Any, edge_key: str) -> str | None:
    survey_map = getattr(world, "survey_map", None)
    if survey_map is None:
        return None
    edge = getattr(survey_map, "edges", {}).get(edge_key)
    if edge is None:
        return None
    node_a = getattr(survey_map, "nodes", {}).get(getattr(edge, "a", None))
    ward_id = getattr(node_a, "ward_id", None)
    return ward_id if ward_id is not None else getattr(edge, "ward_id", None)


def is_transit_denied(
    world: Any,
    edge_key: str,
    *,
    actor_faction_id: str | None,
    actor_ward_id: str | None,
    day: int,
) -> bool:
    cfg = ensure_sanctions_config(world)
    if not cfg.enabled:
        return False
    for rule in _active_rules(world, day=day, kinds={"TRANSIT_DENIAL"}):
        if rule.target_kind == "CORRIDOR" and rule.target_id == edge_key:
            return True
        if rule.target_kind == "FACTION" and actor_faction_id and rule.target_id == actor_faction_id:
            return True
        ward_match = actor_ward_id == rule.target_id or _edge_ward(world, edge_key) == rule.target_id
        if rule.target_kind == "WARD" and ward_match:
            return True
    return False


def evaluate_sanctioned_flow(
    world: Any,
    *,
    goods: Iterable[str],
    actor_faction_id: str | None,
    actor_ward_id: str | None,
    day: int,
    base_cost: float = 0.0,
) -> dict[str, float | bool]:
    cfg = ensure_sanctions_config(world)
    metrics = ensure_metrics(world)
    normalized_goods = _normalize_goods(goods)
    blocked = False
    tariff_multiplier = 1.0
    leak_rate = 0.0
    penalties = 0.0
    if not cfg.enabled:
        return {
            "cost": base_cost,
            "blocked": False,
            "tariff_multiplier": tariff_multiplier,
            "leak_rate": leak_rate,
            "penalties": penalties,
        }

    for rule in _active_rules(world, day=day):
        if normalized_goods and rule.goods and not set(normalized_goods).intersection(rule.goods):
            continue
        enforcement = enforcement_capacity(world, rule, day=day)
        leak = compute_leak_rate(world, rule, day=day, enforcement_override=enforcement)
        leak_rate = max(leak_rate, leak)
        if rule.kind == "TRANSIT_DENIAL":
            blocked = True
            continue
        if rule.kind == "EMBARGO_GOOD":
            blocked = True
            penalties += cfg.penalty_scale * float(rule.severity)
            continue
        if rule.kind == "TARIFF_PUNITIVE":
            tariff_multiplier *= 1.0 + float(rule.severity) * (1.0 + enforcement)
            continue
        if rule.kind == "FINANCIAL_FREEZE":
            penalties += cfg.penalty_scale * float(rule.severity) * (1.0 + enforcement)

    tariff_multiplier = max(1.0, tariff_multiplier)
    metrics.set_gauge("sanctions.rules_active", len(ensure_sanction_rules(world)))
    metrics.set_gauge("sanctions.leak_rate", leak_rate)
    cost = base_cost * tariff_multiplier
    return {
        "cost": cost,
        "blocked": blocked,
        "tariff_multiplier": tariff_multiplier,
        "leak_rate": leak_rate,
        "penalties": penalties,
    }


def update_compliance(world: Any, *, target_id: str, leak_rate: float, penalties: float, day: int) -> SanctionsCompliance:
    compliance = ensure_sanctions_compliance(world)
    entry = compliance.get(target_id)
    if entry is None:
        entry = SanctionsCompliance(entity_id=target_id)
        compliance[target_id] = entry
    entry.violations_lookback = min(entry.violations_lookback + int(round(leak_rate * 10)), 999)
    entry.leak_rate_est = leak_rate
    entry.penalties_applied = penalties
    entry.last_update_day = day
    return entry


def record_sanction_event(world: Any, *, event_type: str, payload: dict[str, object]) -> None:
    events = ensure_sanctions_events(world)
    events.append({"type": event_type, **payload})
    if len(events) > 500:
        del events[: len(events) - 500]
    record_event(world, event_type, payload)


def sanctions_price_multiplier(world: Any, *, material: str, day: int) -> float:
    result = evaluate_sanctioned_flow(world, goods=[material], actor_faction_id=None, actor_ward_id=None, day=day, base_cost=1.0)
    multiplier = float(result.get("tariff_multiplier", 1.0))
    if result.get("blocked"):
        cfg = ensure_sanctions_config(world)
        multiplier += cfg.penalty_scale
    return multiplier


def apply_sanctions_to_market_signal(world: Any, signal, *, day: int) -> None:
    try:
        multiplier = sanctions_price_multiplier(world, material=getattr(signal, "material", ""), day=day)
    except Exception:
        multiplier = 1.0
    if multiplier <= 1.0:
        return
    signal.urgency = _clamp01(float(signal.urgency) * multiplier)
    notes = getattr(signal, "notes", None)
    if isinstance(notes, dict):
        notes["sanctions_multiplier"] = multiplier


__all__ = [
    "SanctionsConfig",
    "SanctionRule",
    "SanctionsCompliance",
    "ensure_sanctions_config",
    "ensure_sanction_rules",
    "ensure_sanctions_compliance",
    "ensure_sanctions_events",
    "register_sanction_rule",
    "enforcement_capacity",
    "compute_leak_rate",
    "is_transit_denied",
    "evaluate_sanctioned_flow",
    "update_compliance",
    "record_sanction_event",
    "sanctions_price_multiplier",
    "apply_sanctions_to_market_signal",
]

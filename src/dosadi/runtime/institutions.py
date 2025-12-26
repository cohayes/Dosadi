from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.world.phases import WorldPhase
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode


@dataclass(slots=True)
class InstitutionConfig:
    enabled: bool = False
    max_active_wards_per_day: int = 24
    issue_topk: int = 12
    deterministic_salt: str = "institutions-v1"
    phase_defaults: dict[str, dict[str, float]] = field(
        default_factory=lambda: {
            "P0": {
                "legitimacy": 0.72,
                "discipline": 0.55,
                "corruption": 0.08,
                "audit": 0.25,
            },
            "P1": {
                "legitimacy": 0.62,
                "discipline": 0.60,
                "corruption": 0.14,
                "audit": 0.24,
            },
            "P2": {
                "legitimacy": 0.48,
                "discipline": 0.54,
                "corruption": 0.22,
                "audit": 0.20,
            },
        }
    )
    daily_delta_caps: dict[str, float] = field(
        default_factory=lambda: {
            "legitimacy": 0.02,
            "corruption": 0.03,
            "audit": 0.02,
            "discipline": 0.02,
        }
    )


@dataclass(slots=True)
class WardInstitutionPolicy:
    ward_id: str
    ration_strictness: float = 0.3
    levy_rate: float = 0.05
    enforcement_budget_points: float = 10.0
    audit_budget_points: float = 2.0
    research_budget_points: float = 0.0
    posture: str = "balanced"
    customs_inspection_bias: float = 0.0
    customs_tariff_bias: float = 0.0
    customs_contraband_bias: float = 0.0
    customs_bribe_tolerance: float = 0.1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class WardInstitutionState:
    ward_id: str
    legitimacy: float = 0.7
    discipline: float = 0.5
    corruption: float = 0.1
    audit: float = 0.2
    unrest: float = 0.0
    last_updated_day: int = -1
    recent_issue_scores: dict[str, float] = field(default_factory=dict)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _phase_key(world: Any) -> str:
    phase_state = getattr(world, "phase_state", None)
    phase = getattr(phase_state, "phase", WorldPhase.PHASE0)
    try:
        phase_enum = WorldPhase(phase)
    except Exception:
        phase_enum = WorldPhase.PHASE0
    return f"P{int(phase_enum.value)}"


def ensure_inst_config(world: Any) -> InstitutionConfig:
    cfg = getattr(world, "inst_cfg", None)
    if not isinstance(cfg, InstitutionConfig):
        cfg = InstitutionConfig()
        world.inst_cfg = cfg
    return cfg


def ensure_policy(world: Any, ward_id: str) -> WardInstitutionPolicy:
    policies: dict[str, WardInstitutionPolicy] = getattr(world, "inst_policy_by_ward", {}) or {}
    policy = policies.get(ward_id)
    if not isinstance(policy, WardInstitutionPolicy):
        policy = WardInstitutionPolicy(ward_id=ward_id)
        policies[ward_id] = policy
    world.inst_policy_by_ward = policies
    return policy


def ensure_state(world: Any, ward_id: str, *, cfg: InstitutionConfig | None = None) -> WardInstitutionState:
    cfg = cfg or ensure_inst_config(world)
    states: dict[str, WardInstitutionState] = getattr(world, "inst_state_by_ward", {}) or {}
    state = states.get(ward_id)
    if not isinstance(state, WardInstitutionState):
        defaults = cfg.phase_defaults.get(_phase_key(world), cfg.phase_defaults.get("P0", {}))
        state = WardInstitutionState(
            ward_id=ward_id,
            legitimacy=float(defaults.get("legitimacy", 0.7)),
            discipline=float(defaults.get("discipline", 0.5)),
            corruption=float(defaults.get("corruption", 0.1)),
            audit=float(defaults.get("audit", 0.2)),
        )
        states[ward_id] = state
    world.inst_state_by_ward = states
    return state


def _ward_for_edge(survey_map: SurveyMap | None, edge_key: str) -> str:
    if survey_map is None:
        return "unknown"
    edge: SurveyEdge | None = getattr(survey_map, "edges", {}).get(edge_key)
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


def _ward_for_location(world: Any, location_id: str | None) -> str | None:
    if not location_id:
        return None
    survey_map: SurveyMap | None = getattr(world, "survey_map", None)
    if survey_map is None:
        return None
    node: SurveyNode | None = getattr(survey_map, "nodes", {}).get(location_id)
    return getattr(node, "ward_id", None)


def _global_shortage_pressure(world: Any) -> float:
    state = getattr(world, "market_state", None)
    if state is None:
        return 0.0
    signals = getattr(state, "global_signals", {}) or {}
    urgencies = [float(getattr(sig, "urgency", 0.0) or 0.0) for sig in signals.values()]
    if not urgencies:
        return 0.0
    return _clamp01(max(urgencies))


def _ward_shortage(world: Any, ward_id: str) -> float:
    wards = getattr(world, "wards", {}) or {}
    ward = wards.get(ward_id)
    need_index = float(getattr(ward, "need_index", 0.0) or 0.0) if ward else 0.0
    global_pressure = _global_shortage_pressure(world)
    combined = 0.6 * need_index + 0.4 * global_pressure
    return _clamp01(combined)


def _ward_risk(world: Any, ward_id: str) -> float:
    ledger = getattr(world, "risk_ledger", None)
    survey_map: SurveyMap | None = getattr(world, "survey_map", None)
    if ledger is None or survey_map is None:
        return 0.0
    risks: list[float] = []
    for edge_key, rec in getattr(ledger, "edges", {}).items():
        if _ward_for_edge(survey_map, edge_key) != ward_id:
            continue
        risks.append(_clamp01(float(getattr(rec, "risk", 0.0) or 0.0)))
        incidents = float(getattr(rec, "incidents_lookback", 0.0) or 0.0)
        if incidents > 0:
            risks.append(_clamp01(0.1 * incidents))
    if not risks:
        return 0.0
    return _clamp01(sum(risks) / len(risks))


def _ward_traffic(world: Any, ward_id: str) -> float:
    ledger = getattr(world, "logistics", None)
    survey_map: SurveyMap | None = getattr(world, "survey_map", None)
    if ledger is None or survey_map is None:
        return 0.0
    score = 0.0
    for delivery_id in getattr(ledger, "active_ids", ()) or ():
        delivery = getattr(ledger, "deliveries", {}).get(delivery_id)
        if delivery is None:
            continue
        for edge_key in getattr(delivery, "route_edge_keys", ()) or ():
            if _ward_for_edge(survey_map, edge_key) == ward_id:
                score += 1.0
    return _clamp01(score / 10.0)


def _ward_faction_pressure(world: Any, ward_id: str) -> float:
    territories: Mapping[str, Any] = getattr(world, "faction_territory", {}) or {}
    claims: list[float] = []
    for territory in territories.values():
        ward_claims = getattr(territory, "wards", {}) or {}
        claim = float(ward_claims.get(ward_id, 0.0) or 0.0)
        if claim > 0:
            claims.append(_clamp01(claim))
    if not claims:
        return 0.0
    strongest = max(claims)
    second = max((c for c in claims if c != strongest), default=0.0)
    contest = strongest - second
    return _clamp01(strongest * (1.0 - contest))


def _ward_belief_anger(world: Any, ward_id: str) -> float:
    agents = getattr(world, "agents", {}) or {}
    survey_map: SurveyMap | None = getattr(world, "survey_map", None)
    if not agents or survey_map is None:
        return 0.0
    stress_scores: list[float] = []
    for agent in agents.values():
        loc_ward = _ward_for_location(world, getattr(agent, "location_id", None))
        if loc_ward != ward_id:
            continue
        physical = getattr(agent, "physical", None)
        if physical is None:
            continue
        stress_scores.append(_clamp01(float(getattr(physical, "stress_level", 0.0) or 0.0)))
    if not stress_scores:
        return 0.0
    return _clamp01(sum(stress_scores) / len(stress_scores))


def _ward_corruption(world: Any, ward_id: str, audit_level: float) -> float:
    traffic = _ward_traffic(world, ward_id)
    return _clamp01(0.5 * traffic + 0.5 * (1.0 - audit_level))


def _issue_scores(world: Any, ward_id: str, *, cfg: InstitutionConfig) -> dict[str, float]:
    shortage = _ward_shortage(world, ward_id)
    predation = _ward_risk(world, ward_id)
    belief_anger = _ward_belief_anger(world, ward_id)
    faction_pressure = _ward_faction_pressure(world, ward_id)
    traffic = _ward_traffic(world, ward_id)
    corruption_opportunity = _ward_corruption(world, ward_id, audit_level=ensure_state(world, ward_id, cfg=cfg).audit)
    wear = 0.0
    wards = getattr(world, "wards", {}) or {}
    ward = wards.get(ward_id)
    if ward is not None:
        wear = _clamp01(1.0 - float(getattr(ward.infrastructure, "maintenance_index", 1.0)))
    issues: dict[str, float] = {
        "issue:shortage": shortage,
        "issue:predation": predation,
        "issue:wear": wear,
        "issue:corruption_opportunity": corruption_opportunity,
        "issue:belief_anger": belief_anger,
        "issue:faction_pressure": faction_pressure,
    }
    ranked = sorted(issues.items(), key=lambda item: (-round(item[1], 6), item[0]))
    return dict(ranked[: max(1, int(cfg.issue_topk))])


def _activity_score(issues: Mapping[str, float]) -> float:
    shortage = issues.get("issue:shortage", 0.0)
    predation = issues.get("issue:predation", 0.0)
    belief_anger = issues.get("issue:belief_anger", 0.0)
    faction_pressure = issues.get("issue:faction_pressure", 0.0)
    corruption = issues.get("issue:corruption_opportunity", 0.0)
    return 0.32 * shortage + 0.22 * predation + 0.16 * belief_anger + 0.14 * faction_pressure + 0.16 * corruption


def select_active_wards(world: Any, *, cfg: InstitutionConfig) -> list[tuple[str, dict[str, float]]]:
    wards = sorted(getattr(world, "wards", {}).keys())
    survey_map: SurveyMap | None = getattr(world, "survey_map", None)
    if not wards and isinstance(survey_map, SurveyMap):
        wards = sorted({node.ward_id for node in survey_map.nodes.values() if node.ward_id})
    active: list[tuple[str, dict[str, float], float]] = []
    for ward_id in wards:
        issues = _issue_scores(world, ward_id, cfg=cfg)
        score = _activity_score(issues)
        if score <= 0.0:
            continue
        active.append((ward_id, issues, score))
    active.sort(key=lambda item: (-round(item[2], 6), item[0]))
    trimmed = active[: max(1, int(cfg.max_active_wards_per_day))]
    return [(ward_id, issues) for ward_id, issues, _ in trimmed]


def _apply_caps(value: float, delta: float, cap: float) -> float:
    bounded = max(-cap, min(cap, delta))
    return _clamp01(value + bounded)


def _update_state(world: Any, state: WardInstitutionState, issues: Mapping[str, float], *, cfg: InstitutionConfig) -> None:
    shortage = issues.get("issue:shortage", 0.0)
    predation = issues.get("issue:predation", 0.0)
    anger = issues.get("issue:belief_anger", 0.0)
    corruption_opportunity = issues.get("issue:corruption_opportunity", 0.0)

    leg_delta = 0.25 * (1.0 - shortage) + 0.20 * (1.0 - predation) - 0.35 * anger - 0.25 * corruption_opportunity
    dis_delta = 0.25 * (1.0 - corruption_opportunity) + 0.25 * (1.0 - anger) - 0.20 * predation + 0.10 * shortage
    corr_delta = 0.30 * shortage + 0.25 * predation + 0.20 * corruption_opportunity - 0.30 * state.audit
    audit_delta = 0.25 * (1.0 - corruption_opportunity) + 0.15 * (1.0 - predation) + 0.15 * state.legitimacy - 0.20 * shortage

    culture = getattr(world, "culture_by_ward", {}) or {}
    culture_state = culture.get(getattr(state, "ward_id", None) or ward_id)
    if culture_state is not None:
        anti_state = float(getattr(culture_state, "norms", {}).get("norm:anti_state", 0.0))
        queue_order = float(getattr(culture_state, "norms", {}).get("norm:queue_order", 0.0))
        leg_delta -= 0.15 * anti_state
        dis_delta += 0.10 * queue_order - 0.05 * anti_state
        audit_delta -= 0.05 * anti_state


    caps = cfg.daily_delta_caps
    state.legitimacy = _apply_caps(state.legitimacy, leg_delta * 0.1, caps.get("legitimacy", 0.02))
    state.discipline = _apply_caps(state.discipline, dis_delta * 0.1, caps.get("discipline", 0.02))
    state.corruption = _apply_caps(state.corruption, corr_delta * 0.1, caps.get("corruption", 0.03))
    state.audit = _apply_caps(state.audit, audit_delta * 0.1, caps.get("audit", 0.02))

    state.unrest = _clamp01(0.5 * shortage + 0.5 * anger + 0.4 * predation - 0.3 * state.legitimacy)
    if culture_state is not None:
        anti_state = float(getattr(culture_state, "norms", {}).get("norm:anti_state", 0.0))
        queue_order = float(getattr(culture_state, "norms", {}).get("norm:queue_order", 0.0))
        state.unrest = _clamp01(state.unrest + 0.25 * anti_state - 0.10 * queue_order)


def _auto_tune_policy(policy: WardInstitutionPolicy, issues: Mapping[str, float]) -> bool:
    changed = False
    shortage = issues.get("issue:shortage", 0.0)
    predation = issues.get("issue:predation", 0.0)
    corruption_opportunity = issues.get("issue:corruption_opportunity", 0.0)

    if shortage > 0.6:
        new_ration = _clamp01(policy.ration_strictness + 0.05)
        if abs(new_ration - policy.ration_strictness) > 1e-9:
            policy.ration_strictness = new_ration
            changed = True
    if predation > 0.5:
        new_budget = min(policy.enforcement_budget_points + 1.0, 20.0)
        if abs(new_budget - policy.enforcement_budget_points) > 1e-9:
            policy.enforcement_budget_points = new_budget
            changed = True
    if corruption_opportunity > 0.5:
        new_audit = min(policy.audit_budget_points + 0.5, 10.0)
        if abs(new_audit - policy.audit_budget_points) > 1e-9:
            policy.audit_budget_points = new_audit
            changed = True
    return changed


def _bucket(value: float) -> str:
    if value >= 0.75:
        return "high"
    if value >= 0.5:
        return "medium"
    return "low"


def _emit_belief_crumbs(world: Any, ward_id: str, state: WardInstitutionState, *, day: int) -> None:
    agents = getattr(world, "agents", {}) or {}
    if not agents:
        return
    legitimacy_bucket = _bucket(state.legitimacy)
    corruption_bucket = _bucket(state.corruption)
    for agent in agents.values():
        loc_ward = _ward_for_location(world, getattr(agent, "location_id", None))
        if loc_ward != ward_id:
            continue
        crumbs = getattr(agent, "crumbs", None)
        if crumbs is None:
            continue
        crumbs.bump(f"institution_legitimacy:{ward_id}:{legitimacy_bucket}", day)
        crumbs.bump(f"institution_corruption:{ward_id}:{corruption_bucket}", day)


def _sync_enforcement_budget(world: Any, policy: WardInstitutionPolicy) -> None:
    policies: dict[str, Any] = getattr(world, "enf_policy_by_ward", {}) or {}
    enf_policy = policies.get(policy.ward_id)
    if enf_policy is not None and hasattr(enf_policy, "budget_points"):
        enf_policy.budget_points = policy.enforcement_budget_points
        policies[policy.ward_id] = enf_policy
        world.enf_policy_by_ward = policies


def run_institutions_for_day(world: Any, *, day: int) -> None:
    cfg = ensure_inst_config(world)
    if not cfg.enabled:
        return
    metrics = ensure_metrics(world)
    active = select_active_wards(world, cfg=cfg)
    wards_updated = 0
    legitimacy_scores: list[float] = []
    corruption_scores: list[float] = []
    unrest_scores: list[float] = []

    for ward_id, issues in active:
        state = ensure_state(world, ward_id, cfg=cfg)
        policy = ensure_policy(world, ward_id)
        state.recent_issue_scores = dict(issues)
        _update_state(world, state, issues, cfg=cfg)
        changed = _auto_tune_policy(policy, issues)
        state.last_updated_day = day
        wards_updated += 1
        legitimacy_scores.append(state.legitimacy)
        corruption_scores.append(state.corruption)
        unrest_scores.append(state.unrest)

        _emit_belief_crumbs(world, ward_id, state, day=day)
        _sync_enforcement_budget(world, policy)

        record_event(
            world,
            {
                "type": "INST_UPDATED",
                "ward_id": ward_id,
                "issues": dict(issues),
                "day": day,
            },
        )
        if changed:
            record_event(
                world,
                {
                    "type": "INST_POLICY_ADJUSTED",
                    "ward_id": ward_id,
                    "policy": {
                        "ration_strictness": policy.ration_strictness,
                        "enforcement_budget_points": policy.enforcement_budget_points,
                        "audit_budget_points": policy.audit_budget_points,
                    },
                    "day": day,
                },
            )

        metrics.topk_add(
            "institutions.most_corrupt_wards",
            ward_id,
            state.corruption,
            payload={"issues": dict(issues)},
        )
        metrics.topk_add(
            "institutions.most_unrest_wards",
            ward_id,
            state.unrest,
            payload={"issues": dict(issues)},
        )
        metrics.topk_add(
            "institutions.biggest_policy_shifts",
            ward_id,
            policy.enforcement_budget_points + policy.audit_budget_points,
            payload={"ration_strictness": policy.ration_strictness},
        )

    metrics.set_gauge("institutions.wards_updated", wards_updated)
    if legitimacy_scores:
        metrics.set_gauge("institutions.avg_legitimacy", sum(legitimacy_scores) / len(legitimacy_scores))
    if corruption_scores:
        metrics.set_gauge("institutions.avg_corruption", sum(corruption_scores) / len(corruption_scores))
    if unrest_scores:
        metrics.set_gauge("institutions.avg_unrest", sum(unrest_scores) / len(unrest_scores))


def institution_seed_payload(world: Any) -> dict[str, Any] | None:
    cfg = getattr(world, "inst_cfg", None)
    if not isinstance(cfg, InstitutionConfig) or not cfg.enabled:
        return None
    policies: Mapping[str, WardInstitutionPolicy] = getattr(world, "inst_policy_by_ward", {}) or {}
    states: Mapping[str, WardInstitutionState] = getattr(world, "inst_state_by_ward", {}) or {}
    entries: list[dict[str, Any]] = []
    for ward_id in sorted(set(policies.keys()) | set(states.keys())):
        policy = policies.get(ward_id)
        state = states.get(ward_id)
        entry: dict[str, Any] = {"ward_id": ward_id}
        if isinstance(policy, WardInstitutionPolicy):
            entry["policy"] = {
                "ration_strictness": policy.ration_strictness,
                "levy_rate": policy.levy_rate,
                "enforcement_budget_points": policy.enforcement_budget_points,
                "audit_budget_points": policy.audit_budget_points,
                "research_budget_points": policy.research_budget_points,
                "posture": policy.posture,
            }
        if isinstance(state, WardInstitutionState):
            entry["state"] = {
                "legitimacy": state.legitimacy,
                "discipline": state.discipline,
                "corruption": state.corruption,
                "audit": state.audit,
                "unrest": state.unrest,
                "last_updated_day": state.last_updated_day,
            }
        entries.append(entry)
    return {"schema": "institutions_v1", "wards": entries}


def save_institutions_seed(world: Any, path) -> None:
    payload = institution_seed_payload(world)
    if payload is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)


def institutions_signature(world: Any) -> str:
    payload = institution_seed_payload(world) or {}
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(data.encode("utf-8")).hexdigest()


__all__ = [
    "InstitutionConfig",
    "WardInstitutionPolicy",
    "WardInstitutionState",
    "ensure_inst_config",
    "ensure_policy",
    "ensure_state",
    "institution_seed_payload",
    "institutions_signature",
    "run_institutions_for_day",
    "save_institutions_seed",
    "select_active_wards",
]

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Mapping

from dosadi.runtime.telemetry import ensure_metrics
from dosadi.world.incidents import Incident, IncidentKind, IncidentLedger
from dosadi.world.phases import WorldPhase


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _phase(world: Any) -> WorldPhase:
    phase_state = getattr(world, "phase_state", None)
    phase = getattr(phase_state, "phase", WorldPhase.PHASE0)
    try:
        return WorldPhase(phase)
    except Exception:
        return WorldPhase.PHASE0


def _pseudo_rand01(*parts: object) -> float:
    blob = "|".join(str(p) for p in parts)
    digest = sha256(blob.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


@dataclass(slots=True)
class GovernanceFailureConfig:
    enabled: bool = False
    max_new_incidents_per_day: int = 2
    active_wards_cap: int = 24
    deterministic_salt: str = "govfail-v1"
    base_rates_by_phase: dict[str, dict[str, float]] = field(
        default_factory=lambda: {
            "P0": {"STRIKE": 0.18, "RIOT": 0.08},
            "P1": {"STRIKE": 0.28, "RIOT": 0.18},
            "P2": {"STRIKE": 0.36, "RIOT": 0.28},
        }
    )
    cooldown_days_by_kind: dict[str, int] = field(
        default_factory=lambda: {"STRIKE": 5, "RIOT": 4}
    )
    severity_caps_by_kind: dict[str, float] = field(
        default_factory=lambda: {"STRIKE": 0.9, "RIOT": 0.95}
    )


@dataclass(slots=True)
class GovernanceIncidentRecord:
    incident_id: str
    kind: IncidentKind
    ward_id: str
    severity: float
    remaining_days: int
    duration_days: int
    faction_id: str | None = None
    status: str = "active"


@dataclass(slots=True)
class WardGovernanceEffects:
    production_multiplier: float = 1.0
    delivery_disruption_prob: float = 0.0


@dataclass(slots=True)
class GovernanceFailureState:
    last_run_day: int = -1
    next_incident_seq: int = 0
    cooldowns: dict[str, dict[str, int]] = field(default_factory=dict)
    active_by_ward: dict[str, list[GovernanceIncidentRecord]] = field(default_factory=dict)
    effects_by_ward: dict[str, WardGovernanceEffects] = field(default_factory=dict)


def ensure_govfail_config(world: Any) -> GovernanceFailureConfig:
    cfg = getattr(world, "govfail_cfg", None)
    if not isinstance(cfg, GovernanceFailureConfig):
        cfg = GovernanceFailureConfig()
        world.govfail_cfg = cfg
    return cfg


def ensure_govfail_state(world: Any) -> GovernanceFailureState:
    state = getattr(world, "govfail_state", None)
    if not isinstance(state, GovernanceFailureState):
        state = GovernanceFailureState()
        world.govfail_state = state
    return state


def _ensure_incident_ledger(world: Any) -> IncidentLedger:
    ledger = getattr(world, "incidents", None)
    if not isinstance(ledger, IncidentLedger):
        ledger = IncidentLedger()
        world.incidents = ledger
    return ledger


def _phase_key(world: Any) -> str:
    return f"P{int(_phase(world).value)}"


def _ward_candidates(world: Any, *, cap: int) -> list[str]:
    survey_map = getattr(world, "survey_map", None)
    wards: set[str] = set()
    if survey_map is not None:
        for node in getattr(survey_map, "nodes", {}).values():
            ward_id = getattr(node, "ward_id", None)
            if ward_id is not None:
                wards.add(str(ward_id))
    ordered = sorted(wards)
    return ordered[: max(0, int(cap))]


def _institution_triggers(world: Any, ward_id: str) -> dict[str, float]:
    inst_state = getattr(world, "inst_state_by_ward", {}).get(ward_id)
    if inst_state is None:
        return {"legitimacy": 0.0, "discipline": 0.0, "corruption": 0.0, "unrest": 0.0, "audit": 0.0}
    return {
        "legitimacy": _clamp01(getattr(inst_state, "legitimacy", 0.0)),
        "discipline": _clamp01(getattr(inst_state, "discipline", 0.0)),
        "corruption": _clamp01(getattr(inst_state, "corruption", 0.0)),
        "unrest": _clamp01(getattr(inst_state, "unrest", 0.0)),
        "audit": _clamp01(getattr(inst_state, "audit", 0.0)),
    }


def _culture_triggers(world: Any, ward_id: str) -> dict[str, float]:
    culture_state = getattr(world, "culture_by_ward", {}).get(ward_id)
    norms = getattr(culture_state, "norms", {}) if culture_state is not None else {}
    return {
        "anti_state": _clamp01(norms.get("norm:anti_state", 0.0)),
        "queue_order": _clamp01(norms.get("norm:queue_order", 0.0)),
        "vigilante": _clamp01(norms.get("norm:vigilante_justice", 0.0)),
    }


def _mitigation_score(inst: Mapping[str, float], enforcement_cover: float) -> float:
    legitimacy = inst.get("legitimacy", 0.0)
    discipline = inst.get("discipline", 0.0)
    corruption = inst.get("corruption", 0.0)
    return _clamp01(0.4 * legitimacy + 0.3 * discipline + 0.2 * enforcement_cover - 0.3 * corruption)


def _enforcement_cover(world: Any, ward_id: str) -> float:
    policies = getattr(world, "enf_policy_by_ward", {}) or {}
    policy = policies.get(ward_id)
    budget = float(getattr(policy, "budget_points", 0.0) or 0.0)
    states = getattr(world, "enf_state_by_ward", {}) or {}
    state = states.get(ward_id)
    patrols = 0
    checkpoints = 0
    if state is not None:
        patrols = sum(int(v) for v in getattr(state, "patrol_edges", {}).values())
        checkpoints = sum(int(v) for v in getattr(state, "checkpoints", {}).values())
    cover = budget / 25.0 + 0.03 * patrols + 0.05 * checkpoints
    return _clamp01(cover)


def _propensity_scores(world: Any, ward_id: str) -> dict[str, float]:
    inst = _institution_triggers(world, ward_id)
    culture = _culture_triggers(world, ward_id)
    enforcement_cover = _enforcement_cover(world, ward_id)
    mitigation = _mitigation_score(inst, enforcement_cover)

    shortage = float(getattr(world, "market_shortage_pressure", 0.0) or 0.0)
    unrest = inst["unrest"]
    corruption = inst["corruption"]
    legitimacy = inst["legitimacy"]
    discipline = inst["discipline"]
    anti_state = culture["anti_state"]
    queue_order = culture["queue_order"]

    strike_score = max(0.0, shortage * 0.6 + unrest * 0.35 - mitigation * 0.4)
    riot_score = max(0.0, unrest * 0.4 + anti_state * 0.25 + (1.0 - queue_order) * 0.2 - mitigation * 0.35)
    secession_score = max(0.0, anti_state * 0.2 + (1.0 - legitimacy) * 0.4 + corruption * 0.1 - mitigation * 0.1)
    coup_plot_score = max(0.0, corruption * 0.3 + (1.0 - discipline) * 0.2 + (1.0 - inst.get("audit", 0.0)) * 0.2 - mitigation * 0.25)

    return {
        "STRIKE": _clamp01(strike_score),
        "RIOT": _clamp01(riot_score),
        "SECESSION_ATTEMPT": _clamp01(secession_score),
        "COUP_PLOT": _clamp01(coup_plot_score),
    }


def _phase_rate(cfg: GovernanceFailureConfig, phase_key: str, kind: str) -> float:
    rates = cfg.base_rates_by_phase.get(phase_key, cfg.base_rates_by_phase.get("P0", {}))
    return float(rates.get(kind, 0.0))


def _severity_for(kind: str, score: float, mitigation: float, cfg: GovernanceFailureConfig) -> float:
    cap = cfg.severity_caps_by_kind.get(kind, 0.9)
    raw = score * (1.0 - 0.4 * mitigation)
    return _clamp01(min(cap, raw))


def _duration_for(kind: str, severity: float, phase: WorldPhase) -> int:
    base = 2 + int(phase.value)
    return max(base, base + int(severity * 4))


def _record_effects(state: GovernanceFailureState) -> None:
    effects: dict[str, WardGovernanceEffects] = {}
    for ward_id, incidents in state.active_by_ward.items():
        prod_mult = 1.0
        disruption = 0.0
        for inc in incidents:
            if inc.status != "active":
                continue
            if inc.kind is IncidentKind.STRIKE:
                prod_mult *= max(0.0, 1.0 - 0.6 * inc.severity)
            elif inc.kind is IncidentKind.RIOT:
                disruption = max(disruption, 0.2 + 0.5 * inc.severity)
        effects[ward_id] = WardGovernanceEffects(
            production_multiplier=_clamp01(prod_mult),
            delivery_disruption_prob=_clamp01(disruption),
        )
    state.effects_by_ward = effects


def _add_to_ledger(ledger: IncidentLedger, incident: Incident) -> None:
    ledger.incidents[incident.incident_id] = incident


def _mark_history(ledger: IncidentLedger, incident_id: str) -> None:
    ledger.history.append(incident_id)
    if len(ledger.history) > 2000:
        ledger.history[:] = ledger.history[-2000:]


def _tick_active_incidents(world: Any, *, day: int, state: GovernanceFailureState) -> None:
    ledger = _ensure_incident_ledger(world)
    for ward_id, incidents in list(state.active_by_ward.items()):
        updated: list[GovernanceIncidentRecord] = []
        for inc in incidents:
            if inc.status != "active":
                updated.append(inc)
                continue
            inc.remaining_days -= 1
            if inc.remaining_days > 0:
                updated.append(inc)
                continue
            inc.status = "resolved"
            incident = ledger.incidents.get(inc.incident_id)
            if incident is not None:
                incident.resolved = True
                incident.resolved_day = day
                incident.status = "resolved"
                _mark_history(ledger, inc.incident_id)
            metrics = ensure_metrics(world)
            metrics.inc(f"govfail.resolved.{inc.kind.value}", 1.0)
        if updated:
            state.active_by_ward[ward_id] = updated
        else:
            state.active_by_ward.pop(ward_id, None)
    _record_effects(state)


def production_multiplier_for_ward(world: Any, ward_id: str | None) -> float:
    if ward_id is None:
        return 1.0
    state = getattr(world, "govfail_state", None)
    effects = getattr(state, "effects_by_ward", {}) if state is not None else {}
    effect = effects.get(str(ward_id)) if isinstance(effects, Mapping) else None
    if effect is None:
        return 1.0
    return float(getattr(effect, "production_multiplier", 1.0) or 1.0)


def delivery_disruption_prob_for_ward(world: Any, ward_id: str | None) -> float:
    if ward_id is None:
        return 0.0
    state = getattr(world, "govfail_state", None)
    effects = getattr(state, "effects_by_ward", {}) if state is not None else {}
    effect = effects.get(str(ward_id)) if isinstance(effects, Mapping) else None
    if effect is None:
        return 0.0
    return float(getattr(effect, "delivery_disruption_prob", 0.0) or 0.0)


def _maybe_spawn_incident(
    *,
    world: Any,
    ward_id: str,
    kind: str,
    score: float,
    mitigation: float,
    cfg: GovernanceFailureConfig,
    state: GovernanceFailureState,
    day: int,
) -> GovernanceIncidentRecord | None:
    cooldowns = state.cooldowns.setdefault(ward_id, {})
    last_day = cooldowns.get(kind, -10)
    cooldown_days = cfg.cooldown_days_by_kind.get(kind, 0)
    if cooldown_days > 0 and day - last_day < cooldown_days:
        return None

    phase = _phase(world)
    severity = _severity_for(kind, score, mitigation, cfg)
    duration = _duration_for(kind, severity, phase)

    state.next_incident_seq += 1
    inc_id = f"govfail:{day}:{state.next_incident_seq}"
    incident = Incident(
        incident_id=inc_id,
        kind=IncidentKind[kind],
        day=day,
        target_kind="ward",
        target_id=ward_id,
        severity=severity,
        payload={
            "ward_id": ward_id,
            "severity": severity,
            "duration_days": duration,
            "mitigation": mitigation,
        },
        created_day=day,
        status="active",
        duration_days=duration,
        cooldown_days=cfg.cooldown_days_by_kind.get(kind, 0),
    )
    _add_to_ledger(_ensure_incident_ledger(world), incident)
    cooldowns[kind] = day
    metrics = ensure_metrics(world)
    metrics.inc(f"govfail.spawned.{kind.lower()}", 1.0)
    return GovernanceIncidentRecord(
        incident_id=inc_id,
        kind=incident.kind,
        ward_id=ward_id,
        severity=severity,
        remaining_days=duration,
        duration_days=duration,
    )


def _candidate_score(cfg: GovernanceFailureConfig, phase_key: str, ward_id: str, kind: str, score: float) -> float:
    rate = _phase_rate(cfg, phase_key, kind)
    return _clamp01(rate * score)


def _rank_candidates(
    candidates: Iterable[tuple[str, str, float]], deterministic_salt: str
) -> List[tuple[str, str, float]]:
    ranked = []
    for ward_id, kind, score in candidates:
        tie = _pseudo_rand01(deterministic_salt, ward_id, kind)
        ranked.append((ward_id, kind, score, tie))
    ranked.sort(key=lambda itm: (-itm[2], itm[0], itm[1], itm[3]))
    return [(w, k, s) for w, k, s, _ in ranked]


def run_governance_failure_for_day(world: Any, *, day: int) -> None:
    cfg = ensure_govfail_config(world)
    state = ensure_govfail_state(world)
    if not cfg.enabled:
        return
    if state.last_run_day == day:
        return

    _tick_active_incidents(world, day=day, state=state)

    wards = _ward_candidates(world, cap=cfg.active_wards_cap)
    if not wards:
        state.last_run_day = day
        return

    phase_key = _phase_key(world)
    candidates: list[tuple[str, str, float]] = []
    mitigation_by_ward: Dict[str, float] = {}

    for ward_id in wards:
        propensities = _propensity_scores(world, ward_id)
        inst = _institution_triggers(world, ward_id)
        enforcement_cover = _enforcement_cover(world, ward_id)
        mitigation = _mitigation_score(inst, enforcement_cover)
        mitigation_by_ward[ward_id] = mitigation
        for kind, score in propensities.items():
            if kind not in {"STRIKE", "RIOT"}:
                continue
            candidate_score = _candidate_score(cfg, phase_key, ward_id, kind, score)
            if candidate_score <= 0.01:
                continue
            candidates.append((ward_id, kind, candidate_score))

    ranked = _rank_candidates(candidates, cfg.deterministic_salt)
    spawned = 0
    for ward_id, kind, score in ranked:
        if spawned >= cfg.max_new_incidents_per_day:
            break
        mitigation = mitigation_by_ward.get(ward_id, 0.0)
        record = _maybe_spawn_incident(
            world=world,
            ward_id=ward_id,
            kind=kind,
            score=score,
            mitigation=mitigation,
            cfg=cfg,
            state=state,
            day=day,
        )
        if record is None:
            continue
        incidents = state.active_by_ward.setdefault(ward_id, [])
        incidents.append(record)
        spawned += 1

    _record_effects(state)
    state.last_run_day = day


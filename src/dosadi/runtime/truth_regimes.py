from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.class_system import class_hardship
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.world.factions import pseudo_rand01
from dosadi.world.phases import WorldPhase


@dataclass(slots=True)
class TruthConfig:
    enabled: bool = False
    update_cadence_days: int = 30
    deterministic_salt: str = "truth-v1"
    max_fraud_events: int = 24
    drift_scale_p2: float = 0.03
    correction_scale: float = 0.04
    fraud_rate_base: float = 0.002
    truth_effect_scale: float = 0.25


@dataclass(slots=True)
class IntegrityState:
    scope_kind: str
    scope_id: str
    metrology: float = 1.0
    ledger: float = 1.0
    census: float = 1.0
    telemetry: float = 1.0
    judiciary: float = 1.0
    propaganda_pressure: float = 0.0
    audit_capacity: float = 0.5
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class TruthEvent:
    day: int
    scope_kind: str
    scope_id: str
    kind: str
    domain: str
    magnitude: float
    reason_codes: list[str]
    effects: dict[str, object] = field(default_factory=dict)


_DOMAIN_ATTR = {
    "METROLOGY": "metrology",
    "LEDGER": "ledger",
    "CENSUS": "census",
    "TELEMETRY": "telemetry",
    "JUDICIARY": "judiciary",
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _phase(world: Any) -> WorldPhase:
    phase_state = getattr(world, "phase_state", None)
    phase = getattr(phase_state, "phase", WorldPhase.PHASE0)
    try:
        return WorldPhase(phase)
    except Exception:
        return WorldPhase.PHASE0


def ensure_truth_config(world: Any) -> TruthConfig:
    cfg = getattr(world, "truth_cfg", None)
    if not isinstance(cfg, TruthConfig):
        cfg = TruthConfig()
        world.truth_cfg = cfg
    return cfg


def ensure_truth_ledgers(world: Any) -> tuple[dict[str, IntegrityState], dict[str, IntegrityState], list[TruthEvent]]:
    integrity_by_polity = getattr(world, "integrity_by_polity", None)
    if not isinstance(integrity_by_polity, dict):
        integrity_by_polity = {}
        world.integrity_by_polity = integrity_by_polity
    integrity_by_ward = getattr(world, "integrity_by_ward", None)
    if not isinstance(integrity_by_ward, dict):
        integrity_by_ward = {}
        world.integrity_by_ward = integrity_by_ward
    truth_events = getattr(world, "truth_events", None)
    if not isinstance(truth_events, list):
        truth_events = []
        world.truth_events = truth_events
    return integrity_by_polity, integrity_by_ward, truth_events


def _scope_signature(kind: str, scope_id: str, day: int, salt: str) -> str:
    parts = [salt, kind, scope_id, str(day)]
    digest = sha256("|".join(parts).encode("utf-8")).digest()
    return str(int.from_bytes(digest[:8], "big"))


def _baseline_propaganda(world: Any, ward_id: str) -> float:
    ideology_state = getattr(world, "ideology_by_ward", {}).get(ward_id)
    if ideology_state is None:
        return 0.0
    return _clamp01(getattr(ideology_state, "propaganda_intensity", 0.0))


def _capture_index(world: Any, ward_id: str) -> float:
    corruption_state = getattr(world, "corruption_by_ward", {}).get(ward_id)
    if corruption_state is None:
        return 0.0
    return _clamp01(getattr(corruption_state, "capture", 0.0))


def _audit_bonus(world: Any, ward_id: str) -> float:
    inst_state = getattr(world, "inst_state_by_ward", {}).get(ward_id)
    if inst_state is None:
        return 0.0
    return _clamp01(getattr(inst_state, "audit", 0.0))


def _ensure_integrity_entry(store: dict[str, IntegrityState], *, kind: str, scope_id: str) -> IntegrityState:
    entry = store.get(scope_id)
    if entry is None:
        entry = IntegrityState(scope_kind=kind, scope_id=scope_id)
        store[scope_id] = entry
    return entry


def _collect_wards(world: Any) -> list[str]:
    wards = getattr(world, "wards", {}) or {}
    return sorted(wards.keys())


def _collect_polities(world: Any) -> list[str]:
    polities: set[str] = set()
    polities.update((getattr(state, "id", pid) for pid, state in (getattr(world, "settlements", {}) or {}).items()))
    polities.update(getattr(world, "constitution_by_polity", {}).keys())
    polities.update(getattr(world, "leadership_by_polity", {}).keys())
    if not polities:
        polities.add("polity:central")
    return sorted(polities)


def _domain_score(state: IntegrityState) -> float:
    return sum(getattr(state, attr) for attr in _DOMAIN_ATTR.values()) / len(_DOMAIN_ATTR)


def _update_integrity(state: IntegrityState, *, drift: Mapping[str, float], correction: float) -> None:
    for attr in _DOMAIN_ATTR.values():
        value = getattr(state, attr)
        updated = _clamp01(value - drift.get(attr, 0.0) + correction)
        setattr(state, attr, updated)


def _bounded_events(events: list[TruthEvent], *, max_events: int) -> None:
    if len(events) <= max_events:
        return
    # Keep the most recent + largest magnitude events deterministically
    ranked = sorted(events, key=lambda evt: (evt.day, evt.magnitude, evt.scope_kind, evt.scope_id, evt.domain))
    keep = ranked[-max_events:]
    events[:] = keep


def _risk_score(state: IntegrityState, *, capture: float) -> float:
    integrity_gap = 1.0 - _clamp01(_domain_score(state))
    propaganda = _clamp01(state.propaganda_pressure)
    return _clamp01(0.45 * integrity_gap + 0.35 * propaganda + 0.2 * capture)


def _event_kind_for(domain: str, *, correcting: bool) -> str:
    if correcting:
        return "CORRECTION"
    if domain == "METROLOGY":
        return "METROLOGY_TAMPERED"
    if domain == "CENSUS":
        return "CENSUS_REWRITE"
    if domain == "LEDGER":
        return "LEDGER_FALSIFIED"
    if domain == "TELEMETRY":
        return "TELEMETRY_SPOOFED"
    return "JUDICIARY_RIGGED"


def _generate_events(
    *,
    candidates: Iterable[tuple[IntegrityState, float, float]],
    cfg: TruthConfig,
    day: int,
    events: list[TruthEvent],
) -> None:
    sorted_candidates = sorted(
        candidates, key=lambda itm: (-itm[1], itm[0].scope_kind, itm[0].scope_id)
    )[: max(0, int(cfg.max_fraud_events))]
    for state, risk, capture in sorted_candidates:
        domain_attr = min(_DOMAIN_ATTR.values(), key=lambda attr: getattr(state, attr))
        domain_key = next(key for key, attr in _DOMAIN_ATTR.items() if attr == domain_attr)
        correction = state.audit_capacity > 0.6 and risk < 0.6
        magnitude = _clamp01(0.1 + 0.6 * risk + 0.2 * capture)
        if correction:
            delta = cfg.correction_scale * magnitude
            setattr(state, domain_attr, _clamp01(getattr(state, domain_attr) + delta))
        else:
            penalty = cfg.truth_effect_scale * magnitude
            setattr(state, domain_attr, _clamp01(getattr(state, domain_attr) - penalty))
        reason_codes: list[str] = []
        if capture > 0.35:
            reason_codes.append("CAPTURE")
        if state.propaganda_pressure > 0.25:
            reason_codes.append("PROPAGANDA")
        if state.audit_capacity < 0.35:
            reason_codes.append("LOW_AUDIT")
        if getattr(state, domain_attr) < 0.75:
            reason_codes.append("DEGRADED")
        events.append(
            TruthEvent(
                day=day,
                scope_kind=state.scope_kind,
                scope_id=state.scope_id,
                kind=_event_kind_for(domain_key, correcting=correction),
                domain=domain_key,
                magnitude=round(magnitude, 6),
                reason_codes=reason_codes or ["DRIFT"],
                effects={"integrity": round(getattr(state, domain_attr), 6)},
            )
        )
    if len(events) > cfg.max_fraud_events:
        _bounded_events(events, max_events=cfg.max_fraud_events)
    events.sort(key=lambda evt: (evt.day, evt.magnitude, evt.scope_kind, evt.scope_id))


def _drift_for_state(
    state: IntegrityState,
    *,
    capture: float,
    hardship: float,
    phase: WorldPhase,
    cfg: TruthConfig,
) -> dict[str, float]:
    base = 0.004 + (cfg.drift_scale_p2 if phase == WorldPhase.PHASE2 else 0.0)
    propaganda = _clamp01(state.propaganda_pressure)
    audit_relief = 0.5 * cfg.correction_scale * _clamp01(state.audit_capacity)
    drifts: dict[str, float] = {}
    for domain, attr in _DOMAIN_ATTR.items():
        driver = base
        if domain in ("LEDGER", "TELEMETRY"):
            driver += 0.02 * capture + 0.015 * propaganda
        elif domain == "CENSUS":
            driver += 0.015 * hardship
        elif domain == "JUDICIARY":
            driver += 0.01 * capture
        else:
            driver += 0.01 * propaganda
        drifts[attr] = max(0.0, driver - audit_relief)
    return drifts


def _update_state_for_ward(world: Any, state: IntegrityState, *, day: int, cfg: TruthConfig, phase: WorldPhase) -> float:
    capture = _capture_index(world, state.scope_id)
    hardship = class_hardship(world, state.scope_id)
    propaganda = _baseline_propaganda(world, state.scope_id)
    state.propaganda_pressure = _clamp01(0.6 * state.propaganda_pressure + 0.4 * propaganda)
    state.audit_capacity = _clamp01(state.audit_capacity + 0.3 * _audit_bonus(world, state.scope_id))
    drift = _drift_for_state(state, capture=capture, hardship=hardship, phase=phase, cfg=cfg)
    correction = 0.35 * cfg.correction_scale * _clamp01(state.audit_capacity - 0.25 * state.propaganda_pressure)
    _update_integrity(state, drift=drift, correction=correction)
    state.last_update_day = day
    return capture


def _update_state_for_polity(world: Any, state: IntegrityState, *, day: int, cfg: TruthConfig, phase: WorldPhase) -> float:
    wards = _collect_wards(world)
    capture_values = [
        _capture_index(world, ward_id) for ward_id in wards
    ] or [0.0]
    propaganda_values = [
        _baseline_propaganda(world, ward_id) for ward_id in wards
    ] or [state.propaganda_pressure]
    hardship_values = [class_hardship(world, ward_id) for ward_id in wards] or [0.0]
    state.propaganda_pressure = _clamp01(
        0.5 * state.propaganda_pressure + 0.5 * (sum(propaganda_values) / len(propaganda_values))
    )
    state.audit_capacity = _clamp01(state.audit_capacity + 0.1 * (1.0 - state.audit_capacity))
    capture = max(capture_values)
    hardship = sum(hardship_values) / len(hardship_values)
    drift = _drift_for_state(state, capture=capture, hardship=hardship, phase=phase, cfg=cfg)
    correction = 0.35 * cfg.correction_scale * _clamp01(state.audit_capacity)
    _update_integrity(state, drift=drift, correction=correction)
    state.last_update_day = day
    return capture


def run_truth_regimes_update(world: Any, *, day: int) -> None:
    cfg = ensure_truth_config(world)
    if not cfg.enabled:
        return
    cadence = max(1, int(cfg.update_cadence_days))
    if day % cadence != 0:
        return

    integrity_by_polity, integrity_by_ward, events = ensure_truth_ledgers(world)
    phase = _phase(world)

    wards = _collect_wards(world)
    ward_captures: list[tuple[IntegrityState, float]] = []
    for ward_id in wards:
        state = _ensure_integrity_entry(integrity_by_ward, kind="WARD", scope_id=ward_id)
        if state.last_update_day == day:
            continue
        capture = _update_state_for_ward(world, state, day=day, cfg=cfg, phase=phase)
        ward_captures.append((state, capture))

    polities = _collect_polities(world)
    polity_captures: list[tuple[IntegrityState, float]] = []
    for polity_id in polities:
        state = _ensure_integrity_entry(integrity_by_polity, kind="POLITY", scope_id=polity_id)
        if state.last_update_day == day:
            continue
        capture = _update_state_for_polity(world, state, day=day, cfg=cfg, phase=phase)
        polity_captures.append((state, capture))

    candidates: list[tuple[IntegrityState, float, float]] = []
    for state, capture in ward_captures + polity_captures:
        risk = _risk_score(state, capture=capture)
        threshold = cfg.fraud_rate_base + 0.6 * risk
        key = _scope_signature(state.scope_kind, state.scope_id, day, cfg.deterministic_salt)
        roll = pseudo_rand01(key)
        if roll <= threshold:
            candidates.append((state, risk, capture))

    _generate_events(candidates=candidates, cfg=cfg, day=day, events=events)

    metrics = ensure_metrics(world)
    truth_gauge = metrics.gauges.setdefault("truth", {}) if hasattr(metrics, "gauges") else {}
    if isinstance(truth_gauge, dict):
        ward_scores = [_domain_score(state) for state, _ in ward_captures] or [1.0]
        polity_scores = [_domain_score(state) for state, _ in polity_captures] or [1.0]
        truth_gauge["avg_ward_integrity"] = round(sum(ward_scores) / len(ward_scores), 4)
        truth_gauge["avg_polity_integrity"] = round(sum(polity_scores) / len(polity_scores), 4)
        truth_gauge["events"] = len(events)


def measurement_noise(world: Any, scope: tuple[str, str] | str, domain: str) -> tuple[float, float, list[str]]:
    cfg = ensure_truth_config(world)
    if isinstance(scope, tuple):
        scope_kind, scope_id = scope
    elif isinstance(scope, str) and scope.startswith("ward:"):
        scope_kind, scope_id = "WARD", scope.split(":", 1)[1]
    else:
        scope_kind, scope_id = "POLITY", str(scope if isinstance(scope, str) else "polity:central")

    integrity_by_polity, integrity_by_ward, _ = ensure_truth_ledgers(world)
    if scope_kind == "WARD":
        state = integrity_by_ward.get(scope_id) or _ensure_integrity_entry(integrity_by_ward, kind="WARD", scope_id=scope_id)
    else:
        state = integrity_by_polity.get(scope_id) or _ensure_integrity_entry(
            integrity_by_polity, kind="POLITY", scope_id=scope_id
        )

    attr = _DOMAIN_ATTR.get(domain.upper(), "ledger")
    integrity = _clamp01(getattr(state, attr))
    bias = (1.0 - integrity) * cfg.truth_effect_scale * (1.0 + 0.5 * _clamp01(state.propaganda_pressure))
    variance = (1.0 - integrity) * (0.15 + 0.35 * (1.0 - _clamp01(state.audit_capacity)))
    flags: list[str] = []
    if integrity < 0.85:
        flags.append("LOW_INTEGRITY")
    if _clamp01(state.propaganda_pressure) > 0.35:
        flags.append("PROPAGANDA")
    if _clamp01(state.audit_capacity) < 0.4:
        flags.append("LOW_AUDIT")
    return round(bias, 6), round(variance, 6), flags


__all__ = [
    "IntegrityState",
    "TruthConfig",
    "TruthEvent",
    "ensure_truth_config",
    "ensure_truth_ledgers",
    "measurement_noise",
    "run_truth_regimes_update",
]

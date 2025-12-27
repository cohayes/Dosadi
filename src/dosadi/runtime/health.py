from __future__ import annotations

import random
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.class_system import class_hardship
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.state import WardState, WorldState

HEALTH_EVENT_KINDS = {"OUTBREAK_STARTED", "OUTBREAK_PEAK", "OUTBREAK_ENDED"}
DISEASE_RESPIRATORY = "RESPIRATORY"
DISEASE_WATERBORNE = "WATERBORNE"
DISEASE_WOUND = "WOUND_INFECTION"
DISEASES = (DISEASE_RESPIRATORY, DISEASE_WATERBORNE, DISEASE_WOUND)


@dataclass(slots=True)
class HealthConfig:
    enabled: bool = False
    update_cadence_days: int = 3
    deterministic_salt: str = "health-v1"
    baseline_chronic_rate: float = 0.02
    outbreak_trigger_rate: float = 0.01
    max_outbreak_intensity: float = 1.0
    spread_strength: float = 0.10
    recovery_per_update: float = 0.06
    mortality_per_update: float = 0.01
    event_history_limit: int = 200


@dataclass(slots=True)
class WardHealthState:
    ward_id: str
    chronic_burden: float = 0.0
    outbreaks: dict[str, float] = field(default_factory=dict)
    healthcare_cap: float = 0.0
    sanitation_cap: float = 0.0
    water_quality: float = 0.5
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class HealthEvent:
    day: int
    ward_id: str
    kind: str
    disease: str
    intensity: float
    reason_codes: list[str]


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _stable_rng(seed: int, day: int, salt: str) -> random.Random:
    digest = sha256(f"{seed}:{day}:{salt}".encode("utf-8")).hexdigest()
    return random.Random(int(digest, 16) % (2**32))


def _pseudo_rand01(seed: int, day: int, ward_id: str, disease: str, salt: str) -> float:
    digest = sha256(f"{salt}:{seed}:{day}:{ward_id}:{disease}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _bounded_append(events: list[HealthEvent], new_events: Iterable[HealthEvent], *, limit: int) -> None:
    events.extend(new_events)
    if len(events) > max(1, limit):
        events[:] = events[-limit:]


def _ensure_health(world: WorldState) -> tuple[HealthConfig, dict[str, WardHealthState], list[HealthEvent]]:
    cfg = getattr(world, "health_cfg", None)
    if not isinstance(cfg, HealthConfig):
        cfg = HealthConfig()
        world.health_cfg = cfg

    by_ward = getattr(world, "health_by_ward", None)
    if by_ward is None or not isinstance(by_ward, dict):
        by_ward = {}
        world.health_by_ward = by_ward

    events = getattr(world, "health_events", None)
    if events is None:
        events = []
        world.health_events = events

    return cfg, by_ward, events


def _ward_policy_bias(world: WorldState, ward_id: str) -> tuple[float, float]:
    policy = getattr(world, "inst_policy_by_ward", {}).get(ward_id, {})
    if not isinstance(policy, Mapping):
        return 0.0, 0.0
    public_health = float(policy.get("public_health_spend_bias", 0.0))
    quarantine = float(policy.get("quarantine_strictness", 0.0))
    return public_health, quarantine


def _update_caps_from_urban(world: WorldState, state: WardHealthState) -> None:
    urban_state = getattr(world, "urban_by_ward", {}).get(state.ward_id)
    if urban_state is None:
        return
    clinic_cap = 0.0
    sanitation_cap = 0.0
    water_cap = 0.0
    if isinstance(getattr(urban_state, "civic_cap", None), Mapping):
        clinic_cap = float(urban_state.civic_cap.get("clinic", 0.0))
    if isinstance(getattr(urban_state, "utility_cap", None), Mapping):
        sanitation_cap = float(urban_state.utility_cap.get("waste", 0.0))
        water_cap = float(urban_state.utility_cap.get("water", 0.0))
    state.healthcare_cap = max(state.healthcare_cap, _clamp(clinic_cap / 120.0))
    state.sanitation_cap = max(state.sanitation_cap, _clamp(sanitation_cap / 180.0))
    state.water_quality = _clamp(state.water_quality + water_cap / 400.0)


def _base_reason_codes(state: WardHealthState, ward: WardState | None) -> list[str]:
    reasons: list[str] = []
    if ward is not None and getattr(ward, "legitimacy", 0.5) < 0.4:
        reasons.append("low_legitimacy")
    if state.healthcare_cap < 0.2:
        reasons.append("low_healthcare")
    if state.sanitation_cap < 0.2:
        reasons.append("low_sanitation")
    return reasons or ["baseline"]


def _trigger_outbreaks(
    *,
    world: WorldState,
    cfg: HealthConfig,
    by_ward: dict[str, WardHealthState],
    events: list[HealthEvent],
    day: int,
) -> None:
    for ward_id in sorted(world.wards):
        ward = world.wards.get(ward_id)
        state = by_ward.get(ward_id)
        if state is None:
            state = WardHealthState(ward_id=ward_id)
            by_ward[ward_id] = state
        _update_caps_from_urban(world, state)

        state.chronic_burden = _clamp(state.chronic_burden + cfg.baseline_chronic_rate * (1.0 - state.healthcare_cap))
        state.last_update_day = day

        public_health_bias, quarantine_strictness = _ward_policy_bias(world, ward_id)
        migration_state = getattr(world, "migration_by_ward", {}).get(ward_id)
        camp_term = 0.0
        if migration_state is not None:
            camp_term = min(0.35, float(getattr(migration_state, "camp", 0)) / 4000.0)
        water_deficit = max(0.0, 1.0 - state.water_quality)
        raid_pressure = 0.0
        if getattr(world, "raid_history", None):
            raid_pressure = 0.05
        phase_multiplier = 1.0
        phase_state = getattr(world, "phase_state", None)
        if getattr(phase_state, "current_phase", 0) >= 2:
            phase_multiplier = 1.5

        mitigation = (state.healthcare_cap + state.sanitation_cap + max(0.0, public_health_bias)) * 0.15
        mitigation += quarantine_strictness * 0.05

        for disease in DISEASES:
            base = cfg.outbreak_trigger_rate * phase_multiplier
            disease_term = 0.0
            if disease == DISEASE_WATERBORNE:
                disease_term += water_deficit * 0.2
            if disease == DISEASE_WOUND:
                disease_term += raid_pressure
            if disease == DISEASE_RESPIRATORY:
                disease_term += 0.02 * max(0.0, 0.5 - getattr(ward, "legitimacy", 0.5))

            p_trigger = _clamp(base + camp_term + disease_term - mitigation)
            if disease in state.outbreaks:
                continue
            if p_trigger <= 0.0:
                continue
            roll = _pseudo_rand01(getattr(world, "seed", 0), day, ward_id, disease, cfg.deterministic_salt)
            if roll < p_trigger:
                state.outbreaks[disease] = 0.10
                events.append(
                    HealthEvent(
                        day=day,
                        ward_id=ward_id,
                        kind="OUTBREAK_STARTED",
                        disease=disease,
                        intensity=state.outbreaks[disease],
                        reason_codes=_base_reason_codes(state, ward),
                    )
                )

    _bounded_append(events, (), limit=cfg.event_history_limit)


def _evolve_outbreaks(
    *,
    world: WorldState,
    cfg: HealthConfig,
    by_ward: dict[str, WardHealthState],
    events: list[HealthEvent],
    day: int,
) -> None:
    new_events: list[HealthEvent] = []
    for ward_id in sorted(by_ward):
        ward_state = by_ward[ward_id]
        ward = world.wards.get(ward_id)
        public_health_bias, quarantine_strictness = _ward_policy_bias(world, ward_id)
        migration_state = getattr(world, "migration_by_ward", {}).get(ward_id)
        camp_term = 0.0
        if migration_state is not None:
            camp_term = min(0.3, float(getattr(migration_state, "camp", 0)) / 3000.0)
        legitimacy = getattr(ward, "legitimacy", 0.5) if ward else 0.5
        legitimacy_penalty = max(0.0, 0.6 - legitimacy) * 0.05
        water_deficit = max(0.0, 1.0 - ward_state.water_quality)

        updated: dict[str, float] = {}
        for disease, intensity in sorted(ward_state.outbreaks.items()):
            growth = 0.04 + camp_term * 0.4 + public_health_bias * 0.02
            if disease == DISEASE_WATERBORNE:
                growth += water_deficit * 0.3
            mitigation = cfg.recovery_per_update * (1.0 + ward_state.healthcare_cap + ward_state.sanitation_cap)
            mitigation += quarantine_strictness * 0.05
            recovery = cfg.recovery_per_update + legitimacy_penalty
            next_intensity = _clamp(intensity + growth - mitigation - recovery, hi=cfg.max_outbreak_intensity)
            if next_intensity >= 0.7 and ward_state.notes.get(f"{disease}:peak", False) is False:
                new_events.append(
                    HealthEvent(
                        day=day,
                        ward_id=ward_id,
                        kind="OUTBREAK_PEAK",
                        disease=disease,
                        intensity=next_intensity,
                        reason_codes=["intensity_high"],
                    )
                )
                ward_state.notes[f"{disease}:peak"] = True
            if next_intensity < 0.05:
                new_events.append(
                    HealthEvent(
                        day=day,
                        ward_id=ward_id,
                        kind="OUTBREAK_ENDED",
                        disease=disease,
                        intensity=0.0,
                        reason_codes=["recovery"],
                    )
                )
                ward_state.notes.pop(f"{disease}:peak", None)
                continue
            updated[disease] = next_intensity
        ward_state.outbreaks = updated
    _bounded_append(events, new_events, limit=cfg.event_history_limit)


def _corridor_pairs(world: WorldState) -> list[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for edge in getattr(world, "edges", {}).values():
        origin = getattr(edge, "origin", None) or getattr(edge, "a", None)
        destination = getattr(edge, "destination", None) or getattr(edge, "b", None)
        if origin and destination:
            pairs.add((str(origin), str(destination)))
            pairs.add((str(destination), str(origin)))
    if not pairs:
        ward_ids = sorted(world.wards)
        for idx, ward_id in enumerate(ward_ids):
            for other in ward_ids[idx + 1 :]:
                pairs.add((ward_id, other))
                pairs.add((other, ward_id))
    return sorted(pairs)


def _spread_outbreaks(world: WorldState, cfg: HealthConfig, by_ward: dict[str, WardHealthState]) -> None:
    deltas: dict[tuple[str, str], dict[str, float]] = {}
    for a, b in _corridor_pairs(world):
        ward_a = by_ward.get(a)
        ward_b = by_ward.get(b)
        if ward_a is None or ward_b is None:
            continue
        for disease in DISEASES:
            ia = ward_a.outbreaks.get(disease, 0.0)
            ib = ward_b.outbreaks.get(disease, 0.0)
            if ia <= ib:
                continue
            spill = (ia - ib) * cfg.spread_strength
            if spill <= 0:
                continue
            deltas.setdefault((a, b), {})[disease] = spill
    for (a, b), transfers in deltas.items():
        for disease, spill in transfers.items():
            from_state = by_ward.get(a)
            to_state = by_ward.get(b)
            if from_state is None or to_state is None:
                continue
            from_state.outbreaks[disease] = _clamp(from_state.outbreaks.get(disease, 0.0) - spill)
            to_state.outbreaks[disease] = _clamp(to_state.outbreaks.get(disease, 0.0) + spill)


def _apply_consequences(world: WorldState, by_ward: dict[str, WardHealthState]) -> None:
    metrics = ensure_metrics(world)
    health_bucket = metrics.gauges.get("health")
    if not isinstance(health_bucket, dict):
        health_bucket = {}
        metrics.gauges["health"] = health_bucket

    total_outbreaks = 0
    labor_mults: dict[str, float] = {}
    for ward_id, state in sorted(by_ward.items()):
        outbreak_sum = sum(state.outbreaks.values())
        total_outbreaks += int(outbreak_sum > 0)
        labor_mult = _clamp(1.0 - 0.3 * state.chronic_burden - 0.6 * outbreak_sum, lo=0.3, hi=1.0)
        state.notes["labor_mult"] = labor_mult
        labor_mults[ward_id] = labor_mult
        ward = world.wards.get(ward_id)
        if ward is not None:
            ward.risk_index = _clamp(ward.risk_index + outbreak_sum * 0.1, hi=2.0)
            migration_state = getattr(world, "migration_by_ward", {}).get(ward_id)
            if migration_state is not None:
                migration_state.notes["disease_pressure"] = outbreak_sum
                if outbreak_sum > 0.5:
                    ward.need_index = _clamp(ward.need_index + 0.05)
            hardship = class_hardship(world, ward_id)
            if hardship > 0.0:
                state.chronic_burden = _clamp(state.chronic_burden + 0.05 * hardship)
    health_bucket["outbreaks_active"] = total_outbreaks
    health_bucket["labor_mult_avg"] = sum(labor_mults.values()) / max(1, len(labor_mults))
    health_bucket["avg_chronic_burden"] = sum(state.chronic_burden for state in by_ward.values()) / max(1, len(by_ward))

    for ward_id, labor_mult in labor_mults.items():
        metrics.topk_add("health:worst_labor", ward_id, 1.0 - labor_mult, payload={"labor_mult": labor_mult})
    for ward_id, state in by_ward.items():
        camp = getattr(getattr(world, "migration_by_ward", {}).get(ward_id), "camp", 0)
        if camp:
            metrics.topk_add("health:camp_risk", ward_id, float(camp), payload={"camp": camp})


def run_health_for_day(world: WorldState, *, day: int | None = None) -> None:
    cfg, by_ward, events = _ensure_health(world)
    if not getattr(cfg, "enabled", False):
        return
    current_day = day if day is not None else getattr(world, "day", 0)

    if current_day % max(1, int(cfg.update_cadence_days)) != 0:
        return

    _trigger_outbreaks(world=world, cfg=cfg, by_ward=by_ward, events=events, day=current_day)
    _evolve_outbreaks(world=world, cfg=cfg, by_ward=by_ward, events=events, day=current_day)
    _spread_outbreaks(world, cfg, by_ward)
    _apply_consequences(world, by_ward)


__all__ = [
    "DISEASE_RESPIRATORY",
    "DISEASE_WATERBORNE",
    "DISEASE_WOUND",
    "HealthConfig",
    "HealthEvent",
    "WardHealthState",
    "run_health_for_day",
]

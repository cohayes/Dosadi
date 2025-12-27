from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping

from dosadi.runtime.institutions import ensure_policy
from dosadi.runtime.telemetry import ensure_metrics, record_event

DOMAINS = (
    "ENGINEERING",
    "LOGISTICS",
    "CIVICS",
    "MEDICINE",
    "SECURITY",
    "TRADE",
)


@dataclass(slots=True)
class EducationConfig:
    enabled: bool = False
    update_cadence_days: int = 14
    deterministic_salt: str = "edu-v1"
    base_gain_per_update: float = 0.01
    base_decay_per_update: float = 0.003
    max_level: float = 1.0
    health_penalty_scale: float = 0.4
    war_penalty_scale: float = 0.3


@dataclass(slots=True)
class WardEducationState:
    ward_id: str
    domains: dict[str, float] = field(default_factory=dict)
    teacher_pool: float = 0.0
    spend_last_update: float = 0.0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


def _clamp01(value: float, *, hi: float = 1.0) -> float:
    return max(0.0, min(hi, value))


def ensure_education_config(world: Any) -> EducationConfig:
    cfg = getattr(world, "education_cfg", None)
    if not isinstance(cfg, EducationConfig):
        cfg = EducationConfig()
        world.education_cfg = cfg
    return cfg


def ensure_ward_education(world: Any, ward_id: str) -> WardEducationState:
    bucket: dict[str, WardEducationState] = getattr(world, "education_by_ward", None) or {}
    state = bucket.get(ward_id)
    if not isinstance(state, WardEducationState):
        state = WardEducationState(ward_id=ward_id)
        bucket[ward_id] = state
    world.education_by_ward = bucket
    return state


def _facility_counts(ward: Any) -> Mapping[str, int]:
    facilities = getattr(ward, "facilities", {}) or {}
    if isinstance(facilities, Mapping):
        return facilities
    return {}


def _culture_modifiers(world: Any, ward_id: str) -> dict[str, float]:
    culture = getattr(world, "culture_by_ward", {}).get(ward_id)
    norms = getattr(culture, "norms", {}) if culture is not None else {}
    modifiers: dict[str, float] = {domain: 1.0 for domain in DOMAINS}
    anti_intellectualism = float(norms.get("anti_intellectualism", 0.0))
    militarism = float(norms.get("militarism", 0.0))
    merchant_ethos = float(norms.get("merchant_ethos", 0.0))

    damp = 1.0 - 0.4 * _clamp01(anti_intellectualism)
    for domain in ("ENGINEERING", "MEDICINE"):
        modifiers[domain] *= damp

    modifiers["SECURITY"] *= 1.0 + 0.3 * _clamp01(militarism)
    modifiers["CIVICS"] *= 1.0 - 0.2 * _clamp01(militarism)
    merchant_boost = 1.0 + 0.25 * _clamp01(merchant_ethos)
    for domain in ("TRADE", "LOGISTICS"):
        modifiers[domain] *= merchant_boost
    return modifiers


def _facility_affinity(counts: Mapping[str, int]) -> dict[str, float]:
    school = int(counts.get("SCHOOLHOUSE_L1", 0))
    training = int(counts.get("TRAINING_HALL_L1", 0))
    academy = int(counts.get("ACADEMY_L2", 0))
    affinity = {domain: 1.0 for domain in DOMAINS}
    civic_boost = 1.0 + 0.1 * school + 0.2 * academy
    affinity["CIVICS"] *= civic_boost
    affinity["TRADE"] *= 1.0 + 0.08 * school
    affinity["LOGISTICS"] *= 1.0 + 0.12 * training + 0.06 * academy
    affinity["SECURITY"] *= 1.0 + 0.1 * training
    affinity["ENGINEERING"] *= 1.0 + 0.15 * academy
    affinity["MEDICINE"] *= 1.0 + 0.1 * academy
    return affinity


def _normalized_weights(policy: Any, modifiers: Mapping[str, float], affinity: Mapping[str, float]) -> dict[str, float]:
    raw_weights = getattr(policy, "education_priority", {}) or {}
    if not raw_weights:
        raw_weights = {domain: 1.0 for domain in DOMAINS}
    weighted: dict[str, float] = {}
    for domain, value in raw_weights.items():
        weighted[domain] = max(0.0, float(value)) * modifiers.get(domain, 1.0) * affinity.get(domain, 1.0)
    total = sum(weighted.values()) or 1.0
    return {domain: weight / total for domain, weight in weighted.items()}


def _penalties(world: Any, ward_id: str, cfg: EducationConfig) -> float:
    health_state: Mapping[str, float] | None = getattr(world, "health_by_ward", {}).get(ward_id)
    outbreaks = 0.0
    outbreaks_data = (
        (health_state.get("outbreaks") if isinstance(health_state, Mapping) else getattr(health_state, "outbreaks", {}))
        or {}
    )
    if isinstance(outbreaks_data, Mapping):
        outbreaks = sum(float(v) for v in outbreaks_data.values())
    health_penalty = _clamp01(outbreaks) * cfg.health_penalty_scale

    inst_state = getattr(world, "inst_state_by_ward", {}).get(ward_id)
    unrest = float(getattr(inst_state, "unrest", 0.0)) if inst_state is not None else 0.0
    war_penalty = _clamp01(unrest) * cfg.war_penalty_scale

    return _clamp01(health_penalty + war_penalty)


def _teacher_pool_update(state: WardEducationState, spend: float, facility_signal: float, cfg: EducationConfig) -> float:
    growth = 0.15 * spend * facility_signal
    decay = 0.05
    state.teacher_pool = _clamp01(state.teacher_pool + growth - decay, hi=cfg.max_level)
    return state.teacher_pool


def ward_competence(world: Any, ward_id: str) -> dict[str, float]:
    state = ensure_ward_education(world, ward_id)
    competence = {domain: _clamp01(state.domains.get(domain, 0.0), hi=ensure_education_config(world).max_level) for domain in DOMAINS}
    return competence


def ward_competence_multipliers(world: Any, ward_id: str) -> dict[str, float]:
    competence = ward_competence(world, ward_id)
    return {domain: 1.0 + 0.6 * level for domain, level in competence.items()}


def _competence_signature(state: Mapping[str, WardEducationState], cfg: EducationConfig) -> str:
    canonical = {
        ward_id: {
            "domains": {k: round(_clamp01(v, hi=cfg.max_level), 6) for k, v in sorted(ward_state.domains.items())},
            "teacher_pool": round(ward_state.teacher_pool, 6),
        }
        for ward_id, ward_state in sorted(state.items())
    }
    digest = sha256(str(canonical).encode("utf-8")).hexdigest()
    return digest


def meets_competence_requirements(world: Any, requirement: Mapping[str, float] | None) -> bool:
    if not requirement:
        return True
    cfg = ensure_education_config(world)
    if not getattr(cfg, "enabled", False):
        return True
    education: Mapping[str, WardEducationState] = getattr(world, "education_by_ward", {}) or {}
    best: dict[str, float] = {domain: 0.0 for domain in requirement}
    for ward_id in sorted(education):
        comp = ward_competence(world, ward_id)
        for domain, needed in requirement.items():
            best[domain] = max(best[domain], comp.get(domain, 0.0))
    return all(best.get(domain, 0.0) >= float(needed) for domain, needed in requirement.items())


def run_education_update(world: Any, *, day: int) -> None:
    cfg = ensure_education_config(world)
    if not cfg.enabled:
        return
    wards = getattr(world, "wards", {}) or {}
    if day % max(1, int(cfg.update_cadence_days)) != 0:
        return

    metrics = ensure_metrics(world)
    metrics_bucket = metrics.gauges.setdefault("education", {}) if hasattr(metrics, "gauges") else {}
    total_spend = 0.0
    level_accumulator = {domain: 0.0 for domain in DOMAINS}

    for ward_id, ward in sorted(wards.items()):
        edu_state = ensure_ward_education(world, ward_id)
        if edu_state.last_update_day == day:
            continue

        policy = ensure_policy(world, ward_id)
        facility_counts = _facility_counts(ward)
        affinity = _facility_affinity(facility_counts)
        modifiers = _culture_modifiers(world, ward_id)
        weights = _normalized_weights(policy, modifiers, affinity)
        penalty = _penalties(world, ward_id, cfg)

        spend_bias = float(getattr(policy, "education_spend_bias", 0.0))
        spend = max(0.0, 1.0 + spend_bias)
        edu_state.spend_last_update = spend
        total_spend += spend

        facility_signal = 1.0 + 0.1 * sum(facility_counts.values())
        teacher_pool = _teacher_pool_update(edu_state, spend, facility_signal, cfg)

        gain = cfg.base_gain_per_update * (1.0 + 0.5 * spend) * (0.7 + 0.3 * teacher_pool)
        gain *= 1.0 - penalty

        for domain, weight in weights.items():
            prev = edu_state.domains.get(domain, 0.0)
            increment = gain * weight
            decay_amount = cfg.base_decay_per_update * (1.0 + 0.3 * penalty)
            decayed = max(0.0, prev - decay_amount)
            new_value = _clamp01(decayed + increment, hi=cfg.max_level)
            if new_value > prev and int(prev * 10) != int(new_value * 10):
                record_event(
                    world,
                    {
                        "type": "EDU_LEVEL_UP",
                        "ward_id": ward_id,
                        "domain": domain,
                        "level": round(new_value, 4),
                        "day": day,
                    },
                )
            edu_state.domains[domain] = new_value
            level_accumulator[domain] += edu_state.domains[domain]

        edu_state.last_update_day = day

    if isinstance(metrics_bucket, dict) and wards:
        metrics_bucket["spend_total"] = round(total_spend, 4)
        metrics_bucket["avg_level_by_domain"] = {
            domain: level_accumulator[domain] / max(1, len(wards)) for domain in DOMAINS
        }
        metrics_bucket["signature"] = _competence_signature(getattr(world, "education_by_ward", {}), cfg)


def logistics_delay_multiplier(world: Any, ward_id: str) -> float:
    multipliers = ward_competence_multipliers(world, ward_id)
    return 1.0 / max(1.0, multipliers.get("LOGISTICS", 1.0))


__all__ = [
    "DOMAINS",
    "EducationConfig",
    "WardEducationState",
    "ensure_education_config",
    "ensure_ward_education",
    "logistics_delay_multiplier",
    "meets_competence_requirements",
    "run_education_update",
    "ward_competence",
    "ward_competence_multipliers",
]

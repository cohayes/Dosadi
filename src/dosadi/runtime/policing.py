from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.constitution import policing_constraints_for_ward


DOCTRINE_KEYS: tuple[str, ...] = ("COMMUNITY", "PROCEDURAL", "MILITARIZED", "TERROR")


DOCTRINE_PROFILES: dict[str, dict[str, float]] = {
    "COMMUNITY": {
        "detection": 0.85,
        "suppression": 0.75,
        "corruption": -0.02,
        "harm": 0.05,
        "legitimacy": 0.03,
        "backlash": 0.05,
    },
    "PROCEDURAL": {
        "detection": 0.95,
        "suppression": 0.90,
        "corruption": -0.01,
        "harm": 0.04,
        "legitimacy": 0.02,
        "backlash": 0.06,
    },
    "MILITARIZED": {
        "detection": 1.05,
        "suppression": 1.15,
        "corruption": 0.01,
        "harm": 0.12,
        "legitimacy": -0.02,
        "backlash": 0.18,
    },
    "TERROR": {
        "detection": 1.20,
        "suppression": 1.30,
        "corruption": 0.04,
        "harm": 0.25,
        "legitimacy": -0.08,
        "backlash": 0.32,
    },
}


@dataclass(slots=True)
class PolicingConfig:
    enabled: bool = False
    update_cadence_days: int = 7
    deterministic_salt: str = "policing-v2"
    doctrine_change_limit: float = 0.10
    corruption_drift_p2: float = 0.02
    backlash_scale: float = 0.25
    effect_scale: float = 0.20


@dataclass(slots=True)
class WardPolicingState:
    ward_id: str
    doctrine_mix: dict[str, float] = field(default_factory=dict)
    inspection_intensity: float = 0.5
    informant_reliance: float = 0.5
    force_threshold: float = 0.5
    corruption: float = 0.0
    capacity_effective: float = 1.0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class PolicingEffects:
    detection_mult: float
    suppression_mult: float
    collateral_harm: float
    legitimacy_delta: float
    corruption_delta: float
    backlash: float
    corruption_index: float


def _clamp01(val: float) -> float:
    return max(0.0, min(1.0, float(val)))


def _normalize_mix(mix: Mapping[str, float]) -> dict[str, float]:
    payload = {key: max(0.0, float(mix.get(key, 0.0))) for key in DOCTRINE_KEYS}
    total = sum(payload.values())
    if total <= 0:
        payload = {key: 1.0 / len(DOCTRINE_KEYS) for key in DOCTRINE_KEYS}
        total = 1.0
    return {key: val / total for key, val in payload.items()}


def ensure_policing_config(world: Any) -> PolicingConfig:
    cfg = getattr(world, "policing_cfg", None)
    if not isinstance(cfg, PolicingConfig):
        cfg = PolicingConfig()
        world.policing_cfg = cfg
    return cfg


def ensure_policing_state(world: Any, ward_id: str) -> WardPolicingState:
    bucket: dict[str, WardPolicingState] = getattr(world, "policing_by_ward", {}) or {}
    state = bucket.get(ward_id)
    if not isinstance(state, WardPolicingState):
        state = WardPolicingState(ward_id=ward_id)
        state.doctrine_mix = _normalize_mix({})
        bucket[ward_id] = state
    elif not state.doctrine_mix:
        state.doctrine_mix = _normalize_mix({})
    world.policing_by_ward = bucket
    return state


def _stable_float(cfg: PolicingConfig, *parts: object) -> float:
    payload = "|".join(str(p) for p in (cfg.deterministic_salt, *parts))
    digest = sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


def _labor_modifier(world: Any, ward_id: str) -> float:
    orgs = getattr(world, "labor_orgs_by_ward", {}).get(ward_id) or []
    strikes = sum(1 for org in orgs if str(getattr(org, "status", "")).upper() == "STRIKE")
    slowdowns = sum(1 for org in orgs if str(getattr(org, "status", "")).upper() == "SLOWDOWN")
    penalty = min(0.7, 0.25 * strikes + 0.10 * slowdowns)
    return max(0.3, 1.0 - penalty)


def _comms_modifier(world: Any, ward_id: str) -> float:
    mods = getattr(world, "comms_mod_by_ward", {}) or {}
    mod = mods.get(ward_id)
    loss = getattr(mod, "loss_mult", 1.0) if mod is not None else 1.0
    try:
        loss = float(loss)
    except Exception:  # pragma: no cover - defensive
        loss = 1.0
    return 1.0 / max(1.0, loss)


def _intel_modifier(world: Any, ward_id: str) -> float:
    coverage = getattr(world, "counterintel_by_ward", {}) or {}
    score = float(coverage.get(ward_id, 0.0) or 0.0)
    return max(0.5, 1.0 + 0.5 * _clamp01(score))


def get_policing_capacity(world: Any, ward_id: str, day: int) -> float:
    cfg = ensure_policing_config(world)
    state = ensure_policing_state(world, ward_id)
    if not cfg.enabled:
        state.capacity_effective = 1.0
        return 1.0

    workforce = getattr(world, "workforce_by_ward", {}).get(ward_id)
    pools = getattr(workforce, "pools", {}) if workforce is not None else {}
    guard = float(pools.get("GUARD", 0.0) or 0.0)
    admin = float(pools.get("ADMIN", 0.0) or 0.0)
    total = sum(float(val) for val in pools.values()) or 1.0
    staffing_ratio = max(0.2, min(1.5, (guard + 0.5 * admin) / total * 1.5))

    labor = _labor_modifier(world, ward_id)
    comms = _comms_modifier(world, ward_id)
    intel = _intel_modifier(world, ward_id)

    capacity = staffing_ratio * labor * comms * intel
    capacity = max(0.1, min(2.5, capacity))
    state.capacity_effective = capacity
    state.notes["capacity_inputs"] = {
        "staffing_ratio": staffing_ratio,
        "labor": labor,
        "comms": comms,
        "intel": intel,
        "day": day,
    }
    return capacity


def _target_scores(world: Any, ward_id: str, cfg: PolicingConfig) -> dict[str, float]:
    ward = getattr(world, "wards", {}).get(ward_id)
    legitimacy = float(getattr(ward, "legitimacy", getattr(world, "legitimacy", 0.5)) or 0.0)
    hardship = float(getattr(ward, "need_index", 0.0) or getattr(world, "need_index", 0.0) or 0.0)
    risk = float(getattr(ward, "risk_index", 0.0) or getattr(world, "risk_index", 0.0) or 0.0)
    raids = getattr(world, "raid_pressure_by_ward", {}).get(ward_id)
    raid_pressure = float(raids if raids is not None else getattr(world, "raid_pressure", 0.0) or 0.0)
    ideology = float(getattr(world, "leadership_authoritarian_bias", 0.0) or 0.0)
    governance_failure = float(getattr(world, "governance_failure_by_ward", {}).get(ward_id, 0.0) or 0.0)

    scores = {
        "COMMUNITY": 0.4 + (1.0 - legitimacy) * 0.4 + hardship * 0.3,
        "PROCEDURAL": 0.5 + legitimacy * 0.5 - governance_failure * 0.3,
        "MILITARIZED": 0.3 + raid_pressure * 0.7 + risk * 0.3,
        "TERROR": 0.2 + governance_failure * 0.6 + ideology * 0.6 + raid_pressure * 0.2,
    }
    noise = _stable_float(cfg, ward_id, getattr(world, "seed", 0), getattr(world, "day", 0))
    scores["MILITARIZED"] += 0.05 * noise
    scores["COMMUNITY"] += 0.03 * (1.0 - noise)
    return scores


def update_policing_doctrine(world: Any, ward_id: str, day: int) -> WardPolicingState:
    cfg = ensure_policing_config(world)
    state = ensure_policing_state(world, ward_id)
    if not cfg.enabled:
        state.last_update_day = day
        return state
    if state.last_update_day == day:
        return state
    scores = _target_scores(world, ward_id, cfg)
    target = _normalize_mix(scores)
    current = _normalize_mix(state.doctrine_mix)

    adjusted: dict[str, float] = {}
    for key in DOCTRINE_KEYS:
        delta = target[key] - current[key]
        limit = cfg.doctrine_change_limit
        if delta > limit:
            delta = limit
        elif delta < -limit:
            delta = -limit
        adjusted[key] = current[key] + delta
    state.doctrine_mix = _normalize_mix(adjusted)
    state.last_update_day = day

    return state


def _weighted_sum(mix: Mapping[str, float], dimension: str) -> float:
    total = 0.0
    for key, weight in mix.items():
        profile = DOCTRINE_PROFILES.get(key, {})
        total += weight * float(profile.get(dimension, 0.0))
    return total


def policing_effects(world: Any, ward_id: str, *, day: int | None = None) -> PolicingEffects:
    cfg = ensure_policing_config(world)
    state = ensure_policing_state(world, ward_id)
    current_day = getattr(world, "day", 0) if day is None else int(day)
    if cfg.enabled and (state.last_update_day < 0 or current_day - state.last_update_day >= cfg.update_cadence_days):
        update_policing_doctrine(world, ward_id, current_day)

    mix = _normalize_mix(state.doctrine_mix)
    constraints = policing_constraints_for_ward(world, ward_id, day=current_day)
    if constraints:
        mix = dict(mix)
        mix["TERROR"] = min(mix.get("TERROR", 0.0), constraints.get("terror_cap", 1.0))
        mix["PROCEDURAL"] = max(mix.get("PROCEDURAL", 0.0), constraints.get("procedural_floor", 0.0))
        mix = _normalize_mix(mix)
        state.doctrine_mix = mix

    capacity = get_policing_capacity(world, ward_id, current_day)

    detection = capacity * _weighted_sum(mix, "detection") * (0.7 + 0.6 * _clamp01(state.informant_reliance))
    suppression = capacity * _weighted_sum(mix, "suppression") * (0.7 + 0.6 * _clamp01(state.force_threshold))
    collateral = capacity * _weighted_sum(mix, "harm") * cfg.effect_scale

    legitimacy_delta = cfg.effect_scale * _weighted_sum(mix, "legitimacy")
    legitimacy_delta -= cfg.backlash_scale * mix.get("TERROR", 0.0) * _clamp01(state.force_threshold)

    corruption_drift = cfg.corruption_drift_p2 * (1.0 - mix.get("PROCEDURAL", 0.0))
    corruption_drift += _weighted_sum(mix, "corruption") * (0.5 + _clamp01(state.inspection_intensity))
    corruption_drift = max(-0.05, min(0.1, corruption_drift))

    backlash = cfg.backlash_scale * _weighted_sum(mix, "backlash") * (0.5 + 0.5 * _clamp01(state.force_threshold))

    state.corruption = _clamp01(state.corruption + corruption_drift)
    state.notes["last_effects_day"] = current_day
    state.notes["last_effects"] = {
        "detection": detection,
        "suppression": suppression,
        "collateral": collateral,
        "legitimacy_delta": legitimacy_delta,
        "corruption_drift": corruption_drift,
        "backlash": backlash,
    }

    return PolicingEffects(
        detection_mult=max(0.1, detection),
        suppression_mult=max(0.1, suppression),
        collateral_harm=max(0.0, collateral),
        legitimacy_delta=legitimacy_delta,
        corruption_delta=corruption_drift,
        backlash=max(0.0, backlash),
        corruption_index=state.corruption,
    )


def policing_corruption_index(world: Any, ward_id: str) -> float:
    state = ensure_policing_state(world, ward_id)
    return float(getattr(state, "corruption", 0.0) or 0.0)


def policing_seed_payload(world: Any) -> dict[str, Any] | None:
    cfg = getattr(world, "policing_cfg", None)
    states = getattr(world, "policing_by_ward", None)
    if cfg is None and states is None:
        return None
    payload: dict[str, Any] = {
        "config": asdict(cfg) if cfg else {},
        "by_ward": {wid: asdict(state) for wid, state in sorted((states or {}).items())},
    }
    return payload


def save_policing_seed(world: Any, path) -> None:
    payload = policing_seed_payload(world) or {}
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, sort_keys=True, indent=2)


def load_policing_seed(world: Any, payload: Mapping[str, Any]) -> None:
    cfg_data = payload.get("config") if isinstance(payload, Mapping) else None
    state_data = payload.get("by_ward") if isinstance(payload, Mapping) else None
    if cfg_data:
        world.policing_cfg = PolicingConfig(**cfg_data)
    if state_data:
        bucket: dict[str, WardPolicingState] = {}
        for ward_id, data in state_data.items():
            state = WardPolicingState(ward_id=str(ward_id))
            for key, val in data.items():
                if key == "ward_id":
                    continue
                setattr(state, key, val)
            state.doctrine_mix = _normalize_mix(getattr(state, "doctrine_mix", {}) or {})
            bucket[state.ward_id] = state
        world.policing_by_ward = bucket


__all__ = [
    "PolicingConfig",
    "WardPolicingState",
    "PolicingEffects",
    "ensure_policing_config",
    "ensure_policing_state",
    "get_policing_capacity",
    "update_policing_doctrine",
    "policing_effects",
    "policing_corruption_index",
    "policing_seed_payload",
    "save_policing_seed",
    "load_policing_seed",
]

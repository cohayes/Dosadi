from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.class_system import class_hardship, class_inequality
from dosadi.runtime.institutions import ensure_policy, ensure_state
from dosadi.runtime.telemetry import ensure_metrics, record_event

AXES = ("ORTHODOXY", "TECHNICISM", "MERCANTILISM", "MILITARISM")


def _clamp01(value: float, *, hi: float = 1.0) -> float:
    return max(0.0, min(hi, float(value)))


@dataclass(slots=True)
class IdeologyConfig:
    enabled: bool = False
    update_cadence_days: int = 14
    max_factions_per_ward: int = 6
    deterministic_salt: str = "ideology-v1"
    capture_rate: float = 0.08
    decay_rate: float = 0.02
    coercion_cost_scale: float = 0.10


@dataclass(slots=True)
class WardIdeologyState:
    ward_id: str
    influence: dict[str, float] = field(default_factory=dict)
    state_share: float = 0.5
    curriculum_axes: dict[str, float] = field(default_factory=dict)
    censorship_level: float = 0.0
    propaganda_intensity: float = 0.0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


def ensure_ideology_config(world: Any) -> IdeologyConfig:
    cfg = getattr(world, "ideology_cfg", None)
    if not isinstance(cfg, IdeologyConfig):
        cfg = IdeologyConfig()
        world.ideology_cfg = cfg
    return cfg


def ensure_ward_ideology(world: Any, ward_id: str) -> WardIdeologyState:
    bucket: dict[str, WardIdeologyState] = getattr(world, "ideology_by_ward", {}) or {}
    state = bucket.get(ward_id)
    if not isinstance(state, WardIdeologyState):
        state = WardIdeologyState(ward_id=ward_id)
        bucket[ward_id] = state
    world.ideology_by_ward = bucket
    return state


def _normalized_axes(raw: Mapping[str, float]) -> dict[str, float]:
    normalized = {axis: max(0.0, float(raw.get(axis, 0.0))) for axis in AXES}
    total = sum(normalized.values()) or 1.0
    return {axis: value / total for axis, value in normalized.items()}


def _axes_from_priorities(priorities: Mapping[str, float] | None) -> dict[str, float]:
    priorities = priorities or {}
    axis_weights = {axis: 0.0 for axis in AXES}
    for domain, weight in priorities.items():
        w = max(0.0, float(weight))
        if domain in {"ENGINEERING", "MEDICINE"}:
            axis_weights["TECHNICISM"] += w
        elif domain in {"TRADE", "LOGISTICS"}:
            axis_weights["MERCANTILISM"] += w
        elif domain == "SECURITY":
            axis_weights["MILITARISM"] += w
        elif domain == "CIVICS":
            axis_weights["ORTHODOXY"] += w
    if not any(axis_weights.values()):
        return {axis: 1.0 / len(AXES) for axis in AXES}
    return _normalized_axes(axis_weights)


def _ideology_signature(world: Any, cfg: IdeologyConfig) -> str:
    data = getattr(world, "ideology_by_ward", {}) or {}
    canonical = {
        ward_id: {
            "axes": {k: round(v, 6) for k, v in sorted(state.curriculum_axes.items())},
            "censorship": round(state.censorship_level, 6),
            "propaganda": round(state.propaganda_intensity, 6),
        }
        for ward_id, state in sorted(data.items())
    }
    digest = sha256((cfg.deterministic_salt + str(canonical)).encode("utf-8")).hexdigest()
    return digest


def _candidate_factions(world: Any, ward_id: str, cfg: IdeologyConfig) -> list[str]:
    wards = getattr(world, "wards", {}) or {}
    ward = wards.get(ward_id)
    candidates: list[str] = []
    governor = getattr(ward, "governor_faction", None)
    if governor:
        candidates.append(str(governor))
    for faction_id in sorted(getattr(world, "factions", {}).keys()):
        if faction_id not in candidates:
            candidates.append(faction_id)
        if len(candidates) >= cfg.max_factions_per_ward:
            break
    return candidates[: cfg.max_factions_per_ward]


def _apply_capture(influence: dict[str, float], *, target: str, shift: float) -> dict[str, float]:
    if shift <= 0.0:
        return influence
    others = [fid for fid in influence if fid != target]
    pool = sum(influence.get(fid, 0.0) for fid in others)
    if pool <= 0.0:
        return influence
    take = min(pool, shift)
    for fid in others:
        share = influence.get(fid, 0.0)
        reduction = take * (share / pool) if pool > 0 else 0.0
        influence[fid] = max(0.0, share - reduction)
    influence[target] = _clamp01(influence.get(target, 0.0) + take)
    return influence


def _axes_from_state(state: WardIdeologyState, censorship: float, priorities: Mapping[str, float] | None) -> dict[str, float]:
    raw = _axes_from_priorities(priorities)
    raw["ORTHODOXY"] += 0.25 * censorship + 0.1 * state.state_share
    raw["TECHNICISM"] *= 1.0 - 0.4 * censorship
    raw["MERCANTILISM"] *= 1.0 - 0.1 * censorship
    raw["MILITARISM"] *= 1.0 + 0.1 * state.influence.get("military", 0.0)
    return _normalized_axes(raw)


def run_ideology_update(world: Any, *, day: int) -> None:
    cfg = ensure_ideology_config(world)
    if not cfg.enabled:
        return
    if day % max(1, int(cfg.update_cadence_days)) != 0:
        return

    wards = getattr(world, "wards", {}) or {}
    metrics = ensure_metrics(world)
    metrics_bucket = metrics.gauges.setdefault("ideology", {}) if hasattr(metrics, "gauges") else {}
    capture_events = 0

    for ward_id in sorted(wards):
        state = ensure_ward_ideology(world, ward_id)
        if state.last_update_day == day:
            continue
        policy = ensure_policy(world, ward_id)
        censorship = _clamp01(0.5 * max(0.0, getattr(policy, "censorship_bias", 0.0)))
        propaganda = _clamp01(max(0.0, getattr(policy, "propaganda_budget_points", 0.0)) / 10.0)
        inequality = class_inequality(world, ward_id)
        hardship = class_hardship(world, ward_id)
        polarization = _clamp01(0.3 * inequality + 0.2 * hardship)

        candidates = _candidate_factions(world, ward_id, cfg)
        influence = dict(state.influence)
        if candidates and not influence:
            remainder = max(0.0, 1.0 - state.state_share)
            even = remainder / len(candidates)
            for fid in candidates:
                influence[fid] = even
        for fid in candidates:
            influence.setdefault(fid, 0.0)

        target = candidates[0] if candidates else "state"
        influence = _apply_capture(influence, target=target, shift=cfg.capture_rate * propaganda)
        baseline = max(0.0, 1.0 - state.state_share) / (len(candidates) or 1)
        for fid in candidates:
            prev = influence.get(fid, 0.0)
            influence[fid] = _clamp01(prev + (baseline - prev) * cfg.decay_rate)

        axes = _axes_from_state(state, censorship, getattr(policy, "education_priority", {}))
        axes["ORTHODOXY"] = _clamp01(axes.get("ORTHODOXY", 0.0) + 0.2 * polarization)
        axes["TECHNICISM"] = _clamp01(axes.get("TECHNICISM", 0.0) - 0.1 * polarization)
        axes = _normalized_axes(axes)
        state.state_share = _clamp01(state.state_share - 0.2 * polarization + 0.05 * propaganda)
        state.curriculum_axes = axes
        state.censorship_level = censorship
        state.propaganda_intensity = propaganda
        state.influence = influence
        state.last_update_day = day

        inst_state = ensure_state(world, ward_id)
        inst_state.unrest = _clamp01(inst_state.unrest + cfg.coercion_cost_scale * censorship + 0.1 * polarization)
        inst_state.legitimacy = _clamp01(inst_state.legitimacy - 0.25 * censorship + 0.1 * propaganda)

        if propaganda > 0.0:
            capture_events += 1
            record_event(
                world,
                {
                    "type": "CURRICULUM_SHIFT",
                    "ward_id": ward_id,
                    "censorship": round(censorship, 4),
                    "propaganda": round(propaganda, 4),
                    "day": day,
                },
            )

    if isinstance(metrics_bucket, dict) and wards:
        metrics_bucket["avg_censorship"] = round(
            sum(getattr(state, "censorship_level", 0.0) for state in getattr(world, "ideology_by_ward", {}).values())
            / max(1, len(wards)),
            4,
        )
        metrics_bucket["signature"] = _ideology_signature(world, cfg)
        metrics_bucket["capture_events"] = capture_events


def ideology_domain_modifiers(world: Any, ward_id: str) -> dict[str, float]:
    cfg = ensure_ideology_config(world)
    if not cfg.enabled:
        return {"ENGINEERING": 1.0, "MEDICINE": 1.0, "TRADE": 1.0, "LOGISTICS": 1.0, "SECURITY": 1.0, "CIVICS": 1.0}
    state = ensure_ward_ideology(world, ward_id)
    axes = state.curriculum_axes or {axis: 1.0 / len(AXES) for axis in AXES}
    mods = {domain: 1.0 for domain in ("ENGINEERING", "MEDICINE", "TRADE", "LOGISTICS", "SECURITY", "CIVICS")}
    mods["ENGINEERING"] *= 1.0 + 0.5 * axes.get("TECHNICISM", 0.0) - 0.2 * axes.get("ORTHODOXY", 0.0)
    mods["MEDICINE"] *= 1.0 + 0.45 * axes.get("TECHNICISM", 0.0) - 0.15 * axes.get("ORTHODOXY", 0.0)
    mods["TRADE"] *= 1.0 + 0.4 * axes.get("MERCANTILISM", 0.0)
    mods["LOGISTICS"] *= 1.0 + 0.25 * axes.get("MERCANTILISM", 0.0) + 0.25 * axes.get("MILITARISM", 0.0)
    mods["SECURITY"] *= 1.0 + 0.5 * axes.get("MILITARISM", 0.0)
    mods["CIVICS"] *= 1.0 + 0.5 * axes.get("ORTHODOXY", 0.0)
    return mods


def ideology_gain_multiplier(world: Any, ward_id: str) -> float:
    cfg = ensure_ideology_config(world)
    if not cfg.enabled:
        return 1.0
    state = ensure_ward_ideology(world, ward_id)
    axes = state.curriculum_axes or {axis: 1.0 / len(AXES) for axis in AXES}
    technicism = axes.get("TECHNICISM", 0.0)
    penalty = 1.0 - 0.6 * state.censorship_level
    bonus = 0.1 * technicism
    return _clamp01(penalty + bonus, hi=1.2)


def tech_delay_multiplier(world: Any, ward_id: str | None) -> float:
    cfg = ensure_ideology_config(world)
    if not cfg.enabled or ward_id is None:
        return 1.0
    state = ensure_ward_ideology(world, ward_id)
    axes = state.curriculum_axes or {axis: 1.0 / len(AXES) for axis in AXES}
    technicism = axes.get("TECHNICISM", 0.0)
    return max(0.7, 1.0 + 0.8 * state.censorship_level - 0.5 * technicism)


__all__ = [
    "AXES",
    "IdeologyConfig",
    "WardIdeologyState",
    "ensure_ideology_config",
    "ensure_ward_ideology",
    "ideology_domain_modifiers",
    "ideology_gain_multiplier",
    "run_ideology_update",
    "tech_delay_multiplier",
]


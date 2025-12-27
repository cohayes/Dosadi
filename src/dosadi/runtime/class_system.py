from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping

from dosadi.runtime.institutions import ensure_policy
from dosadi.runtime.telemetry import ensure_metrics, record_event

TIERS = ("T0_ELITE", "T1_OFFICERS", "T2_SKILLED", "T3_UNSKILLED", "T4_DISPLACED")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class RationingRegime(Enum):
    EQUAL = "EQUAL"
    MERIT = "MERIT"
    OFFICER_FIRST = "OFFICER_FIRST"
    SECURITY_FIRST = "SECURITY_FIRST"
    ELITE_FIRST = "ELITE_FIRST"
    AUSTERITY = "AUSTERITY"


class WageRegime(Enum):
    FLAT = "FLAT"
    SKILL_BONUS = "SKILL_BONUS"
    GUILD_CAPTURE = "GUILD_CAPTURE"
    PATRONAGE = "PATRONAGE"
    WAR_ECONOMY = "WAR_ECONOMY"


@dataclass(slots=True)
class ClassConfig:
    enabled: bool = False
    update_cadence_days: int = 14
    deterministic_salt: str = "class-v1"
    mobility_rate: float = 0.03
    camp_assimilation_rate: float = 0.05
    inequality_sensitivity: float = 0.7
    hardship_sensitivity: float = 0.9


@dataclass(slots=True)
class WardClassState:
    ward_id: str
    tier_share: dict[str, float] = field(default_factory=dict)
    wage_index: dict[str, float] = field(default_factory=dict)
    ration_priority: dict[str, float] = field(default_factory=dict)
    housing_quality: dict[str, float] = field(default_factory=dict)
    suit_priority: dict[str, float] = field(default_factory=dict)
    hardship_index: float = 0.0
    inequality_index: float = 0.0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


def ensure_class_config(world: Any) -> ClassConfig:
    cfg = getattr(world, "class_cfg", None)
    if not isinstance(cfg, ClassConfig):
        cfg = ClassConfig()
        world.class_cfg = cfg
    return cfg


def ensure_ward_class_state(world: Any, ward_id: str) -> WardClassState:
    bucket: dict[str, WardClassState] = getattr(world, "class_by_ward", {}) or {}
    state = bucket.get(ward_id)
    if not isinstance(state, WardClassState):
        base_share = {
            "T0_ELITE": 0.05,
            "T1_OFFICERS": 0.15,
            "T2_SKILLED": 0.30,
            "T3_UNSKILLED": 0.35,
            "T4_DISPLACED": 0.15,
        }
        state = WardClassState(ward_id=ward_id, tier_share=base_share)
        bucket[ward_id] = state
    world.class_by_ward = bucket
    return state


def _shortage_pressure(world: Any, ward_id: str) -> float:
    ward = getattr(world, "wards", {}).get(ward_id)
    need_index = float(getattr(ward, "need_index", 0.0) or 0.0)
    global_signals = getattr(getattr(world, "market_state", None), "global_signals", {}) or {}
    global_urgency = max((float(getattr(sig, "urgency", 0.0) or 0.0) for sig in global_signals.values()), default=0.0)
    combined = 0.6 * need_index + 0.4 * global_urgency
    return _clamp01(combined)


def _normalize_shares(shares: Mapping[str, float]) -> dict[str, float]:
    positive = {tier: max(0.0, float(value)) for tier, value in shares.items() if tier in TIERS}
    total = sum(positive.values())
    if total <= 0:
        even = 1.0 / len(TIERS)
        return {tier: even for tier in TIERS}
    return {tier: value / total for tier, value in positive.items()}


def _apply_regime_weights(
    base: Mapping[str, float],
    *,
    regime: Enum,
    emphasis: Mapping[str, float],
    flatten: float = 0.15,
) -> dict[str, float]:
    avg = sum(base.values()) / max(1, len(base))
    weighted: dict[str, float] = {}
    for tier, value in base.items():
        boost = emphasis.get(tier, 0.0)
        weighted[tier] = _clamp01((1.0 - flatten) * value + flatten * avg + boost)
    return weighted


def _ration_priorities(regime: RationingRegime, *, shortage: float) -> dict[str, float]:
    base = {
        "T0_ELITE": 0.95,
        "T1_OFFICERS": 0.85,
        "T2_SKILLED": 0.70,
        "T3_UNSKILLED": 0.50,
        "T4_DISPLACED": 0.35,
    }
    emphasis: dict[str, float] = {}
    flatten = 0.12
    if regime in {RationingRegime.OFFICER_FIRST, RationingRegime.SECURITY_FIRST}:
        emphasis["T1_OFFICERS"] = 0.08 + 0.1 * shortage
        emphasis["T2_SKILLED"] = 0.04
    if regime is RationingRegime.ELITE_FIRST:
        emphasis["T0_ELITE"] = 0.12 + 0.08 * shortage
        emphasis["T4_DISPLACED"] = -0.08 - 0.06 * shortage
    if regime is RationingRegime.MERIT:
        emphasis["T2_SKILLED"] = 0.06
        emphasis["T1_OFFICERS"] = 0.04
    if regime is RationingRegime.AUSTERITY:
        flatten = 0.25
        for tier in base:
            base[tier] = _clamp01(base[tier] - 0.1 - 0.1 * shortage)
    if regime is RationingRegime.EQUAL:
        flatten = 0.35
    return _apply_regime_weights(base, regime=regime, emphasis=emphasis, flatten=flatten)


def _wage_indices(regime: WageRegime) -> dict[str, float]:
    base = {
        "T0_ELITE": 0.95,
        "T1_OFFICERS": 0.80,
        "T2_SKILLED": 0.65,
        "T3_UNSKILLED": 0.45,
        "T4_DISPLACED": 0.25,
    }
    emphasis: dict[str, float] = {}
    flatten = 0.10
    if regime is WageRegime.FLAT:
        flatten = 0.35
    if regime is WageRegime.SKILL_BONUS:
        emphasis["T2_SKILLED"] = 0.08
        emphasis["T1_OFFICERS"] = 0.04
    if regime is WageRegime.GUILD_CAPTURE:
        emphasis["T2_SKILLED"] = 0.10
        emphasis["T1_OFFICERS"] = 0.06
        emphasis["T0_ELITE"] = 0.04
    if regime is WageRegime.PATRONAGE:
        emphasis["T0_ELITE"] = 0.14
        emphasis["T1_OFFICERS"] = 0.10
        emphasis["T4_DISPLACED"] = -0.08
    if regime is WageRegime.WAR_ECONOMY:
        emphasis["T1_OFFICERS"] = 0.08
        emphasis["T3_UNSKILLED"] = -0.04
        emphasis["T4_DISPLACED"] = -0.06
    return _apply_regime_weights(base, regime=regime, emphasis=emphasis, flatten=flatten)


def _housing_quality(*, shortage: float, segregation_bias: float) -> dict[str, float]:
    base = {
        "T0_ELITE": 0.90,
        "T1_OFFICERS": 0.75,
        "T2_SKILLED": 0.60,
        "T3_UNSKILLED": 0.45,
        "T4_DISPLACED": 0.25,
    }
    penalty = 0.25 * shortage
    for tier in base:
        base[tier] = _clamp01(base[tier] - penalty)
    if segregation_bias >= 0.5:
        bias = segregation_bias - 0.5
        base["T0_ELITE"] = _clamp01(base["T0_ELITE"] + 0.1 * bias)
        base["T1_OFFICERS"] = _clamp01(base["T1_OFFICERS"] + 0.05 * bias)
        base["T3_UNSKILLED"] = _clamp01(base["T3_UNSKILLED"] - 0.08 * bias)
        base["T4_DISPLACED"] = _clamp01(base["T4_DISPLACED"] - 0.12 * bias)
    else:
        flatten = 0.25 * (0.5 - segregation_bias)
        avg = sum(base.values()) / len(base)
        for tier in base:
            base[tier] = _clamp01((1.0 - flatten) * base[tier] + flatten * avg)
    return base


def _suit_priority(bias: float) -> dict[str, float]:
    base = {
        "T0_ELITE": 0.75,
        "T1_OFFICERS": 0.70,
        "T2_SKILLED": 0.65,
        "T3_UNSKILLED": 0.55,
        "T4_DISPLACED": 0.35,
    }
    workforce_bias = _clamp01(bias)
    base["T2_SKILLED"] = _clamp01(base["T2_SKILLED"] + 0.08 * workforce_bias)
    base["T3_UNSKILLED"] = _clamp01(base["T3_UNSKILLED"] + 0.05 * workforce_bias)
    base["T0_ELITE"] = _clamp01(base["T0_ELITE"] + 0.05 * (1.0 - workforce_bias))
    return base


def _spread_index(values: Mapping[str, float]) -> float:
    if not values:
        return 0.0
    scalars = [float(v) for v in values.values()]
    return _clamp01(max(scalars) - min(scalars))


def _hardship_index(
    *,
    shortage: float,
    tier_share: Mapping[str, float],
    suit_priority: Mapping[str, float],
    housing_quality: Mapping[str, float],
    health_burden: float,
) -> float:
    t4 = tier_share.get("T4_DISPLACED", 0.0)
    t3 = tier_share.get("T3_UNSKILLED", 0.0)
    lower_suit = 1.0 - 0.5 * (suit_priority.get("T3_UNSKILLED", 0.5) + suit_priority.get("T4_DISPLACED", 0.3))
    housing_gap = 1.0 - min(housing_quality.get("T3_UNSKILLED", 0.0), housing_quality.get("T4_DISPLACED", 0.0))
    hardship = 0.5 * shortage + 0.2 * (t4 + 0.5 * t3) + 0.15 * housing_gap + 0.15 * lower_suit
    hardship += 0.2 * _clamp01(health_burden)
    return _clamp01(hardship)


def _inequality_index(*, wage: Mapping[str, float], ration: Mapping[str, float], housing: Mapping[str, float], sensitivity: float) -> float:
    wage_spread = _spread_index(wage)
    ration_spread = _spread_index(ration)
    housing_spread = _spread_index(housing)
    combined = 0.5 * wage_spread + 0.35 * ration_spread + 0.15 * housing_spread
    return _clamp01(combined * sensitivity)


def _mobility(
    *,
    shares: dict[str, float],
    mobility_rate: float,
    assimilation_rate: float,
    education_level: float,
    shortage: float,
    camp_integration_bias: float,
    housing_capacity: float,
    health_burden: float,
) -> dict[str, float]:
    shares = dict(shares)
    upward = mobility_rate * _clamp01(education_level)
    downward = mobility_rate * _clamp01(0.5 * shortage + 0.3 * health_burden)
    # Upward flows
    t3_to_t2 = min(shares.get("T3_UNSKILLED", 0.0), upward * shares.get("T3_UNSKILLED", 0.0))
    shares["T3_UNSKILLED"] = max(0.0, shares.get("T3_UNSKILLED", 0.0) - t3_to_t2)
    shares["T2_SKILLED"] = shares.get("T2_SKILLED", 0.0) + t3_to_t2

    t2_to_t1 = min(shares.get("T2_SKILLED", 0.0), 0.5 * upward * shares.get("T2_SKILLED", 0.0))
    shares["T2_SKILLED"] = max(0.0, shares.get("T2_SKILLED", 0.0) - t2_to_t1)
    shares["T1_OFFICERS"] = shares.get("T1_OFFICERS", 0.0) + t2_to_t1

    # Downward pressure
    t2_to_t3 = min(shares.get("T2_SKILLED", 0.0), downward * shares.get("T2_SKILLED", 0.0))
    shares["T2_SKILLED"] = max(0.0, shares.get("T2_SKILLED", 0.0) - t2_to_t3)
    shares["T3_UNSKILLED"] = shares.get("T3_UNSKILLED", 0.0) + t2_to_t3

    t3_to_t4 = min(shares.get("T3_UNSKILLED", 0.0), downward * shares.get("T3_UNSKILLED", 0.0))
    shares["T3_UNSKILLED"] = max(0.0, shares.get("T3_UNSKILLED", 0.0) - t3_to_t4)
    shares["T4_DISPLACED"] = shares.get("T4_DISPLACED", 0.0) + t3_to_t4

    # Camp assimilation
    integration = assimilation_rate * _clamp01(camp_integration_bias) * max(0.0, housing_capacity)
    t4_to_t3 = min(shares.get("T4_DISPLACED", 0.0), integration * shares.get("T4_DISPLACED", 0.0))
    shares["T4_DISPLACED"] = max(0.0, shares.get("T4_DISPLACED", 0.0) - t4_to_t3)
    shares["T3_UNSKILLED"] = shares.get("T3_UNSKILLED", 0.0) + t4_to_t3 * 0.7
    shares["T2_SKILLED"] = shares.get("T2_SKILLED", 0.0) + t4_to_t3 * 0.3

    return _normalize_shares(shares)


def _education_level(world: Any, ward_id: str) -> float:
    edu_state = getattr(world, "education_by_ward", {}).get(ward_id)
    if edu_state is None:
        return 0.0
    domains = getattr(edu_state, "domains", {}) or {}
    if not domains:
        return 0.0
    avg = sum(max(0.0, float(v)) for v in domains.values()) / max(1, len(domains))
    return _clamp01(avg)


def _health_burden(world: Any, ward_id: str) -> float:
    health_state = getattr(world, "health_by_ward", {}).get(ward_id)
    if health_state is None:
        return 0.0
    return _clamp01(float(getattr(health_state, "chronic_burden", 0.0)) + sum(health_state.outbreaks.values()))


def _housing_capacity(world: Any, ward_id: str, shortage: float) -> float:
    migration_state = getattr(world, "migration_by_ward", {}).get(ward_id)
    if migration_state is None:
        return max(0.0, 0.4 - shortage)
    camp_size = float(getattr(migration_state, "camp", 0.0) or 0.0)
    pressure = _clamp01(camp_size / 5000.0)
    return max(0.0, 0.5 - shortage - pressure)


def _signature(state: WardClassState, cfg: ClassConfig, day: int) -> str:
    canonical = {
        "shares": {tier: round(state.tier_share.get(tier, 0.0), 6) for tier in TIERS},
        "wage": {tier: round(state.wage_index.get(tier, 0.0), 6) for tier in TIERS},
        "ration": {tier: round(state.ration_priority.get(tier, 0.0), 6) for tier in TIERS},
        "housing": {tier: round(state.housing_quality.get(tier, 0.0), 6) for tier in TIERS},
        "suit": {tier: round(state.suit_priority.get(tier, 0.0), 6) for tier in TIERS},
        "hardship": round(state.hardship_index, 6),
        "inequality": round(state.inequality_index, 6),
        "day": int(day),
    }
    digest = sha256((cfg.deterministic_salt + str(canonical)).encode("utf-8")).hexdigest()
    return digest


def class_hardship(world: Any, ward_id: str) -> float:
    state = getattr(world, "class_by_ward", {}).get(ward_id)
    if isinstance(state, WardClassState):
        return _clamp01(getattr(state, "hardship_index", 0.0))
    return 0.0


def class_inequality(world: Any, ward_id: str) -> float:
    state = getattr(world, "class_by_ward", {}).get(ward_id)
    if isinstance(state, WardClassState):
        return _clamp01(getattr(state, "inequality_index", 0.0))
    return 0.0


def update_class_system_for_day(world: Any, *, day: int | None = None) -> None:
    cfg = ensure_class_config(world)
    if not getattr(cfg, "enabled", False):
        return

    wards = getattr(world, "wards", {}) or {}
    if not wards:
        return
    current_day = day if day is not None else getattr(world, "day", 0)
    cadence = max(1, int(cfg.update_cadence_days))
    if current_day % cadence != 0:
        return

    metrics = ensure_metrics(world)
    class_gauges = metrics.gauges.setdefault("class", {}) if hasattr(metrics, "gauges") else {}
    hardship_values: list[float] = []
    inequality_values: list[float] = []
    camp_shares: list[float] = []

    for ward_id in sorted(wards):
        state = ensure_ward_class_state(world, ward_id)
        if state.last_update_day == current_day:
            continue
        policy = ensure_policy(world, ward_id)
        shortage = _shortage_pressure(world, ward_id)
        ration_regime = RationingRegime(getattr(policy, "rationing_regime", RationingRegime.EQUAL))
        wage_regime = WageRegime(getattr(policy, "wage_regime", WageRegime.FLAT))
        housing_bias = _clamp01(getattr(policy, "housing_allocation_bias", 0.0))
        camp_bias = _clamp01(getattr(policy, "camp_integration_bias", 0.0))
        suit_bias = _clamp01(getattr(policy, "suit_maintenance_bias", 0.0))

        ration_priority = _ration_priorities(ration_regime, shortage=shortage)
        wage_index = _wage_indices(wage_regime)
        housing_quality = _housing_quality(shortage=shortage, segregation_bias=1.0 - housing_bias)
        suit_priority = _suit_priority(suit_bias)

        health_burden = _health_burden(world, ward_id)
        education_level = _education_level(world, ward_id)
        housing_capacity = _housing_capacity(world, ward_id, shortage)

        shares = _mobility(
            shares=_normalize_shares(state.tier_share),
            mobility_rate=cfg.mobility_rate,
            assimilation_rate=cfg.camp_assimilation_rate,
            education_level=education_level,
            shortage=shortage,
            camp_integration_bias=camp_bias,
            housing_capacity=housing_capacity,
            health_burden=health_burden,
        )

        hardship = _hardship_index(
            shortage=shortage,
            tier_share=shares,
            suit_priority=suit_priority,
            housing_quality=housing_quality,
            health_burden=health_burden,
        )
        inequality = _inequality_index(
            wage=wage_index,
            ration=ration_priority,
            housing=housing_quality,
            sensitivity=cfg.inequality_sensitivity,
        )

        state.tier_share = shares
        state.wage_index = wage_index
        state.ration_priority = ration_priority
        state.housing_quality = housing_quality
        state.suit_priority = suit_priority
        state.hardship_index = hardship
        state.inequality_index = inequality
        state.last_update_day = current_day
        state.notes["signature"] = _signature(state, cfg, current_day)

        hardship_values.append(hardship)
        inequality_values.append(inequality)
        camp_shares.append(shares.get("T4_DISPLACED", 0.0))

        record_event(
            world,
            {
                "type": "RATION_REGIME_CHANGED",
                "ward_id": ward_id,
                "ration_regime": ration_regime.value,
                "wage_regime": wage_regime.value,
                "day": current_day,
            },
        )

    if isinstance(class_gauges, dict) and hardship_values:
        class_gauges["avg_hardship"] = sum(hardship_values) / len(hardship_values)
        class_gauges["avg_inequality"] = sum(inequality_values) / len(inequality_values)
        class_gauges["camp_share_total"] = sum(camp_shares)
        class_gauges["tier_share_avg"] = {
            tier: sum(state.tier_share.get(tier, 0.0) for state in getattr(world, "class_by_ward", {}).values())
            / max(1, len(getattr(world, "class_by_ward", {})))
            for tier in TIERS
        }

    metrics.topk_add("class:hardship", "avg", sum(hardship_values), payload={"day": current_day})
    for ward_id, state in sorted(getattr(world, "class_by_ward", {}).items()):
        metrics.topk_add("class:hardship:wards", ward_id, state.hardship_index, payload={"hardship": state.hardship_index})
        metrics.topk_add("class:inequality:wards", ward_id, state.inequality_index, payload={"inequality": state.inequality_index})
        metrics.topk_add("class:camps", ward_id, state.tier_share.get("T4_DISPLACED", 0.0), payload=state.tier_share)


__all__ = [
    "ClassConfig",
    "WardClassState",
    "WageRegime",
    "RationingRegime",
    "class_hardship",
    "class_inequality",
    "ensure_class_config",
    "ensure_ward_class_state",
    "update_class_system_for_day",
]

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.telemetry import ensure_metrics, record_event


@dataclass(slots=True)
class DemographicsConfig:
    enabled: bool = False
    update_cadence_days: int = 90
    annual_step_days: int = 360
    deterministic_salt: str = "demographics-v1"
    cohort_years: int = 5
    max_age: int = 80
    base_fertility: float = 0.06
    base_mortality: float = 0.01
    shock_scale: float = 0.35


@dataclass(slots=True)
class PolityDemographics:
    polity_id: str
    cohort_pop: list[float] = field(default_factory=list)
    fertility: float = 0.0
    mortality: list[float] = field(default_factory=list)
    household_rate: float = 0.0
    dependency_ratio: float = 0.0
    youth_bulge: float = 0.0
    last_annual_year: int = 0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class DemographicEvent:
    day: int
    polity_id: str
    kind: str
    magnitude: float
    effects: dict[str, object] = field(default_factory=dict)


def _clamp(lo: float, hi: float, value: float) -> float:
    return max(lo, min(hi, value))


def _stable_rng(seed: int, day: int, salt: str) -> random.Random:
    digest = sha256(f"{salt}:{seed}:{day}".encode("utf-8")).hexdigest()
    return random.Random(int(digest, 16) % (2**32))


def _cohort_count(cfg: DemographicsConfig) -> int:
    return max(1, int(math.ceil(cfg.max_age / cfg.cohort_years)) + 1)


def make_default_cohorts(total_pop: float, shape: str = "colony_adult_heavy", *, cfg: DemographicsConfig | None = None) -> list[float]:
    cfg = cfg or DemographicsConfig()
    count = _cohort_count(cfg)
    weights: list[float] = []

    for idx in range(count):
        age_start = idx * cfg.cohort_years
        if shape == "stable_pyramid":
            weight = max(0.3, 1.4 - age_start / 90.0)
        else:
            if age_start < 15:
                weight = 0.6
            elif age_start < 50:
                weight = 1.3
            elif age_start < 70:
                weight = 0.9
            else:
                weight = 0.4
        weights.append(weight)

    total_weight = sum(weights) or 1.0
    scale = float(total_pop) / total_weight if total_weight else 0.0
    return [weight * scale for weight in weights]


def _polity_ids(world: Any) -> list[str]:
    candidates: set[str] = set()
    for mapping_name in (
        "constitution_by_polity",
        "leadership_by_polity",
        "integrity_by_polity",
        "mobility_by_polity",
    ):
        mapping = getattr(world, mapping_name, {}) or {}
        candidates.update(mapping.keys())

    if not candidates:
        candidates.add("polity:central")
    return sorted(candidates)


def _estimate_population(world: Any) -> int:
    ward_total = 0
    for ward in getattr(world, "wards", {}).values():
        ward_total += int(getattr(ward, "population", 0) or 0)
    if ward_total > 0:
        return ward_total
    agent_count = len(getattr(world, "agents", {}))
    return agent_count if agent_count > 0 else 0


def _ensure_demographics(world: Any) -> tuple[DemographicsConfig, dict[str, PolityDemographics], list[DemographicEvent]]:
    cfg = getattr(world, "demographics_cfg", None)
    if not isinstance(cfg, DemographicsConfig):
        cfg = DemographicsConfig()
        world.demographics_cfg = cfg

    demo_by_polity = getattr(world, "demographics_by_polity", None)
    if demo_by_polity is None or not isinstance(demo_by_polity, dict):
        demo_by_polity = {}
        world.demographics_by_polity = demo_by_polity

    events = getattr(world, "demographic_events", None)
    if events is None:
        events = []
        world.demographic_events = events

    return cfg, demo_by_polity, events


def _bounded_append(events: list[DemographicEvent], new_events: Iterable[DemographicEvent], *, limit: int) -> None:
    events.extend(new_events)
    if len(events) > limit:
        events[:] = events[-limit:]


def _ensure_polity_state(world: Any, polity_id: str, cfg: DemographicsConfig, demo_by_polity: Mapping[str, PolityDemographics]) -> PolityDemographics:
    state = demo_by_polity.get(polity_id)
    if state is None:
        state = PolityDemographics(polity_id=polity_id)
        demo_by_polity[polity_id] = state  # type: ignore[index]

    expected_cohorts = _cohort_count(cfg)
    if not state.cohort_pop:
        default_pop = _estimate_population(world)
        state.cohort_pop = make_default_cohorts(default_pop, cfg=cfg)
    if len(state.cohort_pop) != expected_cohorts:
        existing = list(state.cohort_pop)
        if len(existing) < expected_cohorts:
            existing.extend([0.0] * (expected_cohorts - len(existing)))
        else:
            existing = existing[:expected_cohorts]
        state.cohort_pop = existing

    if not state.mortality or len(state.mortality) != expected_cohorts:
        state.mortality = [cfg.base_mortality for _ in range(expected_cohorts)]

    return state


def _mean_need_and_risk(world: Any) -> tuple[float, float]:
    wards = list(getattr(world, "wards", {}).values())
    if not wards:
        return 0.0, 0.0
    need = sum(float(getattr(ward, "need_index", 0.0) or 0.0) for ward in wards) / len(wards)
    risk = sum(float(getattr(ward, "risk_index", 0.0) or 0.0) for ward in wards) / len(wards)
    return _clamp(0.0, 2.0, need), _clamp(0.0, 2.0, risk)


def _health_burden(world: Any) -> float:
    health_states = getattr(world, "health_by_ward", {}) or {}
    if not health_states:
        return 0.0
    burden = sum(float(getattr(state, "chronic_burden", 0.0) or 0.0) for state in health_states.values())
    return _clamp(0.0, 2.0, burden / max(1, len(health_states)))


def _update_rates(world: Any, state: PolityDemographics, cfg: DemographicsConfig, *, day: int) -> None:
    rng = _stable_rng(getattr(world, "seed", 0), day, cfg.deterministic_salt)
    need, risk = _mean_need_and_risk(world)
    health = _health_burden(world)

    scarcity_penalty = 1.0 - _clamp(0.0, 0.8, need * 0.25)
    health_penalty = 1.0 - _clamp(0.0, 0.5, health * 0.2)
    security_penalty = 1.0 - _clamp(0.0, 0.4, risk * 0.15)
    jitter = 1.0 + rng.uniform(-0.02, 0.02)

    state.fertility = cfg.base_fertility * scarcity_penalty * health_penalty * jitter
    state.fertility = _clamp(0.0, cfg.base_fertility * 1.5, state.fertility)

    mortality_curve: list[float] = []
    for idx, cohort_size in enumerate(state.cohort_pop):
        age_floor = idx * cfg.cohort_years
        age_factor = 0.5 if age_floor < 5 else 1.0 + age_floor / max(1.0, cfg.max_age)
        scarcity_factor = 1.0 + need * 0.4
        health_factor = 1.0 + health * 0.3
        risk_factor = 1.0 + risk * 0.25
        base = cfg.base_mortality * age_factor * scarcity_factor * health_factor * risk_factor
        # Protect against negative or NaN due to inputs.
        base = max(0.0, float(base))
        mortality_curve.append(base)

    state.mortality = mortality_curve
    working_pop = _working_age_pop(state, cfg)
    total_pop = sum(state.cohort_pop)
    young_adults = _cohort_share(state, cfg, min_age=18, max_age=34) * total_pop
    scarcity_pressure = 1.0 - _clamp(0.0, 0.9, need * 0.4)
    state.household_rate = (young_adults / max(1.0, total_pop)) * 0.5 * scarcity_pressure
    state.last_update_day = day


def _working_age_pop(state: PolityDemographics, cfg: DemographicsConfig) -> float:
    return _cohort_share(state, cfg, min_age=15, max_age=64) * sum(state.cohort_pop)


def _cohort_share(state: PolityDemographics, cfg: DemographicsConfig, *, min_age: int, max_age: int | None = None) -> float:
    max_age = max_age if max_age is not None else cfg.max_age
    total = sum(state.cohort_pop)
    if total <= 0:
        return 0.0
    share = 0.0
    for idx, cohort_pop in enumerate(state.cohort_pop):
        start_age = idx * cfg.cohort_years
        end_age = start_age + cfg.cohort_years - 1
        if end_age < min_age:
            continue
        if start_age > max_age:
            continue
        share += cohort_pop
    return share / total


def _annual_step(world: Any, state: PolityDemographics, cfg: DemographicsConfig, *, day: int, events: list[DemographicEvent]) -> None:
    total_pop = sum(state.cohort_pop)
    births = state.fertility * total_pop

    mortality_applied = [cohort * rate for cohort, rate in zip(state.cohort_pop, state.mortality)]
    survivors = [max(0.0, cohort - death) for cohort, death in zip(state.cohort_pop, mortality_applied)]

    aged: list[float] = [0.0 for _ in survivors]
    transfer_rate = 1.0 / max(1.0, cfg.cohort_years)
    for idx, cohort in enumerate(survivors):
        move = cohort * transfer_rate
        aged[idx] += cohort - move
        if idx + 1 < len(aged):
            aged[idx + 1] += move
        else:
            aged[idx] += move

    aged[0] += births
    state.cohort_pop = aged

    working_age = _working_age_pop(state, cfg)
    dependents = _cohort_share(state, cfg, min_age=0, max_age=14) * sum(state.cohort_pop)
    dependents += _cohort_share(state, cfg, min_age=65, max_age=None) * sum(state.cohort_pop)
    state.dependency_ratio = dependents / max(working_age, 1e-6)
    state.youth_bulge = _cohort_share(state, cfg, min_age=15, max_age=24)

    _bounded_append(
        events,
        [
            DemographicEvent(
                day=day,
                polity_id=state.polity_id,
                kind="DEMOGRAPHICS_ANNUAL_STEP",
                magnitude=births,
                effects={
                    "population_total": sum(state.cohort_pop),
                    "dependency_ratio": state.dependency_ratio,
                    "youth_bulge": state.youth_bulge,
                },
            )
        ],
        limit=180,
    )

    record_event(
        world,
        {
            "kind": "DEMOGRAPHICS_ANNUAL_STEP",
            "day": day,
            "polity_id": state.polity_id,
            "population": sum(state.cohort_pop),
            "births": births,
        },
    )


def _update_metrics(world: Any, state: PolityDemographics) -> None:
    metrics = ensure_metrics(world)
    prefix = f"demo.{state.polity_id}"
    metrics.set_gauge(f"{prefix}.population_total", sum(state.cohort_pop))
    metrics.set_gauge(f"{prefix}.fertility", state.fertility)
    metrics.set_gauge(f"{prefix}.dependency_ratio", state.dependency_ratio)
    metrics.set_gauge(f"{prefix}.youth_bulge", state.youth_bulge)


def run_demographics_for_day(world: Any, *, day: int | None = None) -> None:
    cfg, demo_by_polity, events = _ensure_demographics(world)
    if not getattr(cfg, "enabled", False):
        return

    current_day = day if day is not None else getattr(world, "day", 0)
    polity_ids = _polity_ids(world)

    for polity_id in polity_ids:
        state = _ensure_polity_state(world, polity_id, cfg, demo_by_polity)
        if current_day == state.last_update_day:
            _update_metrics(world, state)
            continue

        if current_day % max(1, int(cfg.update_cadence_days)) == 0 or state.last_update_day < 0:
            _update_rates(world, state, cfg, day=current_day)

        current_year = int(current_day // max(1, int(cfg.annual_step_days)))
        if state.last_annual_year < current_year:
            _annual_step(world, state, cfg, day=current_day, events=events)
            state.last_annual_year = current_year

        _update_metrics(world, state)


__all__ = [
    "DemographicsConfig",
    "DemographicEvent",
    "PolityDemographics",
    "make_default_cohorts",
    "run_demographics_for_day",
]

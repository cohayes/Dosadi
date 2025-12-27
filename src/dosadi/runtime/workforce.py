from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from dosadi.runtime.education import DOMAINS
from dosadi.runtime.local_interactions import hashed_unit_float
from dosadi.runtime.telemetry import ensure_metrics


SKILL_ENGINEER = "ENGINEER"
SKILL_BUILDER = "BUILDER"
SKILL_REFINER = "REFINER"
SKILL_COURIER = "COURIER"
SKILL_MEDIC = "MEDIC"
SKILL_ADMIN = "ADMIN"
SKILL_GUARD = "GUARD"
SKILL_MAINTAINER = "MAINTAINER"

SKILLS: tuple[str, ...] = (
    SKILL_ENGINEER,
    SKILL_BUILDER,
    SKILL_REFINER,
    SKILL_COURIER,
    SKILL_MEDIC,
    SKILL_ADMIN,
    SKILL_GUARD,
    SKILL_MAINTAINER,
)


@dataclass(slots=True)
class WorkforceConfig:
    enabled: bool = False
    update_cadence_days: int = 3
    deterministic_salt: str = "workforce-v2"
    max_facilities_scored_per_ward: int = 40
    priority_topk: int = 18
    min_staffing_floor: float = 0.20
    allocation_step: float = 0.10


@dataclass(slots=True)
class WardWorkforcePools:
    ward_id: str
    pools: dict[str, float] = field(default_factory=dict)
    reserved: dict[str, float] = field(default_factory=dict)
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class FacilityStaffing:
    facility_id: str
    ward_id: str
    req: dict[str, float]
    alloc: dict[str, float] = field(default_factory=dict)
    ratio: float = 0.0
    priority: float = 0.0
    last_update_day: int = -1


DOMAIN_SKILL_WEIGHTS: dict[str, dict[str, float]] = {
    "ENGINEERING": {SKILL_ENGINEER: 0.6, SKILL_MAINTAINER: 0.4},
    "LOGISTICS": {SKILL_COURIER: 0.5, SKILL_ADMIN: 0.5},
    "MEDICINE": {SKILL_MEDIC: 1.0},
    "CIVICS": {SKILL_ADMIN: 1.0},
    "SECURITY": {SKILL_GUARD: 1.0},
    "TRADE": {SKILL_ADMIN: 1.0},
}


def ensure_workforce_cfg(world: Any) -> WorkforceConfig:
    cfg = getattr(world, "workforce_cfg", None)
    if not isinstance(cfg, WorkforceConfig):
        cfg = WorkforceConfig()
        world.workforce_cfg = cfg
    return cfg


def ensure_ward_workforce(world: Any, ward_id: str) -> WardWorkforcePools:
    bucket: dict[str, WardWorkforcePools] = getattr(world, "workforce_by_ward", {}) or {}
    pools = bucket.get(ward_id)
    if not isinstance(pools, WardWorkforcePools):
        pools = WardWorkforcePools(ward_id=ward_id)
        bucket[ward_id] = pools
    world.workforce_by_ward = bucket
    return pools


def ensure_staffing_entry(world: Any, facility_id: str, *, ward_id: str, req: Mapping[str, float]) -> FacilityStaffing:
    bucket: dict[str, FacilityStaffing] = getattr(world, "staffing_by_facility", {}) or {}
    staffing = bucket.get(facility_id)
    if not isinstance(staffing, FacilityStaffing):
        staffing = FacilityStaffing(facility_id=facility_id, ward_id=ward_id, req=dict(req))
        bucket[facility_id] = staffing
    world.staffing_by_facility = bucket
    return staffing


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _labor_penalty(world: Any, ward_id: str) -> float:
    orgs = getattr(world, "labor_orgs_by_ward", {}).get(ward_id) or []
    strikes = sum(1 for org in orgs if getattr(org, "status", "").upper() == "STRIKE")
    slowdowns = sum(1 for org in orgs if getattr(org, "status", "").upper() == "SLOWDOWN")
    penalty = 0.25 * strikes + 0.1 * slowdowns
    return _clamp01(1.0 - min(0.7, penalty))


def _health_multiplier(world: Any, ward_id: str) -> float:
    state = getattr(world, "health_by_ward", {}).get(ward_id)
    if state is None:
        return 1.0
    labor_mult = getattr(state, "notes", {}).get("labor_mult")
    if labor_mult is None:
        return 1.0
    try:
        return _clamp01(float(labor_mult))
    except Exception:  # pragma: no cover - defensive
        return 1.0


def _education_weights(world: Any, ward_id: str) -> dict[str, float]:
    state = getattr(world, "education_by_ward", {}).get(ward_id)
    domains = getattr(state, "domains", {}) if state is not None else {}
    weights: dict[str, float] = {skill: 0.1 for skill in SKILLS}
    for domain in DOMAINS:
        level = float(domains.get(domain, 0.0) or 0.0)
        for skill, weight in DOMAIN_SKILL_WEIGHTS.get(domain, {}).items():
            weights[skill] = weights.get(skill, 0.0) + level * weight
    total = sum(weights.values()) or 1.0
    return {skill: weight / total for skill, weight in weights.items()}


def compute_workforce_pools(world: Any, *, day: int) -> None:
    cfg = ensure_workforce_cfg(world)
    if not getattr(cfg, "enabled", False):
        return

    participation_rate = 0.35
    wards = getattr(world, "wards", {}) or {}
    for ward_id in sorted(wards.keys()):
        pools = ensure_ward_workforce(world, ward_id)
        if pools.last_update_day >= 0 and day - pools.last_update_day < cfg.update_cadence_days:
            continue

        ward = wards[ward_id]
        population = float(getattr(ward, "population", 0.0) or 0.0)
        camp = float(getattr(getattr(world, "migration_by_ward", {}).get(ward_id), "camp", 0.0) or 0.0)
        participation = participation_rate * (0.85 if camp > 0 else 1.0)
        base_fte = max(0.0, population * participation)

        health_mult = _health_multiplier(world, ward_id)
        labor_mult = _labor_penalty(world, ward_id)

        available_fte = base_fte * health_mult * labor_mult
        weights = _education_weights(world, ward_id)
        pools.pools = {skill: available_fte * weight for skill, weight in weights.items()}
        pools.notes["available_fte"] = available_fte
        pools.last_update_day = day


def _priority_for_facility(facility: Any, req: Mapping[str, float]) -> float:
    tags = getattr(facility, "role_tags", set()) or set()
    priority = 1.0
    if tags & {"water", "health", "life_support"}:
        priority += 2.0
    if SKILL_MEDIC in req:
        priority += 1.5
    if "security" in tags or SKILL_GUARD in req:
        priority += 0.8
    if "logistics" in tags or SKILL_COURIER in req:
        priority += 0.4
    return priority


def _bounded_demands(world: Any, ward_id: str, *, max_count: int) -> list[Any]:
    facilities = getattr(world, "facilities", {}) or {}
    demands = [
        facility
        for facility in facilities.values()
        if getattr(facility, "ward_id", getattr(facility, "site_node_id", "")) == ward_id
        and getattr(facility, "status", "ACTIVE") == "ACTIVE"
        and getattr(facility, "is_operational", True)
    ]
    demands.sort(key=lambda f: f.facility_id)
    return demands[:max_count]


def _alloc_ratio(available: Mapping[str, float], req: Mapping[str, float], *, min_floor: float) -> tuple[float, dict[str, float]]:
    allocations: dict[str, float] = {}
    if not req:
        return 1.0, allocations
    ratios: list[float] = []
    for skill, needed in req.items():
        need = float(needed or 0.0)
        if need <= 0:
            allocations[skill] = 0.0
            continue
        have = float(available.get(skill, 0.0) or 0.0)
        ratio = 0.0 if have <= 0 else min(1.0, have / need)
        allocations[skill] = min(have, need)
        ratios.append(ratio)
    if not ratios:
        return 1.0, allocations
    ratio = min(ratios)
    ratio = max(min_floor, ratio) if sum(req.values()) > 0 else 1.0
    return ratio, allocations


def allocate_staffing_for_ward(world: Any, ward_id: str, *, day: int) -> None:
    cfg = ensure_workforce_cfg(world)
    if not getattr(cfg, "enabled", False):
        return

    pools = ensure_ward_workforce(world, ward_id)
    available = {
        skill: max(0.0, float(count) - float(pools.reserved.get(skill, 0.0)))
        for skill, count in pools.pools.items()
    }

    demands = _bounded_demands(world, ward_id, max_count=cfg.max_facilities_scored_per_ward)
    scored: list[tuple[float, Any]] = []
    for facility in demands:
        req = getattr(facility, "staff_req", {}) or {}
        if not req:
            continue
        priority = _priority_for_facility(facility, req)
        scored.append((priority, facility))

    scored.sort(key=lambda item: (-item[0], getattr(item[1], "facility_id", "")))
    scored = scored[: cfg.priority_topk]

    telemetry = ensure_metrics(world)
    workforce_metrics = telemetry.gauges.setdefault("workforce", {})
    if not isinstance(workforce_metrics, dict):
        workforce_metrics = {}
        telemetry.gauges["workforce"] = workforce_metrics

    total_ratio = 0.0
    staffed = 0
    for priority, facility in scored:
        req = getattr(facility, "staff_req", {}) or {}
        staffing = ensure_staffing_entry(world, facility.facility_id, ward_id=ward_id, req=req)
        ratio, alloc = _alloc_ratio(available, req, min_floor=cfg.min_staffing_floor)
        staffing.alloc = {skill: round(value, 3) for skill, value in alloc.items()}
        staffing.ratio = ratio
        staffing.priority = priority
        staffing.last_update_day = day
        for skill, value in alloc.items():
            available[skill] = max(0.0, available.get(skill, 0.0) - value)
        total_ratio += ratio
        staffed += 1

    workforce_metrics["fte_total"] = workforce_metrics.get("fte_total", 0.0) + sum(pools.pools.values())
    workforce_metrics["fte_by_skill"] = {skill: round(count, 3) for skill, count in pools.pools.items()}
    workforce_metrics["avg_staffing_ratio"] = 0.0 if staffed == 0 else total_ratio / staffed


def staffing_ratio(world: Any, facility_id: str, default: float = 1.0) -> float:
    staffing = getattr(world, "staffing_by_facility", {}).get(facility_id)
    if staffing is None:
        return default
    try:
        return max(0.0, min(1.0, float(staffing.ratio)))
    except Exception:  # pragma: no cover - defensive
        return default


def apply_staffing_multiplier(value: float, world: Any, facility_id: str) -> float:
    return float(value) * staffing_ratio(world, facility_id, default=1.0)


__all__ = [
    "WorkforceConfig",
    "WardWorkforcePools",
    "FacilityStaffing",
    "SKILLS",
    "compute_workforce_pools",
    "allocate_staffing_for_ward",
    "staffing_ratio",
    "apply_staffing_multiplier",
    "ensure_workforce_cfg",
    "ensure_ward_workforce",
]


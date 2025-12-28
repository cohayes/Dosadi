from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from dosadi.runtime.kpis import KPIStore, SCHEMA, update_kpis


@dataclass(slots=True)
class Scorecard:
    score_total: float
    grades: Mapping[str, float] = field(default_factory=dict)
    badges: list[str] = field(default_factory=list)
    kpis: Mapping[str, float] = field(default_factory=dict)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _grade_progress(kpis: Mapping[str, float]) -> float:
    achieved = float(kpis.get("progress.milestones_achieved", 0.0))
    return _clamp(achieved / 5.0)


def _grade_logistics(kpis: Mapping[str, float]) -> float:
    deliveries = float(kpis.get("logistics.deliveries_completed", 0.0))
    routes = float(kpis.get("logistics.routes_active", 0.0))
    success_rate = float(kpis.get("logistics.delivery_success_rate", 0.0))
    base = (deliveries / 10.0) + (routes / 5.0) + success_rate
    return _clamp(base / 3.0)


def _grade_safety(kpis: Mapping[str, float]) -> float:
    alive_ratio = float(kpis.get("safety.population_alive_ratio", 1.0))
    incidents = float(kpis.get("safety.incidents_total", 0.0))
    penalty = min(incidents / 20.0, 1.0)
    return _clamp(alive_ratio - penalty)


def _grade_governance(kpis: Mapping[str, float]) -> float:
    council = float(kpis.get("governance.council_formed", 0.0))
    protocols = float(kpis.get("governance.protocols_authored", 0.0))
    return _clamp((council * 0.6) + min(protocols / 5.0, 0.4))


def _grade_economy(kpis: Mapping[str, float]) -> float:
    shortage_days = float(kpis.get("economy.water_shortage_severe_days", 0.0))
    return _clamp(1.0 - min(shortage_days / 10.0, 1.0))


def compute_scorecard(world: Any, *, tick: int | None = None) -> Scorecard:
    tick_value = getattr(world, "tick", 0) if tick is None else tick
    store: KPIStore = update_kpis(world, tick_value, mode="run_end")
    kpis = {name: value.value for name, value in store.values.items() if name in SCHEMA}

    grades = {
        "progress": _grade_progress(kpis),
        "logistics": _grade_logistics(kpis),
        "safety": _grade_safety(kpis),
        "governance": _grade_governance(kpis),
        "economy": _grade_economy(kpis),
    }

    score_total = (
        grades["progress"] * 0.35
        + grades["logistics"] * 0.25
        + grades["governance"] * 0.15
        + grades["safety"] * 0.15
        + grades["economy"] * 0.10
    )

    badges: list[str] = []
    if kpis.get("logistics.depots_built", 0.0) > 0:
        badges.append("FIRST_DEPOT_BUILT")
    if kpis.get("logistics.deliveries_completed", 0.0) > 0:
        badges.append("FIRST_DELIVERY")
    if kpis.get("governance.council_formed", 0.0) > 0:
        badges.append("COUNCIL_FORMED")
    if kpis.get("economy.water_shortage_severe_days", 0.0) == 0:
        badges.append("NO_SHORTAGE_CRISIS")

    return Scorecard(score_total=score_total, grades=grades, badges=badges, kpis=kpis)


__all__ = ["Scorecard", "compute_scorecard"]

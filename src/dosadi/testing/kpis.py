from __future__ import annotations

from typing import Any, Dict


def _ticks_per_day(world: Any) -> int:
    ticks_per_day = getattr(world, "ticks_per_day", None)
    if ticks_per_day is None:
        ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", None)
    try:
        ticks_per_day = int(ticks_per_day) if ticks_per_day is not None else None
    except (TypeError, ValueError):
        ticks_per_day = None
    return max(1, ticks_per_day or 144_000)


def collect_kpis(world: Any) -> Dict[str, object]:
    ticks_per_day = _ticks_per_day(world)
    day = getattr(world, "day", getattr(world, "tick", 0) // ticks_per_day)
    year = day // 365

    agents = getattr(world, "agents", {}) or {}
    facilities = getattr(world, "facilities", {}) or {}
    groups = getattr(world, "groups", []) or []
    protocols_registry = getattr(world, "protocols", None)
    protocols_total = len(getattr(protocols_registry, "protocols_by_id", {}) or {})

    hunger_levels = []
    hydration_levels = []
    fatigue_levels = []
    for agent in agents.values():
        physical = getattr(agent, "physical", None)
        if physical is None:
            continue
        hunger_levels.append(getattr(physical, "hunger_level", 0.0))
        hydration_levels.append(getattr(physical, "hydration_level", 0.0))
        fatigue_levels.append(getattr(physical, "sleep_pressure", 0.0))

    def _avg(values):
        return float(sum(values) / len(values)) if values else 0.0

    return {
        "agents_total": len(agents),
        "facilities_total": len(facilities),
        "groups_total": len(groups),
        "protocols_total": protocols_total,
        "avg_hunger": _avg(hunger_levels),
        "avg_hydration": _avg(hydration_levels),
        "avg_fatigue": _avg(fatigue_levels),
        "day": day,
        "year": year,
    }


__all__ = ["collect_kpis"]

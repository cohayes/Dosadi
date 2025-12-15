from __future__ import annotations
from typing import Any, Iterable, Mapping


def _ticks_per_day(world) -> int:
    ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", None)
    if ticks_per_day is None:
        ticks_per_day = getattr(world, "ticks_per_day", 144_000)
    try:
        return max(1, int(ticks_per_day))
    except Exception:
        return 144_000


def _iter_agents(world) -> Iterable:
    agents = getattr(world, "agents", None)
    if isinstance(agents, Mapping):
        return agents.values()
    if agents is None:
        return []
    return agents


def _mean_attr(agents: Iterable[Any], attr: str, *, fallback_attr: str | None = None) -> float:
    values = []
    for agent in agents:
        target = getattr(agent, "physical", agent)
        value = getattr(target, attr, None)
        if value is None and fallback_attr:
            value = getattr(target, fallback_attr, None)
        if value is None:
            continue
        try:
            values.append(float(value))
        except Exception:
            continue
    if not values:
        return 0.0
    return sum(values) / len(values)


def collect_kpis(world) -> dict[str, Any]:
    """Collect a stable, lightweight KPI snapshot from the world."""

    tick = getattr(world, "tick", 0)
    ticks_per_day = _ticks_per_day(world)
    day = tick // ticks_per_day
    year = day // 365

    agents = list(_iter_agents(world))
    facilities = getattr(world, "facilities", {}) or {}
    groups = getattr(world, "groups", []) or []
    protocols = getattr(getattr(world, "protocols", None), "protocols_by_id", {}) or {}
    wards = getattr(world, "wards", {}) or {}
    queues = getattr(world, "queues", {}) or {}
    well = getattr(world, "well", None)

    agents_alive = 0
    for agent in agents:
        physical = getattr(agent, "physical", agent)
        is_alive = getattr(physical, "is_alive", getattr(agent, "is_alive", True))
        if is_alive is None:
            is_alive = True
        agents_alive += 1 if is_alive else 0

    return {
        "agents_total": len(agents),
        "agents_alive": agents_alive,
        "groups_total": len(groups),
        "facilities_total": len(facilities),
        "protocols_total": len(protocols),
        "wards_total": len(wards),
        "queues_total": len(queues),
        "avg_hunger": _mean_attr(agents, "hunger_level"),
        "avg_thirst": _mean_attr(agents, "hydration_level", fallback_attr="thirst"),
        "avg_fatigue": _mean_attr(agents, "fatigue", fallback_attr="sleep_pressure"),
        "water_total": getattr(well, "daily_capacity", 0.0) if well is not None else 0.0,
        "day": day,
        "year": year,
        "tick": tick,
    }


__all__ = ["collect_kpis"]

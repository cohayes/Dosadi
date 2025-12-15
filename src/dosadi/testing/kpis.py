"""Lightweight KPI collection helpers for deterministic harness checks."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Iterable, Mapping

from dosadi.runtime.snapshot import world_signature


def _average(values: Iterable[float]) -> float:
    total = 0.0
    count = 0
    for value in values:
        try:
            num = float(value)
        except (TypeError, ValueError):
            continue
        total += num
        count += 1
    return total / count if count else 0.0


def _ticks_per_day(world: Any) -> int:
    ticks_per_day = getattr(world, "ticks_per_day", None)
    if ticks_per_day is None:
        ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", 144_000)
    try:
        ticks_per_day = int(ticks_per_day)
    except (TypeError, ValueError):
        ticks_per_day = 144_000
    return max(1, ticks_per_day)


def _signature_enabled(world: Any) -> bool:
    cfg_candidates = (
        getattr(world, "runtime_config", None),
        getattr(world, "config", None),
    )
    for cfg in cfg_candidates:
        if cfg is None:
            continue
        if getattr(cfg, "kpi_signature_enabled", None) is not None:
            return bool(getattr(cfg, "kpi_signature_enabled"))
        if getattr(cfg, "kpi_signatures_enabled", None) is not None:
            return bool(getattr(cfg, "kpi_signatures_enabled"))
        if getattr(cfg, "world_signature_enabled", None) is not None:
            return bool(getattr(cfg, "world_signature_enabled"))
    return False


def _collect_stocks(world: Any) -> Mapping[str, float]:
    snapshot: Mapping[str, float] = {}
    if hasattr(world, "resource_snapshot"):
        try:
            snapshot = world.resource_snapshot()
        except Exception:
            snapshot = {}
    return snapshot or {}


def collect_kpis(world: Any) -> dict:
    """Collect stable, cheap KPIs from the given world state."""

    tick = getattr(world, "tick", 0)
    ticks_per_day = _ticks_per_day(world)
    day = tick // ticks_per_day
    year = day // 365

    agents = list(getattr(world, "agents", {}).values())
    hunger = _average(getattr(getattr(agent, "physical", SimpleNamespace()), "hunger_level", 0.0) for agent in agents)
    hydration = _average(
        getattr(getattr(agent, "physical", SimpleNamespace()), "hydration_level", 0.0) for agent in agents
    )
    sleep_pressure = _average(
        getattr(getattr(agent, "physical", SimpleNamespace()), "sleep_pressure", 0.0) for agent in agents
    )

    stocks = _collect_stocks(world)
    stock_values = [v for v in stocks.values() if isinstance(v, (int, float))]
    stocks_total = float(sum(stock_values)) if stock_values else 0.0
    water_total = stocks.get("Water") if isinstance(stocks, Mapping) else None
    if water_total is None:
        water_total = getattr(getattr(world, "well", None), "daily_capacity", 0.0)

    kpis = {
        "tick": tick,
        "day": day,
        "year": year,
        "agents_total": len(agents),
        "agents_awake": sum(1 for a in agents if not getattr(a, "is_asleep", False)),
        "agents_alive": sum(1 for a in agents if getattr(a, "is_alive", True)),
        "groups_total": len(getattr(world, "groups", [])),
        "facilities_total": len(getattr(world, "facilities", {})),
        "protocols_total": len(getattr(getattr(world, "protocols", None), "protocols_by_id", {})),
        "avg_hunger": hunger,
        "avg_hydration": hydration,
        "avg_sleep_pressure": sleep_pressure,
        "stocks": stocks,
        "stocks_total": stocks_total,
        "water_total": water_total,
        "ward_count": len(getattr(world, "wards", {})),
    }

    security_reports = getattr(world, "security_reports", None)
    if security_reports is not None:
        try:
            kpis["incidents_total"] = len(security_reports)
        except Exception:
            pass

    if _signature_enabled(world):
        kpis["world_signature"] = world_signature(world)

    return kpis


__all__ = ["collect_kpis"]

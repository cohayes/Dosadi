from __future__ import annotations

from typing import Any

from dosadi.runtime.kpis import flatten_kpis_for_report, update_kpis
from dosadi.runtime.snapshot import world_signature


def collect_kpis(world) -> dict[str, Any]:
    """Collect the canonical KPI snapshot via the runtime KPI pipeline."""

    tick = getattr(world, "tick", 0)
    update_kpis(world, tick, mode="run_end")
    report = flatten_kpis_for_report(getattr(world, "kpis", None))
    ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", 144_000)
    day_value = getattr(world, "day", None)
    if day_value is None or day_value == 0:
        try:
            ticks_per_day = int(ticks_per_day)
        except Exception:
            ticks_per_day = 144_000
        day_value = int(tick) // max(1, ticks_per_day)
    report.setdefault("day", day_value)
    report.setdefault("tick", tick)
    report.setdefault("year", int(report["day"]) // 365 if "day" in report else 0)
    agents = getattr(world, "agents", {}) or {}
    report["agents_total"] = len(agents)
    if agents:
        hunger = 0.0
        hydration = 0.0
        sleep_pressure = 0.0
        for agent in agents.values():
            physical = getattr(agent, "physical", agent)
            hunger += float(getattr(physical, "hunger_level", 0.0) or 0.0)
            hydration += float(getattr(physical, "hydration_level", 0.0) or 0.0)
            sleep_pressure += float(getattr(physical, "sleep_pressure", 0.0) or 0.0)
        denom = max(1, len(agents))
        report["avg_hunger"] = hunger / denom
        report["avg_hydration"] = hydration / denom
        report["avg_sleep_pressure"] = sleep_pressure / denom
    if getattr(getattr(world, "runtime_config", None), "kpi_signatures_enabled", False):
        report["world_signature"] = world_signature(world)
    return report


__all__ = ["collect_kpis"]

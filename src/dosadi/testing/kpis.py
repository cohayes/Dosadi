from __future__ import annotations

from typing import Any

from dosadi.runtime.kpis import flatten_kpis_for_report, update_kpis


def collect_kpis(world) -> dict[str, Any]:
    """Collect the canonical KPI snapshot via the runtime KPI pipeline."""

    tick = getattr(world, "tick", 0)
    update_kpis(world, tick, mode="run_end")
    return flatten_kpis_for_report(getattr(world, "kpis", None))


__all__ = ["collect_kpis"]

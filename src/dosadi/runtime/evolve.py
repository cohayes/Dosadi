from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dosadi.runtime.snapshot import save_snapshot, snapshot_world, world_signature
from dosadi.runtime.timewarp import TimewarpConfig, step_day
from dosadi.world.timebase import TICKS_PER_DAY


def collect_kpis(world: Any) -> Dict[str, Any]:
    """Collect stable, low-cost KPIs from the world state."""

    ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", TICKS_PER_DAY)
    try:
        ticks_per_day = max(1, int(ticks_per_day))
    except (TypeError, ValueError):
        ticks_per_day = TICKS_PER_DAY

    return {
        "agents_total": len(getattr(world, "agents", {})),
        "groups_total": len(getattr(world, "groups", [])),
        "protocols_total": len(getattr(getattr(world, "protocols", None), "protocols_by_id", {})),
        "facilities_total": len(getattr(world, "facilities", {})),
        "water_total": getattr(getattr(world, "well", None), "daily_capacity", 0.0),
        "ward_count": len(getattr(world, "wards", {})),
        "day": getattr(world, "tick", 0) // ticks_per_day,
    }


@dataclass(slots=True)
class EvolveConfig:
    target_years: int = 200
    cruise_days: int = 30
    microsim_days: int = 1
    microsim_every_days: int = 90
    save_every_days: int = 365
    max_steps: Optional[int] = None
    timewarp_cfg: TimewarpConfig = field(default_factory=TimewarpConfig)
    vault_dir: Path = Path("seeds")
    seed_prefix: str = "empire"
    kpi_enabled: bool = True
    signature_enabled: bool = True
    save_initial_snapshot: bool = True


def _ensure_ticks_per_day(world: Any) -> int:
    ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", TICKS_PER_DAY)
    try:
        ticks_per_day = int(ticks_per_day)
    except (TypeError, ValueError):
        ticks_per_day = TICKS_PER_DAY
    return max(1, ticks_per_day)


def _run_ticks(world: Any, *, ticks: int, tick_fn: Callable[[Any], None]) -> None:
    total_ticks = max(0, int(ticks))
    for _ in range(total_ticks):
        tick_fn(world)


def _record_milestone(
    *,
    world: Any,
    scenario_id: str,
    seed: int,
    cfg: EvolveConfig,
    day_cursor: int,
    milestone_type: str,
    milestones: List[Dict[str, Any]],
) -> Dict[str, Any]:
    snapshot = snapshot_world(world, scenario_id=scenario_id)
    snapshot_path = (
        cfg.vault_dir
        / "snapshots"
        / f"{cfg.seed_prefix}__{scenario_id}__seed-{seed}__day-{day_cursor:05d}.json.gz"
    )
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_sha = save_snapshot(snapshot, snapshot_path, gzip_output=True)

    entry: Dict[str, Any] = {
        "scenario_id": scenario_id,
        "seed": seed,
        "milestone_type": milestone_type,
        "day": day_cursor,
        "year": day_cursor // 365,
        "tick": getattr(world, "tick", 0),
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": snapshot_sha,
    }

    if cfg.kpi_enabled:
        entry["kpis"] = collect_kpis(world)
    if cfg.signature_enabled:
        entry["world_signature"] = world_signature(world)

    milestones.append(entry)
    return entry


def evolve_seed(
    *,
    world: Any,
    scenario_id: str,
    seed: int,
    cfg: EvolveConfig,
    tick_fn: Callable[[Any], None],
) -> Dict[str, Any]:
    ticks_per_day = _ensure_ticks_per_day(world)
    total_days_target = cfg.target_years * 365
    day_cursor = 0
    steps = 0

    milestones: List[Dict[str, Any]] = []
    if cfg.save_initial_snapshot:
        _record_milestone(
            world=world,
            scenario_id=scenario_id,
            seed=seed,
            cfg=cfg,
            day_cursor=day_cursor,
            milestone_type="initial",
            milestones=milestones,
        )

    while day_cursor < total_days_target:
        if cfg.max_steps is not None and steps >= cfg.max_steps:
            raise RuntimeError(
                f"Reached max_steps={cfg.max_steps} before completing target_days={total_days_target}"
            )

        step_day(world, days=cfg.cruise_days, cfg=cfg.timewarp_cfg)
        day_cursor += cfg.cruise_days
        steps += 1

        if cfg.microsim_every_days and day_cursor % cfg.microsim_every_days == 0:
            _run_ticks(world, ticks=cfg.microsim_days * ticks_per_day, tick_fn=tick_fn)

        if day_cursor % cfg.save_every_days == 0 or day_cursor >= total_days_target:
            milestone_type = "final" if day_cursor >= total_days_target else "interval"
            _record_milestone(
                world=world,
                scenario_id=scenario_id,
                seed=seed,
                cfg=cfg,
                day_cursor=day_cursor,
                milestone_type=milestone_type,
                milestones=milestones,
            )

    return {
        "scenario_id": scenario_id,
        "seed": seed,
        "ticks_per_day": ticks_per_day,
        "days_simulated": day_cursor,
        "milestones": milestones,
        "steps": steps,
    }


__all__ = ["EvolveConfig", "collect_kpis", "evolve_seed"]

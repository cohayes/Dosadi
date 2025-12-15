from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Sequence

from dosadi.playbook.scenario_runner import FoundingWakeupScenarioConfig

from dosadi.runtime.founding_wakeup import step_world_once
from dosadi.runtime.run_outputs import append_timeline_row, generate_run_id, prepare_run_directory
from dosadi.runtime.snapshot import load_snapshot, restore_world, world_signature
from dosadi.runtime.timewarp import DEFAULT_TICKS_PER_DAY, TimewarpConfig, step_day
from dosadi.runtime.wakeup_prime import step_wakeup_prime_once
from dosadi.vault.seed_vault import save_seed
from dosadi.world.scenarios.founding_wakeup import generate_founding_wakeup_mvp
from dosadi.scenarios.wakeup_prime import WakeupPrimeScenarioConfig, generate_wakeup_scenario_prime
from dosadi.testing.kpis import collect_kpis


@dataclass(slots=True)
class EvolveConfig:
    target_years: int = 200
    cruise_days: int = 30
    microsim_days: int = 1
    microsim_every_days: int = 90
    save_every_days: int = 365
    max_steps: int | None = None
    timewarp_cfg: TimewarpConfig = field(default_factory=TimewarpConfig)
    vault_dir: Path = Path("seeds")
    runs_dir: Path = Path("runs")
    seed_prefix: str = "empire"
    kpi_enabled: bool = True
    signature_enabled: bool = True
    save_initial_snapshot: bool = True


_ScenarioInitializer = Callable[[int], Any]
_StepFn = Callable[[Any], None]


_SCENARIO_REGISTRY: Mapping[str, tuple[_ScenarioInitializer, _StepFn]] = {
    "founding_wakeup": (
        lambda seed: generate_founding_wakeup_mvp(
            num_agents=FoundingWakeupScenarioConfig().num_agents, seed=seed
        ),
        step_world_once,
    ),
    "founding_wakeup_mvp": (
        lambda seed: generate_founding_wakeup_mvp(
            num_agents=FoundingWakeupScenarioConfig().num_agents, seed=seed
        ),
        step_world_once,
    ),
    "wakeup_prime": (
        lambda seed: generate_wakeup_scenario_prime(WakeupPrimeScenarioConfig(seed=seed)).world,
        step_wakeup_prime_once,
    ),
}


def _ticks_per_day(world: Any) -> int:
    ticks_per_day = getattr(world, "ticks_per_day", None)
    if ticks_per_day is None:
        ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", None)
    try:
        ticks_per_day = int(ticks_per_day) if ticks_per_day is not None else None
    except (TypeError, ValueError):
        ticks_per_day = None
    if ticks_per_day is None or ticks_per_day <= 0:
        return DEFAULT_TICKS_PER_DAY
    return ticks_per_day


def _seed_rng(seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np  # type: ignore

        np.random.seed(seed)
    except Exception:
        # NumPy may not be installed in minimal environments.
        pass


def _run_ticks(world: Any, *, ticks: int, step_fn: _StepFn) -> None:
    for _ in range(max(0, int(ticks))):
        step_fn(world)


def _current_day(world: Any, ticks_per_day: int) -> int:
    day = getattr(world, "day", None)
    if isinstance(day, int) and day >= 0:
        return day
    tick = getattr(world, "tick", 0)
    try:
        return int(tick) // max(1, int(ticks_per_day))
    except Exception:
        return 0


def _record_milestone(
    *,
    world: Any,
    scenario_id: str,
    seed: int,
    run_id: str,
    run_dir: Path,
    milestone_type: str,
    day: int,
    cfg: EvolveConfig,
    milestone_idx: int,
) -> Dict[str, Any]:
    seed_id = f"{cfg.seed_prefix}-{seed:05d}-{milestone_idx:04d}"
    snapshot_entry = save_seed(
        cfg.vault_dir,
        world,
        seed_id=seed_id,
        scenario_id=scenario_id,
        meta={"run_id": run_id, "milestone_type": milestone_type, "day": day},
    )

    signature = world_signature(world) if cfg.signature_enabled else None
    kpis = collect_kpis(world) if cfg.kpi_enabled else {}
    snapshot_path = Path(cfg.vault_dir, snapshot_entry.get("snapshot_path", ""))

    row = append_timeline_row(
        run_dir,
        run_id=run_id,
        scenario_id=scenario_id,
        seed=seed,
        day=day,
        tick=getattr(world, "tick", 0),
        milestone_type=milestone_type,
        snapshot_path=snapshot_path,
        snapshot_sha256=snapshot_entry.get("snapshot_sha256", ""),
        kpis=kpis,
        world_signature=signature,
        year=day // 365,
    )
    row["seed_id"] = seed_id
    return row


def _should_run_microsim(day_cursor: int, cfg: EvolveConfig) -> bool:
    if cfg.microsim_days <= 0:
        return False
    if cfg.microsim_every_days <= 0:
        return False
    return day_cursor % cfg.microsim_every_days == 0


def _maybe_trigger_milestones(day_cursor: int) -> Sequence[str]:
    # Placeholder for future trigger-based milestones (e.g., KPI thresholds).
    return []


def _evolve_world(
    *,
    world: Any,
    scenario_id: str,
    seed: int,
    cfg: EvolveConfig,
    run_id: str,
    run_dir: Path,
    step_fn: _StepFn,
) -> Dict[str, Any]:
    ticks_per_day = _ticks_per_day(world)
    target_days = max(0, int(cfg.target_years)) * 365
    day_cursor = _current_day(world, ticks_per_day)
    milestones: List[Dict[str, Any]] = []
    milestone_idx = 0

    if cfg.save_initial_snapshot:
        milestones.append(
            _record_milestone(
                world=world,
                scenario_id=scenario_id,
                seed=seed,
                run_id=run_id,
                run_dir=run_dir,
                milestone_type="initial",
                day=day_cursor,
                cfg=cfg,
                milestone_idx=milestone_idx,
            )
        )
        milestone_idx += 1

    steps = 0
    while day_cursor < target_days:
        if cfg.max_steps is not None and steps >= cfg.max_steps:
            break
        steps += 1

        remaining_days = target_days - day_cursor
        cruise_days = min(cfg.cruise_days, remaining_days)
        step_day(world, days=cruise_days, cfg=cfg.timewarp_cfg)
        day_cursor = _current_day(world, ticks_per_day)

        if _should_run_microsim(day_cursor, cfg):
            _run_ticks(world, ticks=cfg.microsim_days * ticks_per_day, step_fn=step_fn)
            day_cursor = _current_day(world, ticks_per_day)

        if cfg.save_every_days > 0 and day_cursor % cfg.save_every_days == 0:
            milestones.append(
                _record_milestone(
                    world=world,
                    scenario_id=scenario_id,
                    seed=seed,
                    run_id=run_id,
                    run_dir=run_dir,
                    milestone_type="annual",
                    day=day_cursor,
                    cfg=cfg,
                    milestone_idx=milestone_idx,
                )
            )
            milestone_idx += 1

        for trigger_type in _maybe_trigger_milestones(day_cursor):
            milestones.append(
                _record_milestone(
                    world=world,
                    scenario_id=scenario_id,
                    seed=seed,
                    run_id=run_id,
                    run_dir=run_dir,
                    milestone_type=trigger_type,
                    day=day_cursor,
                    cfg=cfg,
                    milestone_idx=milestone_idx,
                )
            )
            milestone_idx += 1

    if not milestones or milestones[-1].get("milestone_type") != "final":
        milestones.append(
            _record_milestone(
                world=world,
                scenario_id=scenario_id,
                seed=seed,
                run_id=run_id,
                run_dir=run_dir,
                milestone_type="final",
                day=day_cursor,
                cfg=cfg,
                milestone_idx=milestone_idx,
            )
        )

    return {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "seed": seed,
        "target_days": target_days,
        "final_tick": getattr(world, "tick", 0),
        "final_day": day_cursor,
        "run_dir": run_dir,
        "milestones": milestones,
        "vault_dir": cfg.vault_dir,
    }


def evolve_seed(
    *,
    scenario_id: str,
    seed: int,
    cfg: EvolveConfig,
    notes: str | None = None,
    timestamp: datetime | None = None,
) -> Dict[str, Any]:
    if scenario_id not in _SCENARIO_REGISTRY:
        raise ValueError(f"Unknown scenario '{scenario_id}'")

    initializer, step_fn = _SCENARIO_REGISTRY[scenario_id]
    _seed_rng(seed)
    world = initializer(seed)

    run_id = generate_run_id(scenario_id, seed, timestamp=timestamp)
    run_dir = prepare_run_directory(cfg.runs_dir, run_id, config=cfg, notes=notes)
    return _evolve_world(
        world=world,
        scenario_id=scenario_id,
        seed=seed,
        cfg=cfg,
        run_id=run_id,
        run_dir=run_dir,
        step_fn=step_fn,
    )


def evolve_from_snapshot(
    *,
    snapshot_path: Path,
    cfg: EvolveConfig,
    notes: str | None = None,
    timestamp: datetime | None = None,
) -> Dict[str, Any]:
    snapshot = load_snapshot(snapshot_path)
    world = restore_world(snapshot)
    scenario_id = snapshot.scenario_id
    seed = snapshot.seed

    if scenario_id not in _SCENARIO_REGISTRY:
        raise ValueError(f"Unknown scenario '{scenario_id}'")

    _, step_fn = _SCENARIO_REGISTRY[scenario_id]

    run_id = (
        generate_run_id(
            scenario_id,
            seed,
            timestamp=timestamp or datetime.now(tz=timezone.utc),
        )
        + "__resume"
    )
    run_dir = prepare_run_directory(cfg.runs_dir, run_id, config=cfg, notes=notes)
    return _evolve_world(
        world=world,
        scenario_id=scenario_id,
        seed=seed,
        cfg=cfg,
        run_id=run_id,
        run_dir=run_dir,
        step_fn=step_fn,
    )


__all__ = [
    "EvolveConfig",
    "evolve_seed",
    "evolve_from_snapshot",
]

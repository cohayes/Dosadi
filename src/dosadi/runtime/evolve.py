from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Sequence

from dosadi.playbook.scenario_runner import FoundingWakeupScenarioConfig

from dosadi.runtime.founding_wakeup import step_world_once
from dosadi.runtime.snapshot import load_snapshot, restore_world, world_signature
from dosadi.runtime.timewarp import TimewarpConfig, step_day
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
    seed_prefix: str = "empire"
    kpi_enabled: bool = True
    signature_enabled: bool = True
    save_initial_snapshot: bool = True


_ScenarioInitializer = Callable[[int], Any]
_StepFn = Callable[[Any], None]


_SCENARIO_REGISTRY: Mapping[str, tuple[_ScenarioInitializer, _StepFn]] = {
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
        return 144_000
    return ticks_per_day


def _run_ticks(world: Any, *, ticks: int, step_fn: _StepFn) -> None:
    for _ in range(max(0, int(ticks))):
        step_fn(world)


def _record_milestone(
    *,
    world: Any,
    scenario_id: str,
    seed: int,
    run_id: str,
    milestone_type: str,
    day: int,
    ticks_per_day: int,
    cfg: EvolveConfig,
    timeline_path: Path,
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

    row = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "seed": seed,
        "tick": getattr(world, "tick", 0),
        "day": day,
        "year": day // 365,
        "milestone_type": milestone_type,
        "seed_id": seed_id,
        "snapshot_path": snapshot_entry.get("snapshot_path"),
        "snapshot_sha256": snapshot_entry.get("snapshot_sha256"),
    }
    if signature is not None:
        row["world_signature"] = signature
    if cfg.kpi_enabled:
        row["kpis"] = kpis

    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    with open(timeline_path, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, sort_keys=True))
        fp.write("\n")
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
    timeline_path: Path,
    step_fn: _StepFn,
) -> Dict[str, Any]:
    ticks_per_day = _ticks_per_day(world)
    target_days = max(0, int(cfg.target_years)) * 365
    day_cursor = getattr(world, "day", getattr(world, "tick", 0) // ticks_per_day)
    milestones: List[Dict[str, Any]] = []
    milestone_idx = 0

    if cfg.save_initial_snapshot:
        milestones.append(
            _record_milestone(
                world=world,
                scenario_id=scenario_id,
                seed=seed,
                run_id=run_id,
                milestone_type="initial",
                day=day_cursor,
                ticks_per_day=ticks_per_day,
                cfg=cfg,
                timeline_path=timeline_path,
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
        day_cursor += cruise_days

        if _should_run_microsim(day_cursor, cfg):
            _run_ticks(world, ticks=cfg.microsim_days * ticks_per_day, step_fn=step_fn)
            day_cursor = getattr(world, "day", getattr(world, "tick", 0) // ticks_per_day)

        if cfg.save_every_days > 0 and day_cursor % cfg.save_every_days == 0:
            milestones.append(
                _record_milestone(
                    world=world,
                    scenario_id=scenario_id,
                    seed=seed,
                    run_id=run_id,
                    milestone_type="annual",
                    day=day_cursor,
                    ticks_per_day=ticks_per_day,
                    cfg=cfg,
                    timeline_path=timeline_path,
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
                    milestone_type=trigger_type,
                    day=day_cursor,
                    ticks_per_day=ticks_per_day,
                    cfg=cfg,
                    timeline_path=timeline_path,
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
                milestone_type="final",
                day=day_cursor,
                ticks_per_day=ticks_per_day,
                cfg=cfg,
                timeline_path=timeline_path,
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
        "timeline_path": timeline_path,
        "milestones": milestones,
        "vault_dir": cfg.vault_dir,
    }


def evolve_seed(*, scenario_id: str, seed: int, cfg: EvolveConfig) -> Dict[str, Any]:
    if scenario_id not in _SCENARIO_REGISTRY:
        raise ValueError(f"Unknown scenario '{scenario_id}'")

    initializer, step_fn = _SCENARIO_REGISTRY[scenario_id]
    world = initializer(seed)

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    run_id = f"{scenario_id}__seed-{seed:05d}__{timestamp}"
    run_dir = Path("runs") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    config_path = run_dir / "config.json"
    with open(config_path, "w", encoding="utf-8") as fp:
        json.dump(asdict(cfg), fp, indent=2, default=str)

    timeline_path = run_dir / "timeline.jsonl"
    return _evolve_world(
        world=world,
        scenario_id=scenario_id,
        seed=seed,
        cfg=cfg,
        run_id=run_id,
        timeline_path=timeline_path,
        step_fn=step_fn,
    )


def evolve_from_snapshot(*, snapshot_path: Path, cfg: EvolveConfig) -> Dict[str, Any]:
    snapshot = load_snapshot(snapshot_path)
    world = restore_world(snapshot)
    scenario_id = snapshot.scenario_id
    seed = snapshot.seed

    if scenario_id not in _SCENARIO_REGISTRY:
        raise ValueError(f"Unknown scenario '{scenario_id}'")

    _, step_fn = _SCENARIO_REGISTRY[scenario_id]

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    run_id = f"{scenario_id}__seed-{seed:05d}__resume__{timestamp}"
    run_dir = Path("runs") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    config_path = run_dir / "config.json"
    with open(config_path, "w", encoding="utf-8") as fp:
        json.dump(asdict(cfg), fp, indent=2, default=str)

    timeline_path = run_dir / "timeline.jsonl"
    return _evolve_world(
        world=world,
        scenario_id=scenario_id,
        seed=seed,
        cfg=cfg,
        run_id=run_id,
        timeline_path=timeline_path,
        step_fn=step_fn,
    )


__all__ = [
    "EvolveConfig",
    "evolve_seed",
    "evolve_from_snapshot",
]

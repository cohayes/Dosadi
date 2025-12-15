from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dosadi.runtime.evolve import EvolveConfig, evolve_from_snapshot, evolve_seed
from dosadi.runtime.timewarp import TimewarpConfig


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the evolution harness")
    parser.add_argument("--scenario", default="founding_wakeup_mvp", help="Scenario id")
    parser.add_argument("--seed", type=int, default=1, help="Seed to use when generating a scenario")
    parser.add_argument("--snapshot", type=Path, help="Resume from an existing snapshot path")
    parser.add_argument("--target-years", type=int, default=EvolveConfig.target_years)
    parser.add_argument("--cruise-days", type=int, default=EvolveConfig.cruise_days)
    parser.add_argument("--microsim-days", type=int, default=EvolveConfig.microsim_days)
    parser.add_argument(
        "--microsim-every-days", type=int, default=EvolveConfig.microsim_every_days
    )
    parser.add_argument("--save-every-days", type=int, default=EvolveConfig.save_every_days)
    parser.add_argument("--max-steps", type=int, help="Optional guard to stop early")
    parser.add_argument("--vault-dir", type=Path, default=EvolveConfig.vault_dir)
    parser.add_argument("--runs-dir", type=Path, default=EvolveConfig.runs_dir)
    parser.add_argument("--seed-prefix", default=EvolveConfig.seed_prefix)
    parser.add_argument("--notes", help="Optional notes to emit alongside config")
    parser.add_argument(
        "--max-awake-agents",
        type=int,
        default=TimewarpConfig.max_awake_agents,
        help="Timewarp max awake agents",
    )
    parser.add_argument("--disable-kpis", action="store_true", help="Skip KPI collection")
    parser.add_argument(
        "--disable-signature",
        action="store_true",
        help="Skip world signature capture",
    )
    parser.add_argument(
        "--no-initial-snapshot",
        action="store_true",
        help="Do not save the initial snapshot/milestone",
    )
    return parser.parse_args()


def _build_config(args: argparse.Namespace) -> EvolveConfig:
    timewarp_cfg = TimewarpConfig(max_awake_agents=args.max_awake_agents)
    return EvolveConfig(
        target_years=args.target_years,
        cruise_days=args.cruise_days,
        microsim_days=args.microsim_days,
        microsim_every_days=args.microsim_every_days,
        save_every_days=args.save_every_days,
        max_steps=args.max_steps,
        timewarp_cfg=timewarp_cfg,
        vault_dir=args.vault_dir,
        runs_dir=args.runs_dir,
        seed_prefix=args.seed_prefix,
        kpi_enabled=not args.disable_kpis,
        signature_enabled=not args.disable_signature,
        save_initial_snapshot=not args.no_initial_snapshot,
    )


def _print_summary(summary: dict[str, Any]) -> None:
    print(f"run_id: {summary.get('run_id')}")
    print(f"scenario: {summary.get('scenario_id')} seed: {summary.get('seed')}")
    print(f"run_dir: {summary.get('run_dir')}")
    print(f"milestones: {len(summary.get('milestones', []))}")
    if summary.get("milestones"):
        first = summary["milestones"][0]
        last = summary["milestones"][-1]
        print(f"first milestone: {first.get('milestone_type')} @ day {first.get('day')}")
        print(f"final milestone: {last.get('milestone_type')} @ day {last.get('day')}")


def main() -> None:
    args = _parse_args()
    cfg = _build_config(args)
    timestamp = datetime.now(tz=timezone.utc)

    if args.snapshot:
        summary = evolve_from_snapshot(
            snapshot_path=args.snapshot,
            cfg=cfg,
            notes=args.notes,
            timestamp=timestamp,
        )
    else:
        summary = evolve_seed(
            scenario_id=args.scenario,
            seed=args.seed,
            cfg=cfg,
            notes=args.notes,
            timestamp=timestamp,
        )

    _print_summary(summary)


if __name__ == "__main__":
    main()

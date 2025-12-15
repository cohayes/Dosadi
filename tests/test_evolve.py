from __future__ import annotations

from pathlib import Path

from dosadi.runtime.evolve import EvolveConfig, evolve_from_snapshot, evolve_seed
from dosadi.runtime.snapshot import load_snapshot
from dosadi.runtime.timewarp import TimewarpConfig


def test_evolve_seed_generates_milestones(tmp_path: Path) -> None:
    cfg = EvolveConfig(
        target_years=1,
        cruise_days=180,
        microsim_days=0,
        microsim_every_days=90,
        save_every_days=200,
        timewarp_cfg=TimewarpConfig(max_awake_agents=10),
        vault_dir=tmp_path / "vault",
        seed_prefix="test-empire",
    )

    summary = evolve_seed(scenario_id="founding_wakeup_mvp", seed=7, cfg=cfg)
    assert summary["milestones"]
    for milestone in summary["milestones"]:
        snapshot_path = Path(cfg.vault_dir, milestone["snapshot_path"])
        assert snapshot_path.exists()


def test_evolve_from_snapshot_resumes(tmp_path: Path) -> None:
    base_cfg = EvolveConfig(
        target_years=0,
        cruise_days=30,
        microsim_days=0,
        microsim_every_days=90,
        save_every_days=365,
        timewarp_cfg=TimewarpConfig(max_awake_agents=5),
        vault_dir=tmp_path / "vault",
        seed_prefix="base-empire",
    )
    base_summary = evolve_seed(scenario_id="founding_wakeup_mvp", seed=3, cfg=base_cfg)

    first_snapshot_rel = base_summary["milestones"][0]["snapshot_path"]
    snapshot_path = Path(base_cfg.vault_dir, first_snapshot_rel)
    snapshot = load_snapshot(snapshot_path)

    resume_cfg = EvolveConfig(
        target_years=1,
        cruise_days=200,
        microsim_days=0,
        microsim_every_days=120,
        save_every_days=365,
        timewarp_cfg=TimewarpConfig(max_awake_agents=5),
        vault_dir=tmp_path / "vault",
        seed_prefix="resume-empire",
    )

    resume_summary = evolve_from_snapshot(snapshot_path=snapshot_path, cfg=resume_cfg)
    assert resume_summary["milestones"]
    assert resume_summary["scenario_id"] == snapshot.scenario_id

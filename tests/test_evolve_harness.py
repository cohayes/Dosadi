from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from dataclasses import replace

from dosadi.runtime.evolve import EvolveConfig, evolve_seed
from dosadi.runtime.timewarp import TimewarpConfig


def _read_jsonl(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as fp:
        return [json.loads(line) for line in fp if line.strip()]


def test_evolve_seed_writes_artifacts(tmp_path: Path) -> None:
    cfg = EvolveConfig(
        target_years=1,
        cruise_days=90,
        microsim_days=0,
        microsim_every_days=120,
        save_every_days=180,
        timewarp_cfg=TimewarpConfig(max_awake_agents=8),
        vault_dir=tmp_path / "vault",
        runs_dir=tmp_path / "runs",
        seed_prefix="artifacts",
    )

    summary = evolve_seed(
        scenario_id="founding_wakeup_mvp",
        seed=42,
        cfg=cfg,
        notes="harness artifact smoke test",
        timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )

    run_dir = Path(summary["run_dir"])
    assert run_dir.exists()
    assert (run_dir / "config.json").exists()
    assert (run_dir / "notes.md").exists()

    timeline_path = run_dir / "timeline.jsonl"
    csv_path = run_dir / "timeline.csv"
    assert timeline_path.exists()
    assert csv_path.exists()

    timeline = _read_jsonl(timeline_path)
    assert len(timeline) >= 2
    assert {row["milestone_type"] for row in timeline} >= {"initial", "final"}

    for row in timeline:
        snapshot_path = Path(cfg.vault_dir, row["snapshot_path"])
        assert snapshot_path.exists()
        assert row["snapshot_sha256"]
        if cfg.kpi_enabled:
            assert row["kpis"]


def test_evolve_seed_determinism(tmp_path: Path) -> None:
    base_cfg = EvolveConfig(
        target_years=1,
        cruise_days=120,
        microsim_days=0,
        microsim_every_days=180,
        save_every_days=365,
        timewarp_cfg=TimewarpConfig(max_awake_agents=6),
        vault_dir=tmp_path / "vault_a",
        runs_dir=tmp_path / "runs_a",
        seed_prefix="determinism",
    )
    timestamp = datetime(2024, 2, 2, 2, 2, 2, tzinfo=timezone.utc)

    first = evolve_seed(
        scenario_id="founding_wakeup_mvp",
        seed=99,
        cfg=base_cfg,
        timestamp=timestamp,
    )
    second_cfg = replace(
        base_cfg,
        vault_dir=tmp_path / "vault_b",
        runs_dir=tmp_path / "runs_b",
    )
    second = evolve_seed(
        scenario_id="founding_wakeup_mvp",
        seed=99,
        cfg=second_cfg,
        timestamp=timestamp,
    )

    first_rows = _read_jsonl(Path(first["run_dir"]) / "timeline.jsonl")
    second_rows = _read_jsonl(Path(second["run_dir"]) / "timeline.jsonl")

    assert [row["milestone_type"] for row in first_rows] == [
        row["milestone_type"] for row in second_rows
    ]

    for row_a, row_b in zip(first_rows, second_rows, strict=True):
        assert row_a.get("world_signature") == row_b.get("world_signature")
        assert row_a.get("kpis") == row_b.get("kpis")


def test_founding_wakeup_alias(tmp_path: Path) -> None:
    cfg = EvolveConfig(
        target_years=1,
        cruise_days=180,
        microsim_days=0,
        microsim_every_days=180,
        save_every_days=365,
        timewarp_cfg=TimewarpConfig(max_awake_agents=6),
        vault_dir=tmp_path / "vault_alias",
        runs_dir=tmp_path / "runs_alias",
    )

    summary = evolve_seed(
        scenario_id="founding_wakeup",
        seed=5,
        cfg=cfg,
        timestamp=datetime(2024, 3, 3, 3, 3, 3, tzinfo=timezone.utc),
    )

    assert summary["scenario_id"] == "founding_wakeup"
    assert summary["final_day"] == cfg.target_years * 365

from __future__ import annotations

from pathlib import Path

import pytest

from dosadi.playbook.scenario_runner import run_scenario
from dosadi.runtime.founding_wakeup import step_world_once
from dosadi.runtime.snapshot import load_snapshot, restore_world, save_snapshot, snapshot_world, world_signature
from dosadi.vault.seed_vault import load_manifest, load_seed, save_seed


@pytest.mark.parametrize("ticks", [50])
def test_snapshot_roundtrip_replay_equivalence(tmp_path: Path, ticks: int) -> None:
    report = run_scenario(
        "founding_wakeup_mvp", overrides={"num_agents": 8, "max_ticks": ticks, "seed": 7}
    )
    world = report.world

    snapshot = snapshot_world(world, scenario_id="founding_wakeup_mvp")
    snapshot_path = tmp_path / "snapshot.json.gz"
    save_snapshot(snapshot, snapshot_path)

    restored_snapshot = load_snapshot(snapshot_path)
    restored_world = restore_world(restored_snapshot)

    for _ in range(10):
        step_world_once(restored_world)

    continued_world = run_scenario(
        "founding_wakeup_mvp",
        overrides={"num_agents": 8, "max_ticks": ticks + 10, "seed": 7},
    ).world

    assert world_signature(restored_world) == world_signature(continued_world)


def test_seed_vault_save_load_roundtrip(tmp_path: Path) -> None:
    base_report = run_scenario(
        "founding_wakeup_mvp", overrides={"num_agents": 6, "max_ticks": 30, "seed": 11}
    )
    base_world = base_report.world

    entry = save_seed(tmp_path, base_world, seed_id="seed-001", scenario_id="founding_wakeup_mvp")

    manifest = load_manifest(tmp_path)
    assert any(seed.get("seed_id") == "seed-001" for seed in manifest.get("seeds", []))

    restored_world, snapshot, snapshot_path = load_seed(tmp_path, seed_id="seed-001")
    assert Path(tmp_path, entry["snapshot_path"]) == snapshot_path

    extended_world = run_scenario(
        "founding_wakeup_mvp",
        overrides={"num_agents": 6, "max_ticks": base_world.tick + 5, "seed": 11},
    ).world

    for _ in range(5):
        step_world_once(restored_world)

    assert world_signature(restored_world) == world_signature(extended_world)

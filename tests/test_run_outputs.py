from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dosadi.runtime.run_outputs import append_timeline_row, generate_run_id, prepare_run_directory
from dosadi.testing.kpis import collect_kpis


@dataclass
class DummyPhysical:
    hunger_level: float
    hydration_level: float
    fatigue: float
    is_alive: bool = True


@dataclass
class DummyAgent:
    agent_id: str
    physical: DummyPhysical


class DummyProtocolRegistry:
    def __init__(self, count: int) -> None:
        self.protocols_by_id = {f"p{i}": object() for i in range(count)}


class DummyWell:
    def __init__(self, capacity: float) -> None:
        self.daily_capacity = capacity


class DummyWorld:
    def __init__(self) -> None:
        self.tick = 288_000
        self.ticks_per_day = 144_000
        self.agents = {
            "a": DummyAgent("a", DummyPhysical(hunger_level=0.2, hydration_level=0.8, fatigue=0.1)),
            "b": DummyAgent("b", DummyPhysical(hunger_level=0.4, hydration_level=0.6, fatigue=0.3, is_alive=False)),
        }
        self.groups = [object(), object()]
        self.facilities = {"f1": object()}
        self.protocols = DummyProtocolRegistry(count=3)
        self.wards = {"w1": object(), "w2": object()}
        self.queues = {"q": object()}
        self.well = DummyWell(capacity=12.5)


@dataclass
class DummyConfig:
    foo: int = 1
    bar: str = "baz"


def test_generate_run_id_and_prepare_directory(tmp_path: Path) -> None:
    ts = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    run_id = generate_run_id("founding_wakeup", 7, timestamp=ts)
    assert run_id == "founding_wakeup__seed-7__20240102-030405"

    run_dir = prepare_run_directory(tmp_path, run_id, config=DummyConfig(foo=2), notes="Sample run")
    assert run_dir.exists()
    config_path = run_dir / "config.json"
    assert config_path.exists()
    assert "foo" in config_path.read_text(encoding="utf-8")
    notes_path = run_dir / "notes.md"
    assert notes_path.exists()
    assert "Sample run" in notes_path.read_text(encoding="utf-8")


def test_append_timeline_row_with_kpis(tmp_path: Path) -> None:
    world = DummyWorld()
    kpis = collect_kpis(world)
    run_id = "founding__seed-1__00000000"
    run_dir = tmp_path / run_id
    run_dir.mkdir()

    snapshot_path = run_dir / "snap.json.gz"
    snapshot_path.write_text("{}", encoding="utf-8")

    row = append_timeline_row(
        run_dir,
        run_id=run_id,
        scenario_id="founding_wakeup",
        seed=1,
        day=kpis["day"],
        tick=world.tick,
        milestone_type="initial",
        snapshot_path=snapshot_path,
        snapshot_sha256="abc123",
        kpis=kpis,
        world_signature="sig",
    )

    assert row["year"] == kpis["year"]
    assert (run_dir / "timeline.jsonl").exists()
    assert (run_dir / "timeline.csv").exists()
    csv_contents = (run_dir / "timeline.csv").read_text(encoding="utf-8")
    assert "snapshot_sha256" in csv_contents
    assert "abc123" in csv_contents
    jsonl_contents = (run_dir / "timeline.jsonl").read_text(encoding="utf-8")
    assert "sig" in jsonl_contents

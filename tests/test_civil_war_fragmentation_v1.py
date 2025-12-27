from dataclasses import dataclass
from pathlib import Path

from dosadi.runtime.sovereignty import (
    SovereigntyConfig,
    contested_trade_multiplier,
    displacement_pressure,
    ensure_sovereignty_state,
    export_sovereignty_seed,
    sovereignty_signature,
    update_sovereignty,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world


@dataclass
class DummyWorld:
    seed: int = 1
    day: int = 0
    metrics: dict | None = None
    governance_failure_pressure: dict[str, float] = None
    insurgency_support: dict[str, float] = None
    hardship_pressure: dict[str, float] = None
    policing_backlash: dict[str, float] = None
    sovereignty_state: object | None = None
    sovereignty_cfg: object | None = None


def _base_world(seed: int = 1) -> DummyWorld:
    world = DummyWorld(seed=seed)
    world.metrics = {}
    world.governance_failure_pressure = {}
    world.insurgency_support = {}
    world.hardship_pressure = {}
    world.policing_backlash = {}
    world.sovereignty_cfg = SovereigntyConfig(enabled=True, update_cadence_days=1)
    return world


def _prep_state(world: DummyWorld):
    wards = ["ward:1", "ward:2", "ward:3", "ward:4"]
    corridors = {
        "c1": ("ward:1", "ward:2"),
        "c2": ("ward:2", "ward:3"),
        "c3": ("ward:3", "ward:4"),
    }
    ensure_sovereignty_state(world, ward_ids=wards, corridors=corridors)
    return corridors


def test_determinism_same_signature():
    def run(seed: int):
        world = _base_world(seed=seed)
        _prep_state(world)
        world.governance_failure_pressure = {"ward:2": 0.9, "ward:3": 0.9}
        world.insurgency_support = {"ward:2": 0.8, "ward:3": 0.8}
        world.hardship_pressure = {"ward:2": 0.8, "ward:3": 0.6}
        update_sovereignty(world, day=1)
        return sovereignty_signature(world)

    sig_a = run(seed=1)
    sig_b = run(seed=1)
    assert sig_a == sig_b


def test_split_when_pressure_high():
    world = _base_world(seed=2)
    _prep_state(world)
    world.governance_failure_pressure = {"ward:2": 0.95, "ward:3": 0.9}
    world.insurgency_support = {"ward:2": 0.85, "ward:3": 0.85}
    world.hardship_pressure = {"ward:2": 0.7, "ward:3": 0.65}
    update_sovereignty(world, day=1)

    polities = world.sovereignty_state.polities
    assert len(polities) > 1
    assert world.sovereignty_state.territory.ward_control.get("ward:2") != "polity:empire"


def test_contested_corridors_raise_trade_costs():
    world = _base_world(seed=3)
    _prep_state(world)
    world.sovereignty_cfg.merge_threshold = -1.0  # keep contests alive for observation
    world.governance_failure_pressure = {"ward:2": 0.95}
    world.insurgency_support = {"ward:2": 0.9}
    world.hardship_pressure = {"ward:2": 0.8}
    update_sovereignty(world, day=1)
    # corridor between split wards should be contested
    contested = world.sovereignty_state.territory.corridor_contested
    assert "c2" in contested
    multiplier = contested_trade_multiplier(world, "c2")
    assert multiplier > 1.0
    assert multiplier == 1.0 + world.sovereignty_cfg.border_friction * max(1, len(contested["c2"]))


def test_reconquest_vs_autonomy_resolution():
    world_reconquest = _base_world(seed=4)
    _prep_state(world_reconquest)
    cfg = world_reconquest.sovereignty_cfg
    cfg.merge_threshold = 0.9  # resolve quickly
    cfg.reconquest_bias = 0.9
    cfg.negotiation_bias = 0.1
    world_reconquest.governance_failure_pressure = {"ward:2": 0.9}
    world_reconquest.insurgency_support = {"ward:2": 0.9}
    world_reconquest.hardship_pressure = {"ward:2": 0.8}
    update_sovereignty(world_reconquest, day=1)
    # weaken splinter polity capacity to favor reconquest
    for polity_id, polity in world_reconquest.sovereignty_state.polities.items():
        if polity_id != "polity:empire":
            polity.capacity = 0.1
    update_sovereignty(world_reconquest, day=2)
    assert world_reconquest.sovereignty_state.territory.corridor_contested == {}
    assert all(
        polity_id == "polity:empire" for polity_id in world_reconquest.sovereignty_state.territory.corridor_control.values()
    )

    world_autonomy = _base_world(seed=5)
    _prep_state(world_autonomy)
    cfg2 = world_autonomy.sovereignty_cfg
    cfg2.merge_threshold = 0.9
    cfg2.reconquest_bias = 0.1
    cfg2.negotiation_bias = 0.9
    world_autonomy.governance_failure_pressure = {"ward:2": 0.95}
    world_autonomy.insurgency_support = {"ward:2": 0.95}
    world_autonomy.hardship_pressure = {"ward:2": 0.85}
    update_sovereignty(world_autonomy, day=1)
    update_sovereignty(world_autonomy, day=2)
    assert world_autonomy.sovereignty_state.territory.corridor_contested == {}
    assert any(
        polity_id != "polity:empire" for polity_id in world_autonomy.sovereignty_state.territory.corridor_control.values()
    )


def test_market_and_migration_impacts():
    world = _base_world(seed=6)
    _prep_state(world)
    world.governance_failure_pressure = {"ward:2": 0.9}
    world.insurgency_support = {"ward:2": 0.9}
    world.hardship_pressure = {"ward:2": 0.85}
    update_sovereignty(world, day=1)
    multiplier = contested_trade_multiplier(world, "c1")
    displacement = displacement_pressure(world, "ward:1")
    assert multiplier >= 1.0
    assert displacement >= 0.0
    # ensure contested edge magnifies both signals
    if "c1" in world.sovereignty_state.territory.corridor_contested:
        assert multiplier > 1.0
        assert displacement > 0.0


def test_snapshot_roundtrip():
    world = _base_world(seed=7)
    _prep_state(world)
    world.governance_failure_pressure = {"ward:2": 0.9, "ward:3": 0.9}
    world.insurgency_support = {"ward:2": 0.9, "ward:3": 0.9}
    world.hardship_pressure = {"ward:2": 0.85, "ward:3": 0.85}
    update_sovereignty(world, day=2)

    snap = snapshot_world(world, scenario_id="test")
    restored = restore_world(snap)

    assert hasattr(restored, "sovereignty_state")
    assert sovereignty_signature(restored) == sovereignty_signature(world)
    # ensure seeds export path can be created
    export_path = export_sovereignty_seed(restored, Path("/tmp/seed"))
    assert export_path.name == "sovereignty.json"


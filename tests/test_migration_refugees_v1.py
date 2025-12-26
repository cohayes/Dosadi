from __future__ import annotations

from dosadi.runtime.migration import WardMigrationState, run_migration_for_day
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WardState, WorldState


def _make_world(seed: int = 1) -> WorldState:
    world = WorldState(seed=seed)
    world.wards["ward:a"] = WardState(id="ward:a", name="A", ring=1, sealed_mode="open", need_index=0.3, risk_index=0.2)
    world.wards["ward:b"] = WardState(id="ward:b", name="B", ring=1, sealed_mode="open", need_index=0.1, risk_index=0.1)
    world.wards["ward:c"] = WardState(id="ward:c", name="C", ring=1, sealed_mode="open", need_index=0.2, risk_index=0.2)
    world.edges = {
        "edge:ab": {"origin": "ward:a", "destination": "ward:b"},
        "edge:ac": {"origin": "ward:a", "destination": "ward:c"},
        "edge:bc": {"origin": "ward:b", "destination": "ward:c"},
    }
    for ward_id in world.wards:
        world.migration_by_ward[ward_id] = WardMigrationState(ward_id=ward_id)
    world.migration_cfg.enabled = True
    world.migration_cfg.update_cadence_days = 1
    world.migration_cfg.max_total_movers_per_update = 500
    world.migration_cfg.route_topk = 2
    world.migration_cfg.neighbor_topk = 3
    return world


def test_deterministic_flows() -> None:
    world_a = _make_world(seed=7)
    world_b = _make_world(seed=7)

    world_a.migration_by_ward["ward:a"].displaced = 300
    world_b.migration_by_ward["ward:a"].displaced = 300

    run_migration_for_day(world_a, day=0)
    run_migration_for_day(world_b, day=0)

    assert [(f.from_ward, f.to_ward, f.movers) for f in world_a.migration_flows] == [
        (f.from_ward, f.to_ward, f.movers) for f in world_b.migration_flows
    ]


def test_capacity_and_camp_overflow() -> None:
    world = _make_world(seed=11)
    world.inst_policy_by_ward["ward:b"] = {"refugee_intake_bias": -0.5}
    world.migration_cfg.max_total_movers_per_update = 300
    world.migration_by_ward["ward:a"].displaced = 500

    run_migration_for_day(world, day=0)

    # capacity reduces inflow and overflow becomes a camp
    assert sum(flow.movers for flow in world.migration_flows) <= 300
    assert world.migration_by_ward["ward:a"].camp > 0


def test_collapsed_corridor_blocks_flow() -> None:
    world = _make_world(seed=13)
    world.edges["edge:ab"]["collapsed"] = True
    world.migration_by_ward["ward:a"].displaced = 200

    run_migration_for_day(world, day=0)

    assert all(
        not (flow.from_ward == "ward:a" and flow.to_ward == "ward:b") for flow in world.migration_flows
    )
    assert world.migration_by_ward["ward:a"].camp > 0


def test_political_effects_from_camp_growth() -> None:
    world = _make_world(seed=17)
    ward = world.wards["ward:a"]
    ward.legitimacy = 0.6
    ward.need_index = 0.05
    world.inst_policy_by_ward["ward:b"] = {"refugee_intake_bias": -0.6}
    world.inst_policy_by_ward["ward:c"] = {"refugee_intake_bias": -0.6}
    world.migration_cfg.max_total_movers_per_update = 100
    world.migration_by_ward["ward:a"].displaced = 400

    run_migration_for_day(world, day=0)

    assert ward.legitimacy < 0.6
    assert ward.need_index > 0.05


def test_flow_history_bounded() -> None:
    world = _make_world(seed=23)
    world.migration_cfg.flow_history_limit = 3
    world.migration_cfg.max_total_movers_per_update = 1000
    world.migration_by_ward["ward:a"].displaced = 800

    for day in range(4):
        run_migration_for_day(world, day=day)

    assert len(world.migration_flows) <= 3


def test_snapshot_roundtrip_preserves_migration_state() -> None:
    world = _make_world(seed=31)
    world.migration_cfg.max_total_movers_per_update = 200
    world.migration_by_ward["ward:a"].displaced = 150

    run_migration_for_day(world, day=0)
    snap = snapshot_world(world, scenario_id="test-scenario")
    restored = restore_world(snap)

    run_migration_for_day(restored, day=1)

    assert restored.migration_by_ward
    assert len(restored.migration_flows) > 0
    assert restored.migration_cfg.enabled is True


from dosadi.runtime.market_signals import MarketSignalsState, MaterialMarketSignal
from dosadi.runtime.urban import WardUrbanState, run_urban_for_day
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WardInstitutionPolicy, WardMigrationState, WardState, WorldState


def _base_world() -> WorldState:
    world = WorldState(seed=123)
    ward = WardState(id="ward:1", name="Ward One", ring=1, sealed_mode="open")
    world.register_ward(ward)
    world.urban_cfg.enabled = True
    world.urban_cfg.update_cadence_days = 1
    world.migration_by_ward[ward.id] = WardMigrationState(
        ward_id=ward.id, camp=600, displaced=400, intake_capacity=200
    )
    world.inst_policy_by_ward[ward.id] = WardInstitutionPolicy(
        ward_id=ward.id,
        zoning_residential_bias=0.35,
        zoning_industrial_bias=0.15,
        growth_aggressiveness=0.9,
    )
    world.market_state = MarketSignalsState(
        global_signals={
            "SCRAP_METAL": MaterialMarketSignal(material="SCRAP_METAL", urgency=0.65),
            "FABRIC": MaterialMarketSignal(material="FABRIC", urgency=0.55),
        }
    )
    return world


def test_urban_projects_are_deterministic():
    world = _base_world()
    run_urban_for_day(world, day=0)
    signature_first = world.projects.signature()
    run_urban_for_day(world, day=0)
    signature_repeat = world.projects.signature()

    world_copy = _base_world()
    run_urban_for_day(world_copy, day=0)
    signature_copy = world_copy.projects.signature()

    assert signature_first == signature_repeat == signature_copy
    assert any(project.kind.startswith("HOUSING") for project in world.projects.projects.values())


def test_urban_state_snapshot_roundtrip():
    world = WorldState(seed=99)
    ward = WardState(id="ward:2", name="Ward Two", ring=2, sealed_mode="open")
    world.register_ward(ward)
    world.urban_cfg.enabled = True
    state = WardUrbanState(ward_id=ward.id, housing_cap=150)
    state.utility_cap["water"] = 75
    state.civic_cap["clinic"] = 20
    world.urban_by_ward[ward.id] = state

    snap = snapshot_world(world, scenario_id="urban-test")
    restored = restore_world(snap)

    assert restored.urban_cfg.enabled is True
    restored_state = restored.urban_by_ward[ward.id]
    assert restored_state.housing_cap == 150
    assert restored_state.utility_cap.get("water") == 75
    assert restored_state.civic_cap.get("clinic") == 20

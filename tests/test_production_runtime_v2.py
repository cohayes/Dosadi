from dataclasses import replace

from dosadi.runtime.production_runtime import (
    FacilityProductionState,
    ProductionConfig,
    ProductionState,
    run_production_for_day,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.state import WorldState
from dosadi.world.facilities import Facility, FacilityKind, FacilityLedger
from dosadi.world.materials import InventoryRegistry, Material
from dosadi.world.recipes import DEFAULT_RECIPES, RecipeRegistry, ensure_recipe_registry


def _base_world() -> WorldState:
    world = WorldState(seed=99)
    world.prod_cfg = ProductionConfig(enabled=True)
    world.prod_state = ProductionState()
    world.fac_prod = {}
    world.facilities = FacilityLedger()
    world.inventories = InventoryRegistry()
    ensure_recipe_registry(world)
    return world


def test_recipe_registry_deterministic() -> None:
    registry_a = RecipeRegistry(reversed(DEFAULT_RECIPES))
    registry_b = RecipeRegistry(DEFAULT_RECIPES)

    assert registry_a.signature() == registry_b.signature()
    assert [r.recipe_id for r in registry_a.get(FacilityKind.RECYCLER)] == [
        r.recipe_id for r in registry_b.get(FacilityKind.RECYCLER)
    ]


def test_production_consumes_and_outputs() -> None:
    world = _base_world()
    world.facilities.add(
        Facility(facility_id="work-1", kind=FacilityKind.WORKSHOP, site_node_id="node:a", created_tick=0)
    )
    inv = world.inventories.inv("facility:work-1")
    inv.add(Material.SCRAP_METAL, 10)

    run_production_for_day(world, day=0)
    state = world.fac_prod["work-1"]
    assert state.active_job == "workshop_fasteners"
    assert inv.get(Material.SCRAP_METAL) == 5

    run_production_for_day(world, day=1)
    assert inv.get(Material.FASTENERS) >= 5


def test_blocks_when_inputs_missing() -> None:
    world = _base_world()
    world.facilities.add(
        Facility(facility_id="chem-1", kind=FacilityKind.CHEM_WORKS, site_node_id="node:b", created_tick=0)
    )

    run_production_for_day(world, day=0)

    metrics = world.metrics.gauges.get("production", {})
    assert metrics.get("blocked_inputs", 0.0) >= 1.0
    prod_state: FacilityProductionState = world.fac_prod["chem-1"]
    assert prod_state.active_job is None


def test_respects_global_cap() -> None:
    world = _base_world()
    world.prod_cfg = ProductionConfig(enabled=True, max_jobs_per_day_global=1, max_jobs_per_facility_per_day=1)
    world.facilities.add(
        Facility(facility_id="work-1", kind=FacilityKind.WORKSHOP, site_node_id="node:a", created_tick=0)
    )
    world.facilities.add(
        Facility(facility_id="work-2", kind=FacilityKind.WORKSHOP, site_node_id="node:b", created_tick=0)
    )
    world.inventories.inv("facility:work-1").add(Material.SCRAP_METAL, 10)
    world.inventories.inv("facility:work-2").add(Material.SCRAP_METAL, 10)

    run_production_for_day(world, day=0)

    active = [state for state in world.fac_prod.values() if state.active_job]
    assert len(active) == 1
    assert world.prod_state.jobs_started_today == 1


def test_prefers_shortage_signals() -> None:
    world = _base_world()
    world.facilities.add(
        Facility(facility_id="depot-1", kind=FacilityKind.DEPOT, site_node_id="node:d", created_tick=0)
    )
    world.facilities.add(
        Facility(facility_id="work-1", kind=FacilityKind.WORKSHOP, site_node_id="node:a", created_tick=0)
    )
    world.stock_policies.profile("depot-1")
    world.inventories.inv("facility:depot-1")
    inv = world.inventories.inv("facility:work-1")
    inv.add(Material.SCRAP_METAL, 10)
    inv.add(Material.FIBER, 10)

    world.prod_cfg = replace(world.prod_cfg, prefer_recipes=["FASTENERS"])
    run_production_for_day(world, day=0)

    assert world.fac_prod["work-1"].active_job == "workshop_fasteners"


def test_snapshot_roundtrip_mid_job() -> None:
    world = _base_world()
    world.facilities.add(
        Facility(facility_id="work-1", kind=FacilityKind.WORKSHOP, site_node_id="node:a", created_tick=0)
    )
    inv = world.inventories.inv("facility:work-1")
    inv.add(Material.SCRAP_METAL, 10)

    run_production_for_day(world, day=0)
    snapshot = snapshot_world(world, scenario_id="prod-test")
    restored = restore_world(snapshot)
    restored.prod_cfg = replace(world.prod_cfg)

    run_production_for_day(world, day=1)
    run_production_for_day(restored, day=1)

    assert world_signature(world) == world_signature(restored)
    assert restored.inventories.signature() == world.inventories.signature()

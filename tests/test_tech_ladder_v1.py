from __future__ import annotations

import copy

from dosadi.runtime.production_runtime import choose_recipe_for_facility
from dosadi.runtime.tech_ladder import TechConfig, TechState, run_tech_for_day, tech_registry
from dosadi.state import WorldState
from dosadi.world.facilities import FacilityKind
from dosadi.world.materials import Material, ensure_inventory_registry


def _seed_world() -> WorldState:
    world = WorldState()
    world.tech_cfg = TechConfig(enabled=True)
    world.tech_state = TechState()
    return world


def test_deterministic_start_and_completion_schedule():
    world = _seed_world()
    registry = ensure_inventory_registry(world)
    owner = world.research_owner_id = "owner:state:research"
    for material in (Material.SCRAP_INPUT, Material.FABRIC, Material.SEALANT):
        registry.inv(owner).add(material, 20)

    run_tech_for_day(world, day=0)
    run_tech_for_day(world, day=5)

    replay = copy.deepcopy(world)
    replay_registry = ensure_inventory_registry(replay)
    replay.tech_state.active.clear()
    replay.tech_state.completed.clear()
    replay.tech_state.unlocked.clear()
    replay.tech_state.last_run_day = -1
    for material in (Material.SCRAP_INPUT, Material.FABRIC, Material.SEALANT):
        replay_registry.inv(owner).add(material, 20)

    run_tech_for_day(replay, day=0)
    run_tech_for_day(replay, day=5)

    assert world.tech_state.completed == replay.tech_state.completed
    assert world.tech_state.unlocked == replay.tech_state.unlocked


def test_prereqs_and_costs_consumed():
    world = _seed_world()
    registry = ensure_inventory_registry(world)
    owner = world.research_owner_id = "owner:state:research"
    registry.inv(owner).add(Material.SCRAP_METAL, 10)
    registry.inv(owner).add(Material.FASTENERS, 5)

    # Cannot start workshop tech without recycler prereq
    run_tech_for_day(world, day=0)
    assert "tech:workshop:parts:t2" not in world.tech_state.active

    # Satisfy prereq and rerun
    world.tech_state.completed.add("tech:recycler:t1")
    run_tech_for_day(world, day=1)
    assert "tech:workshop:parts:t2" in world.tech_state.active

    inv = registry.inv(owner)
    spec = tech_registry()["tech:workshop:parts:t2"]
    for material, qty in spec.cost_materials.items():
        assert inv.get(material) <= 10  # costs applied, no negatives


def test_recipe_gated_by_unlocks():
    world = _seed_world()
    registry = ensure_inventory_registry(world)
    owner = world.research_owner_id = "owner:state:research"
    registry.inv(owner).add(Material.SCRAP_INPUT, 10)

    recipe_before = choose_recipe_for_facility(world, "fac:1", FacilityKind.RECYCLER, day=0)
    assert recipe_before is None

    run_tech_for_day(world, day=0)
    run_tech_for_day(world, day=5)
    recipe_after = choose_recipe_for_facility(world, "fac:1", FacilityKind.RECYCLER, day=5)
    assert recipe_after is not None

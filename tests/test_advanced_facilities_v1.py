from dosadi.runtime.materials_economy import (
    MaterialsEconomyConfig,
    evaluate_project_materials,
    run_materials_production_for_day,
)
from dosadi.runtime.tech_ladder import TechConfig, TechState
from dosadi.state import WorldState
from dosadi.world.construction import ConstructionProject, ProjectCost, ProjectLedger, ProjectStatus
from dosadi.world.corridor_infrastructure import corridor_upgrade_recipe
from dosadi.world.facilities import Facility, FacilityKind, FacilityLedger
from dosadi.world.materials import InventoryRegistry, Material
from dosadi.world.workforce import Assignment, AssignmentKind, WorkforceLedger


def _base_world() -> WorldState:
    world = WorldState(seed=99)
    world.facilities = FacilityLedger()
    world.inventories = InventoryRegistry()
    world.projects = ProjectLedger()
    world.workforce = WorkforceLedger()
    world.tech_cfg = TechConfig(enabled=True)
    world.tech_state = TechState()
    world.mat_cfg = MaterialsEconomyConfig(enabled=True, daily_production_cap=50)
    return world


def _staff(world: WorldState, facility_id: str) -> None:
    world.workforce.assign(
        Assignment(
            agent_id=f"agent:{facility_id}",
            kind=AssignmentKind.FACILITY_STAFF,
            target_id=facility_id,
            start_day=0,
        )
    )


def test_tech_gating_blocks_until_unlocked() -> None:
    world = _base_world()
    world.facilities.add(
        Facility(facility_id="fac:chem", kind=FacilityKind.CHEM_LAB_T2, site_node_id="loc:a")
    )
    inv = world.inventories.inv("facility:fac:chem")
    inv.add(Material.CHEM_SALTS, 4)
    inv.add(Material.FIBER, 2)

    run_materials_production_for_day(world, day=0)

    assert world.inventories.inv("facility:fac:chem").get(Material.SEALANT) == 0
    assert any(evt.get("reason") == "unlock" for evt in getattr(world, "runtime_events", []))

    world.tech_state.unlocked.add("UNLOCK_CHEM_SEALANTS_T2")
    run_materials_production_for_day(world, day=1)

    assert world.inventories.inv("facility:fac:chem").get(Material.SEALANT) > 0


def test_production_consumes_inputs_and_outputs_deterministically() -> None:
    world = _base_world()
    world.tech_state.unlocked.update({"UNLOCK_WORKSHOP_PARTS_T2", "UNLOCK_FABRICATION_SIMPLE_T3"})

    world.facilities.add(
        Facility(facility_id="fac:work", kind=FacilityKind.WORKSHOP_T2, site_node_id="loc:w")
    )
    world.facilities.add(
        Facility(facility_id="fac:fab", kind=FacilityKind.FAB_SHOP_T3, site_node_id="loc:f")
    )
    _staff(world, "fac:work")
    _staff(world, "fac:fab")
    work_inv = world.inventories.inv("facility:fac:work")
    work_inv.add(Material.SCRAP_METAL, 12)
    fab_inv = world.inventories.inv("facility:fac:fab")
    fab_inv.add(Material.FASTENERS, 1)
    fab_inv.add(Material.SEALANT, 1)
    fab_inv.add(Material.METAL_PLATE, 1)

    run_materials_production_for_day(world, day=0)

    assert work_inv.get(Material.SCRAP_METAL) == 6
    assert work_inv.get(Material.FASTENERS) == 4
    assert work_inv.get(Material.FITTINGS) == 2
    assert work_inv.get(Material.METAL_PLATE) == 2
    assert fab_inv.get(Material.ADV_COMPONENTS) == 1


def test_facility_stalls_without_inputs_and_reports() -> None:
    world = _base_world()
    world.tech_state.unlocked.add("UNLOCK_WORKSHOP_PARTS_T2")
    world.facilities.add(
        Facility(facility_id="fac:stall", kind=FacilityKind.WORKSHOP_T2, site_node_id="loc:s")
    )
    _staff(world, "fac:stall")

    run_materials_production_for_day(world, day=0)

    events = getattr(world, "runtime_events", [])
    assert any(evt.get("type") == "FACILITY_STALLED_INPUTS" for evt in events)
    facility_metrics = getattr(getattr(world, "metrics", None), "gauges", {}).get("facilities", {})
    assert facility_metrics.get("inputs_missing", {}).get(Material.SCRAP_METAL.name, 0.0) > 0


def test_corridor_upgrade_recipe_can_be_fed() -> None:
    world = _base_world()
    world.tech_state.unlocked.update({"UNLOCK_CHEM_SEALANTS_T2", "UNLOCK_WORKSHOP_PARTS_T2"})

    world.facilities.add(
        Facility(facility_id="fac:chem", kind=FacilityKind.CHEM_LAB_T2, site_node_id="loc:c")
    )
    world.facilities.add(
        Facility(facility_id="fac:work", kind=FacilityKind.WORKSHOP_T2, site_node_id="loc:w")
    )
    _staff(world, "fac:chem")
    _staff(world, "fac:work")
    world.inventories.inv("facility:fac:chem").add(Material.CHEM_SALTS, 6)
    world.inventories.inv("facility:fac:chem").add(Material.FIBER, 2)
    world.inventories.inv("facility:fac:work").add(Material.SCRAP_METAL, 12)
    world.inventories.inv("facility:fac:work").add(Material.FIBER, 8)

    run_materials_production_for_day(world, day=0)

    recipe = corridor_upgrade_recipe(1, 2)
    project = ConstructionProject(
        project_id="proj:corridor",
        site_node_id="edge:1-2",
        kind="CORRIDOR_UPGRADE",
        status=ProjectStatus.APPROVED,
        created_tick=0,
        last_tick=0,
        cost=ProjectCost(materials={}, labor_hours=1.0),
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
        bom=dict(recipe),
    )
    world.projects.add_project(project)
    staging_inv = world.inventories.inv(project.staging_owner_id)
    chem_inv = world.inventories.inv("facility:fac:chem")
    work_inv = world.inventories.inv("facility:fac:work")
    for material in recipe:
        staging_inv.add(material, chem_inv.get(material) + work_inv.get(material))

    evaluate_project_materials(world, day=1)

    assert not project.blocked_for_materials
    assert project.bom_consumed

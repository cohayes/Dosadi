from dataclasses import replace

from dosadi.runtime.materials_economy import (
    MaterialsEconomyConfig,
    evaluate_project_materials,
    run_materials_production_for_day,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.state import WorldState
from dosadi.world.construction import ConstructionProject, ProjectCost, ProjectLedger, ProjectStatus
from dosadi.world.facilities import Facility, FacilityLedger
from dosadi.world.logistics import assign_pending_deliveries, process_due_deliveries
from dosadi.world.materials import InventoryRegistry, Material
from dosadi.world.workforce import Assignment, AssignmentKind, WorkforceLedger


def _base_world() -> WorldState:
    world = WorldState(seed=42)
    world.facilities = FacilityLedger()
    world.workforce = WorkforceLedger()
    world.projects = ProjectLedger()
    world.inventories = InventoryRegistry()
    return world


def _staff_facility(world: WorldState, facility_id: str) -> None:
    world.workforce.assign(
        Assignment(agent_id="agent:1", kind=AssignmentKind.FACILITY_STAFF, target_id=facility_id, start_day=0)
    )


def test_flag_off_is_noop() -> None:
    world = _base_world()
    world.facilities.add(Facility(facility_id="fac:1", kind="workshop", site_node_id="loc:a", created_tick=0))
    initial_sig = world_signature(world)

    run_materials_production_for_day(world, day=0)
    evaluate_project_materials(world, day=0)

    assert world_signature(world) == initial_sig


def test_deterministic_production() -> None:
    cfg = MaterialsEconomyConfig(enabled=True)
    world_a = _base_world()
    world_a.mat_cfg = cfg
    world_a.facilities.add(Facility(facility_id="fac:1", kind="workshop", site_node_id="loc:a", created_tick=0))
    _staff_facility(world_a, "fac:1")

    world_b = restore_world(snapshot_world(world_a, scenario_id="mat-econ"))
    world_b.mat_cfg = replace(cfg)

    run_materials_production_for_day(world_a, day=0)
    run_materials_production_for_day(world_b, day=0)

    assert world_a.inventories.signature() == world_b.inventories.signature()


def test_project_blocks_and_requests_delivery() -> None:
    cfg = MaterialsEconomyConfig(enabled=True, default_depot_owner_id="ward:0")
    world = _base_world()
    world.mat_cfg = cfg
    project = ConstructionProject(
        project_id="proj:1",
        site_node_id="loc:site",
        kind="outpost",
        status=ProjectStatus.APPROVED,
        created_tick=0,
        last_tick=0,
        cost=ProjectCost(materials={}, labor_hours=1.0),
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
        bom={Material.FASTENERS: 5},
    )
    world.projects.add_project(project)

    evaluate_project_materials(world, day=0)

    assert project.blocked_for_materials
    assert len(project.pending_material_delivery_ids) == 1


def test_delivery_completion_unblocks_project() -> None:
    cfg = MaterialsEconomyConfig(enabled=True, default_depot_owner_id="ward:0")
    world = _base_world()
    world.mat_cfg = cfg
    world.stockpiles = {Material.FASTENERS.name: 10}
    world.inventories.inv("ward:0").add(Material.FASTENERS, 10)
    project = ConstructionProject(
        project_id="proj:2",
        site_node_id="loc:site",
        kind="outpost",
        status=ProjectStatus.APPROVED,
        created_tick=0,
        last_tick=0,
        cost=ProjectCost(materials={}, labor_hours=1.0),
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
        bom={Material.FASTENERS: 3},
    )
    world.projects.add_project(project)

    evaluate_project_materials(world, day=0)
    assign_pending_deliveries(world, tick=0)
    process_due_deliveries(world, tick=0)
    evaluate_project_materials(world, day=1)

    assert not project.blocked_for_materials
    assert project.bom_consumed


def test_no_duplicate_deliveries() -> None:
    cfg = MaterialsEconomyConfig(enabled=True, default_depot_owner_id="ward:0")
    world = _base_world()
    world.mat_cfg = cfg
    project = ConstructionProject(
        project_id="proj:3",
        site_node_id="loc:site",
        kind="outpost",
        status=ProjectStatus.APPROVED,
        created_tick=0,
        last_tick=0,
        cost=ProjectCost(materials={}, labor_hours=1.0),
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
        bom={Material.SEALANT: 4},
    )
    world.projects.add_project(project)

    evaluate_project_materials(world, day=0)
    evaluate_project_materials(world, day=1)

    assert len(project.pending_material_delivery_ids) == 1


def test_daily_cap_enforced() -> None:
    cfg = MaterialsEconomyConfig(enabled=True, daily_production_cap=5)
    world = _base_world()
    world.mat_cfg = cfg
    world.facilities.add(Facility(facility_id="fac:1", kind="workshop", site_node_id="loc:a", created_tick=0))
    _staff_facility(world, "fac:1")

    run_materials_production_for_day(world, day=0)

    inv = world.inventories.inv("facility:fac:1")
    total_units = inv.get(Material.FASTENERS) + inv.get(Material.SEALANT)
    assert total_units == 5


def test_snapshot_roundtrip_preserves_pending_delivery() -> None:
    cfg = MaterialsEconomyConfig(enabled=True, default_depot_owner_id="ward:0")
    world = _base_world()
    world.mat_cfg = cfg
    project = ConstructionProject(
        project_id="proj:4",
        site_node_id="loc:site",
        kind="outpost",
        status=ProjectStatus.APPROVED,
        created_tick=0,
        last_tick=0,
        cost=ProjectCost(materials={}, labor_hours=1.0),
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
        bom={Material.ELECTRICAL: 2},
    )
    world.projects.add_project(project)

    evaluate_project_materials(world, day=0)
    snap = snapshot_world(world, scenario_id="mat-econ")
    restored = restore_world(snap)
    restored.mat_cfg = replace(cfg)
    for target in (world, restored):
        target.mat_cfg = replace(cfg)
        target.stockpiles = {Material.ELECTRICAL.name: 2}
        target.inventories.inv("ward:0").add(Material.ELECTRICAL, 2)
        assign_pending_deliveries(target, tick=0)
        process_due_deliveries(target, tick=0)
        evaluate_project_materials(target, day=1)

    assert world_signature(world) == world_signature(restored)


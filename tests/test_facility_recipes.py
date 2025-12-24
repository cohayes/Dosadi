import copy
from types import SimpleNamespace

from dosadi.runtime.materials_economy import (
    MaterialsEconomyConfig,
    run_materials_production_for_day,
)
from dosadi.world.construction import ConstructionProject, ProjectCost, ProjectLedger, ProjectStatus
from dosadi.world.expansion_planner import ExpansionPlannerConfig, ExpansionPlannerState, maybe_plan
from dosadi.world.facilities import Facility, FacilityKind, ensure_facility_ledger
from dosadi.world.materials import InventoryRegistry, Material, ensure_inventory_registry
from dosadi.world.survey_map import SurveyMap, SurveyNode
from dosadi.world.workforce import Assignment, AssignmentKind, ensure_workforce


def _setup_world() -> SimpleNamespace:
    world = SimpleNamespace(day=0)
    world.mat_cfg = MaterialsEconomyConfig(enabled=True, daily_production_cap=100)
    ensure_inventory_registry(world)
    ensure_workforce(world)
    ensure_facility_ledger(world)
    return world


def _add_facility(world, facility_id: str, kind: FacilityKind) -> Facility:
    ledger = ensure_facility_ledger(world)
    facility = Facility(facility_id=facility_id, kind=kind, site_node_id="loc:test", created_tick=0)
    ledger.add(facility)
    return facility


def _staff(world, facility_id: str, agent_ids: list[str]) -> None:
    workforce = ensure_workforce(world)
    for agent_id in agent_ids:
        workforce.assignments[agent_id] = Assignment(
            agent_id=agent_id,
            kind=AssignmentKind.FACILITY_STAFF,
            target_id=facility_id,
            start_day=0,
        )


def _inventory(world, owner: str) -> InventoryRegistry:
    registry = ensure_inventory_registry(world)
    return registry.inv(owner)


def test_deterministic_recipe_execution():
    world = _setup_world()
    fac = _add_facility(world, "fac:1", FacilityKind.WORKSHOP)
    _staff(world, fac.facility_id, ["a1"])
    inv = _inventory(world, f"facility:{fac.facility_id}")
    inv.add(Material.SCRAP_METAL, 12)
    inv.add(Material.PLASTICS, 10)

    clone = copy.deepcopy(world)

    run_materials_production_for_day(world, day=0)
    run_materials_production_for_day(clone, day=0)

    assert ensure_inventory_registry(world).signature() == ensure_inventory_registry(clone).signature()


def test_staffing_gate_blocks_and_allows():
    world = _setup_world()
    fac = _add_facility(world, "fac:2", FacilityKind.WORKSHOP)
    inv = _inventory(world, f"facility:{fac.facility_id}")
    inv.add(Material.SCRAP_METAL, 10)

    run_materials_production_for_day(world, day=0)
    assert inv.get(Material.FASTENERS) == 0

    _staff(world, fac.facility_id, ["s1"])
    run_materials_production_for_day(world, day=1)
    assert inv.get(Material.FASTENERS) > 0


def test_insufficient_inputs_skip_recipe():
    world = _setup_world()
    fac = _add_facility(world, "fac:3", FacilityKind.WORKSHOP)
    _staff(world, fac.facility_id, ["s1"])
    inv = _inventory(world, f"facility:{fac.facility_id}")
    inv.add(Material.SCRAP_METAL, 2)

    run_materials_production_for_day(world, day=0)

    assert inv.get(Material.SCRAP_METAL) == 2
    assert inv.get(Material.FASTENERS) == 0


def test_downtime_prevents_production_until_day_passes():
    world = _setup_world()
    fac = _add_facility(world, "fac:4", FacilityKind.WORKSHOP)
    fac.down_until_day = 1
    _staff(world, fac.facility_id, ["s1"])
    inv = _inventory(world, f"facility:{fac.facility_id}")
    inv.add(Material.SCRAP_METAL, 10)

    run_materials_production_for_day(world, day=0)
    assert inv.get(Material.FASTENERS) == 0

    run_materials_production_for_day(world, day=2)
    assert inv.get(Material.FASTENERS) > 0


def test_expansion_planner_picks_facility_kind_from_shortage():
    world = _setup_world()
    world.stockpiles = {"metal": 20.0, "polymer": 20.0}
    world.agents = {f"agent:{i}": {} for i in range(25)}
    world.survey_map = SurveyMap(
        nodes={
            "loc:alpha": SurveyNode(node_id="loc:alpha", kind="site", confidence=1.0),
            "loc:beta": SurveyNode(node_id="loc:beta", kind="site", confidence=1.0),
        },
        edges={},
    )
    ledger = ProjectLedger()
    world.projects = ledger
    project = ConstructionProject(
        project_id="proj:test",
        site_node_id="loc:alpha",
        kind=FacilityKind.WORKSHOP.value,
        status=ProjectStatus.APPROVED,
        created_tick=0,
        last_tick=0,
        cost=ProjectCost(materials={Material.FASTENERS.name: 5}, labor_hours=0.0),
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
    )
    ledger.add_project(project)

    cfg = ExpansionPlannerConfig()
    state = ExpansionPlannerState(next_plan_day=0)
    created = maybe_plan(world, cfg=cfg, state=state)
    assert created, "Planner should create a project when resources allow"
    created_project = ledger.get(created[0])
    assert created_project.kind == FacilityKind.WORKSHOP.value


def test_snapshot_roundtrip_preserves_downtime_state():
    world = _setup_world()
    fac = _add_facility(world, "fac:5", FacilityKind.WORKSHOP)
    fac.down_until_day = 3
    _staff(world, fac.facility_id, ["s1"])
    inv = _inventory(world, f"facility:{fac.facility_id}")
    inv.add(Material.SCRAP_METAL, 10)

    snapshot = copy.deepcopy(world)
    run_materials_production_for_day(world, day=1)
    run_materials_production_for_day(snapshot, day=1)

    assert inv.get(Material.FASTENERS) == 0
    assert ensure_inventory_registry(world).signature() == ensure_inventory_registry(snapshot).signature()

    run_materials_production_for_day(world, day=5)
    assert inv.get(Material.FASTENERS) > 0

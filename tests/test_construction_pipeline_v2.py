from __future__ import annotations

from dataclasses import replace

from dosadi.agents.core import AgentState, Attributes
from dosadi.runtime.materials_economy import (
    MaterialsEconomyConfig,
    bom_missing,
    evaluate_project_materials,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.world.construction import (
    ConstructionPipelineConfig,
    ConstructionProject,
    ProjectCost,
    ProjectLedger,
    ProjectStatus,
    StageState,
    apply_project_work,
)
from dosadi.world.materials import Material, ensure_inventory_registry
from dosadi.world.workforce import Assignment, AssignmentKind, ensure_workforce


def _make_agent(agent_id: str) -> AgentState:
    attrs = Attributes(INT=12, END=12)
    return AgentState(agent_id=agent_id, name=agent_id, attributes=attrs)


def _make_project(project_id: str = "proj-1") -> ConstructionProject:
    cost = ProjectCost(
        materials={Material.FASTENERS: 5.0, Material.SEALANT: 3.0},
        labor_hours=8.0,
    )
    return ConstructionProject(
        project_id=project_id,
        site_node_id="loc:survey-1",
        kind="outpost",
        status=ProjectStatus.APPROVED,
        created_tick=0,
        last_tick=0,
        cost=cost,
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
    )


def _setup_world(seed: int = 1):
    from dosadi.state import WorldState

    world = WorldState(seed=seed)
    world.projects = ProjectLedger()
    world.mat_cfg = MaterialsEconomyConfig(enabled=True, project_consumption_enabled=True)
    world.construction_cfg = ConstructionPipelineConfig(enabled=True)
    return world


def _assign_worker(world, project_id: str, agent_id: str) -> None:
    ledger = ensure_workforce(world)
    ledger.assign(
        Assignment(
            agent_id=agent_id,
            kind=AssignmentKind.PROJECT_WORK,
            target_id=project_id,
            start_day=0,
        )
    )


def test_deterministic_progression() -> None:
    world_a = _setup_world(seed=3)
    world_b = _setup_world(seed=3)

    agent = _make_agent("a-1")
    for target in (world_a, world_b):
        target.agents[agent.agent_id] = replace(agent)
        project = _make_project()
        target.projects.add_project(project)
        inv = ensure_inventory_registry(target).inv(project.staging_owner_id)
        inv.add(Material.FASTENERS, 5)
        inv.add(Material.SEALANT, 3)
        _assign_worker(target, project.project_id, agent.agent_id)

    for day in range(2):
        evaluate_project_materials(world_a, day=day)
        apply_project_work(world_a, elapsed_hours=6.0, tick=day * 10)
        evaluate_project_materials(world_b, day=day)
        apply_project_work(world_b, elapsed_hours=6.0, tick=day * 10)

    assert world_signature(world_a) == world_signature(world_b)


def test_blocks_when_materials_missing() -> None:
    world = _setup_world(seed=5)
    project = _make_project()
    world.projects.add_project(project)

    evaluate_project_materials(world, day=0)

    assert project.stage_state is StageState.WAITING_MATERIALS
    assert project.block_reason is not None
    missing = project.block_reason.details.get("missing", {})
    assert missing.get(Material.FASTENERS.name) == 5
    assert project.pending_material_delivery_ids


def test_partial_deliveries_reduce_missing() -> None:
    world = _setup_world(seed=7)
    project = _make_project()
    world.projects.add_project(project)

    evaluate_project_materials(world, day=0)
    inv = ensure_inventory_registry(world).inv(project.staging_owner_id)
    inv.add(Material.FASTENERS, 2)

    evaluate_project_materials(world, day=1)

    missing = project.block_reason.details.get("missing", {}) if project.block_reason else {}
    assert missing.get(Material.FASTENERS.name) == 3
    assert missing.get(Material.SEALANT.name) == 3
    assert len(project.pending_material_delivery_ids) == 1


def test_project_starts_with_materials_and_staff() -> None:
    world = _setup_world(seed=9)
    agent = _make_agent("a-1")
    world.agents[agent.agent_id] = agent
    project = _make_project()
    world.projects.add_project(project)
    inv = ensure_inventory_registry(world).inv(project.staging_owner_id)
    inv.add(Material.FASTENERS, 5)
    inv.add(Material.SEALANT, 3)
    _assign_worker(world, project.project_id, agent.agent_id)

    evaluate_project_materials(world, day=0)

    assert project.stage_state is StageState.IN_PROGRESS
    assert project.status is ProjectStatus.BUILDING
    assert project.block_reason is None
    assert project.bom_consumed
    assert inv.get(Material.FASTENERS) == 0


def test_incident_pause_blocks_progress() -> None:
    world = _setup_world(seed=11)
    agent = _make_agent("a-1")
    world.agents[agent.agent_id] = agent
    project = _make_project()
    project.incident_paused = True
    world.projects.add_project(project)
    inv = ensure_inventory_registry(world).inv(project.staging_owner_id)
    inv.add(Material.FASTENERS, 5)
    inv.add(Material.SEALANT, 3)
    _assign_worker(world, project.project_id, agent.agent_id)

    evaluate_project_materials(world, day=0)
    evaluate_project_materials(world, day=1)

    assert project.stage_state is StageState.PAUSED_INCIDENT
    assert project.progress_days_in_stage == 0


def test_completion_advances_stage() -> None:
    world = _setup_world(seed=13)
    agent = _make_agent("a-1")
    world.agents[agent.agent_id] = agent
    project = _make_project()
    world.projects.add_project(project)
    inv = ensure_inventory_registry(world).inv(project.staging_owner_id)
    inv.add(Material.FASTENERS, 5)
    inv.add(Material.SEALANT, 3)
    _assign_worker(world, project.project_id, agent.agent_id)

    evaluate_project_materials(world, day=0)
    apply_project_work(world, elapsed_hours=8.0, tick=5)

    assert project.status is ProjectStatus.COMPLETE
    assert project.stage_state is StageState.DONE
    assert project.progress_days_in_stage == 0


def test_snapshot_roundtrip_mid_block() -> None:
    world = _setup_world(seed=15)
    agent = _make_agent("a-1")
    world.agents[agent.agent_id] = agent
    project = _make_project()
    world.projects.add_project(project)

    evaluate_project_materials(world, day=0)
    snap = snapshot_world(world, scenario_id="construction-pipeline-v2")
    restored = restore_world(snap)

    inv_live = ensure_inventory_registry(world).inv(project.staging_owner_id)
    inv_live.add(Material.FASTENERS, 5)
    inv_live.add(Material.SEALANT, 3)
    inv_restored = ensure_inventory_registry(restored).inv(project.staging_owner_id)
    inv_restored.add(Material.FASTENERS, 5)
    inv_restored.add(Material.SEALANT, 3)
    for target in (world, restored):
        target.agents[agent.agent_id] = replace(agent)
        _assign_worker(target, project.project_id, agent.agent_id)
        evaluate_project_materials(target, day=1)
        apply_project_work(target, elapsed_hours=8.0, tick=10)

    assert world_signature(world) == world_signature(restored)


def test_bom_missing_helper() -> None:
    inv = ensure_inventory_registry(_setup_world()).inv("owner:1")
    inv.add(Material.FASTENERS, 2)
    missing = bom_missing(inv, {Material.FASTENERS: 4, Material.SEALANT: 1})
    assert missing[Material.FASTENERS] == 2
    assert missing[Material.SEALANT] == 1


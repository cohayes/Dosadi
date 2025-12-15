from __future__ import annotations

from dataclasses import replace

from dosadi.agents.core import AgentState, Attributes
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.runtime.timewarp import TimewarpConfig, step_day
from dosadi.state import WorldState
from dosadi.world.construction import (
    ConstructionProject,
    ProjectCost,
    ProjectLedger,
    ProjectStatus,
    apply_project_work,
    process_projects,
    stage_project_if_ready,
)


def _make_agent(agent_id: str) -> AgentState:
    attrs = Attributes(INT=12, END=12)
    return AgentState(agent_id=agent_id, name=agent_id, attributes=attrs)


def _make_project(project_id: str = "proj-1") -> ConstructionProject:
    cost = ProjectCost(materials={"polymer": 50.0, "metal": 20.0}, labor_hours=10.0)
    return ConstructionProject(
        project_id=project_id,
        site_node_id="loc:survey-1",
        kind="outpost",
        status=ProjectStatus.PROPOSED,
        created_tick=0,
        last_tick=0,
        cost=cost,
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
    )


def test_state_machine_progression() -> None:
    world = WorldState(seed=3)
    world.config.tick_seconds = 3600.0
    world.stockpiles = {"polymer": 60.0, "metal": 30.0}
    world.projects = ProjectLedger()

    agent = _make_agent("a-1")
    world.agents[agent.agent_id] = agent

    project = _make_project()
    project.status = ProjectStatus.APPROVED
    world.projects.add_project(project)

    assert stage_project_if_ready(world, project, 0)
    assert world.stockpiles["polymer"] == 10.0
    project.assigned_agents.append(agent.agent_id)

    for tick in range(12):
        process_projects(world, tick=tick)

    assert project.status == ProjectStatus.COMPLETE
    assert "fac:proj-1" in world.facilities


def test_resource_nonnegativity() -> None:
    world = WorldState(seed=5)
    world.stockpiles = {"polymer": 10.0, "metal": 5.0}
    project = _make_project()
    project.status = ProjectStatus.APPROVED

    assert not stage_project_if_ready(world, project, 0)
    assert world.stockpiles["polymer"] == 10.0
    assert project.status == ProjectStatus.APPROVED


def test_deterministic_signature() -> None:
    base_world = WorldState(seed=7)
    base_world.config.tick_seconds = 1800.0
    base_world.stockpiles = {"polymer": 80.0, "metal": 40.0}
    base_world.projects = ProjectLedger()
    agent = _make_agent("a-1")
    base_world.agents[agent.agent_id] = agent

    project = _make_project()
    project.status = ProjectStatus.APPROVED
    project.assigned_agents.append(agent.agent_id)
    base_world.projects.add_project(project)

    for tick in range(16):
        process_projects(base_world, tick=tick)

    world_copy = replace(base_world)
    world_copy.projects = ProjectLedger()
    copied_project = _make_project()
    copied_project.status = project.status
    copied_project.assigned_agents = list(project.assigned_agents)
    copied_project.materials_delivered = dict(project.materials_delivered)
    copied_project.labor_applied_hours = project.labor_applied_hours
    world_copy.projects.add_project(copied_project)

    assert base_world.projects.signature() == world_copy.projects.signature()


def test_snapshot_roundtrip_continues_build() -> None:
    world = WorldState(seed=11)
    world.config.tick_seconds = 3600.0
    world.stockpiles = {"polymer": 60.0, "metal": 20.0}
    world.projects = ProjectLedger()
    agent = _make_agent("a-1")
    world.agents[agent.agent_id] = agent

    project = _make_project()
    project.status = ProjectStatus.APPROVED
    project.assigned_agents.append(agent.agent_id)
    world.projects.add_project(project)

    apply_project_work(world, elapsed_hours=4.0, tick=0)
    snapshot = snapshot_world(world, scenario_id="construction-test")
    restored_world = restore_world(snapshot)

    apply_project_work(world, elapsed_hours=6.0, tick=10)
    apply_project_work(restored_world, elapsed_hours=6.0, tick=10)

    assert world_signature(world) == world_signature(restored_world)
    assert restored_world.projects.get(project.project_id).status == ProjectStatus.COMPLETE


def test_macrostep_completion() -> None:
    world = WorldState(seed=13)
    world.stockpiles = {"polymer": 80.0, "metal": 50.0}
    world.projects = ProjectLedger()
    agent = _make_agent("a-1")
    world.agents[agent.agent_id] = agent

    project = _make_project()
    project.status = ProjectStatus.APPROVED
    project.assigned_agents.append(agent.agent_id)
    world.projects.add_project(project)

    step_day(world, days=5, cfg=TimewarpConfig(physiology_enabled=False))

    assert project.status == ProjectStatus.COMPLETE
    assert "fac:proj-1" in world.facilities

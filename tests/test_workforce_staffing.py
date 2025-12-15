import pytest

from dosadi.runtime.facility_updates import update_facilities_for_day
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.staffing import StaffingConfig, StaffingState, run_staffing_policy
from dosadi.state import AgentState, WorldState
from dosadi.world.construction import ConstructionProject, ProjectCost, ProjectStatus, apply_project_work
from dosadi.world.facilities import Facility, FacilityBehavior, FacilityLedger, _FACILITY_BEHAVIORS
from dosadi.world.scout_missions import MissionIntent, MissionStatus, ScoutMission, ScoutMissionLedger
from dosadi.world.workforce import Assignment, AssignmentKind, WorkforceLedger, ensure_workforce


def _basic_agent(agent_id: str, role: str | None = None) -> AgentState:
    return AgentState(id=agent_id, name=agent_id, faction="f:1", ward="w:1", role=role)


def test_assign_prevents_double_assignment():
    ledger = WorkforceLedger()
    ledger.assign(
        Assignment(
            agent_id="agent-1",
            kind=AssignmentKind.PROJECT_WORK,
            target_id="project-1",
            start_day=1,
        )
    )

    with pytest.raises(ValueError):
        ledger.assign(
            Assignment(
                agent_id="agent-1",
                kind=AssignmentKind.SCOUT_MISSION,
                target_id="mission-1",
                start_day=2,
            )
        )


def test_staffing_policy_is_deterministic_under_snapshot():
    world = WorldState()
    world.agents = {f"agent-{i}": _basic_agent(f"agent-{i}") for i in range(4)}
    world.projects.add_project(
        ConstructionProject(
            project_id="proj-1",
            site_node_id="loc:1",
            kind="outpost",
            status=ProjectStatus.STAGED,
            created_tick=0,
            last_tick=0,
            cost=ProjectCost(materials={}, labor_hours=10.0),
            materials_delivered={},
            labor_applied_hours=0.0,
            assigned_agents=[],
        )
    )

    cfg = StaffingConfig(min_idle_agents=1, max_changes_per_cycle=10, project_workers_default=2)
    state = StaffingState()
    run_staffing_policy(world, day=1, cfg=cfg, state=state)
    signature_first = world.workforce.signature()

    snap = snapshot_world(world, scenario_id="test")
    restored = restore_world(snap)
    run_staffing_policy(restored, day=1, cfg=cfg, state=restored.staffing_state)

    assert restored.workforce.signature() == signature_first


def test_staffing_respects_idle_reserve():
    world = WorldState()
    world.agents = {f"agent-{i}": _basic_agent(f"agent-{i}") for i in range(5)}
    world.projects.add_project(
        ConstructionProject(
            project_id="proj-2",
            site_node_id="loc:1",
            kind="outpost",
            status=ProjectStatus.BUILDING,
            created_tick=0,
            last_tick=0,
            cost=ProjectCost(materials={}, labor_hours=10.0),
            materials_delivered={},
            labor_applied_hours=0.0,
            assigned_agents=[],
        )
    )

    cfg = StaffingConfig(min_idle_agents=2, project_workers_default=5)
    state = StaffingState()
    run_staffing_policy(world, day=1, cfg=cfg, state=state)

    assignments = [a for a in world.workforce.assignments.values() if a.kind is not AssignmentKind.IDLE]
    assert len(assignments) <= 3


def test_project_progress_depends_on_staffing():
    world = WorldState()
    world.agents = {"agent-1": _basic_agent("agent-1"), "agent-2": _basic_agent("agent-2")}
    project = ConstructionProject(
        project_id="proj-3",
        site_node_id="loc:1",
        kind="outpost",
        status=ProjectStatus.BUILDING,
        created_tick=0,
        last_tick=0,
        cost=ProjectCost(materials={}, labor_hours=10.0),
        materials_delivered={},
        labor_applied_hours=0.0,
        assigned_agents=[],
    )
    world.projects.add_project(project)

    apply_project_work(world, elapsed_hours=4.0, tick=0)
    assert project.labor_applied_hours == 0.0

    ledger = ensure_workforce(world)
    ledger.assign(
        Assignment(
            agent_id="agent-1",
            kind=AssignmentKind.PROJECT_WORK,
            target_id=project.project_id,
            start_day=0,
        )
    )
    apply_project_work(world, elapsed_hours=4.0, tick=1)
    assert project.labor_applied_hours > 0.0


def test_facility_outputs_require_staff_when_flagged():
    world = WorldState()
    world.agents = {"agent-1": _basic_agent("agent-1")}
    facility = Facility(
        facility_id="fac-1",
        kind="lab",
        site_node_id="loc:1",
        created_tick=0,
        state={},
    )
    world.facilities = FacilityLedger({facility.facility_id: facility})
    _FACILITY_BEHAVIORS["lab"] = FacilityBehavior(
        kind="lab",
        inputs_per_day={},
        outputs_per_day={"samples": 10.0},
        requires_labor=True,
        labor_agents=1,
    )

    update_facilities_for_day(world, day=0, days=1)
    assert world.stockpiles.get("samples", 0) == 0

    ledger = ensure_workforce(world)
    ledger.assign(
        Assignment(
            agent_id="agent-1",
            kind=AssignmentKind.FACILITY_STAFF,
            target_id=facility.facility_id,
            start_day=0,
        )
    )
    update_facilities_for_day(world, day=1, days=1)
    assert world.stockpiles.get("samples", 0) > 0


def test_snapshot_roundtrip_preserves_assignments():
    world = WorldState()
    world.agents = {f"agent-{i}": _basic_agent(f"agent-{i}") for i in range(3)}
    mission = ScoutMission(
        mission_id="m-1",
        status=MissionStatus.EN_ROUTE,
        intent=MissionIntent.PERIMETER,
        origin_node_id="loc:home",
        current_node_id="loc:home",
        target_node_id=None,
        heading_deg=None,
        max_days=5,
        party_agent_ids=["agent-0", "agent-1"],
        supplies={},
        risk_budget=1.0,
        start_day=0,
        last_step_day=0,
        days_elapsed=0,
        discoveries=[],
    )
    world.scout_missions = ScoutMissionLedger(missions={mission.mission_id: mission}, active_ids=[mission.mission_id])

    cfg = StaffingConfig(min_idle_agents=0, project_workers_default=1)
    run_staffing_policy(world, day=1, cfg=cfg, state=world.staffing_state)
    before_signature = world.workforce.signature()

    snap = snapshot_world(world, scenario_id="test")
    restored = restore_world(snap)
    run_staffing_policy(restored, day=2, cfg=cfg, state=restored.staffing_state)

    assert restored.workforce.signature() == before_signature

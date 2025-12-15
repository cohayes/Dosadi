from __future__ import annotations

import copy

import pytest

from dosadi.agents.core import AgentState, Attributes
from dosadi.runtime.facility_updates import update_facilities_for_day
from dosadi.runtime.snapshot import restore_world, snapshot_world, world_signature
from dosadi.runtime.timewarp import TimewarpConfig, step_day
from dosadi.state import WorldState
from dosadi.world import stocks
from dosadi.world.construction import ProjectLedger, process_projects
from dosadi.world.expansion_planner import ExpansionPlannerConfig, ExpansionPlannerState, maybe_plan
from dosadi.world.facilities import Facility, FacilityLedger
from dosadi.world.survey_map import SurveyMap, SurveyNode


def _make_world_with_facility(kind: str = "pump_station") -> WorldState:
    world = WorldState(seed=123)
    world.rng.seed(world.seed)
    world.facilities = FacilityLedger()
    facility = Facility(
        facility_id="fac:test",
        kind=kind,
        site_node_id="loc:test",
        created_tick=0,
    )
    world.facilities.add(facility)
    world.stockpiles = {}
    return world


def test_deterministic_daily_outputs() -> None:
    base_world = _make_world_with_facility()
    base_world.stockpiles["filters"] = 1.0

    snapshot = snapshot_world(base_world, scenario_id="facility-test")
    world_a = restore_world(snapshot)
    world_b = restore_world(snapshot)

    update_facilities_for_day(world_a, day=0)
    update_facilities_for_day(world_b, day=0)

    assert stocks.snapshot_totals(world_a) == stocks.snapshot_totals(world_b)


def test_resource_constraints_block_outputs() -> None:
    world = _make_world_with_facility()
    before = stocks.snapshot_totals(world)

    update_facilities_for_day(world, day=0)

    after = stocks.snapshot_totals(world)
    assert after == before
    assert world.facilities.get("fac:test").last_update_day == 0


def test_macrostep_equivalence_matches_daily() -> None:
    world_daily = _make_world_with_facility()
    world_daily.stockpiles = {"filters": 2.0}

    world_macro = copy.deepcopy(world_daily)

    for day in range(7):
        update_facilities_for_day(world_daily, day=day)

    step_day(world_macro, days=7, cfg=TimewarpConfig(physiology_enabled=False))

    macro_totals = stocks.snapshot_totals(world_macro)
    daily_totals = stocks.snapshot_totals(world_daily)
    assert macro_totals.keys() == daily_totals.keys()
    for key in daily_totals:
        assert macro_totals[key] == pytest.approx(daily_totals[key])


def test_snapshot_roundtrip_is_consistent() -> None:
    world = _make_world_with_facility()
    world.stockpiles = {"filters": 1.0}
    world.rng.seed(99)

    update_facilities_for_day(world, day=0)
    snapshot = snapshot_world(world, scenario_id="facility-roundtrip")
    restored = restore_world(snapshot)

    update_facilities_for_day(world, day=1)
    update_facilities_for_day(restored, day=1)

    assert stocks.snapshot_totals(world) == stocks.snapshot_totals(restored)
    assert world_signature(world) == world_signature(restored)


def test_expansion_planner_facility_produces_outputs() -> None:
    world = WorldState(seed=7)
    world.rng.seed(world.seed)
    world.stockpiles = {"polymer": 20.0, "metal": 10.0}
    world.facilities = FacilityLedger()
    world.projects = ProjectLedger()

    # Agents to satisfy deterministic labor selection.
    agent = AgentState(agent_id="a-1", name="a-1", attributes=Attributes(INT=10, END=10))
    world.agents[agent.agent_id] = agent

    world.survey_map = SurveyMap()
    world.survey_map.upsert_node(
        SurveyNode(
            node_id="loc:survey-1",
            kind="outpost_site",
            ward_id="ward:core",
            water=5.0,
            hazard=0.1,
            tags=("resource_rich",),
            confidence=0.9,
            last_seen_tick=0,
        ),
        confidence_delta=0.1,
    )

    planner_cfg = ExpansionPlannerConfig(
        project_kinds=("outpost",), labor_pool_size=1, min_idle_agents=0
    )
    planner_state = ExpansionPlannerState(next_plan_day=0)

    created = maybe_plan(world, cfg=planner_cfg, state=planner_state)
    assert created

    project_id = created[0]
    project = world.projects.get(project_id)

    # Fast-forward construction completion.
    process_projects(world, tick=0)
    project.labor_applied_hours = project.cost.labor_hours
    process_projects(world, tick=1)

    assert world.facilities

    before = stocks.snapshot_totals(world)
    update_facilities_for_day(world, day=world.day, days=1)
    after = stocks.snapshot_totals(world)

    assert after.get("survey_progress", 0.0) > before.get("survey_progress", 0.0)


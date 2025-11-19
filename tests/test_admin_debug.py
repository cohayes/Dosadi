from types import SimpleNamespace

from dosadi import (
    AdminDashboardCLI,
    AdminDebugView,
    AdminEventLog,
    ScenarioTimelineCLI,
    snapshot_agent_debug,
    snapshot_ward,
    snapshot_world_state,
)
from dosadi.worldgen import WorldgenConfig, generate_world


def _build_world(seed: int = 99):
    config = WorldgenConfig.minimal(seed=seed, wards=4)
    config.enable_agents = True
    config.agent_roll = type(config.agent_roll)(2, 3)
    return generate_world(config)


def test_world_snapshot_contains_metrics():
    world = _build_world()
    snapshot = snapshot_world_state(world)
    assert snapshot.total_agents == len(world.agents)
    assert snapshot.ward_summaries
    assert "avg_hunger" in snapshot.global_metrics


def test_ward_snapshot_contains_facilities():
    world = _build_world(seed=100)
    ward_id = next(iter(world.wards))
    snapshot = snapshot_ward(world, ward_id)
    assert snapshot.facilities
    assert snapshot.metrics["need_index"] >= 0.0


def test_agent_snapshot_and_view_render():
    world = _build_world(seed=7)
    agent_id = next(iter(world.agents))
    agent_snapshot = snapshot_agent_debug(world, agent_id)
    assert agent_snapshot.agent_id == agent_id
    assert 0.0 <= agent_snapshot.hunger <= 1.0
    view = AdminDebugView()
    dashboard = view.render_dashboard(world, ward_id=world.agents[agent_id].ward, agent_id=agent_id)
    assert agent_id in dashboard
    assert world.agents[agent_id].ward in dashboard


def test_agent_identity_details_in_snapshot():
    world = _build_world(seed=19)
    agent_id = next(iter(world.agents))
    agent = world.agents[agent_id]
    agent.identity.add_handle("B-Whisper")
    agent.identity.issue_permit(
        permit_id="permit:test",
        kind="carry:HEAVY_WEAPON",
        issued_by="AP-North",
        issued_tick=world.tick,
    )
    agent.identity.set_trust_flag("sting_watchlist", 0.9)

    snapshot = snapshot_agent_debug(world, agent_id)
    assert "B-Whisper" in snapshot.identity.handles
    assert snapshot.identity.active_permits
    assert "sting_watchlist" in snapshot.identity.trust_flags


def test_agent_snapshot_includes_loadout_details():
    world = _build_world(seed=23)
    agent_id = next(iter(world.agents))
    snapshot = snapshot_agent_debug(world, agent_id)
    assert snapshot.loadout.readiness >= 0.0
    view = AdminDebugView()
    render = view.render_agent(snapshot)
    assert "Loadout" in render


def test_cli_dashboard_includes_events():
    world = _build_world(seed=11)
    ward_id = next(iter(world.wards))
    agent_id = next(iter(world.agents))
    log = AdminEventLog()
    log.log_facility_event(tick=world.tick, ward_id=ward_id, facility_id=f"{ward_id}:SOUP", event_kind="SHORTAGE")
    cli = AdminDashboardCLI(width=60)
    output = cli.render(world, ward_id=ward_id, agent_id=agent_id, event_log=log)
    assert "World" in output
    assert "Ward" in output
    assert "Recent events" in output


def test_scenario_timeline_cli_handles_generic_phases():
    cli = ScenarioTimelineCLI(width=50)
    phases = [
        SimpleNamespace(key="A", description="Phase A", metrics={"foo": 1.23}, events=[1, 2]),
        SimpleNamespace(key="B", description="Phase B", metrics={}, events=[]),
    ]
    output = cli.render(phases, title="Scenario")
    assert "Scenario" in output
    assert "Phase" in output
    assert "foo=1.23" in output

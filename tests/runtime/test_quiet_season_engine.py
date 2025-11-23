from pathlib import Path

from dosadi.interfaces.campaign_dashboard import CampaignDashboardCLI
from dosadi.runtime.campaign_engine import CampaignEngine, load_scenario_definition


def test_quiet_season_engine_runs_and_renders_dashboard():
    scenario_path = Path("docs/latest/11_scenarios/S-0001_Pre_Sting_Quiet_Season.yaml")
    scenario = load_scenario_definition(scenario_path)
    engine = CampaignEngine(scenario)
    result = engine.run(8)

    assert result.states[-1].tick == scenario.starting_tick + 8
    statuses = {status.objective.id: status.status_current for status in result.objectives}
    assert statuses.get("delay_crackdown") in {"on_track", "at_risk"}
    assert statuses.get("no_open_conflict") != "failed"
    assert result.states[-1].security_summary is not None

    dashboard = CampaignDashboardCLI(width=60).render(result)
    assert scenario.name in dashboard
    assert "Objectives" in dashboard
    assert "Counterintelligence Posture" in dashboard
    assert "Security Summary" in dashboard
    assert "Stance" in dashboard


def test_ci_stance_changes_metrics():
    scenario_path = Path("docs/latest/11_scenarios/S-0001_Pre_Sting_Quiet_Season.yaml")
    scenario = load_scenario_definition(scenario_path)

    aggressive = CampaignEngine(scenario)
    aggressive.state.ci_stance = "aggressive"
    for _ in range(4):
        aggressive.step()

    cautious = CampaignEngine(scenario)
    cautious.state.ci_stance = "cautious"
    for _ in range(4):
        cautious.step()

    assert aggressive.state.global_stress_index > cautious.state.global_stress_index
    assert aggressive.state.ci_states[0].infiltration_risk < cautious.state.ci_states[0].infiltration_risk

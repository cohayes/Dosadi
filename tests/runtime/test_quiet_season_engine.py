from pathlib import Path

from dosadi.interfaces.campaign_dashboard import CampaignDashboardCLI
from dosadi.runtime.campaign_engine import CampaignEngine, load_scenario_definition


def test_quiet_season_engine_runs_and_renders_dashboard():
    scenario_path = Path("docs/latest/11_scenarios/S-0001_Pre_Sting_Quiet_Season.yaml")
    scenario = load_scenario_definition(scenario_path)
    engine = CampaignEngine(scenario)
    result = engine.run(8)

    assert result.states[-1].tick == scenario.starting_tick + 8
    statuses = {status.objective.id: status.status for status in result.objectives}
    assert statuses.get("delay_crackdown") in {"pending", "achieved"}
    assert statuses.get("no_open_conflict") != "failed"
    assert result.states[-1].security_summary is not None

    dashboard = CampaignDashboardCLI(width=60).render(result)
    assert scenario.name in dashboard
    assert "Objectives" in dashboard
    assert "Counterintelligence Posture" in dashboard
    assert "Security Summary" in dashboard

from dosadi import StingWaveConfig, run_sting_wave_day3
from dosadi.playbook.cli import _parse_overrides
from dosadi.playbook.scenario_runner import available_scenarios, run_scenario
from dosadi.playbook.scenario_validation import verify_scenario


def test_sting_wave_report_covers_all_phases_and_events():
    report = run_sting_wave_day3(StingWaveConfig(scenario_seed=1))

    assert len(report.phases) == 10
    event_types = {event.type for event in report.events}
    for expected in [
        "ListingPosted",
        "StingInjected",
        "AmbushAttempted",
        "CrackdownExecuted",
        "ArbiterDecree",
        "FXMarked",
        "RumorHeatUpdated",
    ]:
        assert expected in event_types

    assert report.kpis["reserve_floor"] >= report.config.reserve_floor
    assert report.kpis["heat_peak"] >= 0.5


def test_scenario_runner_registry_and_validation():
    entries = [entry.name for entry in available_scenarios()]
    assert "sting_wave_day3" in entries

    report = run_scenario("sting_wave_day3", overrides={"scenario_seed": 5})
    result = verify_scenario("sting_wave_day3", report)
    assert result.passed
    assert result.metrics["bust_rate"] >= 0.8


def test_cli_override_parser_handles_types():
    overrides = _parse_overrides(["world_seed=42", "sting_injection_rate=0.12", "enable_fx=true"])
    assert overrides["world_seed"] == 42
    assert abs(overrides["sting_injection_rate"] - 0.12) < 1e-6
    assert overrides["enable_fx"] is True

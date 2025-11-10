from dosadi import Day0Config, run_day0_playbook


def test_day0_playbook_emits_expected_events():
    report = run_day0_playbook(Day0Config())

    assert len(report.steps) == 9

    event_types = {event.type for event in report.events}
    for expected in [
        "WorldCreated",
        "BarrelDelivered",
        "MaintenanceCompleted",
        "ClinicOutcome",
        "CaseRuling",
        "LegitimacyRecalculated",
    ]:
        assert expected in event_types

    step1 = next(step for step in report.steps if step.key == "1")
    leg_grad = step1.metrics["legitimacy_gradient"]
    assert leg_grad[0] > leg_grad[1] > leg_grad[2]

    step2 = next(step for step in report.steps if step.key == "2")
    route_result = step2.metrics["route_results"]["route:well-w21"]
    manifest = step2.metrics["manifest_per_route"]
    assert abs(route_result["delivered"] - manifest * 0.95) < 1e-6
    assert route_result["incident"]["type"] == "AMBUSH"

    step4 = next(step for step in report.steps if step.key == "4")
    assert step4.metrics["no_show_rate"] <= 0.1

    step9 = next(step for step in report.steps if step.key == "9")
    assert step9.metrics["legitimacy_after"] > step9.metrics["legitimacy_before"]
    assert step9.metrics["risk_after"] < step9.metrics["risk_before"]


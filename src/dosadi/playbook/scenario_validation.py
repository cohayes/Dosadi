"""Scenario validation helpers.

Each documented scenario in docs/latest/11_scenarios ships with a light-weight
verification suite so notebook and CLI operators can assert that critical KPIs
match the reference description.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping

from .scenario_runner import get_scenario_entry
from .sting_wave import StingWaveReport


@dataclass(slots=True)
class ScenarioValidationIssue:
    check: str
    message: str


@dataclass(slots=True)
class ScenarioValidationResult:
    scenario: str
    doc_path: str
    passed: bool
    issues: List[ScenarioValidationIssue] = field(default_factory=list)
    metrics: Mapping[str, float] = field(default_factory=dict)


Verifier = Callable[[object], ScenarioValidationResult]


def verify_scenario(name: str, report: object) -> ScenarioValidationResult:
    try:
        verifier = _SCENARIO_VERIFIERS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown scenario '{name}'") from exc
    return verifier(report)


def _verify_sting_wave(report: StingWaveReport) -> ScenarioValidationResult:
    entry = get_scenario_entry("sting_wave_day3")
    issues: List[ScenarioValidationIssue] = []
    expected_phases = ["0", "A", "B", "C", "D", "E", "F", "G", "H", "I"]
    phase_keys = [phase.key for phase in report.phases]
    if phase_keys != expected_phases:
        issues.append(
            ScenarioValidationIssue(
                check="phases",
                message=f"expected phases {expected_phases} but received {phase_keys}",
            )
        )

    expected_event_types = {
        "ListingPosted",
        "StingInjected",
        "AmbushAttempted",
        "CrackdownExecuted",
        "ArbiterDecree",
        "FXMarked",
        "RumorHeatUpdated",
    }
    observed_event_types = {event.type for event in report.events}
    missing = sorted(expected_event_types - observed_event_types)
    if missing:
        issues.append(
            ScenarioValidationIssue(
                check="events",
                message=f"missing event types: {', '.join(missing)}",
            )
        )

    reserve_floor = report.kpis.get("reserve_floor")
    if reserve_floor is None or reserve_floor < report.config.reserve_floor:
        issues.append(
            ScenarioValidationIssue(
                check="reserve_floor",
                message=(
                    f"reserve_floor {reserve_floor} fell below configured floor "
                    f"{report.config.reserve_floor}"
                ),
            )
        )

    heat_peak = report.kpis.get("heat_peak")
    if heat_peak is None or heat_peak < 0.5:
        issues.append(
            ScenarioValidationIssue(
                check="heat_peak",
                message=f"expected heat_peak >= 0.5, observed {heat_peak}",
            )
        )

    bust_rate = report.kpis.get("bust_rate")
    if bust_rate is None or bust_rate < 0.8:
        issues.append(
            ScenarioValidationIssue(
                check="bust_rate",
                message=f"expected bust_rate >= 0.8, observed {bust_rate}",
            )
        )

    passed = not issues
    return ScenarioValidationResult(
        scenario=entry.name,
        doc_path=entry.doc_path,
        passed=passed,
        issues=issues,
        metrics=dict(report.kpis),
    )


_SCENARIO_VERIFIERS: Dict[str, Verifier] = {
    "sting_wave_day3": _verify_sting_wave,
}


__all__ = [
    "ScenarioValidationIssue",
    "ScenarioValidationResult",
    "verify_scenario",
]

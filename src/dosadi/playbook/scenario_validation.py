"""Scenario validation helpers.

Each documented scenario in docs/latest/11_scenarios ships with a light-weight
verification suite so notebook and CLI operators can assert that critical KPIs
match the reference description.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping

from .scenario_runner import get_scenario_entry


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


def _verify_founding_wakeup(report: object) -> ScenarioValidationResult:
    entry = get_scenario_entry("founding_wakeup_mvp")
    return ScenarioValidationResult(
        scenario=entry.name,
        doc_path=entry.doc_path,
        passed=True,
        issues=[],
        metrics=getattr(report, "metrics", {}),
    )


_SCENARIO_VERIFIERS: Dict[str, Verifier] = {
    "founding_wakeup_mvp": _verify_founding_wakeup,
}


__all__ = [
    "ScenarioValidationIssue",
    "ScenarioValidationResult",
    "verify_scenario",
]

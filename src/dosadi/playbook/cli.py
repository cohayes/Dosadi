"""Command line interface for scenario runners."""

from __future__ import annotations

import argparse
from typing import Dict, Mapping, Sequence

from ..interfaces.cli_dashboard import AdminDashboardCLI, ScenarioTimelineCLI
from ..state import WorldState
from .scenario_runner import available_scenarios, run_scenario
from .scenario_validation import ScenarioValidationResult, verify_scenario


def _parse_overrides(pairs: Sequence[str]) -> Dict[str, object]:
    overrides: Dict[str, object] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Overrides must be of the form key=value, received '{pair}'")
        key, raw_value = pair.split("=", 1)
        overrides[key.strip()] = _coerce_value(raw_value.strip())
    return overrides


def _coerce_value(raw: str) -> object:
    for cast in (int, float):
        try:
            return cast(raw)
        except ValueError:
            continue
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    return raw


def _render_dashboard(world: WorldState, *, ward_id: str | None, agent_id: str | None, width: int) -> str:
    cli = AdminDashboardCLI(width=width)
    return cli.render(world, ward_id=ward_id, agent_id=agent_id)


def _render_timeline(phases, *, title: str, width: int) -> str:
    cli = ScenarioTimelineCLI(width=width)
    return cli.render(phases, title=title)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run documented Dosadi scenarios")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--scenario", default="sting_wave_day3", help="Scenario identifier")
    parser.add_argument(
        "--config",
        action="append",
        default=[],
        metavar="key=value",
        help="Override scenario config fields",
    )
    parser.add_argument("--width", type=int, default=90, help="Panel width")
    parser.add_argument("--dashboard", action="store_true", help="Render the admin dashboard panels")
    parser.add_argument("--ward", help="Ward focus for the dashboard")
    parser.add_argument("--agent", help="Agent focus for the dashboard")
    parser.add_argument("--no-timeline", dest="timeline", action="store_false", help="Disable the timeline output")
    parser.add_argument("--verify", action="store_true", help="Run scenario validation checks")
    args = parser.parse_args(argv)

    if args.list:
        for entry in available_scenarios():
            print(f"{entry.name:20} | {entry.description} ({entry.doc_path})")
        return 0

    overrides = _parse_overrides(args.config)
    report = run_scenario(args.scenario, overrides=overrides or None)

    if args.timeline:
        print(_render_timeline(report.phases, title=f"Scenario {args.scenario}", width=args.width))
        print("")

    if args.dashboard:
        print(_render_dashboard(report.world, ward_id=args.ward, agent_id=args.agent, width=args.width))
        print("")

    if args.verify:
        result = verify_scenario(args.scenario, report)
        _print_validation(result)
        if not result.passed:
            return 2

    return 0


def _print_validation(result: ScenarioValidationResult) -> None:
    status = "PASSED" if result.passed else "FAILED"
    print(f"Validation {status} for {result.scenario} ({result.doc_path})")
    if result.metrics:
        metric_line = ", ".join(f"{k}={v:0.2f}" for k, v in result.metrics.items())
        print(f"KPIs: {metric_line}")
    if result.issues:
        for issue in result.issues:
            print(f" - [{issue.check}] {issue.message}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

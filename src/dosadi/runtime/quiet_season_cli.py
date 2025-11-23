"""Simple CLI harness for the Quiet Season scenario."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..interfaces.campaign_dashboard import CampaignDashboardCLI
from .campaign_engine import CampaignEngine, load_scenario_definition


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Quiet Season scenario sandbox")
    parser.add_argument(
        "--scenario",
        type=Path,
        default=Path("docs/latest/11_scenarios/S-0001_Pre_Sting_Quiet_Season.yaml"),
        help="Path to the scenario definition YAML",
    )
    parser.add_argument("--ticks", type=int, default=12, help="Number of ticks to simulate")
    parser.add_argument("--width", type=int, default=80, help="Dashboard width")
    args = parser.parse_args()

    scenario = load_scenario_definition(args.scenario)
    engine = CampaignEngine(scenario)
    result = engine.run(args.ticks)
    cli = CampaignDashboardCLI(width=args.width)
    print(cli.render(result))


if __name__ == "__main__":
    main()

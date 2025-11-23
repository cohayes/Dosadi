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
    parser.add_argument(
        "--interactive-ci",
        action="store_true",
        help="Prompt for CI stance adjustments during the run",
    )
    parser.add_argument(
        "--ci-prompt-interval",
        type=int,
        default=4,
        help="How often (in ticks) to prompt for CI stance when interactive",
    )
    args = parser.parse_args()

    scenario = load_scenario_definition(args.scenario)
    engine = CampaignEngine(scenario)
    history = [engine.state.snapshot()]
    if not args.interactive_ci:
        result = engine.run(args.ticks)
    else:
        prompt_interval = max(1, args.ci_prompt_interval)
        for _ in range(args.ticks):
            history.append(engine.step())
            if engine.state.tick % prompt_interval == 0:
                print(f"\n[Tick {engine.state.tick}] Current CI stance: {engine.state.ci_stance}")
                choice = input("CI stance? [c]autious / [b]alanced / [a]ggressive (ENTER = keep current): ").strip().lower()
                if choice.startswith("c"):
                    engine.state.ci_stance = "cautious"
                elif choice.startswith("a"):
                    engine.state.ci_stance = "aggressive"
                elif choice.startswith("b"):
                    engine.state.ci_stance = "balanced"
                history[-1] = engine.state.snapshot()
        result = engine.build_result(history)
    cli = CampaignDashboardCLI(width=args.width)
    print(cli.render(result))


if __name__ == "__main__":
    main()

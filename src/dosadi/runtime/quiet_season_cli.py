"""Simple CLI harness for the Quiet Season scenario."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..interfaces.campaign_dashboard import CampaignDashboardCLI
from .ai_profiles import AiPersonality, Stance, get_ai_personality
from .campaign_engine import CampaignEngine, load_scenario_definition


def ai_choose_ci_stance(
    personality: AiPersonality,
    stress: float,
    infiltration_risk: float,
    legitimacy: float,
) -> Stance:
    """Pick a CI stance based on current stress and perceived risks."""

    legitimacy_decent = legitimacy >= 0.5
    low_risk_tolerance = personality.risk_tolerance < 0.4
    high_infiltration = infiltration_risk >= 0.55
    high_legitimacy_weight = personality.weight_legitimacy >= 0.65

    if stress < personality.crackdown_threshold and legitimacy_decent:
        return "cautious" if low_risk_tolerance else "balanced"

    if stress >= personality.crackdown_threshold and high_infiltration:
        if high_legitimacy_weight:
            return "balanced"
        if personality.paranoia >= 0.55 or personality.weight_control >= 0.65:
            return "aggressive"
    return "balanced"


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
        "--ai-esp-personality",
        type=str,
        help="Use the given AI personality id to drive Espionage CI stance decisions",
    )
    parser.add_argument(
        "--ai-duke-personality",
        type=str,
        help="Use the given AI personality id to drive ducal campaign decisions",
    )
    parser.add_argument(
        "--ci-prompt-interval",
        type=int,
        default=4,
        help="How often (in ticks) to prompt for CI stance when interactive",
    )
    args = parser.parse_args()

    scenario = load_scenario_definition(args.scenario)
    duke_ai: AiPersonality | None = None
    if args.ai_duke_personality:
        try:
            duke_ai = get_ai_personality(args.ai_duke_personality)
        except KeyError as exc:
            parser.error(str(exc))

    engine = CampaignEngine(scenario, ai_duke_personality=duke_ai)
    history = [engine.state.snapshot()]

    ai_personality: AiPersonality | None = None
    if args.ai_esp_personality:
        try:
            ai_personality = get_ai_personality(args.ai_esp_personality)
        except KeyError as exc:
            parser.error(str(exc))

    if not args.interactive_ci and not ai_personality:
        result = engine.run(args.ticks)
    else:
        prompt_interval = max(1, args.ci_prompt_interval)
        for _ in range(args.ticks):
            history.append(engine.step())
            if engine.state.tick % prompt_interval == 0:
                if ai_personality:
                    stress = engine.state.global_stress_index
                    infiltration_avg = (
                        sum(state.infiltration_risk for state in engine.state.ci_states) / len(engine.state.ci_states)
                        if engine.state.ci_states
                        else 0.0
                    )
                    legitimacy = engine.state.regime_legitimacy_index
                    new_stance = ai_choose_ci_stance(
                        ai_personality,
                        stress=stress,
                        infiltration_risk=infiltration_avg,
                        legitimacy=legitimacy,
                    )
                    if new_stance != engine.state.ci_stance:
                        engine.state.ci_stance = new_stance
                        print(
                            f"[Tick {engine.state.tick}] Espionage AI ({ai_personality.id}) sets CI stance to {new_stance}"
                        )
                        history[-1] = engine.state.snapshot()
                elif args.interactive_ci:
                    print(f"\n[Tick {engine.state.tick}] Current CI stance: {engine.state.ci_stance}")
                    choice = input(
                        "CI stance? [c]autious / [b]alanced / [a]ggressive (ENTER = keep current): "
                    ).strip().lower()
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

"""Convenience runner for the Wakeup Prime scenario.

Usage (from repository root):
    python run_founding_wakeup_mvp.py

You can override defaults, for example:
    python run_founding_wakeup_mvp.py --max-ticks 8000 --seed 42 --num-agents 24

The script runs the `wakeup_prime` scenario and prints a compact summary plus
sample agent place beliefs and recent episodes so you can visually sanity-check
memory generation.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import List, Sequence


REPO_ROOT = Path(__file__).resolve().parent
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from dosadi.playbook.scenario_runner import run_scenario
from dosadi.scenarios.wakeup_prime import WakeupPrimeReport


def _sample_agents(agents: Sequence, sample_size: int, seed: int) -> List:
    pool = list(agents)
    if not pool:
        return []

    rng = random.Random(seed)
    if len(pool) <= sample_size:
        return pool

    return rng.sample(pool, sample_size)


def _format_place_belief(pb) -> str:
    return (
        f"{pb.place_id}: danger={pb.danger_score:.2f} safety={pb.safety_score:.2f} "
        f"congestion={pb.congestion_score:.2f} efficiency={pb.efficiency_score:.2f} "
        f"last_tick={pb.last_updated_tick}"
    )


def _print_agent_beliefs(agent, max_places: int = 3) -> None:
    beliefs = list(getattr(agent, "place_beliefs", {}).values())
    if not beliefs:
        print("  Place beliefs: none yet")
        return

    beliefs.sort(key=lambda pb: getattr(pb, "last_updated_tick", 0), reverse=True)
    shown = beliefs[:max_places]
    print(f"  Place beliefs (showing {len(shown)} of {len(beliefs)}):")
    for pb in shown:
        print(f"    - {_format_place_belief(pb)}")


def _print_agent_episodes(agent, max_eps: int = 4) -> None:
    eps = list(getattr(agent, "episodes", None).short_term) if getattr(agent, "episodes", None) else []
    if not eps:
        print("  Recent episodes: none yet")
        return

    eps.sort(key=lambda ep: getattr(ep, "tick", 0), reverse=True)
    shown = eps[:max_eps]
    print(f"  Recent episodes (short-term; showing {len(shown)} of {len(eps)}):")
    for ep in shown:
        location = getattr(ep, "location_id", None) or "n/a"
        print(
            f"    - tick {getattr(ep, 'tick', 0)} @ {location}: "
            f"{getattr(ep, 'verb', 'UNKNOWN')} (importance={getattr(ep, 'importance', 0.0):.2f}, "
            f"relevance={getattr(ep, 'goal_relevance', 0.0):.2f})"
        )


def print_report(report: WakeupPrimeReport, sample_size: int, seed: int) -> None:
    world = report.world
    print("\n=== Wakeup Prime run complete ===")
    print(f"Ticks simulated: {report.summary.get('ticks', world.tick)}")
    print(f"Agents: {report.summary.get('agents', len(world.agents))}")
    print(f"Queues: {report.summary.get('queues', len(world.queues))}")

    sample = _sample_agents(tuple(world.agents.values()), sample_size, seed)
    if not sample:
        print("\nNo agents to sample.")
        return

    print(f"\nSampled agent beliefs and episodes (n={len(sample)}):")
    for agent in sample:
        print(f"- {agent.name} ({agent.agent_id}) at {agent.location_id}")
        _print_agent_beliefs(agent)
        _print_agent_episodes(agent)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-agents", type=int, default=50, help="Number of colonist agents")
    parser.add_argument("--max-ticks", type=int, default=6_000, help="Maximum ticks to simulate")
    parser.add_argument("--seed", type=int, default=1337, help="Random seed for reproducibility")
    parser.add_argument(
        "--sample-agents",
        type=int,
        default=5,
        help="How many agents to sample for belief/episode inspection",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    overrides = {"num_agents": args.num_agents, "max_ticks": args.max_ticks, "seed": args.seed}
    report = run_scenario("wakeup_prime", overrides=overrides)
    if not isinstance(report, WakeupPrimeReport):
        raise SystemExit("Expected a WakeupPrimeReport; check scenario wiring.")
    print_report(report, sample_size=args.sample_agents, seed=args.seed)


if __name__ == "__main__":
    main()

"""Convenience runner for the Founding Wakeup MVP scenario.

Usage (from repository root):
    python run_founding_wakeup_mvp.py

You can override defaults, for example:
    python run_founding_wakeup_mvp.py --max-ticks 8000 --seed 42 --num-agents 24

The script runs the `founding_wakeup_mvp` scenario and prints a compact summary
plus scenario milestone checks so you can see whether pod reps, the proto
council, and protocol adoption are emerging.
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
from dosadi.runtime.founding_wakeup import FoundingWakeupReport
from dosadi.agents.groups import GroupType
from dosadi.systems.protocols import ProtocolStatus


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


def _print_success(success: dict) -> None:
    if not success:
        print("No success metrics available.")
        return

    print("\nScenario success checks:")
    for key, passed in success.items():
        status = "OK" if passed else "MISSING"
        print(f"- {key}: {status}")


def _print_council_members(world) -> None:
    council = next((g for g in getattr(world, "groups", []) if g.group_type == GroupType.COUNCIL), None)
    if council is None:
        print("\nProto-council members: not yet formed.")
        return

    print("\nProto-council members:")
    for member_id in council.member_ids:
        agent = world.agents.get(member_id)
        name = getattr(agent, "name", member_id)
        location = getattr(agent, "location_id", "n/a") if agent else "n/a"
        roles = council.roles_by_agent.get(member_id, [])
        roles_str = ", ".join(str(role) for role in roles) if roles else "none"
        print(f"- {name} ({member_id}) at {location} roles={roles_str}")


def _print_protocols(world) -> None:
    registry = getattr(world, "protocols", None)
    if registry is None or not getattr(registry, "protocols_by_id", {}):
        print("\nProtocols authored: none yet.")
        return

    protocols = sorted(registry.protocols_by_id.values(), key=lambda p: getattr(p, "created_at_tick", 0))
    print("\nProtocols authored:")
    for protocol in protocols:
        author_agent = world.agents.get(protocol.author_agent_id) if protocol.author_agent_id else None
        author_name = getattr(author_agent, "name", None) if author_agent else None
        author_label = protocol.author_agent_id or "unknown"
        if author_name:
            author_label = f"{author_name} ({protocol.author_agent_id})"

        status_label = protocol.status
        if protocol.status == ProtocolStatus.ACTIVE and protocol.activated_at_tick is not None:
            status_label = f"{status_label} @ tick {protocol.activated_at_tick}"

        coverage_bits = []
        if protocol.covered_location_ids:
            coverage_bits.append("locations=" + ", ".join(protocol.covered_location_ids))
        if protocol.covered_edge_ids:
            coverage_bits.append("edges=" + ", ".join(protocol.covered_edge_ids))
        coverage = "; ".join(coverage_bits) if coverage_bits else "none specified"

        print(f"- {protocol.name} ({protocol.protocol_id})")
        print(
            f"  Authored tick {protocol.created_at_tick} by {author_label}; "
            f"group={protocol.author_group_id or 'n/a'}; status={status_label}"
        )
        print(f"  Field: {protocol.protocol_type}; coverage: {coverage}")
        print(f"  Content: {protocol.description}")


def print_report(report: FoundingWakeupReport, sample_size: int, seed: int) -> None:
    world = report.world
    print("\n=== Founding Wakeup MVP run complete ===")
    print(f"Ticks simulated: {report.summary.get('ticks', world.tick)}")
    print(f"Agents: {report.summary.get('agents', len(world.agents))}")
    print(f"Groups: {report.summary.get('groups', len(world.groups))}")
    print(f"Protocols: {report.summary.get('protocols', len(getattr(world, 'protocols', {}).protocols_by_id))}")

    _print_success(getattr(report, "success", {}))

    sample = _sample_agents(tuple(world.agents.values()), sample_size, seed)
    if not sample:
        print("\nNo agents to sample.")
        return

    print(f"\nSampled agent beliefs and episodes (n={len(sample)}):")
    for agent in sample:
        print(f"- {agent.name} ({agent.agent_id}) at {agent.location_id}")
        _print_agent_beliefs(agent)
        _print_agent_episodes(agent)

    _print_council_members(world)
    _print_protocols(world)


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
    report = run_scenario("founding_wakeup_mvp", overrides=overrides)
    if not isinstance(report, FoundingWakeupReport):
        raise SystemExit("Expected a FoundingWakeupReport; check scenario wiring.")
    print_report(report, sample_size=args.sample_agents, seed=args.seed)


if __name__ == "__main__":
    main()

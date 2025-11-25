"""Convenience runner for the Founding Wakeup MVP scenario.

Usage (from repository root):
    python run_founding_wakeup_mvp.py

You can override defaults, for example:
    python run_founding_wakeup_mvp.py --max-ticks 20000 --seed 42 --num-agents 16

The script runs the `founding_wakeup_mvp` scenario and prints a small
post-run inspection covering:
- Protocol authoring/activation ticks and covered corridors.
- Hazard incident rates on covered corridors before vs. after activation.
- A quick snapshot of the highest-risk edges from aggregate metrics.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parent
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from dosadi.playbook.scenario_runner import run_scenario
from dosadi.runtime.founding_wakeup import FoundingWakeupReport
from dosadi.systems.protocols import Protocol


@dataclass
class CorridorRates:
    corridor_id: str
    activation_tick: Optional[int]
    movements_before: int
    incidents_before: int
    rate_before: Optional[float]
    movements_after: int
    incidents_after: int
    rate_after: Optional[float]


@dataclass
class ProtocolInspection:
    protocol: Protocol
    covered_rates: List[CorridorRates]


def _collect_episode_counts(
    *,
    agents: Iterable,
    corridor_id: str,
    activation_tick: Optional[int],
) -> CorridorRates:
    before = {"moves": 0, "incidents": 0}
    after = {"moves": 0, "incidents": 0}

    for agent in agents:
        for ep in getattr(agent, "episodes", ()):  # Episodes are list-like
            if ep.location_id != corridor_id:
                continue
            if activation_tick is None or ep.tick_end < activation_tick:
                bucket = before
            else:
                bucket = after

            if ep.event_type == "MOVEMENT":
                bucket["moves"] += 1
            elif ep.event_type == "HAZARD_INCIDENT":
                bucket["incidents"] += 1

    def _rate(counts: Dict[str, int]) -> Optional[float]:
        if counts["moves"] == 0:
            return None
        return counts["incidents"] / counts["moves"]

    return CorridorRates(
        corridor_id=corridor_id,
        activation_tick=activation_tick,
        movements_before=before["moves"],
        incidents_before=before["incidents"],
        rate_before=_rate(before),
        movements_after=after["moves"],
        incidents_after=after["incidents"],
        rate_after=_rate(after),
    )


def inspect_protocols(report: FoundingWakeupReport) -> List[ProtocolInspection]:
    world = report.world
    registry = getattr(world, "protocols", None)
    if registry is None or not getattr(registry, "protocols_by_id", {}):
        return []

    inspections: List[ProtocolInspection] = []
    for protocol in registry.protocols_by_id.values():
        rates = []
        activation_tick = protocol.activated_at_tick or protocol.created_at_tick
        for corridor_id in protocol.covered_location_ids:
            rates.append(
                _collect_episode_counts(
                    agents=world.agents.values(),
                    corridor_id=corridor_id,
                    activation_tick=activation_tick,
                )
            )
        inspections.append(ProtocolInspection(protocol=protocol, covered_rates=rates))

    inspections.sort(
        key=lambda insp: insp.protocol.activated_at_tick
        if insp.protocol.activated_at_tick is not None
        else insp.protocol.created_at_tick
    )
    return inspections


def _edge_incident_rates(metrics: Dict[str, float], top_n: int = 5) -> List[Tuple[float, str, float, float]]:
    rates: List[Tuple[float, str, float, float]] = []
    for key, traversals in metrics.items():
        if not key.startswith("traversals:"):
            continue
        edge_id = key.split(":", 1)[1]
        incidents = metrics.get(f"incidents:{edge_id}", 0.0)
        rate = incidents / traversals if traversals else 0.0
        rates.append((rate, edge_id, traversals, incidents))

    rates.sort(key=lambda item: item[0], reverse=True)
    return rates[:top_n]


def print_report(report: FoundingWakeupReport, top_edges: int) -> None:
    world = report.world
    print("\n=== Founding Wakeup MVP run complete ===")
    print(f"Ticks simulated: {report.summary.get('ticks', world.tick)}")
    print(f"Agents: {report.summary.get('agents', len(world.agents))}")
    print(f"Protocols authored: {report.summary.get('protocols', 0)}")

    node_names = {
        node_id: getattr(node, "name", node_id) for node_id, node in world.nodes.items()
    }

    inspections = inspect_protocols(report)
    if not inspections:
        print("\nNo protocols were authored during this run.")
    else:
        print("\nProtocol timeline and corridor hazard rates:")
        for insp in inspections:
            p = insp.protocol
            corridors = ", ".join(node_names.get(cid, cid) for cid in p.covered_location_ids)
            print(
                f"- {p.name} (ID: {p.protocol_id}) covering {corridors} | "
                f"created tick {p.created_at_tick}, activated tick {p.activated_at_tick}"
            )
            for rate in insp.covered_rates:
                before_msg = (
                    f"{rate.incidents_before}/{rate.movements_before} incidents"
                    f" ({rate.rate_before:.3f} rate)" if rate.rate_before is not None else "no movement"
                )
                after_msg = (
                    f"{rate.incidents_after}/{rate.movements_after} incidents"
                    f" ({rate.rate_after:.3f} rate)" if rate.rate_after is not None else "no post-activation movement"
                )
                print(
                    f"    · {node_names.get(rate.corridor_id, rate.corridor_id)}: "
                    f"before {before_msg}; after {after_msg}"
                )

    edge_rates = _edge_incident_rates(report.metrics, top_edges)
    if edge_rates:
        print("\nTop corridor edges by incident rate (final metrics):")
        for rate, edge_id, traversals, incidents in edge_rates:
            print(
                f"- {edge_id}: {incidents:.0f}/{traversals:.0f} incidents"
                f" (rate {rate:.3f})"
            )
    else:
        print("\nNo movement metrics recorded.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-agents", type=int, default=12, help="Number of colonist agents")
    parser.add_argument("--max-ticks", type=int, default=10_000, help="Maximum ticks to simulate")
    parser.add_argument("--seed", type=int, default=1337, help="Random seed for reproducibility")
    parser.add_argument(
        "--top-edges",
        type=int,
        default=5,
        help="How many high-risk edges to display from aggregate metrics",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    overrides = {"num_agents": args.num_agents, "max_ticks": args.max_ticks, "seed": args.seed}
    report = run_scenario("founding_wakeup_mvp", overrides=overrides)
    if not isinstance(report, FoundingWakeupReport):
        raise SystemExit("Expected a FoundingWakeupReport; check scenario wiring.")
    print_report(report, top_edges=args.top_edges)


if __name__ == "__main__":
    main()

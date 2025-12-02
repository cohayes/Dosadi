from __future__ import annotations

from collections import defaultdict
from typing import Dict, Optional
from dosadi.memory.facility_summary import FacilityBeliefSummary
from dosadi.state import WorldState


def _normalize_belief_score(value: float) -> float:
    """Map belief scores in [-1, 1] to [0, 1] with clamping."""

    return max(0.0, min(1.0, 0.5 * (value + 1.0)))


def _resolve_facility_id(
    *,
    place_id: str,
    world: WorldState,
    queue_location_to_facility: Dict[str, Optional[str]],
) -> Optional[str]:
    """Return the facility_id that corresponds to a given place_id, if any."""

    if place_id in queue_location_to_facility:
        return queue_location_to_facility[place_id]

    facilities = getattr(world, "facilities", {}) or {}
    if place_id in facilities:
        return place_id

    node = getattr(world, "nodes", {}).get(place_id)
    if node is not None and getattr(node, "kind", None) == "facility":
        return place_id

    for facilities in getattr(world, "service_facilities", {}).values():
        if place_id in facilities:
            return place_id

    if place_id in getattr(world, "policy", {}).get("facilities", {}):
        return place_id

    return None


def recompute_facility_belief_summaries(world: WorldState) -> None:
    """
    Aggregate per-agent PlaceBeliefs into world.facility_belief_summaries.

    MVP: average the normalized scores across all agents who have a belief for
    a place that corresponds to a facility_id.
    """

    totals: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    counts: Dict[str, int] = defaultdict(int)

    agents = world.agents.values() if hasattr(world, "agents") else []

    queue_location_to_facility: Dict[str, Optional[str]] = {}
    if hasattr(world, "queues"):
        for queue in world.queues.values():
            if queue.location_id:
                queue_location_to_facility[queue.location_id] = queue.associated_facility

    for agent in agents:
        place_beliefs = getattr(agent, "place_beliefs", {}) or {}
        for place_id, pb in place_beliefs.items():
            fac_id = _resolve_facility_id(
                place_id=place_id,
                world=world,
                queue_location_to_facility=queue_location_to_facility,
            )
            if fac_id is None:
                continue

            totals[fac_id]["safety"] += _normalize_belief_score(pb.safety_score)
            comfort_value = getattr(pb, "comfort_score", None)
            if comfort_value is None:
                comfort_value = getattr(pb, "reliability_score", 0.0)
            totals[fac_id]["comfort"] += _normalize_belief_score(comfort_value)
            totals[fac_id]["fairness"] += _normalize_belief_score(pb.fairness_score)
            totals[fac_id]["queue"] += _normalize_belief_score(pb.congestion_score)
            counts[fac_id] += 1

    summaries: Dict[str, FacilityBeliefSummary] = {}

    for fac_id, c in counts.items():
        if c <= 0:
            continue

        s = FacilityBeliefSummary(
            facility_id=fac_id,
            safety_score=totals[fac_id]["safety"] / c,
            comfort_score=totals[fac_id]["comfort"] / c,
            fairness_score=totals[fac_id]["fairness"] / c,
            queue_pressure=max(0.0, min(1.0, totals[fac_id]["queue"] / c)),
            incident_rate=0.0,  # Placeholder until facility incident metrics are wired
            contributors=c,
        )
        summaries[fac_id] = s

    world.facility_belief_summaries = summaries

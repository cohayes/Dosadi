from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple, TYPE_CHECKING

from dosadi.agents.core import AgentState, PlaceBelief
from dosadi.runtime.work_details import WorkDetailType

if TYPE_CHECKING:
    from dosadi.state import WorldState


COUNCIL_UPDATE_INTERVAL_TICKS = 5_000


@dataclass
class CouncilMetrics:
    last_update_tick: int = 0

    # Mean scores (0–1)
    corridor_congestion_index: float = 0.0
    stores_reliability_index: float = 0.0
    food_hall_reliability_index: float = 0.0

    # Simple counts (for debugging / dashboards)
    corridor_count: int = 0
    store_count: int = 0
    food_hall_count: int = 0


@dataclass
class CouncilStaffingConfig:
    # Target ranges for metrics
    target_corridor_congestion_low: float = 0.30
    target_corridor_congestion_high: float = 0.60

    target_store_reliability_low: float = 0.40
    target_store_reliability_high: float = 0.75

    target_food_reliability_low: float = 0.45
    target_food_reliability_high: float = 0.85

    # Step sizes for changing desired staffing
    scout_adjust_step: int = 1
    inventory_adjust_step: int = 1
    food_adjust_step: int = 1

    # Min/max caps (safety rails)
    min_scouts: int = 0
    max_scouts: int = 32

    min_inventory: int = 0
    max_inventory: int = 32

    min_food_processing: int = 0
    max_food_processing: int = 32


def iter_council_place_beliefs(world: "WorldState") -> Iterable[Tuple[str, PlaceBelief]]:
    """
    Return the set of place beliefs council should treat as its input.

    MVP implementation:
    - If a world-level aggregated index exists (e.g. world.place_belief_index),
      yield from that.
    - Otherwise, aggregate over agents' place_beliefs by averaging their scores
      per place_id.
    """
    index = getattr(world, "place_belief_index", None)
    if index is not None:
        for place_id, pb in index.items():
            yield place_id, pb
        return

    accum: Dict[str, PlaceBelief] = {}
    counts: Dict[str, int] = defaultdict(int)

    agents = getattr(world, "agents", {})
    if isinstance(agents, dict):
        agent_iterable = agents.values()
    else:
        agent_iterable = list(agents)  # type: ignore[assignment]

    for agent in agent_iterable:
        if not isinstance(agent, AgentState):
            continue
        for place_id, pb in getattr(agent, "place_beliefs", {}).items():
            if place_id not in accum:
                accum[place_id] = PlaceBelief(
                    owner_id="council",
                    place_id=place_id,
                    safety_score=pb.safety_score,
                    comfort_score=pb.comfort_score,
                    fairness_score=pb.fairness_score,
                    congestion_score=pb.congestion_score,
                    reliability_score=pb.reliability_score,
                    efficiency_score=pb.efficiency_score,
                    danger_score=pb.danger_score,
                    enforcement_score=pb.enforcement_score,
                    opportunity_score=pb.opportunity_score,
                )
                counts[place_id] = 1
            else:
                a = accum[place_id]
                a.safety_score += pb.safety_score
                a.comfort_score += pb.comfort_score
                a.fairness_score += pb.fairness_score
                a.congestion_score += pb.congestion_score
                a.reliability_score += pb.reliability_score
                a.efficiency_score += pb.efficiency_score
                a.danger_score += pb.danger_score
                a.enforcement_score += pb.enforcement_score
                a.opportunity_score += pb.opportunity_score
                counts[place_id] += 1

    for place_id, pb in accum.items():
        c = counts[place_id]
        if c <= 0:
            continue
        pb.safety_score /= c
        pb.comfort_score /= c
        pb.fairness_score /= c
        pb.congestion_score /= c
        pb.reliability_score /= c
        pb.efficiency_score /= c
        pb.danger_score /= c
        pb.enforcement_score /= c
        pb.opportunity_score /= c
        yield place_id, pb


def is_corridor(world: "WorldState", place_id: str) -> bool:
    """
    MVP: determine if place_id should be treated as an interior corridor/junction.
    Prefer facility metadata; fall back to simple naming conventions if needed.
    """
    place = None
    if hasattr(world, "places"):
        place = getattr(world, "places").get(place_id)  # type: ignore[assignment]
    if place is not None:
        kind = getattr(place, "kind", None) or getattr(place, "category", None)
        if kind in {"corridor", "junction", "interior_corridor"}:
            return True

    return place_id.startswith("loc:corridor") or place_id.startswith("corridor:")


def is_store(world: "WorldState", place_id: str) -> bool:
    """
    MVP: determine if place_id should be treated as a store/depot.
    """
    place = None
    if hasattr(world, "places"):
        place = getattr(world, "places").get(place_id)  # type: ignore[assignment]
    if place is not None:
        kind = getattr(place, "kind", None) or getattr(place, "category", None)
        if kind in {"store", "depot", "inventory"}:
            return True

    return place_id.startswith("loc:store") or place_id.startswith("store:")


def update_council_metrics_and_staffing(world: "WorldState") -> None:
    """
    Periodically recompute council metrics from place beliefs and adjust desired
    staffing for key work details.
    """
    metrics = getattr(world, "council_metrics", None)
    if metrics is None:
        return

    current_tick = getattr(world, "tick", 0)
    if current_tick - metrics.last_update_tick < COUNCIL_UPDATE_INTERVAL_TICKS:
        return
    metrics.last_update_tick = current_tick

    corridor_scores: list[float] = []
    store_scores: list[float] = []
    food_scores: list[float] = []

    for place_id, pb in iter_council_place_beliefs(world):
        if is_corridor(world, place_id):
            corridor_scores.append(pb.congestion_score)
        if is_store(world, place_id):
            store_scores.append(pb.reliability_score)
        place = None
        if hasattr(world, "places"):
            place = getattr(world, "places").get(place_id)  # type: ignore[assignment]
        if place is None:
            place = getattr(world, "facilities", {}).get(place_id)
        kind = getattr(place, "kind", None) if place is not None else None
        if kind == "mess_hall":
            food_scores.append(pb.reliability_score)

    if corridor_scores:
        metrics.corridor_congestion_index = sum(corridor_scores) / len(corridor_scores)
        metrics.corridor_count = len(corridor_scores)
    else:
        metrics.corridor_congestion_index = 0.0
        metrics.corridor_count = 0

    if store_scores:
        metrics.stores_reliability_index = sum(store_scores) / len(store_scores)
        metrics.store_count = len(store_scores)
    else:
        metrics.stores_reliability_index = 1.0
        metrics.store_count = 0

    if food_scores:
        metrics.food_hall_reliability_index = sum(food_scores) / len(food_scores)
        metrics.food_hall_count = len(food_scores)
    else:
        metrics.food_hall_reliability_index = 1.0
        metrics.food_hall_count = 0

    _adjust_staffing_from_metrics(world)


def _adjust_staffing_from_metrics(world: "WorldState") -> None:
    cfg = getattr(world, "council_staffing_config", None)
    desired = getattr(world, "desired_work_details", None)
    if cfg is None or desired is None:
        return

    desired.setdefault(WorkDetailType.SCOUT_INTERIOR, 0)
    desired.setdefault(WorkDetailType.INVENTORY_STORES, 0)
    desired.setdefault(WorkDetailType.FOOD_PROCESSING_DETAIL, 0)

    cc = world.council_metrics.corridor_congestion_index
    if cc > cfg.target_corridor_congestion_high:
        desired[WorkDetailType.SCOUT_INTERIOR] += cfg.scout_adjust_step
    elif cc < cfg.target_corridor_congestion_low:
        desired[WorkDetailType.SCOUT_INTERIOR] -= cfg.scout_adjust_step

    sr = world.council_metrics.stores_reliability_index
    if sr < cfg.target_store_reliability_low:
        desired[WorkDetailType.INVENTORY_STORES] += cfg.inventory_adjust_step
    elif sr > cfg.target_store_reliability_high:
        desired[WorkDetailType.INVENTORY_STORES] -= cfg.inventory_adjust_step

    fr = world.council_metrics.food_hall_reliability_index
    if fr < cfg.target_food_reliability_low:
        desired[WorkDetailType.FOOD_PROCESSING_DETAIL] += cfg.food_adjust_step
    elif fr > cfg.target_food_reliability_high:
        desired[WorkDetailType.FOOD_PROCESSING_DETAIL] -= cfg.food_adjust_step

    desired[WorkDetailType.SCOUT_INTERIOR] = max(
        cfg.min_scouts,
        min(desired[WorkDetailType.SCOUT_INTERIOR], cfg.max_scouts),
    )
    desired[WorkDetailType.INVENTORY_STORES] = max(
        cfg.min_inventory,
        min(desired[WorkDetailType.INVENTORY_STORES], cfg.max_inventory),
    )
    desired[WorkDetailType.FOOD_PROCESSING_DETAIL] = max(
        cfg.min_food_processing,
        min(desired[WorkDetailType.FOOD_PROCESSING_DETAIL], cfg.max_food_processing),
    )

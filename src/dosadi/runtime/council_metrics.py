from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple, TYPE_CHECKING

from dosadi.agents.core import AgentState, PlaceBelief
from dosadi.memory.episode_factory import EpisodeFactory
from dosadi.runtime.config import (
    MAX_SUPERVISORS_PER_WORK_TYPE,
    MIN_PROFICIENCY_FOR_SUPERVISOR,
    MIN_SHIFTS_FOR_SUPERVISOR,
    MIN_TICKS_BEFORE_PROMOTION,
    PROMOTION_CHECK_INTERVAL_TICKS,
    SENIORITY_HORIZON,
)
from dosadi.runtime.work_details import WorkDetailType

if TYPE_CHECKING:
    from dosadi.state import WorldState
    from dosadi.agents.work_history import WorkHistory  # type: ignore


COUNCIL_UPDATE_INTERVAL_TICKS = 5_000


@dataclass
class CouncilMetrics:
    last_update_tick: int = 0

    # Mean scores (0–1)
    corridor_congestion_index: float = 0.0
    stores_reliability_index: float = 0.0
    food_hall_reliability_index: float = 0.0
    interior_comfort_index: float = 0.0
    water_depot_fill_index: float = 0.0

    # Simple counts (for debugging / dashboards)
    corridor_count: int = 0
    store_count: int = 0
    food_hall_count: int = 0
    interior_place_count: int = 0
    water_depot_count: int = 0


@dataclass
class CouncilStaffingConfig:
    # Target ranges for metrics
    target_corridor_congestion_low: float = 0.30
    target_corridor_congestion_high: float = 0.60

    target_store_reliability_low: float = 0.40
    target_store_reliability_high: float = 0.75

    target_food_reliability_low: float = 0.45
    target_food_reliability_high: float = 0.85

    target_interior_comfort_low: float = 0.45
    target_interior_comfort_high: float = 0.70

    target_water_fill_low: float = 0.40
    target_water_fill_high: float = 0.80

    # Step sizes for changing desired staffing
    scout_adjust_step: int = 1
    inventory_adjust_step: int = 1
    food_adjust_step: int = 1
    env_control_adjust_step: int = 1
    water_handling_adjust_step: int = 1

    # Min/max caps (safety rails)
    min_scouts: int = 0
    max_scouts: int = 32

    min_inventory: int = 0
    max_inventory: int = 32

    min_food_processing: int = 0
    max_food_processing: int = 32

    min_env_control: int = 0
    max_env_control: int = 32

    min_water_handling: int = 0
    max_water_handling: int = 32


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


def is_interior_place(world: "WorldState", place_id: str) -> bool:
    place = None
    if hasattr(world, "places"):
        place = getattr(world, "places").get(place_id)  # type: ignore[assignment]
    if place is None:
        place = getattr(world, "facilities", {}).get(place_id)

    kind = getattr(place, "kind", None) or getattr(place, "type", None)
    if kind in {"pod", "bunk_pod", "corridor", "junction", "mess_hall", "store", "depot"}:
        return True

    return place_id.startswith("loc:")


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
    comfort_scores: list[float] = []
    water_fill: list[float] = []

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
        if is_interior_place(world, place_id):
            comfort_scores.append(pb.comfort_score)
        if kind == "water_depot":
            facility = getattr(world, "facilities", {}).get(place_id)
            if facility and getattr(facility, "water_capacity", 0.0) > 0:
                fill_ratio = getattr(facility, "water_stock", 0.0) / float(getattr(facility, "water_capacity", 1.0))
                fill_ratio = max(0.0, min(1.0, fill_ratio))
                water_fill.append(fill_ratio)

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

    if comfort_scores:
        metrics.interior_comfort_index = sum(comfort_scores) / len(comfort_scores)
        metrics.interior_place_count = len(comfort_scores)
    else:
        metrics.interior_comfort_index = 0.5
        metrics.interior_place_count = 0

    if water_fill:
        metrics.water_depot_fill_index = sum(water_fill) / len(water_fill)
        metrics.water_depot_count = len(water_fill)
    else:
        metrics.water_depot_fill_index = 1.0
        metrics.water_depot_count = 0

    _adjust_staffing_from_metrics(world)
    assign_work_crews(world, getattr(world, "desired_work_details", {}))
    maybe_run_promotion_cycle(world)


def _adjust_staffing_from_metrics(world: "WorldState") -> None:
    cfg = getattr(world, "council_staffing_config", None)
    desired = getattr(world, "desired_work_details", None)
    if cfg is None or desired is None:
        return

    desired.setdefault(WorkDetailType.SCOUT_INTERIOR, 0)
    desired.setdefault(WorkDetailType.INVENTORY_STORES, 0)
    desired.setdefault(WorkDetailType.FOOD_PROCESSING_DETAIL, 0)
    desired.setdefault(WorkDetailType.ENV_CONTROL, 0)
    desired.setdefault(WorkDetailType.WATER_HANDLING, 0)

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

    ic = world.council_metrics.interior_comfort_index
    if ic < cfg.target_interior_comfort_low:
        desired[WorkDetailType.ENV_CONTROL] += cfg.env_control_adjust_step
    elif ic > cfg.target_interior_comfort_high:
        desired[WorkDetailType.ENV_CONTROL] -= cfg.env_control_adjust_step

    wf = world.council_metrics.water_depot_fill_index
    if wf < cfg.target_water_fill_low:
        desired[WorkDetailType.WATER_HANDLING] += cfg.water_handling_adjust_step
    elif wf > cfg.target_water_fill_high:
        desired[WorkDetailType.WATER_HANDLING] -= cfg.water_handling_adjust_step

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
    desired[WorkDetailType.ENV_CONTROL] = max(
        cfg.min_env_control,
        min(desired[WorkDetailType.ENV_CONTROL], cfg.max_env_control),
    )
    desired[WorkDetailType.WATER_HANDLING] = max(
        cfg.min_water_handling,
        min(desired[WorkDetailType.WATER_HANDLING], cfg.max_water_handling),
    )


def _ensure_default_crew_for_type(world: "WorldState", work_type: WorkDetailType) -> str:
    prefix = f"crew:{work_type.name.lower()}"
    for crew_id, crew in world.crews.items():
        if crew.work_type == work_type and crew_id.startswith(prefix):
            return crew_id

    from dosadi.state import CrewState

    crew_id = f"{prefix}:0"
    world.crews[crew_id] = CrewState(
        crew_id=crew_id,
        work_type=work_type,
        member_ids=[],
    )
    return crew_id


def assign_work_crews(
    world: "WorldState",
    desired_counts: Dict[WorkDetailType, int],
) -> None:
    agents: List[AgentState] = list(world.agents.values())

    for work_type, target_count in desired_counts.items():
        if target_count <= 0:
            crew_id = _ensure_default_crew_for_type(world, work_type)
            crew = world.crews[crew_id]
            removed_members: Set[str] = set(crew.member_ids)
            crew.member_ids = []
            for agent_id in removed_members:
                other = world.agents.get(agent_id)
                if other is not None and other.current_crew_id == crew_id:
                    other.current_crew_id = None
            continue

        scored: List[Tuple[float, AgentState]] = []

        for agent in agents:
            if agent.physical.is_sleeping:
                continue

            wh = agent.work_history.get_or_create(work_type)
            prof = wh.proficiency
            stress = agent.physical.stress_level
            morale = agent.physical.morale_level

            sup_bonus = 0.0
            if agent.supervisor_work_type == work_type:
                sup_bonus = 0.1

            score = 0.6 * prof + 0.2 * morale - 0.2 * stress + sup_bonus
            scored.append((score, agent))

        scored.sort(key=lambda pair: pair[0], reverse=True)

        selected_agents = [a for (_s, a) in scored[:target_count]]

        crew_id = _ensure_default_crew_for_type(world, work_type)
        crew = world.crews[crew_id]
        previous_members: Set[str] = set(crew.member_ids)
        crew.member_ids = [a.id for a in selected_agents]

        for agent in selected_agents:
            agent.current_crew_id = crew_id

        removed_members = previous_members.difference(crew.member_ids)
        for agent_id in removed_members:
            other = world.agents.get(agent_id)
            if other is not None and other.current_crew_id == crew_id:
                other.current_crew_id = None


def maybe_run_promotion_cycle(world: "WorldState") -> None:
    current_tick = getattr(world, "tick", getattr(world, "current_tick", 0))
    last_check = getattr(world, "last_promotion_check_tick", 0)
    if current_tick - last_check < PROMOTION_CHECK_INTERVAL_TICKS:
        return
    world.last_promotion_check_tick = current_tick
    _run_promotion_cycle(world)


def _is_eligible_supervisor_candidate(agent: AgentState, work_type: WorkDetailType) -> bool:
    if agent.tier != 1:
        return False
    if agent.supervisor_work_type is not None:
        return False
    if agent.total_ticks_employed < MIN_TICKS_BEFORE_PROMOTION:
        return False

    wh = agent.work_history.get_or_create(work_type)
    if wh.proficiency < MIN_PROFICIENCY_FOR_SUPERVISOR:
        return False
    if wh.shifts < MIN_SHIFTS_FOR_SUPERVISOR:
        return False

    if agent.physical.stress_level > 0.7:
        return False
    if agent.physical.morale_level < 0.3:
        return False

    return True


def _run_promotion_cycle(world: "WorldState") -> None:
    agents: List[AgentState] = list(world.agents.values())

    sup_counts: Dict[WorkDetailType, int] = {}
    for agent in agents:
        if agent.supervisor_work_type is not None:
            wt = agent.supervisor_work_type
            sup_counts[wt] = sup_counts.get(wt, 0) + 1

    for work_type in WorkDetailType:
        current_sup = sup_counts.get(work_type, 0)
        if current_sup >= MAX_SUPERVISORS_PER_WORK_TYPE:
            continue

        candidate_scores: List[Tuple[float, AgentState]] = []

        for agent in agents:
            if not _is_eligible_supervisor_candidate(agent, work_type):
                continue

            wh = agent.work_history.get_or_create(work_type)
            prof = wh.proficiency
            seniority = min(1.0, agent.total_ticks_employed / SENIORITY_HORIZON)
            morale = agent.physical.morale_level
            stress = agent.physical.stress_level

            score = (
                0.5 * prof
                + 0.2 * seniority
                + 0.2 * morale
                - 0.1 * stress
            )
            candidate_scores.append((score, agent))

        if not candidate_scores:
            continue

        candidate_scores.sort(key=lambda pair: pair[0], reverse=True)

        best_score, best_agent = candidate_scores[0]
        _promote_to_supervisor(world, best_agent, work_type)


def _promote_to_supervisor(
    world: "WorldState",
    agent: AgentState,
    work_type: WorkDetailType,
) -> None:
    agent.tier = 2
    agent.supervisor_work_type = work_type
    agent.times_promoted += 1

    crew_id = _ensure_default_crew_for_type(world, work_type)
    crew = world.crews[crew_id]
    agent.supervisor_crew_id = crew_id

    if agent.id not in crew.member_ids:
        crew.member_ids.append(agent.id)

    if getattr(crew, "leader_id", None) is None:
        crew.leader_id = agent.id

    factory = EpisodeFactory(world=world)
    ep = factory.create_promotion_episode(
        owner_agent_id=agent.id,
        tick=getattr(world, "tick", getattr(world, "current_tick", 0)),
        work_type=work_type,
        new_tier=2,
        crew_id=crew_id,
    )
    agent.record_episode(ep)

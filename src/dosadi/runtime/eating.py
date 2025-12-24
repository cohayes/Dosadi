"""Lightweight hunger and eating utilities for the MVP loop."""

from __future__ import annotations

from typing import Optional, List
import random

from dosadi.agents.core import AgentState, Goal, GoalStatus, GoalType
from dosadi.agents.physiology import (
    accumulate_sleep_pressure,
    compute_needs_pressure,
    update_stress_and_morale,
)
from dosadi.memory.episodes import EpisodeChannel, EpisodeVerb
from dosadi.memory.episode_factory import EpisodeFactory
from dosadi.world.environment import get_or_create_place_env
from dosadi.runtime.config import (
    MIN_TICKS_AS_SUPERVISOR_BEFORE_REPORT,
    SUPERVISOR_REPORT_INTERVAL_TICKS,
)
from dosadi.runtime.suit_wear import ensure_suit_config, suit_decay_multiplier

# Hunger and meal tuning constants (MVP defaults)
HUNGER_RATE_PER_TICK: float = 1.0 / 50_000.0
HUNGER_MAX: float = 2.0

HUNGER_GOAL_THRESHOLD: float = 0.4
MEAL_SATIATION_AMOUNT: float = 0.7
GET_MEAL_GOAL_TIMEOUT_TICKS: int = 100_000

HYDRATION_DECAY_PER_TICK: float = 1.0 / 80_000.0
HYDRATION_GOAL_THRESHOLD: float = 0.6
GET_WATER_GOAL_TIMEOUT_TICKS: int = 80_000

DRINK_REPLENISH_AMOUNT: float = 0.7
DRINK_WATER_UNIT: float = 1.0

SLEEP_PRESSURE_GOAL_THRESHOLD: float = 0.6
MIN_TICKS_BETWEEN_SLEEP_GOALS: int = 40_000

CHRONIC_PHYSIO_GOAL_INTERVAL_TICKS: int = 1_500

MEAL_BODY_SIGNAL_TYPES = {
    "WEAK_FROM_HUNGER_AND_THIRST",
    "NEEDS_OVERWHELMING",
}

WATER_BODY_SIGNAL_TYPES = {
    "THIRSTY",
    "VERY_THIRSTY",
    "EXTREMELY_THIRSTY",
    "WEAK_FROM_HUNGER_AND_THIRST",
    "NEEDS_OVERWHELMING",
}

REST_BODY_SIGNAL_TYPES = {
    "NEEDS_OVERWHELMING",
    "WEAK_FROM_HUNGER_AND_THIRST",
}

ENV_UNCOMFORTABLE_THRESHOLD = 0.3
ENV_COMFORTABLE_THRESHOLD = 0.7

CHRONIC_PHYSICAL_UPDATE_INTERVAL_TICKS: int = 10


def chronic_update_agent_physical_state(
    world, agent: AgentState, rng: Optional[random.Random] = None
) -> None:
    """Update physiological drift and signals on a 10-tick cadence."""

    physical = agent.physical
    current_tick = getattr(world, "tick", getattr(world, "current_tick", 0))

    if getattr(agent, "is_asleep", False) and not physical.is_sleeping:
        physical.last_physical_update_tick = current_tick
        return
    if physical.is_sleeping:
        physical.last_physical_update_tick = current_tick
        return

    if current_tick - physical.last_physical_update_tick < CHRONIC_PHYSICAL_UPDATE_INTERVAL_TICKS:
        return

    rng = rng or getattr(world, "rng", None) or random
    env = get_or_create_place_env(world, agent.location_id)
    factory = EpisodeFactory(world=world)
    suit_cfg = ensure_suit_config(world)
    suit_multiplier = 1.0
    if getattr(suit_cfg, "enabled", False) and getattr(suit_cfg, "apply_physio_penalties", False):
        suit_multiplier = suit_decay_multiplier(agent, cfg=suit_cfg)

    start_tick = max(
        physical.last_physical_update_tick + 1,
        current_tick - CHRONIC_PHYSICAL_UPDATE_INTERVAL_TICKS + 1,
        0,
    )
    for tick in range(start_tick, current_tick + 1):
        physical.hunger_level += HUNGER_RATE_PER_TICK
        if physical.hunger_level > HUNGER_MAX:
            physical.hunger_level = HUNGER_MAX

        physical.hydration_level -= HYDRATION_DECAY_PER_TICK * max(1.0, suit_multiplier)
        if physical.hydration_level < 0.0:
            physical.hydration_level = 0.0
        elif physical.hydration_level > 1.0:
            physical.hydration_level = 1.0

        needs_pressure = compute_needs_pressure(physical)
        update_stress_and_morale(physical, needs_pressure)
        accumulate_sleep_pressure(physical)

        signal_type = None
        intensity = 0.0

        if agent.physical.hydration_level < 0.2 and rng.random() < 0.05:
            signal_type = "EXTREMELY_THIRSTY"
            intensity = 1.0
        elif agent.physical.hydration_level < 0.4 and rng.random() < 0.03:
            signal_type = "VERY_THIRSTY"
            intensity = 0.7
        elif agent.physical.hydration_level < 0.7 and rng.random() < 0.02:
            signal_type = "THIRSTY"
            intensity = 0.4

        if signal_type is not None:
            episode = factory.create_body_signal_episode(
                owner_agent_id=agent.id,
                tick=tick,
                signal_type=signal_type,
                intensity=intensity,
            )
            agent.record_episode(episode)

        if needs_pressure > 0.9 and rng.random() < 0.02:
            episode = factory.create_body_signal_episode(
                owner_agent_id=agent.id,
                tick=tick,
                signal_type="NEEDS_OVERWHELMING",
                intensity=needs_pressure,
            )
            agent.record_episode(episode)
        elif needs_pressure > 0.6 and rng.random() < 0.02:
            episode = factory.create_body_signal_episode(
                owner_agent_id=agent.id,
                tick=tick,
                signal_type="WEAK_FROM_HUNGER_AND_THIRST",
                intensity=needs_pressure,
            )
            agent.record_episode(episode)

        if env.comfort < ENV_UNCOMFORTABLE_THRESHOLD and rng.random() < 0.02:
            episode = factory.create_body_signal_episode(
                owner_agent_id=agent.id,
                tick=tick,
                signal_type="ENV_UNCOMFORTABLE",
                intensity=1.0 - env.comfort,
            )
            agent.record_episode(episode)
        elif env.comfort > ENV_COMFORTABLE_THRESHOLD and rng.random() < 0.02:
            episode = factory.create_body_signal_episode(
                owner_agent_id=agent.id,
                tick=tick,
                signal_type="ENV_COMFORTABLE",
                intensity=env.comfort,
            )
            agent.record_episode(episode)

    physical.last_physical_update_tick = current_tick


def has_active_or_pending_get_meal_goal(agent: AgentState) -> bool:
    for g in agent.goals:
        if g.goal_type == GoalType.GET_MEAL_TODAY and g.status in (
            GoalStatus.PENDING,
            GoalStatus.ACTIVE,
        ):
            return True
    return False


def create_get_meal_goal(world, agent: AgentState) -> Goal:
    current_tick = getattr(world, "tick", 0)
    g = Goal(
        goal_id=f"goal:get_meal:{agent.id}:{current_tick}",
        owner_id=agent.id,
        goal_type=GoalType.GET_MEAL_TODAY,
        status=GoalStatus.PENDING,
        created_at_tick=current_tick,
        metadata={},
    )
    agent.goals.append(g)
    return g


def maybe_create_get_meal_goal(world, agent: AgentState) -> None:
    if agent.physical.hunger_level < HUNGER_GOAL_THRESHOLD:
        return
    if has_active_or_pending_get_meal_goal(agent):
        return
    create_get_meal_goal(world, agent)


def has_active_or_pending_get_water_goal(agent: AgentState) -> bool:
    for g in agent.goals:
        if g.goal_type == GoalType.GET_WATER_TODAY and g.status in (
            GoalStatus.PENDING,
            GoalStatus.ACTIVE,
        ):
            return True
    return False


def create_get_water_goal(world, agent: AgentState) -> Goal:
    current_tick = getattr(world, "tick", 0)
    g = Goal(
        goal_id=f"goal:get_water:{agent.id}:{current_tick}",
        owner_id=agent.id,
        goal_type=GoalType.GET_WATER_TODAY,
        status=GoalStatus.PENDING,
        created_at_tick=current_tick,
        metadata={},
    )
    agent.goals.append(g)
    return g


def maybe_create_get_water_goal(world, agent: AgentState) -> None:
    if agent.physical.hydration_level > HYDRATION_GOAL_THRESHOLD:
        return
    if has_active_or_pending_get_water_goal(agent):
        return
    create_get_water_goal(world, agent)


def has_active_or_pending_rest_goal(agent: AgentState) -> bool:
    for g in agent.goals:
        if g.goal_type == GoalType.REST_TONIGHT and g.status in (
            GoalStatus.PENDING,
            GoalStatus.ACTIVE,
        ):
            return True
    return False


def maybe_create_rest_goal(world, agent: AgentState) -> None:
    physical = agent.physical
    current_tick = getattr(world, "tick", getattr(world, "current_tick", 0))

    if physical.is_sleeping:
        return
    if physical.sleep_pressure < SLEEP_PRESSURE_GOAL_THRESHOLD:
        return
    if has_active_or_pending_rest_goal(agent):
        return
    if current_tick - physical.last_sleep_tick < MIN_TICKS_BETWEEN_SLEEP_GOALS:
        return

    if physical.hunger_level > 1.0 or physical.hydration_level < 0.3:
        return

    goal = Goal(
        goal_id=f"goal:rest:{agent.id}:{current_tick}",
        owner_id=agent.id,
        goal_type=GoalType.REST_TONIGHT,
        status=GoalStatus.PENDING,
        created_at_tick=current_tick,
        priority=max(physical.sleep_pressure, 0.6),
        urgency=max(0.0, min(1.0, physical.sleep_pressure)),
        metadata={},
    )
    agent.goals.append(goal)


def _body_signal_types_in_short_term(agent: AgentState) -> set[str]:
    signal_types: set[str] = set()
    for episode in agent.episodes.short_term:
        if episode.channel != EpisodeChannel.BODY_SIGNAL and episode.verb != EpisodeVerb.BODY_SIGNAL:
            continue
        details = getattr(episode, "details", {}) or {}
        signal_type = details.get("signal_type")
        if isinstance(signal_type, str):
            signal_types.add(signal_type)
    return signal_types


def _refresh_goal_priority_and_status(goal: Goal, priority: float, urgency: float, tick: int) -> None:
    goal.priority = max(0.0, min(1.0, priority))
    goal.urgency = max(0.0, min(1.0, urgency))
    goal.last_updated_tick = tick
    if goal.status == GoalStatus.PENDING:
        goal.status = GoalStatus.ACTIVE


def maybe_update_chronic_physiological_goals(world, agent: AgentState) -> None:
    current_tick = getattr(world, "tick", getattr(world, "current_tick", 0))
    if current_tick - agent.last_chronic_goal_tick < CHRONIC_PHYSIO_GOAL_INTERVAL_TICKS:
        return

    agent.last_chronic_goal_tick = current_tick
    signal_types = _body_signal_types_in_short_term(agent)

    def _has_signal(match_set: set[str]) -> bool:
        return any(sig in match_set for sig in signal_types)

    if _has_signal(MEAL_BODY_SIGNAL_TYPES):
        maybe_create_get_meal_goal(world, agent)
        hunger_priority = min(1.0, max(0.0, agent.physical.hunger_level / HUNGER_MAX))
        for goal in agent.goals:
            if goal.goal_type == GoalType.GET_MEAL_TODAY and goal.status in (
                GoalStatus.PENDING,
                GoalStatus.ACTIVE,
            ):
                _refresh_goal_priority_and_status(goal, hunger_priority, hunger_priority, current_tick)

    if _has_signal(WATER_BODY_SIGNAL_TYPES):
        maybe_create_get_water_goal(world, agent)
        hydration_priority = min(1.0, max(0.0, 1.0 - agent.physical.hydration_level))
        for goal in agent.goals:
            if goal.goal_type == GoalType.GET_WATER_TODAY and goal.status in (
                GoalStatus.PENDING,
                GoalStatus.ACTIVE,
            ):
                _refresh_goal_priority_and_status(goal, hydration_priority, hydration_priority, current_tick)

    if _has_signal(REST_BODY_SIGNAL_TYPES):
        maybe_create_rest_goal(world, agent)
        rest_priority = max(agent.physical.sleep_pressure, 0.6)
        rest_urgency = max(0.0, min(1.0, agent.physical.sleep_pressure))
        for goal in agent.goals:
            if goal.goal_type == GoalType.REST_TONIGHT and goal.status in (
                GoalStatus.PENDING,
                GoalStatus.ACTIVE,
            ):
                _refresh_goal_priority_and_status(goal, rest_priority, rest_urgency, current_tick)


def maybe_create_supervisor_report_goal(world, agent: AgentState) -> None:
    # Only Tier-2 supervisors with an assigned work type
    if agent.tier != 2 or agent.supervisor_work_type is None:
        return

    current_tick = getattr(world, "tick", getattr(world, "current_tick", 0))

    # Cadence check
    if current_tick - agent.last_report_tick < SUPERVISOR_REPORT_INTERVAL_TICKS:
        return

    # Require some time as supervisor
    if agent.total_ticks_employed < MIN_TICKS_AS_SUPERVISOR_BEFORE_REPORT:
        return

    # Avoid during acute food/water crisis
    physical = agent.physical
    if physical.hunger_level > 1.2 or physical.hydration_level < 0.2:
        return

    # Avoid duplicates
    for g in agent.goals:
        if g.goal_type == GoalType.WRITE_SUPERVISOR_REPORT and g.status in (
            GoalStatus.PENDING,
            GoalStatus.ACTIVE,
        ):
            return

    goal = Goal(
        goal_id=f"goal:write_report:{agent.id}:{current_tick}",
        owner_id=agent.id,
        goal_type=GoalType.WRITE_SUPERVISOR_REPORT,
        status=GoalStatus.PENDING,
        created_at_tick=current_tick,
        metadata={},
    )
    agent.goals.append(goal)


def choose_mess_hall_for_agent(
    world,
    agent: AgentState,
    rng: random.Random,
) -> Optional[str]:
    """Pick a mess hall using place beliefs and simple congestion cues."""

    hall_ids: List[str] = [
        fid
        for fid, facility in getattr(world, "facilities", {}).items()
        if getattr(facility, "kind", None) == "mess_hall"
    ]
    if not hall_ids:
        return None

    def hall_utility(hall_id: str) -> float:
        pb = agent.get_or_create_place_belief(hall_id)
        q_state = getattr(world, "facility_queues", {}).get(hall_id)
        q_len = len(q_state.queue) if q_state else 0
        normalized_q = min(1.0, q_len / 20.0)

        w_rel = 0.5
        w_comfort = 0.1
        w_fair = 0.2
        w_cong = 0.1
        w_q = 0.2

        return (
            w_rel * pb.reliability_score
            + w_comfort * pb.comfort_score
            + w_fair * pb.fairness_score
            - w_cong * pb.congestion_score
            - w_q * normalized_q
        )

    if rng.random() < 0.1:
        return rng.choice(hall_ids)

    best_id = None
    best_score = float("-inf")
    for hid in hall_ids:
        score = hall_utility(hid)
        if score > best_score:
            best_score = score
            best_id = hid
    return best_id


def choose_water_source_for_agent(
    world,
    agent: AgentState,
    rng: random.Random,
) -> Optional[str]:
    candidate_ids: List[str] = []
    for fid, facility in getattr(world, "facilities", {}).items():
        kind = getattr(facility, "kind", None)
        if kind in {"water_tap", "mess_hall"}:
            candidate_ids.append(fid)

    if not candidate_ids:
        return None

    def utility(place_id: str) -> float:
        pb = agent.get_or_create_place_belief(place_id)
        w_rel = 0.5
        w_fair = 0.2
        w_cong = 0.1
        return (
            w_rel * pb.reliability_score
            + w_fair * pb.fairness_score
            - w_cong * pb.congestion_score
        )

    if rng.random() < 0.1:
        return rng.choice(candidate_ids)

    best_id = None
    best_score = float("-inf")
    for pid in candidate_ids:
        score = utility(pid)
        if score > best_score:
            best_score = score
            best_id = pid

    return best_id


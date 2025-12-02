"""Lightweight hunger and eating utilities for the MVP loop."""

from __future__ import annotations

from typing import Optional, List
import random

from dosadi.agents.core import AgentState, Goal, GoalStatus, GoalType
from dosadi.memory.episode_factory import EpisodeFactory
from dosadi.world.environment import get_or_create_place_env

# Hunger and meal tuning constants (MVP defaults)
HUNGER_RATE_PER_TICK: float = 1.0 / 50_000.0
HUNGER_MAX: float = 2.0

HUNGER_GOAL_THRESHOLD: float = 0.4
MEAL_SATIATION_AMOUNT: float = 0.7
GET_MEAL_GOAL_TIMEOUT_TICKS: int = 100_000

ENV_UNCOMFORTABLE_THRESHOLD = 0.3
ENV_COMFORTABLE_THRESHOLD = 0.7


def update_agent_physical_state(
    world, agent: AgentState, rng: Optional[random.Random] = None
) -> None:
    """Update per-tick physiological drift such as hunger."""

    if getattr(agent, "is_asleep", False):
        return

    rng = rng or getattr(world, "rng", None) or random
    agent.physical.hunger_level += HUNGER_RATE_PER_TICK
    if agent.physical.hunger_level > HUNGER_MAX:
        agent.physical.hunger_level = HUNGER_MAX

    env = get_or_create_place_env(world, agent.location_id)
    factory = EpisodeFactory(world=world)
    current_tick = getattr(world, "tick", 0)

    if env.comfort < ENV_UNCOMFORTABLE_THRESHOLD and rng.random() < 0.02:
        episode = factory.create_body_signal_episode(
            owner_agent_id=agent.id,
            tick=current_tick,
            signal_type="ENV_UNCOMFORTABLE",
            intensity=1.0 - env.comfort,
        )
        agent.record_episode(episode)
    elif env.comfort > ENV_COMFORTABLE_THRESHOLD and rng.random() < 0.02:
        episode = factory.create_body_signal_episode(
            owner_agent_id=agent.id,
            tick=current_tick,
            signal_type="ENV_COMFORTABLE",
            intensity=env.comfort,
        )
        agent.record_episode(episode)


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


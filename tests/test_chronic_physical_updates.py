import random

import pytest

from dosadi.agents.core import AgentState, GoalType
from dosadi.runtime.eating import (
    CHRONIC_PHYSICAL_UPDATE_INTERVAL_TICKS,
    HUNGER_GOAL_THRESHOLD,
    HUNGER_RATE_PER_TICK,
    chronic_update_agent_physical_state,
    maybe_create_get_meal_goal,
)
from dosadi.state import WorldState


def test_chronic_update_runs_every_interval():
    world = WorldState()
    agent = AgentState(agent_id="agent:1", name="Test Agent")
    world.agents[agent.id] = agent

    rng = random.Random(1234)
    hunger_by_tick = {}

    for tick in range(CHRONIC_PHYSICAL_UPDATE_INTERVAL_TICKS * 2 + 1):
        world.tick = tick
        chronic_update_agent_physical_state(world, agent, rng)
        hunger_by_tick[tick] = agent.physical.hunger_level

    first_update = hunger_by_tick[0]
    for t in range(1, CHRONIC_PHYSICAL_UPDATE_INTERVAL_TICKS):
        assert hunger_by_tick[t] == first_update

    interval_update = hunger_by_tick[CHRONIC_PHYSICAL_UPDATE_INTERVAL_TICKS]
    assert interval_update > first_update

    for t in range(
        CHRONIC_PHYSICAL_UPDATE_INTERVAL_TICKS + 1,
        CHRONIC_PHYSICAL_UPDATE_INTERVAL_TICKS * 2,
    ):
        assert hunger_by_tick[t] == interval_update


def test_chronic_update_still_creates_meal_goals():
    world = WorldState()
    agent = AgentState(agent_id="agent:2", name="Hungry Agent")
    world.agents[agent.id] = agent

    rng = random.Random(7)
    agent.physical.hunger_level = HUNGER_GOAL_THRESHOLD - 0.01

    total_ticks = CHRONIC_PHYSICAL_UPDATE_INTERVAL_TICKS * 60
    for tick in range(total_ticks):
        world.tick = tick
        chronic_update_agent_physical_state(world, agent, rng)
        maybe_create_get_meal_goal(world, agent)

    assert any(g.goal_type == GoalType.GET_MEAL_TODAY for g in agent.goals)

    expected_hunger = agent.physical.hunger_level
    assert expected_hunger >= HUNGER_GOAL_THRESHOLD
    assert (
        agent.physical.last_physical_update_tick
        == total_ticks - CHRONIC_PHYSICAL_UPDATE_INTERVAL_TICKS
    )
    ticks_processed = agent.physical.last_physical_update_tick + 1
    assert expected_hunger == pytest.approx(
        HUNGER_GOAL_THRESHOLD - 0.01 + HUNGER_RATE_PER_TICK * ticks_processed
    )

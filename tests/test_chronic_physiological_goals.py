from dosadi.agents.core import AgentState, GoalStatus, GoalType
from dosadi.memory.episodes import Episode, EpisodeChannel, EpisodeVerb
from dosadi.runtime.eating import (
    CHRONIC_PHYSIO_GOAL_INTERVAL_TICKS,
    maybe_update_chronic_physiological_goals,
)


class DummyWorld:
    def __init__(self, tick: int) -> None:
        self.tick = tick


def _make_body_signal(owner_id: str, tick: int, signal_type: str) -> Episode:
    return Episode(
        episode_id=f"ep:{signal_type}:{tick}",
        owner_agent_id=owner_id,
        tick=tick,
        channel=EpisodeChannel.BODY_SIGNAL,
        verb=EpisodeVerb.BODY_SIGNAL,
        details={"signal_type": signal_type, "intensity": 0.5},
    )


def test_interval_blocks_chronic_goal_updates_without_waiting():
    agent = AgentState(agent_id="agent:1", name="Agent 1")
    agent.physical.hunger_level = 1.0
    agent.last_chronic_goal_tick = 1_000
    world = DummyWorld(tick=1_400)

    agent.episodes.short_term.append(
        _make_body_signal(agent.id, tick=1_300, signal_type="WEAK_FROM_HUNGER_AND_THIRST")
    )

    maybe_update_chronic_physiological_goals(world, agent)

    assert not any(g.goal_type == GoalType.GET_MEAL_TODAY for g in agent.goals)
    assert agent.last_chronic_goal_tick == 1_000


def test_meal_goal_created_and_refreshed_when_body_signal_present():
    agent = AgentState(agent_id="agent:2", name="Agent 2")
    agent.physical.hunger_level = 1.0
    world = DummyWorld(tick=2_000)

    agent.episodes.short_term.append(
        _make_body_signal(agent.id, tick=1_900, signal_type="WEAK_FROM_HUNGER_AND_THIRST")
    )

    maybe_update_chronic_physiological_goals(world, agent)

    meal_goals = [g for g in agent.goals if g.goal_type == GoalType.GET_MEAL_TODAY]
    assert len(meal_goals) == 1
    meal_goal = meal_goals[0]
    assert meal_goal.status == GoalStatus.ACTIVE
    assert meal_goal.priority > 0.0
    assert meal_goal.urgency > 0.0
    assert agent.last_chronic_goal_tick == world.tick


def test_water_goal_requires_body_signal():
    agent = AgentState(agent_id="agent:3", name="Agent 3")
    agent.physical.hydration_level = 0.1
    world = DummyWorld(tick=CHRONIC_PHYSIO_GOAL_INTERVAL_TICKS)

    maybe_update_chronic_physiological_goals(world, agent)
    assert not any(g.goal_type == GoalType.GET_WATER_TODAY for g in agent.goals)

    agent.episodes.short_term.append(
        _make_body_signal(agent.id, tick=world.tick, signal_type="THIRSTY")
    )
    world.tick += CHRONIC_PHYSIO_GOAL_INTERVAL_TICKS
    maybe_update_chronic_physiological_goals(world, agent)

    water_goals = [g for g in agent.goals if g.goal_type == GoalType.GET_WATER_TODAY]
    assert len(water_goals) == 1
    assert water_goals[0].status == GoalStatus.ACTIVE

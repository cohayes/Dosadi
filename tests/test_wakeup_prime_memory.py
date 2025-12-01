import random

from dosadi.memory.episodes import Episode, EpisodeChannel
from dosadi.runtime.memory_runtime import step_agent_sleep_wake
from dosadi.scenarios.wakeup_prime import (
    WakeupPrimeScenarioConfig,
    generate_wakeup_scenario_prime,
)


def test_sleep_consolidation_creates_place_beliefs():
    """Agents in Wakeup Prime should consolidate daily episodes into beliefs when sleeping."""

    random.seed(1337)
    report = generate_wakeup_scenario_prime(WakeupPrimeScenarioConfig(num_agents=1, seed=42))
    world = report.world
    agent = report.agents[0]
    mem_cfg = world.memory_config

    place_id = "queue:suit-issue:front"
    episode = Episode(
        episode_id="ep:test",
        owner_agent_id=agent.agent_id,
        tick=0,
        location_id=place_id,
        importance=0.8,
        reliability=0.9,
        channel=EpisodeChannel.DIRECT,
        tags={"queue_served"},
        details={"wait_ticks": 20},
    )

    agent.episodes.daily.append(episode)

    agent.is_asleep = False
    agent.next_sleep_tick = 1
    agent.next_wake_tick = agent.next_sleep_tick + mem_cfg.sleep_duration_ticks
    agent.last_consolidation_tick = -mem_cfg.min_consolidation_interval_ticks

    step_agent_sleep_wake(world, agent, tick=1, config=mem_cfg)

    belief = agent.place_beliefs.get(place_id)
    assert agent.is_asleep
    assert belief is not None
    assert belief.fairness_score > 0.0
    assert belief.efficiency_score > 0.0
    assert not agent.episodes.daily


def test_short_term_promoted_on_sleep_and_consolidated():
    """Short-term queue experiences should be promoted when an agent falls asleep."""

    random.seed(9001)
    report = generate_wakeup_scenario_prime(WakeupPrimeScenarioConfig(num_agents=1, seed=5))
    world = report.world
    agent = report.agents[0]
    mem_cfg = world.memory_config

    place_id = "queue:assignment:front"
    episode = Episode(
        episode_id="ep:short-term",
        owner_agent_id=agent.agent_id,
        tick=0,
        location_id=place_id,
        importance=0.9,
        reliability=0.8,
        channel=EpisodeChannel.DIRECT,
        tags={"queue_denied"},
    )

    agent.episodes.push_short_term(episode)

    agent.is_asleep = False
    agent.next_sleep_tick = 0
    agent.next_wake_tick = agent.next_sleep_tick + mem_cfg.sleep_duration_ticks
    agent.last_consolidation_tick = -mem_cfg.min_consolidation_interval_ticks

    step_agent_sleep_wake(world, agent, tick=0, config=mem_cfg)

    belief = agent.place_beliefs.get(place_id)
    assert agent.is_asleep
    assert belief is not None
    assert belief.fairness_score < 0.0
    assert not agent.episodes.daily


import random

from dosadi.memory.episodes import Episode, EpisodeChannel
from dosadi.runtime.wakeup_prime import (
    WakeupPrimeRuntimeConfig,
    run_wakeup_prime,
    step_wakeup_prime_once,
)
from dosadi.scenarios.wakeup_prime import (
    WakeupPrimeScenarioConfig,
    generate_wakeup_scenario_prime,
)


def test_runtime_steps_and_consolidates_daily_memory():
    random.seed(1234)
    scenario_config = WakeupPrimeScenarioConfig(num_agents=1, seed=7)
    report = generate_wakeup_scenario_prime(scenario_config)
    world = report.world
    world.runtime_config = WakeupPrimeRuntimeConfig(max_ticks=2, queue_interval_ticks=1)

    agent = report.agents[0]
    mem_cfg = world.memory_config

    episode = Episode(
        episode_id="ep:runtime",  # type: ignore[arg-type]
        owner_agent_id=agent.agent_id,
        tick=0,
        location_id="queue:suit-issue:front",
        importance=0.9,
        reliability=0.8,
        channel=EpisodeChannel.DIRECT,
    )
    agent.episodes.daily.append(episode)

    agent.is_asleep = False
    agent.next_sleep_tick = 0
    agent.next_wake_tick = agent.next_sleep_tick + mem_cfg.sleep_duration_ticks
    agent.last_consolidation_tick = -mem_cfg.min_consolidation_interval_ticks

    step_wakeup_prime_once(world)

    assert world.tick == 1
    assert agent.is_asleep
    assert not agent.episodes.daily


def test_run_wakeup_prime_advances_to_max_ticks():
    report = run_wakeup_prime(num_agents=2, max_ticks=5, seed=99)
    assert report.world.tick == 5
    assert report.summary.get("ticks") == 5
    assert report.summary.get("agents") == 2

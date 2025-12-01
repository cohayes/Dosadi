"""Runtime orchestration for the Wakeup Scenario Prime."""
from __future__ import annotations

import random
from dataclasses import dataclass

from dosadi.memory.config import MemoryConfig
from dosadi.runtime.memory_runtime import step_agent_memory_maintenance, step_agent_sleep_wake
from dosadi.runtime.queue_episodes import QueueEpisodeEmitter
from dosadi.runtime.queues import process_all_queues
from dosadi.scenarios.wakeup_prime import (
    WakeupPrimeReport,
    WakeupPrimeScenarioConfig,
    generate_wakeup_scenario_prime,
)
from dosadi.state import WorldState


@dataclass(slots=True)
class WakeupPrimeRuntimeConfig:
    """Tunable runtime configuration for Wakeup Scenario Prime."""

    max_ticks: int = 10_000
    queue_interval_ticks: int = 100


def step_wakeup_prime_once(world: WorldState) -> None:
    """Advance the Wakeup Prime world by a single tick."""

    tick = world.tick
    rng = getattr(world, "rng", None) or random.Random(getattr(world, "seed", 0))
    world.rng = rng

    cfg: WakeupPrimeRuntimeConfig = getattr(world, "runtime_config", None) or WakeupPrimeRuntimeConfig()
    world.runtime_config = cfg

    queue_emitter = getattr(world, "queue_episode_emitter", None) or QueueEpisodeEmitter()
    world.queue_episode_emitter = queue_emitter

    memory_config: MemoryConfig = getattr(world, "memory_config", None) or MemoryConfig()
    world.memory_config = memory_config

    for agent in world.agents.values():
        step_agent_sleep_wake(world, agent, tick, memory_config)
        step_agent_memory_maintenance(world, agent, tick, memory_config)

    if tick % cfg.queue_interval_ticks == 0:
        process_all_queues(world, tick, queue_emitter)

    world.tick += 1


def run_wakeup_prime(
    *,
    num_agents: int = 240,
    max_ticks: int = 10_000,
    seed: int = 1337,
    include_canteen: bool = True,
    basic_suit_stock: int | None = None,
) -> WakeupPrimeReport:
    """Generate and run Wakeup Scenario Prime."""

    scenario_config = WakeupPrimeScenarioConfig(
        num_agents=num_agents,
        seed=seed,
        include_canteen=include_canteen,
        max_ticks=max_ticks,
        basic_suit_stock=basic_suit_stock,
    )
    report = generate_wakeup_scenario_prime(scenario_config)
    world = report.world

    runtime_cfg = WakeupPrimeRuntimeConfig(max_ticks=max_ticks)
    world.runtime_config = runtime_cfg
    world.rng.seed(seed)

    while world.tick < runtime_cfg.max_ticks:
        step_wakeup_prime_once(world)

    report.summary = {
        "ticks": world.tick,
        "agents": len(world.agents),
        "queues": len(world.queues),
    }
    return report


__all__ = [
    "WakeupPrimeRuntimeConfig",
    "run_wakeup_prime",
    "step_wakeup_prime_once",
]

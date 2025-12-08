"""Runtime orchestration for the Wakeup Scenario Prime."""
from __future__ import annotations

import random
from dataclasses import dataclass

from dosadi.memory.config import MemoryConfig
from dosadi.runtime.memory_runtime import step_agent_memory_maintenance, step_agent_sleep_wake
from dosadi.runtime.queue_episodes import QueueEpisodeEmitter
from dosadi.runtime.queues import process_all_queues
from dosadi.agents.groups import (
    GroupType,
    _find_dangerous_corridors_from_metrics,
    maybe_form_proto_council,
    maybe_run_council_meeting,
    maybe_run_pod_meeting,
)
from dosadi.scenarios.wakeup_prime import (
    WakeupPrimeReport,
    WakeupPrimeScenarioConfig,
    generate_wakeup_scenario_prime,
)
from dosadi.state import WorldState
from dosadi.runtime.proto_council import run_proto_council_tuning
from dosadi.runtime.protocol_authoring import maybe_author_movement_protocols
from dosadi.runtime.agent_preferences import maybe_update_desired_work_type


@dataclass(slots=True)
class WakeupPrimeRuntimeConfig:
    """Tunable runtime configuration for Wakeup Scenario Prime."""

    max_ticks: int = 10_000
    queue_interval_ticks: int = 100
    pod_meeting_interval_ticks: int = 120
    council_meeting_cooldown_ticks: int = 80
    rep_vote_fraction_threshold: float = 0.4
    min_leadership_threshold: float = 0.6
    max_pod_representatives: int = 2
    max_council_size: int = 8
    min_incidents_for_protocol: int = 1
    risk_threshold_for_protocol: float = 0.15


def _maybe_run_proto_council(world: WorldState, tick: int) -> None:
    ticks_per_day = getattr(world, "ticks_per_day", None)
    if ticks_per_day is None:
        ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", 144_000)

    try:
        ticks_per_day = int(ticks_per_day)
    except Exception:
        ticks_per_day = 144_000

    ticks_per_day = max(1, ticks_per_day)
    current_day = tick // ticks_per_day
    last_day = getattr(world, "last_proto_council_tuning_day", -1)

    if current_day <= last_day:
        return

    rng = getattr(world, "rng", None) or random.Random(getattr(world, "seed", 0))
    run_proto_council_tuning(world=world, rng=rng, current_day=current_day)
    world.last_proto_council_tuning_day = current_day


def _step_governance(world: WorldState, tick: int, cfg: WakeupPrimeRuntimeConfig) -> None:
    rng = getattr(world, "rng", None) or random.Random(getattr(world, "seed", 0))

    groups = getattr(world, "groups", None)
    if groups is None:
        world.groups = []
        groups = world.groups

    metrics = getattr(world, "metrics", None)
    dangerous_edge_ids = []
    if isinstance(metrics, dict):
        dangerous_edge_ids = _find_dangerous_corridors_from_metrics(
            metrics=metrics,
            min_incidents_for_protocol=cfg.min_incidents_for_protocol,
            risk_threshold_for_protocol=cfg.risk_threshold_for_protocol,
        )

    for group in groups:
        if group.group_type != GroupType.POD:
            continue
        maybe_run_pod_meeting(
            pod_group=group,
            agents_by_id=world.agents,
            tick=tick,
            rng=rng,
            meeting_interval_ticks=cfg.pod_meeting_interval_ticks,
            rep_vote_fraction_threshold=cfg.rep_vote_fraction_threshold,
            min_leadership_threshold=cfg.min_leadership_threshold,
            max_representatives=cfg.max_pod_representatives,
        )

    council = maybe_form_proto_council(
        groups=groups,
        agents_by_id=world.agents,
        tick=tick,
        hub_location_id="corr:main-core",
        max_council_size=cfg.max_council_size,
    )

    if council is not None:
        world.council_agent_ids = list(council.member_ids)
        maybe_run_council_meeting(
            world=world,
            council_group=council,
            agents_by_id=world.agents,
            tick=tick,
            rng=rng,
            cooldown_ticks=cfg.council_meeting_cooldown_ticks,
            hub_location_id="corr:main-core",
            metrics=getattr(world, "metrics", {}),
            cfg=cfg,
        )

    if dangerous_edge_ids:
        maybe_author_movement_protocols(
            world=world, dangerous_edge_ids=dangerous_edge_ids, tick=tick
        )


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
        if not agent.physical.is_sleeping:
            agent.total_ticks_employed += 1.0
        maybe_update_desired_work_type(world, agent)

    if tick % cfg.queue_interval_ticks == 0:
        process_all_queues(world, tick, queue_emitter)

    _step_governance(world, tick, cfg)
    _maybe_run_proto_council(world, tick)

    world.tick += 1


def run_wakeup_prime(
    *,
    num_agents: int = 240,
    max_ticks: int = 10_000,
    seed: int = 1337,
    include_canteen: bool = True,
    include_hazard_spurs: bool = True,
    basic_suit_stock: int | None = None,
) -> WakeupPrimeReport:
    """Generate and run Wakeup Scenario Prime."""

    scenario_config = WakeupPrimeScenarioConfig(
        num_agents=num_agents,
        seed=seed,
        include_canteen=include_canteen,
        include_hazard_spurs=include_hazard_spurs,
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
        "protocols": len(getattr(getattr(world, "protocols", None), "protocols_by_id", {}) or {}),
    }
    return report


__all__ = [
    "WakeupPrimeRuntimeConfig",
    "run_wakeup_prime",
    "step_wakeup_prime_once",
]

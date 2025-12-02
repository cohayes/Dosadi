"""Runtime orchestration for the Founding Wakeup MVP scenario."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random

from dosadi.agents.core import (
    Action,
    AgentState,
    Goal,
    GoalHorizon,
    GoalOrigin,
    GoalStatus,
    GoalType,
    apply_action,
    decide_next_action,
    make_goal_id,
    prepare_navigation_context,
)
from dosadi.agents.groups import (
    Group,
    GroupType,
    maybe_form_proto_council,
    _find_dangerous_corridors_from_metrics,
    maybe_run_council_meeting,
    maybe_run_pod_meeting,
)
from dosadi.runtime.agent_navigation import (
    attempt_join_queue,
    choose_queue_for_goal,
    step_agent_movement_toward_target,
)
from dosadi.runtime.eating import maybe_create_get_meal_goal, update_agent_physical_state
from dosadi.runtime.council_metrics import update_council_metrics_and_staffing
from dosadi.memory.config import MemoryConfig
from dosadi.runtime.memory_runtime import (
    step_agent_memory_maintenance,
    step_agent_sleep_wake,
)
from dosadi.runtime.proto_council import run_proto_council_tuning
from dosadi.systems.protocols import ProtocolRegistry, activate_protocol, create_movement_protocol_from_goal
from dosadi.runtime.queue_episodes import QueueEpisodeEmitter
from dosadi.runtime.queues import process_all_queues
from dosadi.world.scenarios.founding_wakeup import generate_founding_wakeup_mvp
from dosadi.state import WorldState


@dataclass
class RuntimeConfig:
    """Tunable configuration for the Founding Wakeup MVP runtime."""

    pod_meeting_interval_ticks: int = 600
    council_meeting_cooldown_ticks: int = 300
    min_council_members_for_meeting: int = 2
    rep_vote_fraction_threshold: float = 0.4
    min_leadership_threshold: float = 0.6
    max_pod_representatives: int = 2
    max_council_size: int = 10
    min_incidents_for_protocol: int = 1
    risk_threshold_for_protocol: float = 0.15
    max_ticks: int = 100_000
    queue_interval_ticks: int = 100


@dataclass
class FoundingWakeupReport:
    world: WorldState
    metrics: Dict[str, float]
    summary: Dict[str, object] = field(default_factory=dict)


def _step_agent_movement(world: WorldState) -> None:
    for agent in world.agents.values():
        if getattr(agent, "is_asleep", False):
            continue
        step_agent_movement_toward_target(agent, world)


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


def step_world_once(world: WorldState) -> None:
    """Advance the world by a single tick for the Founding Wakeup MVP."""

    tick = world.tick
    rng = getattr(world, "rng", None) or random.Random(getattr(world, "seed", 0))
    world.rng = rng
    cfg: RuntimeConfig = getattr(world, "runtime_config", None) or RuntimeConfig()
    world.runtime_config = cfg
    queue_emitter = getattr(world, "queue_episode_emitter", None) or QueueEpisodeEmitter()
    world.queue_episode_emitter = queue_emitter
    memory_config = getattr(world, "memory_config", None) or MemoryConfig()
    world.memory_config = memory_config

    for agent in world.agents.values():
        step_agent_sleep_wake(world, agent, tick, memory_config)
        step_agent_memory_maintenance(world, agent, tick, memory_config)
        update_agent_physical_state(world, agent)
        maybe_create_get_meal_goal(world, agent)

    _step_agent_movement(world)
    _phase_A_groups_and_council(world, tick, rng, cfg)
    actions_by_agent = _phase_B_agent_decisions(world, tick)
    _phase_C_apply_actions_and_hazards(world, tick, actions_by_agent)

    if tick % cfg.queue_interval_ticks == 0:
        process_all_queues(world, tick, queue_emitter)

    _maybe_run_proto_council(world, tick)
    update_council_metrics_and_staffing(world)

    world.tick += 1


def _phase_A_groups_and_council(world: WorldState, tick: int, rng: random.Random, cfg: RuntimeConfig) -> None:
    metrics = getattr(world, "metrics", None)

    for g in world.groups:
        if g.group_type == GroupType.POD:
            maybe_run_pod_meeting(
                pod_group=g,
                agents_by_id=world.agents,
                tick=tick,
                rng=rng,
                meeting_interval_ticks=cfg.pod_meeting_interval_ticks,
                rep_vote_fraction_threshold=cfg.rep_vote_fraction_threshold,
                min_leadership_threshold=cfg.min_leadership_threshold,
                max_representatives=cfg.max_pod_representatives,
            )

    council = maybe_form_proto_council(
        groups=world.groups,
        agents_by_id=world.agents,
        tick=tick,
        hub_location_id="loc:well-core",
        max_council_size=cfg.max_council_size,
    )

    dangerous_edge_ids: List[str] = []
    if metrics is not None:
        dangerous_edge_ids = _find_dangerous_corridors_from_metrics(
            metrics=metrics,
            min_incidents_for_protocol=cfg.min_incidents_for_protocol,
            risk_threshold_for_protocol=cfg.risk_threshold_for_protocol,
        )

    if council is not None:
        prev_last_meeting = council.last_meeting_tick
        maybe_run_council_meeting(
            council_group=council,
            agents_by_id=world.agents,
            tick=tick,
            rng=rng,
            cooldown_ticks=cfg.council_meeting_cooldown_ticks,
            hub_location_id="loc:well-core",
            metrics=world.metrics,
            cfg=cfg,
        )
        if council.last_meeting_tick == tick and prev_last_meeting != tick:
            for member_id in council.member_ids:
                agent = world.agents.get(member_id)
                if agent is None or agent.location_id != "loc:well-core":
                    continue
                agent.last_decision_tick = tick

    if dangerous_edge_ids:
        registry = world.protocols if isinstance(world.protocols, ProtocolRegistry) else None
        covered = set()
        if registry is not None:
            for proto in registry.protocols_by_id.values():
                covered.update(proto.covered_location_ids)

        uncovered_edges = [edge for edge in dangerous_edge_ids if edge not in covered]
        if uncovered_edges:
            scribe = next(iter(world.agents.values()), None)
            if scribe is not None:
                author_goal = Goal(
                    goal_id=make_goal_id(),
                    owner_id=scribe.agent_id,
                    goal_type=GoalType.AUTHOR_PROTOCOL,
                    description=f"Draft movement/safety protocol for: {', '.join(uncovered_edges)}",
                    target={"corridor_ids": uncovered_edges, "edge_ids": uncovered_edges},
                    priority=0.95,
                    urgency=0.95,
                    horizon=GoalHorizon.MEDIUM,
                    status=GoalStatus.ACTIVE,
                    created_at_tick=tick,
                    last_updated_tick=tick,
                    origin=GoalOrigin.OPPORTUNITY,
                )
                handle_protocol_authoring(world, scribe, author_goal, uncovered_edges)


def _phase_B_agent_decisions(world: WorldState, tick: int) -> Dict[str, Action]:
    actions_by_agent: Dict[str, Action] = {}

    topology, neighbors, well_core_id, rng = prepare_navigation_context(world)

    for agent_id, agent in world.agents.items():
        if getattr(agent, "is_asleep", False):
            continue
        focus_goal = agent.choose_focus_goal()
        queue_id, queue_location_id = choose_queue_for_goal(
            agent, world, focus_goal, rng=rng
        )

        if queue_location_id is not None:
            agent.navigation_target_id = queue_location_id

            if (
                agent.location_id == queue_location_id
                and agent.current_queue_id is None
                and queue_id is not None
            ):
                attempt_join_queue(agent, world, queue_id, tick)

        action = decide_next_action(
            agent,
            world,
            topology=topology,
            neighbors=neighbors,
            well_core_id=well_core_id,
            rng=rng,
        )
        actions_by_agent[agent_id] = action
        agent.last_decision_tick = tick

    return actions_by_agent


def _phase_C_apply_actions_and_hazards(world: WorldState, tick: int, actions_by_agent: Dict[str, Action]) -> None:
    for agent_id, action in actions_by_agent.items():
        agent = world.agents[agent_id]
        apply_action(agent, action, world, tick)


def run_founding_wakeup_mvp(num_agents: int, max_ticks: int, seed: int) -> FoundingWakeupReport:
    """Run the Founding Wakeup MVP scenario from scratch."""

    world = generate_founding_wakeup_mvp(num_agents=num_agents, seed=seed)
    world.runtime_config = RuntimeConfig(max_ticks=max_ticks)
    world.rng.seed(seed)

    while world.tick < world.runtime_config.max_ticks:
        step_world_once(world)

    return build_founding_wakeup_report(world)


def build_founding_wakeup_report(world: WorldState) -> FoundingWakeupReport:
    summary = {
        "ticks": world.tick,
        "agents": len(world.agents),
        "groups": len(world.groups),
        "protocols": len(world.protocols.protocols_by_id),
    }
    return FoundingWakeupReport(world=world, metrics=dict(world.metrics), summary=summary)


def handle_protocol_authoring(world: WorldState, scribe: AgentState, authoring_goal: Goal, corridors: List[str]) -> None:
    council_group_id = authoring_goal.target.get("council_group_id", "group:council:alpha")
    registry = world.protocols if isinstance(world.protocols, ProtocolRegistry) else ProtocolRegistry()
    if not isinstance(world.protocols, ProtocolRegistry):
        world.protocols = registry
    protocol = create_movement_protocol_from_goal(
        council_group_id=council_group_id,
        scribe_agent_id=scribe.agent_id,
        group_goal=authoring_goal,
        corridors=corridors,
        tick=world.tick,
        registry=registry,
    )
    activate_protocol(protocol, tick=world.tick)


@dataclass(slots=True)
class FoundingWakeupConfig:
    num_agents: int = 12
    max_ticks: int = 10_000
    seed: int = 1337


def run_founding_wakeup_from_config(config: FoundingWakeupConfig) -> FoundingWakeupReport:
    return run_founding_wakeup_mvp(
        num_agents=config.num_agents,
        max_ticks=config.max_ticks,
        seed=config.seed,
    )


__all__ = [
    "RuntimeConfig",
    "FoundingWakeupConfig",
    "FoundingWakeupReport",
    "step_world_once",
    "run_founding_wakeup_mvp",
    "run_founding_wakeup_from_config",
    "build_founding_wakeup_report",
    "handle_protocol_authoring",
]

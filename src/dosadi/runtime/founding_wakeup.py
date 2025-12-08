"""Runtime loop for the Founding Wakeup MVP scenario."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random

from dosadi.agents.core import Action, Goal, GoalHorizon, GoalOrigin, GoalStatus, GoalType, apply_action, decide_next_action, make_goal_id, prepare_navigation_context
from dosadi.agents.groups import (
    Group,
    GroupRole,
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
from dosadi.runtime.eating import (
    maybe_create_get_meal_goal,
    maybe_create_get_water_goal,
    maybe_create_rest_goal,
    maybe_create_supervisor_report_goal,
    update_agent_physical_state,
)
from dosadi.runtime.council_metrics import update_council_metrics_and_staffing
from dosadi.memory.config import MemoryConfig
from dosadi.runtime.memory_runtime import (
    step_agent_memory_maintenance,
    step_agent_sleep_wake,
)
from dosadi.runtime.proto_council import run_proto_council_tuning
from dosadi.runtime.agent_preferences import maybe_update_desired_work_type
from dosadi.runtime.protocol_authoring import maybe_author_movement_protocols
from dosadi.runtime.queue_episodes import QueueEpisodeEmitter
from dosadi.runtime.queues import process_all_queues
from dosadi.state import WorldState
from dosadi.world.scenarios.founding_wakeup import generate_founding_wakeup_mvp
from dosadi.systems.protocols import ProtocolStatus, ProtocolType


@dataclass
class RuntimeConfig:
    """Tunable configuration for the Founding Wakeup MVP runtime."""

    pod_meeting_interval_ticks: int = 120
    council_meeting_cooldown_ticks: int = 80
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
    success: Dict[str, bool] = field(default_factory=dict)


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
        if not agent.physical.is_sleeping:
            agent.total_ticks_employed += 1.0
        maybe_update_desired_work_type(world, agent)
        maybe_create_get_meal_goal(world, agent)
        maybe_create_get_water_goal(world, agent)
        maybe_create_rest_goal(world, agent)
        maybe_create_supervisor_report_goal(world, agent)

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
        maybe_author_movement_protocols(
            world=world, dangerous_edge_ids=dangerous_edge_ids, tick=tick
        )


def _phase_B_agent_decisions(world: WorldState, tick: int) -> Dict[str, Action]:
    actions_by_agent: Dict[str, Action] = {}

    topology, neighbors, well_core_id, rng = prepare_navigation_context(world)

    for agent_id, agent in world.agents.items():
        if getattr(agent, "is_asleep", False) and not agent.physical.is_sleeping:
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


def _gather_information_goal_exists(world: WorldState) -> bool:
    from dosadi.agents import groups as groups_module

    for group in getattr(world, "groups", []):
        if group.group_type != GroupType.COUNCIL:
            continue

        for goal_id in getattr(group, "goal_ids", []):
            goal = groups_module._GOAL_REGISTRY.get(goal_id)  # noqa: SLF001
            if goal and goal.goal_type == GoalType.GATHER_INFORMATION:
                return True

    for agent in world.agents.values():
        for goal in getattr(agent, "goals", []):
            if goal.goal_type == GoalType.GATHER_INFORMATION and goal.origin == GoalOrigin.GROUP_DECISION:
                return True
    return False


def _count_protocol_reads(world: WorldState, protocol_id: str) -> int:
    readers: set[str] = set()
    for agent in world.agents.values():
        buffers = getattr(agent, "episodes", None)
        if not buffers:
            continue
        for ep in list(getattr(buffers, "short_term", [])) + list(getattr(buffers, "daily", [])):
            if getattr(ep, "verb", "") != "READ_PROTOCOL":
                continue
            if getattr(ep, "metadata", {}).get("protocol_id") == protocol_id:
                readers.add(agent.agent_id)
    return len(readers)


def _pod_representatives(world: WorldState) -> Dict[str, List[str]]:
    reps: Dict[str, List[str]] = {}
    for group in getattr(world, "groups", []):
        if group.group_type != GroupType.POD:
            continue
        pod_id = group.parent_location_id or group.group_id
        reps[pod_id] = [aid for aid, roles in group.roles_by_agent.items() if GroupRole.POD_REPRESENTATIVE in roles]
    return reps


def _proto_council_members(world: WorldState) -> Tuple[Optional[Group], List[str]]:
    council = None
    for group in getattr(world, "groups", []):
        if group.group_type == GroupType.COUNCIL:
            council = group
            break
    members = council.member_ids if council is not None else []
    return council, members


def _hazard_reduction_achieved(world: WorldState, protocol_baselines: Dict[str, Dict[str, float]]) -> bool:
    registry = getattr(world, "protocols", None)
    metrics = getattr(world, "metrics", {}) or {}
    if registry is None:
        return False

    for protocol in registry.protocols_by_id.values():
        if protocol.protocol_type != ProtocolType.TRAFFIC_AND_SAFETY or protocol.status != ProtocolStatus.ACTIVE:
            continue
        baseline = protocol_baselines.get(protocol.protocol_id, {})
        for edge_id in protocol.covered_edge_ids:
            inc_key = f"incidents:{edge_id}"
            trav_key = f"traversals:{edge_id}"
            pre_incidents = float(baseline.get(inc_key, 0.0))
            pre_traversals = float(baseline.get(trav_key, 0.0))
            post_incidents = float(metrics.get(inc_key, 0.0)) - pre_incidents
            post_traversals = float(metrics.get(trav_key, 0.0)) - pre_traversals
            if pre_traversals <= 0 or post_traversals <= 0:
                continue
            pre_rate = pre_incidents / pre_traversals
            post_rate = post_incidents / post_traversals
            if post_rate < pre_rate:
                return True
    return False


def evaluate_founding_wakeup_success(
    world: WorldState, protocol_baselines: Optional[Dict[str, Dict[str, float]]] = None
) -> Dict[str, bool]:
    reps_by_pod = _pod_representatives(world)
    all_pods_have_reps = bool(reps_by_pod) and all(bool(reps) for reps in reps_by_pod.values())

    council, council_members = _proto_council_members(world)
    pod_rep_ids = {rep for reps in reps_by_pod.values() for rep in reps}
    council_has_two_reps = council is not None and len(pod_rep_ids.intersection(council_members)) >= 2

    info_goal = _gather_information_goal_exists(world)
    registry = getattr(world, "protocols", None)
    active_protocols = []
    if registry is not None:
        active_protocols = [
            p
            for p in registry.protocols_by_id.values()
            if p.protocol_type == ProtocolType.TRAFFIC_AND_SAFETY and p.status == ProtocolStatus.ACTIVE
        ]

    protocol_authored = bool(active_protocols)
    adoption_success = False
    if active_protocols and len(world.agents) > 0:
        for protocol in active_protocols:
            readers = _count_protocol_reads(world, protocol.protocol_id)
            if readers / max(len(world.agents), 1) >= 0.10:
                adoption_success = True
                break

    hazard_reduction = False
    if protocol_baselines is None:
        protocol_baselines = {}
    if active_protocols:
        hazard_reduction = _hazard_reduction_achieved(world, protocol_baselines)

    return {
        "pod_leadership": all_pods_have_reps,
        "proto_council_formed": council_has_two_reps,
        "gather_information_goals": info_goal,
        "protocol_authored": protocol_authored,
        "protocol_adoption": adoption_success,
        "hazard_reduction": hazard_reduction,
    }


def run_founding_wakeup_mvp(num_agents: int, max_ticks: int, seed: int) -> FoundingWakeupReport:
    """Run the documented Founding Wakeup MVP loop and evaluate milestones."""

    world = generate_founding_wakeup_mvp(num_agents=num_agents, seed=seed)
    runtime_cfg = RuntimeConfig(max_ticks=max_ticks)
    world.runtime_config = runtime_cfg
    world.rng.seed(seed)

    protocol_baselines: Dict[str, Dict[str, float]] = {}

    while world.tick < runtime_cfg.max_ticks:
        metrics_snapshot = dict(getattr(world, "metrics", {}) or {})
        step_world_once(world)

        registry = getattr(world, "protocols", None)
        if registry is None:
            continue
        for protocol in registry.protocols_by_id.values():
            if protocol.protocol_type != ProtocolType.TRAFFIC_AND_SAFETY or protocol.status != ProtocolStatus.ACTIVE:
                continue
            protocol_baselines.setdefault(protocol.protocol_id, metrics_snapshot)

    report = build_founding_wakeup_report(world, protocol_baselines)
    return report


def build_founding_wakeup_report(
    world: WorldState, protocol_baselines: Optional[Dict[str, Dict[str, float]]] = None
) -> FoundingWakeupReport:
    summary = {
        "ticks": world.tick,
        "agents": len(world.agents),
        "groups": len(world.groups),
        "protocols": len(world.protocols.protocols_by_id),
    }
    success = evaluate_founding_wakeup_success(world, protocol_baselines)
    return FoundingWakeupReport(world=world, metrics=dict(world.metrics), summary=summary, success=success)


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
]

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
    maybe_create_supervisor_report_goal,
    maybe_update_chronic_physiological_goals,
    chronic_update_agent_physical_state,
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
from dosadi.runtime.protocols import update_protocol_adoption_metrics
from dosadi.runtime.queue_episodes import QueueEpisodeEmitter
from dosadi.runtime.queues import process_all_queues
from dosadi.runtime.success_contracts import (
    ContractResult,
    evaluate_contract,
)
from dosadi.world.construction import process_projects
from dosadi.runtime.work_details import ensure_scout_detail_for_gather_goal
from dosadi.state import WorldState
from dosadi.world.scenarios.founding_wakeup import generate_founding_wakeup_mvp
from dosadi.systems.protocols import ProtocolStatus, ProtocolType
from dosadi.scenarios.founding_wakeup.contracts import build_founding_wakeup_contract


@dataclass
class HazardSnapshot:
    tick: int
    hazard_rate_by_edge: dict[str, float]


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
    min_traversals_for_adoption_check: int = 20
    min_ticks_since_authored_for_adoption_check: int = 200
    min_protocol_adoption_ratio: float = 0.6
    min_edges_for_hazard_check: int = 1
    min_baseline_hazard_rate: float = 0.05
    min_hazard_reduction_fraction: float = 0.30


# Alias used in docs/specs
FoundingWakeupRuntimeConfig = RuntimeConfig


@dataclass
class FoundingWakeupReport:
    world: WorldState
    metrics: Dict[str, float]
    summary: Dict[str, object] = field(default_factory=dict)
    success: Dict[str, bool] = field(default_factory=dict)
    contract_result: ContractResult | None = None


def _step_agent_movement(world: WorldState) -> None:
    for agent_id in sorted(world.agents):
        agent = world.agents[agent_id]
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

    for agent_id in sorted(world.agents):
        agent = world.agents[agent_id]
        step_agent_sleep_wake(world, agent, tick, memory_config)
        step_agent_memory_maintenance(world, agent, tick, memory_config)
        chronic_update_agent_physical_state(world, agent)
        if not agent.physical.is_sleeping:
            agent.total_ticks_employed += 1.0
        maybe_update_desired_work_type(world, agent)
        maybe_update_chronic_physiological_goals(world, agent)
        maybe_create_supervisor_report_goal(world, agent)

    _step_agent_movement(world)
    _phase_A_groups_and_council(world, tick, rng, cfg)
    actions_by_agent = _phase_B_agent_decisions(world, tick)
    _phase_C_apply_actions_and_hazards(world, tick, actions_by_agent)

    if tick % cfg.queue_interval_ticks == 0:
        process_all_queues(world, tick, queue_emitter)

    _maybe_run_proto_council(world, tick)
    update_protocol_adoption_metrics(world, tick)
    update_council_metrics_and_staffing(world)
    process_projects(world, tick=tick)

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
            world=world,
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
        gather_goal = next(
            (
                g
                for g in agent.goals
                if g.goal_type == GoalType.GATHER_INFORMATION and g.status == GoalStatus.ACTIVE
            ),
            None,
        )
        if gather_goal is not None:
            ensure_scout_detail_for_gather_goal(world, agent, gather_goal, tick)
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
    goals = list(getattr(world, "goals", {}).values())

    group_goals = [
        g
        for g in goals
        if g.goal_type == GoalType.GATHER_INFORMATION
        and str(getattr(g, "owner_id", "")).startswith("group:")
    ]
    if not group_goals:
        return False

    for gg in group_goals:
        for ag in goals:
            if (
                ag.goal_type == GoalType.GATHER_INFORMATION
                and str(getattr(ag, "owner_id", "")).startswith("agent:")
                and ag.metadata.get("parent_group_goal_id") == gg.goal_id
                and (
                    ag.status is GoalStatus.COMPLETED
                    or ag.metadata.get("visits_recorded", 0) >= 1
                )
            ):
                return True
    return False


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


def _compute_hazard_rates_for_target_edges(world: WorldState) -> dict[str, float]:
    target_edges: set[str] = set()
    for p in world.protocols.values():
        if p.status is not ProtocolStatus.ACTIVE:
            continue
        field = getattr(p, "field", getattr(p, "protocol_type", None))
        if field != ProtocolType.TRAFFIC_AND_SAFETY:
            continue
        coverage = getattr(p, "coverage", None)
        edge_ids = list(getattr(coverage, "edge_ids", []) or [])
        if hasattr(p, "covered_edge_ids"):
            edge_ids.extend(getattr(p, "covered_edge_ids", []) or [])
        for eid in edge_ids:
            target_edges.add(eid)

    rates: dict[str, float] = {}
    for edge_id in target_edges:
        incidents = world.council_metrics.hazard_incidents_by_edge.get(edge_id, 0)
        traversals = world.council_metrics.traversals_by_edge.get(edge_id, 0)
        if traversals <= 0:
            rate = 0.0
        else:
            rate = incidents / float(traversals)
        rates[edge_id] = rate

    return rates


def _protocol_adoption_ok(world: WorldState, cfg: RuntimeConfig) -> bool:
    registry = getattr(world, "protocols", None)
    if registry is None:
        return False

    protocols = []
    if hasattr(registry, "protocols_by_id"):
        protocols = list(registry.protocols_by_id.values())
    elif isinstance(registry, dict):
        protocols = list(registry.values())
    else:
        values_fn = getattr(registry, "values", None)
        if callable(values_fn):
            protocols = list(values_fn())

    protocols = [
        p
        for p in protocols
        if getattr(p, "status", None) is ProtocolStatus.ACTIVE
        and getattr(p, "protocol_type", getattr(p, "field", None))
        == ProtocolType.TRAFFIC_AND_SAFETY
    ]
    if not protocols:
        return False

    candidates: List = []
    for p in protocols:
        m = getattr(p, "adoption", None)
        if m is None or m.total_traversals < cfg.min_traversals_for_adoption_check:
            continue
        authored_tick = getattr(p, "authored_at_tick", getattr(p, "created_at_tick", 0))
        if m.last_observed_tick is not None:
            if (
                m.last_observed_tick - authored_tick
                < cfg.min_ticks_since_authored_for_adoption_check
            ):
                continue
        candidates.append(p)

    if not candidates:
        return False

    total_traversals = sum(
        getattr(p.adoption, "total_traversals", 0) for p in candidates if getattr(p, "adoption", None)
    )
    conforming_traversals = sum(
        getattr(p.adoption, "conforming_traversals", 0)
        for p in candidates
        if getattr(p, "adoption", None)
    )
    if total_traversals == 0:
        return False

    ratio = conforming_traversals / float(total_traversals)
    return ratio >= cfg.min_protocol_adoption_ratio


def _hazard_reduction_ok(
    baseline: HazardSnapshot | None,
    final: HazardSnapshot | None,
    cfg: FoundingWakeupRuntimeConfig,
) -> bool:
    if baseline is None or final is None:
        return False

    edges = set(baseline.hazard_rate_by_edge.keys()) | set(final.hazard_rate_by_edge.keys())
    if len(edges) < cfg.min_edges_for_hazard_check:
        return False

    baseline_vals = [baseline.hazard_rate_by_edge.get(e, 0.0) for e in edges]
    final_vals = [final.hazard_rate_by_edge.get(e, 0.0) for e in edges]

    if not baseline_vals:
        return False

    baseline_avg = sum(baseline_vals) / float(len(baseline_vals))
    final_avg = sum(final_vals) / float(len(final_vals))

    # If there basically wasn't a hazard problem, don't demand a reduction
    if baseline_avg < cfg.min_baseline_hazard_rate:
        return True

    required_max_final = baseline_avg * (1.0 - cfg.min_hazard_reduction_fraction)
    return final_avg <= required_max_final


def evaluate_founding_wakeup_success(
    world: WorldState,
    baseline_snapshot: HazardSnapshot | None = None,
    final_snapshot: HazardSnapshot | None = None,
    cfg: Optional[RuntimeConfig] = None,
) -> Dict[str, bool]:
    cfg = cfg or getattr(world, "runtime_config", None) or RuntimeConfig()
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
    adoption_success = _protocol_adoption_ok(world, cfg)

    hazard_reduction = _hazard_reduction_ok(baseline_snapshot, final_snapshot, cfg)

    success_flags = {
        "pod_leadership": all_pods_have_reps,
        "proto_council_formed": council_has_two_reps,
        "gather_information_goals": info_goal,
        "protocol_authored": protocol_authored,
        "protocol_adoption": adoption_success,
        "hazard_reduction": hazard_reduction,
    }

    success_flags["scenario_success"] = all(success_flags.values())
    return success_flags


def run_founding_wakeup_mvp(num_agents: int, max_ticks: int, seed: int) -> FoundingWakeupReport:
    """Run the documented Founding Wakeup MVP loop and evaluate milestones."""

    random.seed(seed)
    world = generate_founding_wakeup_mvp(num_agents=num_agents, seed=seed)
    runtime_cfg = RuntimeConfig(max_ticks=max_ticks)
    world.runtime_config = runtime_cfg
    world.rng.seed(seed)

    contract_bundle = build_founding_wakeup_contract(scenario_id="founding_wakeup_mvp", max_ticks=max_ticks)
    world.contract_cfg = contract_bundle.config
    world.active_contract = contract_bundle.contract

    contract_result: ContractResult | None = None

    baseline_snapshot: HazardSnapshot | None = None
    final_snapshot: HazardSnapshot | None = None

    while world.tick < runtime_cfg.max_ticks:
        step_world_once(world)
        current_tick = world.tick

        contract_result = contract_result or evaluate_contract(world, current_tick)
        if contract_result is not None and contract_result.ended_reason in {"SUCCESS", "FAILURE"}:
            break

        if baseline_snapshot is None:
            registry = getattr(world, "protocols", None)
            protocols = registry.values() if registry is not None else []
            has_traffic_protocol = any(
                p.status is ProtocolStatus.ACTIVE
                and getattr(p, "field", getattr(p, "protocol_type", None))
                == ProtocolType.TRAFFIC_AND_SAFETY
                for p in protocols
            )
            if has_traffic_protocol:
                baseline_snapshot = HazardSnapshot(
                    tick=current_tick,
                    hazard_rate_by_edge=_compute_hazard_rates_for_target_edges(world),
                )

    final_snapshot = HazardSnapshot(
        tick=world.tick,
        hazard_rate_by_edge=_compute_hazard_rates_for_target_edges(world),
    )

    if contract_result is None:
        contract_result = evaluate_contract(world, world.tick) or ContractResult(
            contract_id=world.active_contract.contract_id if world.active_contract else "founding_wakeup_contract_v1",
            scenario_id="founding_wakeup_mvp",
            tick_end=world.tick,
            ended_reason="TIMEOUT",
            ended_detail=f"timeout at tick {world.tick}",
            milestones=list(getattr(world.active_contract, "milestones", [])),
        )

    report = build_founding_wakeup_report(
        world=world,
        cfg=runtime_cfg,
        baseline_snapshot=baseline_snapshot,
        final_snapshot=final_snapshot,
        contract_result=contract_result,
    )
    return report


def build_founding_wakeup_report(
    world: WorldState,
    cfg: Optional[RuntimeConfig] = None,
    baseline_snapshot: HazardSnapshot | None = None,
    final_snapshot: HazardSnapshot | None = None,
    contract_result: ContractResult | None = None,
) -> FoundingWakeupReport:
    cfg = cfg or getattr(world, "runtime_config", None) or RuntimeConfig()
    summary = {
        "ticks": world.tick,
        "agents": len(world.agents),
        "groups": len(world.groups),
        "protocols": len(world.protocols.protocols_by_id),
    }
    if contract_result is not None:
        summary["ended_reason"] = contract_result.ended_reason
        summary["ended_detail"] = contract_result.ended_detail
    success = evaluate_founding_wakeup_success(
        world=world,
        baseline_snapshot=baseline_snapshot,
        final_snapshot=final_snapshot,
        cfg=cfg,
    )
    summary["scenario_success"] = success.get("scenario_success", False)
    flags = {
        key: "OK" if success.get(key) else "MISSING"
        for key in (
            "pod_leadership",
            "proto_council_formed",
            "gather_information_goals",
            "protocol_authored",
            "protocol_adoption",
            "hazard_reduction",
        )
    }
    flags["scenario_success"] = "OK" if summary["scenario_success"] else "MISSING"
    summary["flags"] = flags
    return FoundingWakeupReport(
        world=world,
        metrics=dict(world.metrics),
        summary=summary,
        success=success,
        contract_result=contract_result,
    )


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
    "FoundingWakeupRuntimeConfig",
    "FoundingWakeupConfig",
    "FoundingWakeupReport",
    "step_world_once",
    "run_founding_wakeup_mvp",
    "run_founding_wakeup_from_config",
    "build_founding_wakeup_report",
]

"""Wakeup Scenario Prime builder (D-SCEN-0001)."""
from __future__ import annotations

import random

from dataclasses import dataclass, field
from typing import Iterable, List

from dosadi.agents.core import (
    AgentState,
    Goal,
    GoalHorizon,
    GoalOrigin,
    GoalStatus,
    GoalType,
    create_agent,
    make_goal_id,
)
from dosadi.agents.groups import Group, GroupRole, create_pod_group, maybe_form_proto_council
from dosadi.law import FacilityProtocolTuning
from dosadi.memory.config import MemoryConfig
from dosadi.runtime.queues import QueueLifecycleState, QueuePriorityRule, QueueState
from dosadi.state import WorldState
from dosadi.world.layout_prime import DEFAULT_PODS, build_habitat_layout_prime


@dataclass(slots=True)
class WakeupPrimeScenarioConfig:
    num_agents: int = 240
    seed: int = 1337
    include_canteen: bool = True
    include_hazard_spurs: bool = True
    max_ticks: int = 10_000
    basic_suit_stock: int | None = None


@dataclass
class WakeupPrimeReport:
    world: WorldState
    agents: List[AgentState] = field(default_factory=list)
    queues: List[object] = field(default_factory=list)
    config: WakeupPrimeScenarioConfig = field(default_factory=WakeupPrimeScenarioConfig)
    metadata: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)


def _initial_wakeup_goals(owner_id: str) -> List[Goal]:
    suit_goal = Goal(
        goal_id=make_goal_id("goal"),
        owner_id=owner_id,
        goal_type=GoalType.ACQUIRE_RESOURCE,
        description="Acquire suit from issue point",
        target={"location_id": "fac:suit-issue-1"},
        priority=0.75,
        urgency=0.4,
        horizon=GoalHorizon.SHORT,
        status=GoalStatus.PENDING,
        origin=GoalOrigin.INTERNAL_STATE,
    )
    suit_goal.kind = "get_suit"

    assignment_goal = Goal(
        goal_id=make_goal_id("goal"),
        owner_id=owner_id,
        goal_type=GoalType.ACQUIRE_RESOURCE,
        description="Obtain assignment",
        target={"location_id": "fac:assign-hall-1"},
        priority=0.7,
        urgency=0.35,
        horizon=GoalHorizon.SHORT,
        status=GoalStatus.PENDING,
        origin=GoalOrigin.INTERNAL_STATE,
    )
    assignment_goal.kind = "get_assignment"

    return [suit_goal, assignment_goal]


def _register_wakeup_queues(world: WorldState) -> List[QueueState]:
    """Create and register Wakeup Scenario Prime queues."""

    suit_queue = QueueState(
        queue_id="queue:suit-issue",
        location_id="queue:suit-issue:front",
        associated_facility="fac:suit-issue-1",
        priority_rule=QueuePriorityRule.FIFO,
        processing_rate=2,
        process_interval_ticks=100,
        state=QueueLifecycleState.ACTIVE,
    )

    assignment_queue = QueueState(
        queue_id="queue:assignment",
        location_id="queue:assignment:front",
        associated_facility="fac:assign-hall-1",
        priority_rule=QueuePriorityRule.FIFO,
        processing_rate=2,
        process_interval_ticks=120,
        state=QueueLifecycleState.ACTIVE,
    )

    world.register_queue(suit_queue)
    world.register_queue(assignment_queue)

    return [suit_queue, assignment_queue]


def _create_agents(num_agents: int, pods: Iterable[str], seed: int) -> List[AgentState]:
    agents: List[AgentState] = []
    pod_ids = list(pods) or list(DEFAULT_PODS)
    pod_count = len(pod_ids)
    rng = None
    try:
        import random

        rng = random.Random(seed)
    except Exception:
        rng = None

    for i in range(num_agents):
        pod_location_id = pod_ids[i % pod_count]
        agent_id = f"agent:{i}"
        name = f"Colonist {i}"
        agent = create_agent(agent_id=agent_id, name=name, pod_location_id=pod_location_id, rng=rng)
        agent.goals.extend(_initial_wakeup_goals(agent.agent_id))
        agents.append(agent)

    return agents


def _initialize_pod_groups(world: WorldState, pod_ids: Iterable[str]) -> List[Group]:
    groups: List[Group] = []
    pod_members: dict[str, list[str]] = {pid: [] for pid in pod_ids}

    for agent in world.agents.values():
        pod_members.setdefault(agent.location_id, []).append(agent.agent_id)

    for pod_id, members in pod_members.items():
        group = create_pod_group(pod_location_id=pod_id, member_ids=members, tick=world.tick)
        if members:
            rep_id = members[0]
            roles = group.roles_by_agent.setdefault(rep_id, [])
            if GroupRole.POD_REPRESENTATIVE not in roles:
                roles.append(GroupRole.POD_REPRESENTATIVE)
        groups.append(group)
        world.groups.append(group)

    council = maybe_form_proto_council(
        groups=world.groups,
        agents_by_id=world.agents,
        tick=world.tick,
        hub_location_id="corr:main-core",
    )

    if council is not None:
        world.council_agent_ids = list(council.member_ids)

    return groups


def _seed_risk_metrics(world: WorldState) -> None:
    metrics = getattr(world, "metrics", None)
    if metrics is None or not isinstance(metrics, dict):
        metrics = {}

    hazard_edges = [
        edge for edge in world.edges.values() if getattr(edge, "base_hazard_prob", 0.0) >= 0.15
    ]

    for edge in hazard_edges:
        traversals_key = f"traversals:{edge.id}"
        incidents_key = f"incidents:{edge.id}"
        traversals = float(metrics.get(traversals_key, 12.0))
        incidents_default = max(1.0, round(traversals * max(0.15, edge.base_hazard_prob)))
        metrics.setdefault(traversals_key, traversals)
        metrics.setdefault(incidents_key, incidents_default)

    world.metrics = metrics


def generate_wakeup_scenario_prime(config: WakeupPrimeScenarioConfig) -> WakeupPrimeReport:
    """Build the initial world + agents for Wakeup Scenario Prime."""

    layout = build_habitat_layout_prime(
        include_canteen=config.include_canteen, include_hazard_spurs=config.include_hazard_spurs
    )
    world = WorldState(seed=config.seed)
    world.rng.seed(config.seed)

    memory_config = MemoryConfig()
    world.memory_config = memory_config

    world.policy["topology"] = layout.to_topology()
    world.nodes = layout.nodes
    world.edges = layout.edges

    world.facilities = {
        node_id: node
        for node_id, node in layout.nodes.items()
        if getattr(node, "kind", None) == "facility"
    }

    world.service_facilities.setdefault("suit_issue", []).append("fac:suit-issue-1")
    world.service_facilities.setdefault("assignment_hall", []).append("fac:assign-hall-1")

    for fac_id in world.facilities.keys():
        world.facility_protocol_tuning.setdefault(
            fac_id, FacilityProtocolTuning(facility_id=fac_id)
        )

    pods = [pid for pid in layout.nodes.keys() if pid.startswith("pod:")]
    agents = _create_agents(config.num_agents, pods, config.seed)
    for agent in agents:
        world.register_agent(agent)
        _initialize_agent_sleep_schedule(agent, world, memory_config)

    queues = _register_wakeup_queues(world)

    num_agents = len(agents)
    default_suits = getattr(config, "basic_suit_stock", None)
    world.basic_suit_stock = num_agents if default_suits is None else default_suits

    _initialize_pod_groups(world, pods)
    _seed_risk_metrics(world)

    metadata = {
        "scenario_id": "wakeup_prime",
        "objectives": (
            "queue_discipline",
            "proto_council_readiness",
            "risk_protocol_feedback",
        ),
    }

    return WakeupPrimeReport(
        world=world,
        agents=agents,
        queues=queues,
        config=config,
        metadata=metadata,
    )


def _initialize_agent_sleep_schedule(
    agent: AgentState,
    world: WorldState,
    memory_config: MemoryConfig,
) -> None:
    """
    Give each agent a personal sleep/wake phase.

    For MVP, assign a random offset across the day so not everyone sleeps at once.
    """

    ticks_per_day = getattr(world, "ticks_per_day", 144_000)

    offset = random.randint(0, ticks_per_day - 1)

    agent.is_asleep = False
    agent.next_sleep_tick = offset
    agent.next_wake_tick = agent.next_sleep_tick + memory_config.sleep_duration_ticks

    agent.last_short_term_maintenance_tick = 0
    agent.last_daily_promotion_tick = 0
    agent.last_consolidation_tick = -memory_config.min_consolidation_interval_ticks


__all__ = [
    "WakeupPrimeScenarioConfig",
    "WakeupPrimeReport",
    "generate_wakeup_scenario_prime",
]

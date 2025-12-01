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
from dosadi.memory.config import MemoryConfig
from dosadi.runtime.queues import QueueLifecycleState, QueuePriorityRule, QueueState
from dosadi.state import WorldState
from dosadi.world.layout_prime import DEFAULT_PODS, build_habitat_layout_prime


@dataclass(slots=True)
class WakeupPrimeScenarioConfig:
    num_agents: int = 240
    seed: int = 1337
    include_canteen: bool = True
    basic_suit_stock: int | None = None


@dataclass
class WakeupPrimeReport:
    world: WorldState
    agents: List[AgentState] = field(default_factory=list)
    queues: List[object] = field(default_factory=list)
    config: WakeupPrimeScenarioConfig = field(default_factory=WakeupPrimeScenarioConfig)
    metadata: dict = field(default_factory=dict)


def _initial_wakeup_goals(owner_id: str) -> List[Goal]:
    return [
        Goal(
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
        ),
        Goal(
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
        ),
    ]


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


def generate_wakeup_scenario_prime(config: WakeupPrimeScenarioConfig) -> WakeupPrimeReport:
    """Build the initial world + agents for Wakeup Scenario Prime."""

    layout = build_habitat_layout_prime(include_canteen=config.include_canteen)
    world = WorldState(seed=config.seed)
    world.rng.seed(config.seed)

    memory_config = MemoryConfig()
    world.memory_config = memory_config

    world.policy["topology"] = layout.to_topology()
    world.nodes = layout.nodes
    world.edges = layout.edges

    pods = [pid for pid in layout.nodes.keys() if pid.startswith("pod:")]
    agents = _create_agents(config.num_agents, pods, config.seed)
    for agent in agents:
        world.register_agent(agent)
        _initialize_agent_sleep_schedule(agent, world, memory_config)

    queues = _register_wakeup_queues(world)

    num_agents = len(agents)
    default_suits = getattr(config, "basic_suit_stock", None)
    world.basic_suit_stock = num_agents if default_suits is None else default_suits

    return WakeupPrimeReport(
        world=world,
        agents=agents,
        queues=queues,
        config=config,
        metadata={"scenario_id": "wakeup_prime"},
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

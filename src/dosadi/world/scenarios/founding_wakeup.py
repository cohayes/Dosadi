"""Founding Wakeup MVP world generation.

Constructs the minimal topology and initial colonist population described in
``docs/latest/11_scenarios/D-SCEN-0002_Founding_Wakeup_MVP_Scenario.md``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional, Tuple
import random

from dosadi.agents.core import AgentState, initialize_agents_for_founding_wakeup
from dosadi.agents.core import Goal, GoalHorizon, GoalOrigin, GoalStatus, GoalType, make_goal_id
from dosadi.agents.groups import create_pod_group
from dosadi.law import FacilityProtocolTuning
from dosadi.memory.config import MemoryConfig
from dosadi.runtime.work_details import WorkDetailType
from dosadi.runtime.queues import QueueLifecycleState, QueuePriorityRule, QueueState
from ...state import FactionState, WorldState
from ..environment import get_or_create_place_env
from ..constants import WATER_DAILY_CAPACITY
from ..survey_map import SurveyNode


@dataclass(frozen=True)
class LocationNode:
    """Lightweight location representation for the founding wakeup layout."""

    id: str
    name: str
    type: str
    kind: Optional[str] = None
    tags: Tuple[str, ...] = ()
    is_well_core: bool = False
    water_stock: float = 0.0
    water_capacity: float = 0.0


@dataclass(frozen=True)
class LocationEdge:
    """Undirected edge connecting two locations with a hazard probability."""

    id: str
    a: str
    b: str
    base_hazard_prob: float


@dataclass
class FacilityState:
    """Mutable facility representation with water storage fields."""

    id: str
    name: str
    type: str
    kind: Optional[str] = None
    location_id: Optional[str] = None
    ward: str = "ward:core"
    tags: Tuple[str, ...] = ()
    water_stock: float = 0.0
    water_capacity: float = 0.0


POD_IDS: Tuple[str, ...] = (
    "loc:pod-1",
    "loc:pod-2",
    "loc:pod-3",
    "loc:pod-4",
)


CORRIDOR_IDS: Tuple[str, ...] = (
    "loc:corridor-2A",
    "loc:corridor-3A",
    "loc:corridor-7A",
)


JUNCTION_ID = "loc:junction-7A-7B"
WELL_CORE_ID = "loc:well-core"


BASE_NODES: Tuple[LocationNode, ...] = (
    LocationNode(id="loc:pod-1", name="Pod 1", type="pod", tags=("sealed", "safe", "residential")),
    LocationNode(id="loc:pod-2", name="Pod 2", type="pod", tags=("sealed", "safe", "residential")),
    LocationNode(id="loc:pod-3", name="Pod 3", type="pod", tags=("sealed", "safe", "residential")),
    LocationNode(id="loc:pod-4", name="Pod 4", type="pod", tags=("sealed", "safe", "residential")),
    LocationNode(id="loc:corridor-2A", name="Corridor 2A", type="corridor"),
    LocationNode(id="loc:corridor-3A", name="Corridor 3A", type="corridor"),
    LocationNode(id="loc:corridor-7A", name="Corridor 7A", type="corridor"),
    LocationNode(id=JUNCTION_ID, name="Junction 7A-7B", type="junction"),
    LocationNode(id=WELL_CORE_ID, name="Well Core", type="hub", is_well_core=True),
    LocationNode(
        id="loc:well-head-core",
        name="Well Head",
        type="facility",
        kind="well_head",
        tags=("well_head",),
        water_stock=0.0,
        water_capacity=0.0,
    ),
    LocationNode(
        id="loc:depot-water-1",
        name="Water Depot 1",
        type="facility",
        kind="water_depot",
        tags=("water_depot",),
        water_stock=2_000.0,
        water_capacity=5_000.0,
    ),
    LocationNode(
        id="loc:tap-1",
        name="Water Tap 1",
        type="facility",
        kind="water_tap",
        tags=("water_tap",),
    ),
    LocationNode(
        id="loc:mess-hall-1",
        name="Mess Hall 1",
        type="facility",
        kind="mess_hall",
        tags=("mess_hall",),
    ),
    LocationNode(
        id="loc:suit-issue-1",
        name="Suit Issue Point 1",
        type="facility",
        kind="suit_issue",
        tags=("suit_issue",),
    ),
    LocationNode(
        id="loc:assign-hall-1",
        name="Assignment Hall 1",
        type="facility",
        kind="assignment_hall",
        tags=("assignment_hall",),
    ),
)

BASE_EDGES: Tuple[LocationEdge, ...] = (
    LocationEdge(id="edge:pod-1:corridor-2A", a="loc:pod-1", b="loc:corridor-2A", base_hazard_prob=0.02),
    LocationEdge(id="edge:corridor-2A:well", a="loc:corridor-2A", b=WELL_CORE_ID, base_hazard_prob=0.02),
    LocationEdge(id="edge:pod-2:corridor-3A", a="loc:pod-2", b="loc:corridor-3A", base_hazard_prob=0.02),
    LocationEdge(id="edge:pod-3:corridor-3A", a="loc:pod-3", b="loc:corridor-3A", base_hazard_prob=0.02),
    LocationEdge(id="edge:corridor-3A:well", a="loc:corridor-3A", b=WELL_CORE_ID, base_hazard_prob=0.02),
    LocationEdge(id="edge:pod-4:corridor-7A", a="loc:pod-4", b="loc:corridor-7A", base_hazard_prob=0.20),
    LocationEdge(id="edge:corridor-7A:junction-7A-7B", a="loc:corridor-7A", b=JUNCTION_ID, base_hazard_prob=0.20),
    LocationEdge(id="edge:junction-7A-7B:well", a=JUNCTION_ID, b=WELL_CORE_ID, base_hazard_prob=0.05),
    LocationEdge(id="edge:well:well-head", a=WELL_CORE_ID, b="loc:well-head-core", base_hazard_prob=0.01),
    LocationEdge(id="edge:well:water-depot-1", a=WELL_CORE_ID, b="loc:depot-water-1", base_hazard_prob=0.01),
    LocationEdge(id="edge:well:tap-1", a=WELL_CORE_ID, b="loc:tap-1", base_hazard_prob=0.01),
    LocationEdge(id="edge:mess-hall-1:well", a="loc:mess-hall-1", b=WELL_CORE_ID, base_hazard_prob=0.01),
    LocationEdge(id="edge:well:suit-issue-1", a=WELL_CORE_ID, b="loc:suit-issue-1", base_hazard_prob=0.01),
    LocationEdge(id="edge:well:assign-hall-1", a=WELL_CORE_ID, b="loc:assign-hall-1", base_hazard_prob=0.01),
)


def _initial_wakeup_goals(owner_id: str) -> List[Goal]:
    """Seed suit + assignment goals to drive queue discipline."""

    suit_goal = Goal(
        goal_id=make_goal_id("goal"),
        owner_id=owner_id,
        goal_type=GoalType.ACQUIRE_RESOURCE,
        description="Acquire suit from issue point",
        target={"location_id": "loc:suit-issue-1"},
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
        target={"location_id": "loc:assign-hall-1"},
        priority=0.7,
        urgency=0.35,
        horizon=GoalHorizon.SHORT,
        status=GoalStatus.PENDING,
        origin=GoalOrigin.INTERNAL_STATE,
    )
    assignment_goal.kind = "get_assignment"

    return [suit_goal, assignment_goal]


def _register_wakeup_queues(world: WorldState) -> List[QueueState]:
    """Create and register founding wakeup queues for scarce services."""

    suit_queue = QueueState(
        queue_id="queue:suit-issue",
        location_id="queue:suit-issue:front",
        associated_facility="loc:suit-issue-1",
        priority_rule=QueuePriorityRule.FIFO,
        processing_rate=2,
        process_interval_ticks=100,
        state=QueueLifecycleState.ACTIVE,
    )

    assignment_queue = QueueState(
        queue_id="queue:assignment",
        location_id="queue:assignment:front",
        associated_facility="loc:assign-hall-1",
        priority_rule=QueuePriorityRule.FIFO,
        processing_rate=2,
        process_interval_ticks=120,
        state=QueueLifecycleState.ACTIVE,
    )

    world.register_queue(suit_queue)
    world.register_queue(assignment_queue)

    return [suit_queue, assignment_queue]


def _seed_risk_metrics(world: WorldState) -> None:
    """Prime traversal/incident metrics based on base hazard to trigger early protocols."""

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


def _initialize_pod_groups(world: WorldState, pod_ids: Iterable[str]) -> None:
    pod_members: Dict[str, List[str]] = {pid: [] for pid in pod_ids}

    for agent in world.agents.values():
        pod_members.setdefault(agent.location_id, []).append(agent.agent_id)

    for pod_id, members in pod_members.items():
        group = create_pod_group(pod_location_id=pod_id, member_ids=members, tick=world.tick)
        world.groups.append(group)


def generate_founding_wakeup_mvp(num_agents: int, seed: int) -> WorldState:
    """Construct the Founding Wakeup MVP topology and initial population."""

    world = WorldState(seed=seed)
    world.rng.seed(seed)
    planner_cfg = world.expansion_planner_cfg
    planner_state = world.expansion_planner_state
    planner_state.next_plan_day = seed % max(1, planner_cfg.planning_interval_days)
    memory_config = MemoryConfig()
    world.memory_config = memory_config
    world.well.daily_capacity = WATER_DAILY_CAPACITY
    world.well.well_id = "loc:well-head-core"
    world.desired_work_details[WorkDetailType.SCOUT_INTERIOR] = 8
    world.desired_work_details[WorkDetailType.SCOUT_EXTERIOR] = 4
    world.desired_work_details[WorkDetailType.INVENTORY_STORES] = 6
    world.desired_work_details[WorkDetailType.ENV_CONTROL] = 4
    world.desired_work_details[WorkDetailType.FOOD_PROCESSING_DETAIL] = 4
    world.desired_work_details[WorkDetailType.SCRIBE_DETAIL] = 2
    world.desired_work_details[WorkDetailType.DISPATCH_DETAIL] = 1
    world.desired_work_details[WorkDetailType.WATER_HANDLING] = 2
    topology_nodes = [asdict(node) for node in BASE_NODES]
    topology_edges = [asdict(edge) for edge in BASE_EDGES]
    world.policy["topology"] = {
        "nodes": topology_nodes,
        "edges": topology_edges,
        "id": "founding_wakeup_mvp",
    }
    world.nodes = {node.id: node for node in BASE_NODES}
    world.edges = {edge.id: edge for edge in BASE_EDGES}
    world.facilities = {}
    for node in BASE_NODES:
        if getattr(node, "kind", None):
            world.facilities[node.id] = FacilityState(
                id=node.id,
                name=node.name,
                type=node.type,
                kind=node.kind,
                location_id=node.id,
                tags=node.tags,
                water_stock=node.water_stock,
                water_capacity=node.water_capacity,
            )

    for fac_id in world.facilities.keys():
        world.facility_protocol_tuning.setdefault(fac_id, FacilityProtocolTuning(facility_id=fac_id))
    world.service_facilities.setdefault("suit_issue", []).append("loc:suit-issue-1")
    world.service_facilities.setdefault("assignment_hall", []).append("loc:assign-hall-1")
    world.places = world.nodes
    world.water_tap_sources["loc:tap-1"] = "loc:depot-water-1"

    colonist_faction = FactionState(
        id="faction:colonists",
        name="Founding Colonists",
        archetype="CIVIC",
        home_ward=WELL_CORE_ID,
    )
    world.register_faction(colonist_faction)

    pod_ids = ["loc:pod-1", "loc:pod-2", "loc:pod-3", "loc:pod-4"]
    agents = initialize_agents_for_founding_wakeup(num_agents=num_agents, seed=seed, pod_ids=pod_ids)

    for agent in agents:
        colonist_faction.members.append(agent.id)
        world.register_agent(agent)
        _initialize_agent_sleep_schedule(agent, world, memory_config)
        agent.goals.extend(_initial_wakeup_goals(agent.agent_id))

    _register_wakeup_queues(world)
    world.basic_suit_stock = len(agents)

    _initialize_pod_groups(world, pod_ids)
    _seed_risk_metrics(world)
    world.scenario_metadata = {
        "scenario_id": "founding_wakeup_mvp",
        "objectives": (
            "queue_discipline",
            "proto_council_readiness",
            "risk_protocol_feedback",
        ),
    }

    world.survey_map.upsert_node(
        SurveyNode(
            node_id="loc:survey-outpost-1",
            kind="outpost_site",
            ward_id=WELL_CORE_ID,
            water=5.0,
            hazard=0.1,
            tags=("resource_rich",),
            confidence=0.8,
            last_seen_tick=world.tick,
        ),
        confidence_delta=0.2,
    )

    initialize_environment_for_founding_wakeup(world)

    return world


def initialize_environment_for_founding_wakeup(world: WorldState) -> None:
    for place_id, facility in world.places.items():
        env = get_or_create_place_env(world, place_id)

        kind = getattr(facility, "kind", None) or getattr(facility, "type", None)
        if kind in {"pod", "bunk_pod"}:
            env.comfort = 0.7
        elif kind in {"mess_hall"}:
            env.comfort = 0.65
        elif kind in {"corridor", "junction"}:
            env.comfort = 0.4
        elif kind in {"store", "depot", "water_depot"}:
            env.comfort = 0.45
        elif kind in {"well_head"}:
            env.comfort = 0.4
        else:
            env.comfort = 0.5


def _initialize_agent_sleep_schedule(agent: AgentState, world: WorldState, memory_config: MemoryConfig) -> None:
    ticks_per_day = getattr(world, "ticks_per_day", 144_000)

    offset = random.randint(0, ticks_per_day - 1)

    agent.is_asleep = False
    agent.next_sleep_tick = offset
    agent.next_wake_tick = agent.next_sleep_tick + memory_config.sleep_duration_ticks

    agent.last_short_term_maintenance_tick = 0
    agent.last_daily_promotion_tick = 0
    agent.last_consolidation_tick = -memory_config.min_consolidation_interval_ticks


__all__ = [
    "generate_founding_wakeup_mvp",
    "LocationNode",
    "LocationEdge",
    "FacilityState",
]

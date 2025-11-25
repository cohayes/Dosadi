"""Founding Wakeup MVP world generation.

Constructs the minimal topology and initial colonist population described in
``docs/latest/11_scenarios/D-SCEN-0002_Founding_Wakeup_MVP_Scenario.md``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple

from dosadi.agents.core import AgentState, initialize_agents_for_founding_wakeup
from dosadi.agents.groups import create_pod_group
from ...state import FactionState, WorldState


@dataclass(frozen=True)
class LocationNode:
    """Lightweight location representation for the founding wakeup layout."""

    id: str
    name: str
    type: str
    tags: Tuple[str, ...] = ()
    is_well_core: bool = False


@dataclass(frozen=True)
class LocationEdge:
    """Undirected edge connecting two locations with a hazard probability."""

    id: str
    a: str
    b: str
    base_hazard_prob: float


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
)


def generate_founding_wakeup_mvp(num_agents: int, seed: int) -> WorldState:
    """Construct the Founding Wakeup MVP topology and initial population."""

    world = WorldState(seed=seed)
    world.rng.seed(seed)
    topology_nodes = [asdict(node) for node in BASE_NODES]
    topology_edges = [asdict(edge) for edge in BASE_EDGES]
    world.policy["topology"] = {
        "nodes": topology_nodes,
        "edges": topology_edges,
        "id": "founding_wakeup_mvp",
    }
    world.nodes = {node.id: node for node in BASE_NODES}
    world.edges = {edge.id: edge for edge in BASE_EDGES}

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

    # Create pod groups based on initial occupancy
    pod_members: Dict[str, List[str]] = {pid: [] for pid in pod_ids}
    for agent in agents:
        pod_members.setdefault(agent.location_id, []).append(agent.agent_id)

    for pod_id, members in pod_members.items():
        group = create_pod_group(pod_location_id=pod_id, member_ids=members, tick=world.tick)
        world.groups.append(group)

    return world


__all__ = ["generate_founding_wakeup_mvp", "LocationNode", "LocationEdge"]

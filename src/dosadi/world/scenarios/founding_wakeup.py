"""Founding Wakeup MVP world generation.

Constructs the minimal topology and initial colonist population described in
``docs/latest/11_scenarios/D-SCEN-0002_Founding_Wakeup_MVP_Scenario.md``.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple

from ...state import AgentState, AffectState, BodyState, FactionState, WorldState


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


def _even_pod_assignment(num_agents: int) -> List[str]:
    """Return a round-robin pod assignment list for ``num_agents``."""

    assignments: List[str] = []
    for idx in range(num_agents):
        assignments.append(POD_IDS[idx % len(POD_IDS)])
    return assignments


def _sample_affinity_block(rng: random.Random) -> Dict[str, float]:
    return {
        "STR": rng.uniform(8.0, 12.0),
        "DEX": rng.uniform(8.0, 12.0),
        "CON": rng.uniform(8.0, 12.0),
        "INT": rng.uniform(8.0, 12.0),
        "WILL": rng.uniform(8.0, 12.0),
        "CHA": rng.uniform(8.0, 12.0),
    }


def _base_goals() -> List[Dict[str, object]]:
    return [
        {
            "id": "MAINTAIN_SURVIVAL_TODAY",
            "priority": 1.0,
            "horizon": "SHORT",
        },
        {
            "id": "ACQUIRE_RESOURCE",
            "priority": 0.8,
            "horizon": "SHORT",
            "resource": "life_support",
        },
        {
            "id": "SECURE_SHELTER",
            "priority": 0.6,
            "horizon": "SHORT",
        },
    ]


def generate_founding_wakeup_mvp(num_agents: int, seed: int) -> Tuple[WorldState, List[AgentState], List[Dict[str, object]]]:
    """Construct the Founding Wakeup MVP topology and initial population."""

    rng = random.Random(seed)

    world = WorldState(seed=seed)
    world.policy["topology"] = {
        "nodes": [asdict(node) for node in BASE_NODES],
        "edges": [asdict(edge) for edge in BASE_EDGES],
        "id": "founding_wakeup_mvp",
    }

    colonist_faction = FactionState(
        id="faction:colonists",
        name="Founding Colonists",
        archetype="CIVIC",
        home_ward=WELL_CORE_ID,
    )
    world.register_faction(colonist_faction)

    pod_assignments = _even_pod_assignment(num_agents)
    if num_agents > 0:
        leader_count = max(1, int(num_agents * 0.15))
        leader_count = min(num_agents, leader_count)
        leadership_pool = set(rng.sample(range(num_agents), k=leader_count))
    else:
        leadership_pool = set()

    agents: List[AgentState] = []
    for idx in range(num_agents):
        pod_id = pod_assignments[idx]
        agent_id = f"agent:{idx}"
        name = f"Colonist {idx + 1:03d}"

        body = BodyState(
            health=rng.uniform(94.0, 100.0),
            nutrition=rng.uniform(2200.0, 2800.0),
            hydration=rng.uniform(2.4, 3.4),
            stamina=rng.uniform(72.0, 92.0),
            energy=rng.uniform(70.0, 90.0),
            bladder=rng.uniform(0.1, 0.3),
            bowel=rng.uniform(0.05, 0.25),
            body_mass=rng.uniform(55.0, 90.0),
            activity_level=0.15,
        )

        affect = AffectState(
            fear=rng.uniform(0.25, 0.45),
            ambition=rng.uniform(0.35, 0.6),
            loyalty=rng.uniform(0.45, 0.65),
            curiosity=rng.uniform(0.35, 0.6),
            stress=rng.uniform(0.15, 0.35),
        )

        agent = AgentState(
            id=agent_id,
            name=name,
            faction=colonist_faction.id,
            ward=pod_id,
            role="colonist",
            body=body,
            affect=affect,
        )

        agent.affinities.update(_sample_affinity_block(rng))
        agent.identity.add_handle(agent_id)
        agent.social.loyalty[pod_id] = rng.uniform(0.55, 0.75)

        goals = _base_goals()
        if idx in leadership_pool:
            goals.append({"id": "REDUCE_POD_RISK", "priority": 0.75, "horizon": "MEDIUM", "scope": pod_id})
            agent.social.loyalty["communalism"] = rng.uniform(0.6, 0.85)
        agent.memory.beliefs["goals"] = goals

        colonist_faction.members.append(agent.id)
        world.register_agent(agent)
        agents.append(agent)

    groups: List[Dict[str, object]] = []
    return world, agents, groups


__all__ = ["generate_founding_wakeup_mvp", "LocationNode", "LocationEdge"]

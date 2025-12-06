"""Habitat Layout Prime builder (D-WORLD-0100)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Set


@dataclass(frozen=True)
class Location:
    """Minimal location representation for habitat layout graphs."""

    id: str
    name: str
    kind: str
    sealed: bool
    hostile: bool
    conditioned: bool
    capacity_soft: Optional[int] = None
    capacity_hard: Optional[int] = None
    tags: tuple = field(default_factory=tuple)


@dataclass(frozen=True)
class LayoutEdge:
    """Undirected edge connecting two locations."""

    id: str
    a: str
    b: str
    base_hazard_prob: float = 0.0


@dataclass(frozen=True)
class HabitatLayoutPrime:
    """Container for Habitat Layout Prime topology."""

    nodes: MutableMapping[str, Location]
    edges: MutableMapping[str, LayoutEdge]
    adjacency: Mapping[str, Set[str]]

    def to_topology(self) -> Dict[str, List[Dict[str, object]]]:
        return {
            "nodes": [asdict(node) for node in self.nodes.values()],
            "edges": [asdict(edge) for edge in self.edges.values()],
        }


DEFAULT_PODS = ["pod:A", "pod:B", "pod:C", "pod:D"]


def _make_location(
    *,
    loc_id: str,
    kind: str,
    name: Optional[str] = None,
    sealed: bool = False,
    hostile: bool = False,
    conditioned: bool = True,
    capacity_soft: Optional[int] = None,
    capacity_hard: Optional[int] = None,
    tags: Iterable[str] = (),
) -> Location:
    return Location(
        id=loc_id,
        name=name or loc_id,
        kind=kind,
        sealed=sealed,
        hostile=hostile,
        conditioned=conditioned,
        capacity_soft=capacity_soft,
        capacity_hard=capacity_hard,
        tags=tuple(tags),
    )


def build_habitat_layout_prime(
    *,
    pods: Iterable[str] = DEFAULT_PODS,
    include_canteen: bool = True,
    include_hazard_spurs: bool = True,
) -> HabitatLayoutPrime:
    """Build the Habitat Layout Prime graph described in D-WORLD-0100."""

    pod_ids = list(pods)

    adjacency: Dict[str, Set[str]] = {
        pod: {"corr:main-core"} for pod in pod_ids
    }

    adjacency.update(
        {
            "corr:main-core": {
                *pod_ids,
                "corr:med",
                "corr:suit",
                "corr:assign",
                "corr:canteen",
                "corr:holding",
                "corr:survey-a",
                "corr:maintenance-a",
            },
            "corr:med": {"corr:main-core", "fac:med-bay-1", "queue:med-triage:front"},
            "corr:suit": {"corr:main-core", "fac:suit-issue-1", "queue:suit-issue:front"},
            "corr:assign": {"corr:main-core", "fac:assign-hall-1", "queue:assignment:front"},
            "corr:canteen": {"corr:main-core", "fac:canteen-1"},
            "corr:holding": {"corr:main-core", "fac:holding-1"},
            "fac:med-bay-1": {"corr:med"},
            "fac:suit-issue-1": {"corr:suit"},
            "fac:assign-hall-1": {"corr:assign"},
            "fac:canteen-1": {"corr:canteen"},
            "fac:holding-1": {"corr:holding"},
            "queue:med-triage:front": {"corr:med"},
            "queue:suit-issue:front": {"corr:suit"},
            "queue:assignment:front": {"corr:assign"},
            "corr:survey-a": {"corr:main-core", "corr:survey-b"},
            "corr:survey-b": {"corr:survey-a"},
            "corr:maintenance-a": {"corr:main-core", "corr:maintenance-b"},
            "corr:maintenance-b": {"corr:maintenance-a"},
        }
    )

    if not include_canteen:
        adjacency.pop("corr:canteen", None)
        adjacency.pop("fac:canteen-1", None)
        adjacency["corr:main-core"].discard("corr:canteen")

    if not include_hazard_spurs:
        for spur in ["corr:survey-a", "corr:survey-b", "corr:maintenance-a", "corr:maintenance-b"]:
            adjacency.pop(spur, None)
            adjacency["corr:main-core"].discard(spur)

    nodes: Dict[str, Location] = {}

    for pod in pod_ids:
        nodes[pod] = _make_location(
            loc_id=pod,
            kind="pod",
            sealed=True,
            hostile=False,
            conditioned=True,
            capacity_soft=60,
            capacity_hard=64,
            name=f"Hab Pod {pod.split(':')[-1]}",
            tags=("residential", "safe"),
        )

    corridor_defaults = dict(
        kind="corridor",
        sealed=False,
        hostile=True,
        conditioned=True,
        capacity_soft=80,
        capacity_hard=100,
        tags=("transit",),
    )

    for corridor in [
        "corr:main-core",
        "corr:med",
        "corr:suit",
        "corr:assign",
        "corr:canteen",
        "corr:holding",
        "corr:survey-a",
        "corr:survey-b",
        "corr:maintenance-a",
        "corr:maintenance-b",
    ]:
        if corridor == "corr:canteen" and not include_canteen:
            continue
        if not include_hazard_spurs and corridor.startswith("corr:survey"):
            continue
        if not include_hazard_spurs and corridor.startswith("corr:maintenance"):
            continue
        nodes[corridor] = _make_location(loc_id=corridor, name=corridor, **corridor_defaults)

    facility_specs = {
        "fac:med-bay-1": dict(sealed=False, hostile=False, conditioned=True, capacity_soft=12, capacity_hard=16),
        "fac:suit-issue-1": dict(sealed=False, hostile=False, conditioned=True, capacity_soft=20, capacity_hard=24),
        "fac:assign-hall-1": dict(sealed=False, hostile=False, conditioned=True, capacity_soft=25, capacity_hard=30),
        "fac:canteen-1": dict(sealed=False, hostile=False, conditioned=True, capacity_soft=60, capacity_hard=80),
        "fac:holding-1": dict(sealed=True, hostile=False, conditioned=False, capacity_soft=8, capacity_hard=10),
    }

    for facility_id, env in facility_specs.items():
        if facility_id == "fac:canteen-1" and not include_canteen:
            continue
        nodes[facility_id] = _make_location(
            loc_id=facility_id,
            kind="facility",
            name=facility_id,
            **env,
        )

    queue_specs = {
        "queue:med-triage:front": dict(kind="queue", sealed=False, hostile=False, conditioned=True),
        "queue:suit-issue:front": dict(kind="queue", sealed=False, hostile=False, conditioned=True),
        "queue:assignment:front": dict(kind="queue", sealed=False, hostile=False, conditioned=True),
    }

    for queue_id, env in queue_specs.items():
        nodes[queue_id] = _make_location(loc_id=queue_id, name=queue_id, capacity_soft=30, capacity_hard=40, **env)

    edge_pairs: Set[frozenset] = set()
    edges: Dict[str, LayoutEdge] = {}

    hazard_overrides: Dict[frozenset, float] = {
        frozenset({"corr:main-core", "corr:survey-a"}): 0.25,
        frozenset({"corr:survey-a", "corr:survey-b"}): 0.06,
        frozenset({"corr:main-core", "corr:maintenance-a"}): 0.18,
        frozenset({"corr:maintenance-a", "corr:maintenance-b"}): 0.04,
    }

    for src, targets in adjacency.items():
        for tgt in targets:
            pair = frozenset({src, tgt})
            if pair in edge_pairs:
                continue
            edge_pairs.add(pair)
            a, b = sorted(pair)
            edge_id = f"edge:{a}:{b}"
            hazard = hazard_overrides.get(pair, 0.02)
            edges[edge_id] = LayoutEdge(id=edge_id, a=a, b=b, base_hazard_prob=hazard)

    return HabitatLayoutPrime(nodes=nodes, edges=edges, adjacency=adjacency)


__all__ = ["HabitatLayoutPrime", "LayoutEdge", "Location", "build_habitat_layout_prime", "DEFAULT_PODS"]

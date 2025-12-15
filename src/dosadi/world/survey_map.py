from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Dict, Iterable, Mapping


def edge_key(a: str, b: str) -> str:
    """Return the canonical key for an undirected edge.

    Ordering the endpoints keeps hashes stable and avoids duplicate edge
    representations when observations arrive in different orientations.
    """

    return "|".join(sorted((str(a), str(b))))


def _canonical_json(data: Mapping[str, object]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


@dataclass(slots=True)
class SurveyNode:
    node_id: str
    kind: str
    ward_id: str | None = None
    tags: tuple[str, ...] = ()
    hazard: float = 0.0
    water: float = 0.0
    confidence: float = 0.0
    last_seen_tick: int = 0

    def merge_from(self, other: "SurveyNode") -> "SurveyNode":
        merged_tags = tuple(sorted(set(self.tags) | set(other.tags)))
        merged_hazard = max(self.hazard, other.hazard)
        merged_water = max(self.water, other.water)
        merged_confidence = min(1.0, max(self.confidence, other.confidence))
        merged_last_seen = max(self.last_seen_tick, other.last_seen_tick)
        merged_kind = self.kind or other.kind
        merged_ward = self.ward_id or other.ward_id
        return SurveyNode(
            node_id=self.node_id,
            kind=merged_kind,
            ward_id=merged_ward,
            tags=merged_tags,
            hazard=merged_hazard,
            water=merged_water,
            confidence=merged_confidence,
            last_seen_tick=merged_last_seen,
        )


@dataclass(slots=True)
class SurveyEdge:
    a: str
    b: str
    distance_m: float
    travel_cost: float
    hazard: float = 0.0
    confidence: float = 0.0
    last_seen_tick: int = 0

    @property
    def key(self) -> str:
        return edge_key(self.a, self.b)

    def merge_from(self, other: "SurveyEdge") -> "SurveyEdge":
        merged_hazard = max(self.hazard, other.hazard)
        merged_confidence = min(1.0, max(self.confidence, other.confidence))
        merged_last_seen = max(self.last_seen_tick, other.last_seen_tick)
        merged_distance = min(self.distance_m, other.distance_m)
        merged_travel_cost = min(self.travel_cost, other.travel_cost)
        return SurveyEdge(
            a=self.a,
            b=self.b,
            distance_m=merged_distance,
            travel_cost=merged_travel_cost,
            hazard=merged_hazard,
            confidence=merged_confidence,
            last_seen_tick=merged_last_seen,
        )


@dataclass(slots=True)
class SurveyMap:
    nodes: Dict[str, SurveyNode] = field(default_factory=dict)
    edges: Dict[str, SurveyEdge] = field(default_factory=dict)
    schema_version: str = "survey_map_v1"

    def upsert_node(self, node: SurveyNode, *, confidence_delta: float = 0.1) -> None:
        existing = self.nodes.get(node.node_id)
        candidate = node
        if existing:
            boosted_confidence = min(1.0, max(existing.confidence, node.confidence) + confidence_delta)
            candidate = existing.merge_from(node)
            candidate.confidence = boosted_confidence
            candidate.last_seen_tick = max(existing.last_seen_tick, node.last_seen_tick)
        else:
            candidate.confidence = min(1.0, max(node.confidence, confidence_delta))
        self.nodes[node.node_id] = candidate

    def upsert_edge(self, edge: SurveyEdge, *, confidence_delta: float = 0.1) -> None:
        key = edge.key
        existing = self.edges.get(key)
        candidate = edge
        if existing:
            boosted_confidence = min(1.0, max(existing.confidence, edge.confidence) + confidence_delta)
            candidate = existing.merge_from(edge)
            candidate.confidence = boosted_confidence
            candidate.last_seen_tick = max(existing.last_seen_tick, edge.last_seen_tick)
        else:
            candidate.confidence = min(1.0, max(edge.confidence, confidence_delta))
        self.edges[key] = candidate

    def merge_observation(self, obs: Mapping[str, object], *, tick: int) -> None:
        nodes: Iterable[Mapping[str, object]] = obs.get("discovered_nodes", [])  # type: ignore[assignment]
        edges: Iterable[Mapping[str, object]] = obs.get("discovered_edges", [])  # type: ignore[assignment]

        for raw in nodes:
            node = SurveyNode(
                node_id=str(raw.get("node_id")),
                kind=str(raw.get("kind", "unknown")),
                ward_id=raw.get("ward_id"),
                tags=tuple(sorted(raw.get("tags", ()))),
                hazard=float(raw.get("hazard", 0.0)),
                water=float(raw.get("water", 0.0)),
                confidence=float(raw.get("confidence", 0.0)),
                last_seen_tick=tick,
            )
            delta = float(raw.get("confidence_delta", 0.1))
            self.upsert_node(node, confidence_delta=delta)

        for raw in edges:
            a = str(raw.get("a"))
            b = str(raw.get("b"))
            edge = SurveyEdge(
                a=a,
                b=b,
                distance_m=float(raw.get("distance_m", 0.0)),
                travel_cost=float(raw.get("travel_cost", 0.0)),
                hazard=float(raw.get("hazard", 0.0)),
                confidence=float(raw.get("confidence", 0.0)),
                last_seen_tick=tick,
            )
            delta = float(raw.get("confidence_delta", 0.1))
            self.upsert_edge(edge, confidence_delta=delta)

    def signature(self) -> str:
        canonical_nodes = {
            node_id: {
                "confidence": node.confidence,
                "hazard": node.hazard,
                "kind": node.kind,
                "last_seen_tick": node.last_seen_tick,
                "tags": list(node.tags),
                "ward_id": node.ward_id,
                "water": node.water,
            }
            for node_id, node in sorted(self.nodes.items())
        }
        canonical_edges = {
            key: {
                "a": edge.a,
                "b": edge.b,
                "confidence": edge.confidence,
                "distance_m": edge.distance_m,
                "hazard": edge.hazard,
                "last_seen_tick": edge.last_seen_tick,
                "travel_cost": edge.travel_cost,
            }
            for key, edge in sorted(self.edges.items())
        }
        canonical = {
            "schema_version": self.schema_version,
            "nodes": canonical_nodes,
            "edges": canonical_edges,
        }
        return sha256(_canonical_json(canonical).encode("utf-8")).hexdigest()


__all__ = [
    "SurveyEdge",
    "SurveyMap",
    "SurveyNode",
    "edge_key",
]

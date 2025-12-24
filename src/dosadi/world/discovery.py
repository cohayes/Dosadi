from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping

from .extraction import create_sites_for_node
from .survey_map import SurveyEdge, SurveyMap, SurveyNode, edge_key


@dataclass(slots=True)
class DiscoveryConfig:
    enabled: bool = False
    max_new_nodes_per_day: int = 3
    max_new_edges_per_day: int = 5
    max_frontier_expansions_per_mission: int = 8
    resource_tag_probs: Mapping[str, float] = None  # type: ignore[assignment]
    hazard_range: tuple[float, float] = (0.0, 0.8)
    deterministic_salt: str = "discover-v1"

    def __post_init__(self) -> None:
        if self.resource_tag_probs is None:
            self.resource_tag_probs = {
                "scrap_field": 0.25,
                "salvage_cache": 0.20,
                "brine_pocket": 0.10,
            }


def hashed_unit_float(*parts: str) -> float:
    joined = ":".join(parts)
    digest = sha256(joined.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)


def _stable_distance(seed_parts: Iterable[str]) -> float:
    base = hashed_unit_float(*seed_parts)
    return 75.0 + 450.0 * base


def _stable_hazard(seed_parts: Iterable[str], *, cfg: DiscoveryConfig) -> float:
    base = hashed_unit_float(*seed_parts)
    return cfg.hazard_range[0] + (cfg.hazard_range[1] - cfg.hazard_range[0]) * base


def _stable_node_id(seed_parts: Iterable[str], survey: SurveyMap) -> str:
    salt = 0
    while True:
        digest = sha256(":".join((*seed_parts, str(salt))).encode("utf-8")).hexdigest()
        candidate = f"node:{digest[:12]}"
        if candidate not in survey.nodes:
            return candidate
        salt += 1


def expand_frontier(
    world,
    *,
    from_node: str,
    budget_nodes: int,
    budget_edges: int,
    day: int,
    mission_id: str,
    cfg: DiscoveryConfig | None = None,
) -> list[str]:
    cfg = cfg or getattr(world, "discovery_cfg", None) or DiscoveryConfig()
    if not cfg.enabled or budget_nodes <= 0 or budget_edges <= 0:
        return []

    survey: SurveyMap = getattr(world, "survey_map", SurveyMap())
    max_nodes = min(budget_nodes, cfg.max_new_nodes_per_day, cfg.max_frontier_expansions_per_mission)
    max_edges = min(budget_edges, cfg.max_new_edges_per_day)
    if max_nodes <= 0 or max_edges <= 0:
        return []

    count_seed = (str(getattr(world, "seed", 0)), cfg.deterministic_salt, from_node, mission_id, str(day))
    count = int(hashed_unit_float(*count_seed) * max_nodes) + 1
    count = min(max(1, count), max_nodes, max_edges)
    if count <= 0:
        return []

    discoveries: list[tuple[float, str]] = []
    metrics = getattr(world, "metrics", {}) or {}
    discovery_metrics = metrics.get("discovery") or {}

    for idx in range(count):
        base_parts = (
            str(getattr(world, "seed", 0)),
            cfg.deterministic_salt,
            from_node,
            mission_id,
            str(day),
            str(idx),
        )
        node_id = _stable_node_id(base_parts, survey)
        hazard = _stable_hazard((*base_parts, "hazard"), cfg=cfg)
        distance = _stable_distance((*base_parts, "distance"))
        tag_seed_base = (*base_parts, "tag")
        resource_tags: list[str] = []
        for tag, prob in sorted(cfg.resource_tag_probs.items()):
            if hashed_unit_float(*(*tag_seed_base, tag)) < float(prob):
                resource_tags.append(tag)
        richness = hashed_unit_float(*base_parts)

        node = SurveyNode(
            node_id=node_id,
            kind="frontier",
            ward_id=None,
            tags=tuple(sorted(resource_tags)),
            resource_tags=tuple(sorted(resource_tags)),
            resource_richness=richness,
            hazard=hazard,
            water=0.0,
            confidence=0.55,
            last_seen_tick=int(getattr(world, "tick", day * getattr(getattr(world, "config", None), "ticks_per_day", 0))),
            discovered=True,
        )
        survey.upsert_node(node)

        edge = SurveyEdge(
            a=from_node,
            b=node_id,
            distance_m=distance,
            travel_cost=distance,
            hazard=hazard,
            confidence=0.55,
            last_seen_tick=node.last_seen_tick,
            discovered=True,
        )
        survey.upsert_edge(edge)

        discoveries.append((hashed_unit_float(*(*base_parts, "order")), node_id))

        create_sites_for_node(world, node, day=day)

        discovery_metrics["nodes_added"] = discovery_metrics.get("nodes_added", 0) + 1
        discovery_metrics["edges_added"] = discovery_metrics.get("edges_added", 0) + 1
        if resource_tags:
            discovery_metrics["resources_found"] = discovery_metrics.get("resources_found", 0) + len(
                resource_tags
            )

        events_log = getattr(world, "runtime_events", None)
        payloads = [
            {"type": "DISCOVERY_NODE", "node_id": node_id, "from_node": from_node, "tags": list(resource_tags)},
            {
                "type": "DISCOVERY_EDGE",
                "edge_key": edge.key,
                "hazard": edge.hazard,
                "a": edge.a,
                "b": edge.b,
            },
        ]
        for tag in resource_tags:
            payloads.append(
                {"type": "DISCOVERY_RESOURCE", "node_id": node_id, "tag": tag, "richness": richness}
            )
        if isinstance(events_log, list):
            events_log.extend(payloads)
        elif events_log is not None:
            try:
                events_log += payloads  # type: ignore[operator]
            except Exception:
                pass
        else:
            world.runtime_events = payloads

    discoveries.sort(key=lambda item: (item[0], item[1]))
    metrics["discovery"] = discovery_metrics
    world.metrics = metrics
    discovery_metrics["missions_completed"] = discovery_metrics.get("missions_completed", 0)
    return [node_id for _, node_id in discoveries]


from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .survey_map import SurveyMap, SurveyNode, edge_key


@dataclass(slots=True)
class SiteScoreConfig:
    hazard_weight: float = 1.0
    distance_weight: float = 1.0
    water_weight: float = 1.0
    strategic_tag_weights: Mapping[str, float] = field(default_factory=dict)
    disconnected_penalty: float = 10.0


def score_site(
    node: SurveyNode,
    *,
    origin_node_id: str | None,
    survey: SurveyMap,
    cfg: SiteScoreConfig,
) -> float:
    """Deterministic, side-effect free site score.

    The heuristic rewards water potential and strategic tags while penalizing
    hazards and travel distance from the origin node when connected. When the
    node is unreachable, a fixed penalty is applied to keep the function
    monotonic and deterministic.
    """

    score = 0.0
    score -= cfg.hazard_weight * max(0.0, node.hazard)
    score += cfg.water_weight * max(0.0, node.water)

    for tag in node.tags:
        score += cfg.strategic_tag_weights.get(tag, 0.0)

    if origin_node_id and origin_node_id != node.node_id:
        key = edge_key(origin_node_id, node.node_id)
        edge = survey.edges.get(key)
        if edge:
            score -= cfg.distance_weight * max(edge.travel_cost, edge.distance_m)
        else:
            score -= cfg.disconnected_penalty * cfg.distance_weight

    return float(score)


__all__ = ["SiteScoreConfig", "score_site"]

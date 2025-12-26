from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from dosadi.runtime.telemetry import ensure_metrics
from dosadi.runtime.customs import iter_border_crossings
from dosadi.world.routing import compute_route
from dosadi.world.factions import pseudo_rand01


_SMUGGLING_COMMODITIES: dict[str, dict[str, float]] = {
    "UNLICENSED_SUIT_MODS": {"value_density": 6.0, "seizure_penalty": 0.35},
    "NARCOTICS": {"value_density": 5.0, "seizure_penalty": 0.30},
    "WEAPON_PARTS": {"value_density": 8.0, "seizure_penalty": 0.45},
    "STOLEN_GOODS": {"value_density": 4.0, "seizure_penalty": 0.25},
    "RAIDER_SUPPLIES": {"value_density": 7.0, "seizure_penalty": 0.40},
}


@dataclass(slots=True)
class SmugglingConfig:
    enabled: bool = False
    max_active_factions: int = 8
    max_shipments_per_day: int = 12
    commodity_topk: int = 8
    route_topk: int = 24
    border_topk: int = 24
    learning_rate: float = 0.15
    deterministic_salt: str = "smuggling-v1"


@dataclass(slots=True)
class SmugglingEdgeStats:
    edge_id: str
    risk_est: float = 0.5
    cost_est: float = 0.1
    last_update_day: int = -1


@dataclass(slots=True)
class SmugglingNetworkState:
    faction_id: str
    commodity_prefs: dict[str, float] = field(default_factory=dict)
    preferred_borders: dict[str, float] = field(default_factory=dict)
    edge_stats: dict[str, SmugglingEdgeStats] = field(default_factory=dict)
    bribe_budget_fraction: float = 0.15
    last_run_day: int = -1
    recent_outcomes: list[dict[str, object]] = field(default_factory=list)


def smuggling_commodities() -> dict[str, dict[str, float]]:
    return dict(_SMUGGLING_COMMODITIES)


def ensure_smuggling_config(world: Any) -> SmugglingConfig:
    cfg = getattr(world, "smuggling_cfg", None)
    if not isinstance(cfg, SmugglingConfig):
        cfg = SmugglingConfig()
        world.smuggling_cfg = cfg
    return cfg


def ensure_smuggling_state(world: Any) -> dict[str, SmugglingNetworkState]:
    state = getattr(world, "smuggling_by_faction", None)
    if not isinstance(state, dict):
        state = {}
        world.smuggling_by_faction = state
    return state


def _stable_topk(items: Iterable[tuple[str, float]], k: int) -> list[tuple[str, float]]:
    scored = [(float(score), key) for key, score in items if score > 0]
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [(key, score) for score, key in scored[: max(0, int(k))]]


def _ward_norm(world: Any, ward_id: str, key: str) -> float:
    culture = getattr(world, "culture_by_ward", {}).get(ward_id)
    return float(getattr(culture, "norms", {}).get(key, 0.0)) if culture else 0.0


def _ward_need(world: Any, ward_id: str) -> float:
    ward = getattr(world, "wards", {}).get(ward_id)
    if not ward:
        return 0.0
    return float(getattr(ward, "need_index", 0.0))


def _ward_smuggle_risk(world: Any, ward_id: str) -> float:
    ward = getattr(world, "wards", {}).get(ward_id)
    if not ward:
        return 0.0
    return float(getattr(ward, "smuggle_risk", 0.0))


def _default_node_for_ward(world: Any, ward_id: str) -> str | None:
    survey_map = getattr(world, "survey_map", None)
    if survey_map is None:
        return None
    candidates = [node_id for node_id, node in survey_map.nodes.items() if getattr(node, "ward_id", None) == ward_id]
    if not candidates:
        return None
    return sorted(candidates)[0]


def _score_demand(world: Any, ward_id: str, commodity: str) -> float:
    tolerance = _ward_norm(world, ward_id, "norm:smuggling_tolerance")
    corruption = _ward_norm(world, ward_id, "norm:corruption")
    shortage = _ward_need(world, ward_id)
    return max(0.0, tolerance * 0.6 + corruption * 0.2 + shortage * 0.2)


def _score_source(world: Any, ward_id: str, commodity: str) -> float:
    raider = _ward_norm(world, ward_id, "norm:raider_alignment")
    tolerance = _ward_norm(world, ward_id, "norm:smuggling_tolerance")
    smuggle_risk = _ward_smuggle_risk(world, ward_id)
    return max(0.0, 0.4 * raider + 0.4 * tolerance + 0.2 * smuggle_risk)


def _commodity_preferences(faction: Any) -> dict[str, float]:
    prefs = getattr(faction, "smuggling_profile", {}) or {}
    if prefs:
        return {str(k).upper(): float(v) for k, v in prefs.items() if float(v) > 0}
    return {key: 1.0 for key in _SMUGGLING_COMMODITIES.keys()}


def _route_score(edge_stats: dict[str, SmugglingEdgeStats], edge_keys: Iterable[str]) -> float:
    keys = list(edge_keys)
    score = 0.0
    for edge in keys:
        stats = edge_stats.get(edge, SmugglingEdgeStats(edge_id=edge))
        score += stats.risk_est + stats.cost_est * 0.25
    return score / max(1, len(keys))


def _allocate_bribes(cfg: SmugglingConfig, net: SmugglingNetworkState, *, faction, route, crossings, day: int) -> dict[str, float]:
    total_budget = float(getattr(getattr(faction, "assets", None), "credits", {}).get("credits", 0.0))
    bribe_budget = total_budget * float(net.bribe_budget_fraction)
    if bribe_budget <= 0 or not crossings:
        return {}
    weights: list[tuple[str, float]] = []
    for crossing in crossings:
        edge_id = str(getattr(crossing, "border_at", ""))
        risk = net.edge_stats.get(edge_id, SmugglingEdgeStats(edge_id=edge_id)).risk_est
        pref = net.preferred_borders.get(edge_id, 0.0)
        weight = max(0.0, (1.0 - risk) * (1.0 + pref))
        if weight > 0:
            weights.append((edge_id, weight))
    weights.sort(key=lambda itm: (-itm[1], itm[0]))
    weights = weights[: cfg.border_topk]
    total_weight = sum(weight for _, weight in weights) or 1.0
    allocation = {edge_id: bribe_budget * weight / total_weight for edge_id, weight in weights}
    return allocation


def _shipment_signature(day: int, faction_id: str, commodity: str, source: str, dest: str, salt: str) -> str:
    parts = [salt, str(day), faction_id, commodity, source, dest]
    return "|".join(parts)


def plan_smuggling_shipments(world: Any, *, day: int) -> list[Any]:
    cfg = ensure_smuggling_config(world)
    if not cfg.enabled:
        return []
    state = ensure_smuggling_state(world)
    metrics = ensure_metrics(world)
    factions = sorted(getattr(world, "factions", {}).items())[: cfg.max_active_factions]
    shipments = []
    per_day_cap = max(0, int(cfg.max_shipments_per_day))

    for faction_id, faction in factions:
        net = state.get(faction_id)
        if net is None:
            net = SmugglingNetworkState(faction_id=faction_id)
            net.commodity_prefs = _commodity_preferences(faction)
            state[faction_id] = net
        commodity_prefs = _stable_topk(net.commodity_prefs.items(), cfg.commodity_topk)
        for commodity, pref_score in commodity_prefs:
            demand_scores = _stable_topk(
                ((ward_id, _score_demand(world, ward_id, commodity)) for ward_id in getattr(world, "wards", {})),
                cfg.route_topk,
            )
            source_scores = _stable_topk(
                ((ward_id, _score_source(world, ward_id, commodity)) for ward_id in getattr(world, "wards", {})),
                cfg.route_topk,
            )
            if not demand_scores or not source_scores:
                continue
            dest_id, dest_score = demand_scores[0]
            src_id, src_score = source_scores[0]
            if dest_id == src_id:
                continue
            origin_node = _default_node_for_ward(world, src_id)
            dest_node = _default_node_for_ward(world, dest_id)
            if not origin_node or not dest_node:
                continue
            route = compute_route(world, from_node=origin_node, to_node=dest_node)
            if route is None:
                continue
            score = _route_score(net.edge_stats, route.edge_keys)
            signature = _shipment_signature(day, faction_id, commodity, src_id, dest_id, cfg.deterministic_salt)
            weight_roll = pseudo_rand01(signature)
            if weight_roll * (dest_score + src_score + pref_score) < score:
                continue
            delivery_id = f"smuggle:{faction_id}:{day}:{len(shipments)}"
            crossings = iter_border_crossings(world, route.nodes, route.edge_keys)
            bribe_map = _allocate_bribes(cfg, net, faction=faction, route=route, crossings=crossings, day=day)
            shipment = _build_delivery(
                delivery_id=delivery_id,
                faction=faction,
                faction_id=faction_id,
                commodity=commodity,
                route=route,
                bribe_map=bribe_map,
            )
            shipments.append(shipment)
            net.last_run_day = day
            metrics.counters.setdefault("smuggling", {})["shipments_created"] = metrics.counters.get("smuggling", {}).get("shipments_created", 0) + 1
            if len(shipments) >= per_day_cap:
                break
        if len(shipments) >= per_day_cap:
            break
    return shipments


def _build_delivery(*, delivery_id: str, faction, faction_id: str, commodity: str, route, bribe_map: Mapping[str, float]):
    from dosadi.world.logistics import DeliveryRequest, DeliveryStatus

    value_density = _SMUGGLING_COMMODITIES.get(commodity, {}).get("value_density", 1.0)
    cargo_amount = max(1.0, value_density)
    bribe_total = sum(bribe_map.values()) if bribe_map else 0.0
    return DeliveryRequest(
        delivery_id=delivery_id,
        project_id="smuggling",
        origin_node_id=route.nodes[0],
        dest_node_id=route.nodes[-1],
        items={commodity: cargo_amount},
        cargo={commodity: cargo_amount},
        status=DeliveryStatus.REQUESTED,
        created_tick=0,
        due_tick=None,
        notes={"smuggling": "true"},
        route_nodes=list(route.nodes),
        route_edge_keys=list(route.edge_keys),
        route_corridors=list(route.edge_keys),
        owner_party=f"party:fac:{faction_id}",
        flags={"smuggling", commodity},
        declared_value=value_density * 10.0,
        smuggling_bribe_budget_total=bribe_total,
        smuggling_bribe_map=dict(bribe_map),
    )


def record_smuggling_outcome(
    net: SmugglingNetworkState,
    *,
    day: int,
    route_edge_keys: Iterable[str],
    seized: bool,
    tariff_paid: float = 0.0,
    bribe_paid: float = 0.0,
) -> None:
    lr = 0.15
    for edge_id in route_edge_keys:
        stats = net.edge_stats.get(edge_id)
        if stats is None:
            stats = SmugglingEdgeStats(edge_id=edge_id)
            net.edge_stats[edge_id] = stats
        target = 1.0 if seized else 0.0
        stats.risk_est = max(0.0, min(1.0, stats.risk_est + (target - stats.risk_est) * lr))
        stats.cost_est = max(0.0, stats.cost_est + (bribe_paid + tariff_paid - stats.cost_est) * lr)
        stats.last_update_day = day
    if len(net.edge_stats) > 0:
        ordered = sorted(net.edge_stats.values(), key=lambda es: (es.last_update_day, es.edge_id))
        while len(ordered) > 24:
            victim = ordered.pop(0)
            net.edge_stats.pop(victim.edge_id, None)
    net.recent_outcomes.append({"day": day, "seized": seized, "bribe": bribe_paid, "tariff": tariff_paid})
    if len(net.recent_outcomes) > 50:
        net.recent_outcomes = net.recent_outcomes[-50:]


def smuggling_seed_payload(world: Any) -> dict[str, Any] | None:
    cfg = getattr(world, "smuggling_cfg", None)
    state = getattr(world, "smuggling_by_faction", None)
    if cfg is None and state is None:
        return None
    payload = {
        "config": asdict(cfg) if cfg else {},
        "by_faction": {
            fid: {
                "commodity_prefs": dict(net.commodity_prefs),
                "preferred_borders": dict(net.preferred_borders),
                "edge_stats": {k: es.__dict__ for k, es in sorted(net.edge_stats.items())},
                "bribe_budget_fraction": net.bribe_budget_fraction,
                "last_run_day": net.last_run_day,
                "recent_outcomes": list(net.recent_outcomes),
            }
            for fid, net in sorted((state or {}).items())
        },
    }
    return payload


def save_smuggling_seed(world: Any, path: Path) -> None:
    payload = smuggling_seed_payload(world) or {}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, sort_keys=True, indent=2)


def load_smuggling_seed(world: Any, payload: Mapping[str, Any]) -> None:
    cfg_data = payload.get("config") if isinstance(payload, Mapping) else None
    state_data = payload.get("by_faction") if isinstance(payload, Mapping) else None
    if cfg_data:
        world.smuggling_cfg = SmugglingConfig(**cfg_data)
    if state_data:
        smuggling_state: dict[str, SmugglingNetworkState] = {}
        for fid, net_data in state_data.items():
            net = SmugglingNetworkState(faction_id=fid)
            net.commodity_prefs = dict(net_data.get("commodity_prefs", {}))
            net.preferred_borders = dict(net_data.get("preferred_borders", {}))
            edge_stats = {}
            for edge_id, stats_data in (net_data.get("edge_stats", {}) or {}).items():
                edge_stats[edge_id] = SmugglingEdgeStats(edge_id=edge_id, **{k: v for k, v in stats_data.items() if k != "edge_id"})
            net.edge_stats = edge_stats
            net.bribe_budget_fraction = float(net_data.get("bribe_budget_fraction", net.bribe_budget_fraction))
            net.last_run_day = int(net_data.get("last_run_day", -1))
            net.recent_outcomes = list(net_data.get("recent_outcomes", []))
            smuggling_state[fid] = net
        world.smuggling_by_faction = smuggling_state


__all__ = [
    "SmugglingConfig",
    "SmugglingEdgeStats",
    "SmugglingNetworkState",
    "ensure_smuggling_config",
    "ensure_smuggling_state",
    "plan_smuggling_shipments",
    "record_smuggling_outcome",
    "save_smuggling_seed",
    "load_smuggling_seed",
    "smuggling_commodities",
]

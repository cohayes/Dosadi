from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

from dosadi.runtime.institutions import ensure_policy
from dosadi.runtime.comms import (
    CommsModifiers,
    get_comms_modifiers_for_hop,
    relay_path_available,
)
from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.runtime.ideology import ensure_ward_ideology
from dosadi.runtime.corridor_risk import CorridorRiskLedger
from dosadi.world.survey_map import SurveyEdge, SurveyMap, edge_key


@dataclass(slots=True)
class MediaConfig:
    enabled: bool = False
    max_messages_in_flight: int = 5000
    max_messages_per_ward_queue: int = 200
    relay_bandwidth_per_day: int = 50
    deterministic_salt: str = "media-v1"
    loss_rate_base: float = 0.01
    distortion_rate_base: float = 0.02
    intercept_rate_base: float = 0.03


@dataclass(slots=True)
class MediaMessage:
    msg_id: str
    day_sent: int
    sender: str
    origin_ward: str
    dest_scope: str
    dest_id: str
    channel: str
    kind: str
    priority: int
    ttl_days: int
    payload: dict[str, object] = field(default_factory=dict)
    integrity: float = 1.0
    status: str = "IN_FLIGHT"
    notes: dict[str, object] = field(default_factory=dict)


def ensure_media_config(world: Any) -> MediaConfig:
    cfg = getattr(world, "media_cfg", None)
    if not isinstance(cfg, MediaConfig):
        cfg = MediaConfig()
        world.media_cfg = cfg
    return cfg


def ensure_media_state(world: Any) -> None:
    cfg = ensure_media_config(world)
    world.media_cfg = cfg
    if not isinstance(getattr(world, "media_in_flight", None), MutableMapping):
        world.media_in_flight = {}
    if not isinstance(getattr(world, "media_inbox_by_ward", None), MutableMapping):
        world.media_inbox_by_ward = {}
    if not isinstance(getattr(world, "media_inbox_by_faction", None), MutableMapping):
        world.media_inbox_by_faction = {}
    if not isinstance(getattr(world, "media_stats", None), MutableMapping):
        world.media_stats = {}
    if not isinstance(getattr(world, "next_media_seq", None), int):
        world.next_media_seq = 0


def _stable_float(parts: Iterable[object], salt: str) -> float:
    joined = "|".join(str(p) for p in parts)
    digest = sha256((salt + joined).encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12)


def _next_msg_id(world: Any) -> str:
    seq = getattr(world, "next_media_seq", 0)
    seq += 1
    world.next_media_seq = seq
    return f"msg:{seq}"


def _survey_edges(world: Any) -> Mapping[str, SurveyEdge]:
    survey_map: SurveyMap | None = getattr(world, "survey_map", None)
    return getattr(survey_map, "edges", {}) if survey_map else {}


def _edge_neighbors(world: Any, node_id: str) -> Sequence[tuple[str, SurveyEdge]]:
    edges = _survey_edges(world)
    neighbors: list[tuple[str, SurveyEdge]] = []
    for edge in edges.values():
        if edge.a == node_id:
            neighbors.append((edge.b, edge))
        elif edge.b == node_id:
            neighbors.append((edge.a, edge))
    neighbors.sort(key=lambda item: item[0])
    return neighbors


def _shortest_path(world: Any, origin: str, dest: str) -> list[str]:
    if origin == dest:
        return [origin]
    frontier: list[list[str]] = [[origin]]
    visited = {origin}
    while frontier:
        path = frontier.pop(0)
        tail = path[-1]
        for neighbor, _ in _edge_neighbors(world, tail):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            next_path = path + [neighbor]
            if neighbor == dest:
                return next_path
            frontier.append(next_path)
    return []


def _relay_nodes(world: Any) -> set[str]:
    nodes: set[str] = set()
    for ward_id, ward in getattr(world, "wards", {}).items():
        facilities = getattr(ward, "facilities", {}) or {}
        if facilities.get("RELAY_TOWER_L2"):
            nodes.add(ward_id)
    return nodes


def _relay_path(world: Any, origin: str, dest: str) -> list[str]:
    relays = _relay_nodes(world)
    if origin not in relays or dest not in relays:
        return []
    # BFS restricted to relay-enabled wards
    frontier: list[list[str]] = [[origin]]
    visited = {origin}
    while frontier:
        path = frontier.pop(0)
        tail = path[-1]
        for neighbor, _ in _edge_neighbors(world, tail):
            if neighbor not in relays or neighbor in visited:
                continue
            visited.add(neighbor)
            next_path = path + [neighbor]
            if neighbor == dest:
                return next_path
            frontier.append(next_path)
    return []


def _select_channel(world: Any, origin: str, dest: str, *, requested: str | None) -> str:
    if requested:
        return requested
    path = _relay_path(world, origin, dest)
    if path:
        return "RELAY"
    return "COURIER"


def _edge_risk(world: Any, a: str, b: str) -> float:
    ledger: CorridorRiskLedger | None = getattr(world, "risk_ledger", None)
    if ledger is None:
        return 0.0
    rec = ledger.edges.get(edge_key(a, b))
    return float(getattr(rec, "risk", 0.0) or 0.0)


def _transit_time_days(world: Any, path: Sequence[str], channel: str) -> int:
    if len(path) <= 1:
        return 0
    edges = _survey_edges(world)
    total = 0.0
    for a, b in zip(path, path[1:]):
        rec = edges.get(edge_key(a, b))
        if rec is None:
            total += 1.0
        else:
            cost = getattr(rec, "travel_cost", 1.0) or 1.0
            total += max(1.0, cost if channel == "COURIER" else 1.0)
    return max(1, int(round(total)))


def _comms_latency_add(world: Any, path: Sequence[str], channel: str) -> int:
    if len(path) <= 1:
        return 0
    latency = 0
    for a, b in zip(path, path[1:]):
        modifiers = get_comms_modifiers_for_hop(world, a, b, channel)
        latency += max(0, int(modifiers.latency_add_days))
    return latency


def _apply_hop_effects(
    message: MediaMessage,
    *,
    cfg: MediaConfig,
    hop_index: int,
    risk: float,
    modifiers: CommsModifiers | None = None,
) -> None:
    salt = cfg.deterministic_salt
    base_parts = (message.msg_id, hop_index, message.channel, message.dest_id)
    mod = modifiers or CommsModifiers()
    intercept_chance = (cfg.intercept_rate_base + 0.5 * risk) * mod.intercept_mult
    loss_chance = (cfg.loss_rate_base + 0.5 * risk) * mod.loss_mult
    distortion_chance = (cfg.distortion_rate_base + 0.25 * risk) * mod.distortion_mult
    if _stable_float(base_parts, salt + "intercept") < intercept_chance:
        message.status = "INTERCEPTED"
        return
    if _stable_float(base_parts, salt + "loss") < loss_chance:
        message.status = "DROPPED"
        return
    if _stable_float(base_parts, salt + "distort") < distortion_chance:
        message.integrity = max(0.0, message.integrity * (1.0 - 0.25 * (1.0 + risk)))


def _simulate_transit(world: Any, message: MediaMessage, path: Sequence[str]) -> None:
    cfg = ensure_media_config(world)
    for hop_index, (a, b) in enumerate(zip(path, path[1:])):
        if message.status != "IN_FLIGHT":
            break
        risk = _edge_risk(world, a, b)
        modifiers = get_comms_modifiers_for_hop(world, a, b, message.channel)
        _apply_hop_effects(message, cfg=cfg, hop_index=hop_index, risk=risk, modifiers=modifiers)
    if message.status == "IN_FLIGHT":
        message.status = "DELIVERED"


def send_media_message(
    world: Any,
    *,
    sender: str,
    origin_ward: str,
    dest_scope: str,
    dest_id: str,
    kind: str,
    priority: int = 1,
    ttl_days: int = 7,
    payload: Mapping[str, object] | None = None,
    channel: str | None = None,
    day_sent: int | None = None,
) -> MediaMessage:
    ensure_media_state(world)
    cfg = ensure_media_config(world)
    if not cfg.enabled:
        raise RuntimeError("Media system disabled")
    day = getattr(world, "day", 0) if day_sent is None else int(day_sent)
    chosen_channel = _select_channel(world, origin_ward, dest_id if dest_scope == "WARD" else origin_ward, requested=channel)
    msg = MediaMessage(
        msg_id=_next_msg_id(world),
        day_sent=day,
        sender=str(sender),
        origin_ward=str(origin_ward),
        dest_scope=str(dest_scope),
        dest_id=str(dest_id),
        channel=chosen_channel,
        kind=str(kind),
        priority=max(0, int(priority)),
        ttl_days=max(1, int(ttl_days)),
        payload=dict(payload or {}),
    )
    world.media_in_flight[msg.msg_id] = msg
    if len(world.media_in_flight) > cfg.max_messages_in_flight:
        oldest_id = sorted(world.media_in_flight.items(), key=lambda item: (item[1].day_sent, item[0]))[0][0]
        world.media_in_flight[oldest_id].status = "DROPPED"
        world.media_in_flight.pop(oldest_id, None)
        ensure_metrics(world).inc("media.dropped")
    return msg


def _deliver_to_inbox(world: Any, message: MediaMessage) -> None:
    cfg = ensure_media_config(world)
    if message.dest_scope == "WARD":
        queue = world.media_inbox_by_ward.setdefault(message.dest_id, deque())
    elif message.dest_scope == "FACTION":
        queue = world.media_inbox_by_faction.setdefault(message.dest_id, deque())
    else:
        return
    queue.append(message.msg_id)
    limit = max(1, int(cfg.max_messages_per_ward_queue))
    if len(queue) > limit:
        # drop lowest priority then oldest deterministically
        msgs = list(queue)
        msgs.sort(key=lambda msg_id: (
            getattr(world.media_in_flight.get(msg_id), "priority", 0) * -1,
            getattr(world.media_in_flight.get(msg_id), "day_sent", 0),
            msg_id,
        ))
        keep = set(msgs[:limit])
        new_queue: deque[str] = deque()
        for msg_id in queue:
            if msg_id in keep:
                new_queue.append(msg_id)
            else:
                dropped = world.media_in_flight.get(msg_id)
                if dropped:
                    dropped.status = "DROPPED"
                ensure_metrics(world).inc("media.dropped")
        queue.clear()
        queue.extend(new_queue)


def process_media_for_day(world: Any, *, current_day: int | None = None) -> None:
    ensure_media_state(world)
    day = getattr(world, "day", 0) if current_day is None else int(current_day)
    cfg = ensure_media_config(world)
    edges = _survey_edges(world)
    metrics = ensure_metrics(world)
    for message in list(world.media_in_flight.values()):
        if message.status not in {"IN_FLIGHT"}:
            continue
        if day - message.day_sent >= message.ttl_days:
            message.status = "DROPPED"
            metrics.inc("media.dropped")
            continue
        if message.dest_scope != "WARD":
            path = [message.origin_ward]
        else:
            if message.channel == "RELAY":
                path = _relay_path(world, message.origin_ward, message.dest_id)
                if not path or not relay_path_available(world, path):
                    metrics.inc("comms.relay_fallbacks")
                    message.channel = "COURIER"
                    path = _shortest_path(world, message.origin_ward, message.dest_id)
            else:
                path = _shortest_path(world, message.origin_ward, message.dest_id)
        if not path:
            path = [message.origin_ward, message.dest_id]
        transit_days = _transit_time_days(world, path, message.channel)
        transit_days += _comms_latency_add(world, path, message.channel)
        eta_day = message.day_sent + transit_days
        message.notes["eta_day"] = eta_day
        message.notes["path"] = path
        if day < eta_day:
            continue
        _simulate_transit(world, message, path)
        if message.status == "DELIVERED":
            metrics.inc("media.delivered")
            _deliver_to_inbox(world, message)
            record_event(
                world,
                {
                    "kind": "MSG_DELIVERED",
                    "msg_id": message.msg_id,
                    "channel": message.channel,
                    "dest": message.dest_id,
                    "day": day,
                },
            )
        elif message.status == "INTERCEPTED":
            metrics.inc("media.intercepted")
        elif message.status == "DROPPED":
            metrics.inc("media.dropped")


def consume_order_messages(world: Any, ward_id: str, *, current_day: int) -> float:
    ensure_media_state(world)
    queue = world.media_inbox_by_ward.get(ward_id, deque())
    applied = 0.0
    policy = ensure_policy(world, ward_id)
    history = policy.notes.setdefault("order_effects", [])
    remaining: deque[str] = deque()
    for msg_id in list(queue):
        message = world.media_in_flight.get(msg_id)
        if message is None:
            continue
        if message.kind not in {"ORDER", "ALERT"}:
            remaining.append(msg_id)
            continue
        staleness = max(0, current_day - message.day_sent)
        freshness = max(0.0, 1.0 - staleness / float(max(1, message.ttl_days)))
        effect = float(message.payload.get("order_value", 0.0)) * message.integrity * freshness
        applied += effect
        history.append(effect)
        policy.notes["last_order_effect"] = effect
    world.media_inbox_by_ward[ward_id] = remaining
    return applied


def consume_propaganda(world: Any, ward_id: str, *, current_day: int) -> float:
    ensure_media_state(world)
    queue = world.media_inbox_by_ward.get(ward_id, deque())
    ideology = ensure_ward_ideology(world, ward_id)
    applied = 0.0
    remaining: deque[str] = deque()
    for msg_id in list(queue):
        message = world.media_in_flight.get(msg_id)
        if message is None:
            continue
        if message.kind != "PROPAGANDA":
            remaining.append(msg_id)
            continue
        age = max(0, current_day - message.day_sent)
        freshness = max(0.0, 1.0 - age / float(max(1, message.ttl_days)))
        intensity = float(message.payload.get("intensity", 0.0))
        delta = intensity * message.integrity * freshness
        ideology.propaganda_intensity = max(0.0, ideology.propaganda_intensity + delta)
        applied += delta
    world.media_inbox_by_ward[ward_id] = remaining
    return applied


def media_signature(world: Any) -> str:
    ensure_media_state(world)
    canonical = {
        "in_flight": {
            msg_id: {
                "status": msg.status,
                "integrity": round(msg.integrity, 6),
                "eta": msg.notes.get("eta_day"),
            }
            for msg_id, msg in sorted(world.media_in_flight.items())
        },
        "inbox": {ward: list(queue) for ward, queue in sorted(world.media_inbox_by_ward.items())},
    }
    payload = str(canonical)
    return sha256(payload.encode("utf-8")).hexdigest()

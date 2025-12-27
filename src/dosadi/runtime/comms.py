from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.telemetry import ensure_metrics, record_event


@dataclass(slots=True)
class CommsConfig:
    enabled: bool = False
    update_cadence_days: int = 1
    deterministic_salt: str = "comms-v1"
    base_outage_rate: float = 0.001
    base_degrade_rate: float = 0.003
    jam_rate_war: float = 0.010
    repair_rate: float = 0.15
    resilience_spend_effect: float = 0.25
    max_events_per_day: int = 6


@dataclass(slots=True)
class CommsNodeState:
    node_id: str
    ward_id: str
    kind: str
    status: str = "OK"
    status_until_day: int = -1
    health: float = 1.0
    jammer_faction: str | None = None
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class CommsModifiers:
    loss_mult: float = 1.0
    latency_add_days: int = 0
    distortion_mult: float = 1.0
    intercept_mult: float = 1.0


def _stable_float(parts: Iterable[object], salt: str) -> float:
    joined = "|".join(str(p) for p in parts)
    digest = sha256((salt + joined).encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12)


def ensure_comms_config(world: Any) -> CommsConfig:
    cfg = getattr(world, "comms_cfg", None)
    if not isinstance(cfg, CommsConfig):
        cfg = CommsConfig()
        world.comms_cfg = cfg
    return cfg


def ensure_comms_state(world: Any) -> None:
    ensure_comms_config(world)
    if not isinstance(getattr(world, "comms_nodes", None), Mapping):
        world.comms_nodes = {}
    if not isinstance(getattr(world, "comms_mod_by_ward", None), Mapping):
        world.comms_mod_by_ward = {}
    if not isinstance(getattr(world, "comms_events", None), list):
        world.comms_events = []


def _facility_present(world: Any, ward_id: str, kind: str) -> bool:
    ward = getattr(world, "wards", {}).get(ward_id)
    facilities = getattr(ward, "facilities", {}) if ward is not None else {}
    if kind == "RELAY":
        return bool(facilities.get("RELAY_TOWER_L2"))
    if kind == "BROADCAST":
        return bool(facilities.get("BROADCAST_HUB"))
    return False


def _sync_nodes(world: Any) -> None:
    ensure_comms_state(world)
    for ward_id, ward in sorted(getattr(world, "wards", {}).items()):
        facilities = getattr(ward, "facilities", {}) or {}
        if facilities.get("RELAY_TOWER_L2"):
            node_id = f"relay:{ward_id}"
            world.comms_nodes.setdefault(
                node_id,
                CommsNodeState(node_id=node_id, ward_id=ward_id, kind="RELAY"),
            )
        if facilities.get("BROADCAST_HUB"):
            node_id = f"broadcast:{ward_id}"
            world.comms_nodes.setdefault(
                node_id,
                CommsNodeState(node_id=node_id, ward_id=ward_id, kind="BROADCAST"),
            )

    for node in world.comms_nodes.values():
        if not _facility_present(world, node.ward_id, node.kind):
            node.status = "OUTAGE"


def _ward_risk(world: Any, ward_id: str) -> float:
    ledger = getattr(world, "risk_ledger", None)
    if ledger is None:
        return 1.0
    risks: list[float] = []
    for ek, rec in getattr(ledger, "edges", {}).items():
        a, b = ek.split("|")
        if ward_id in {a, b}:
            risks.append(float(getattr(rec, "risk", 0.0) or 0.0))
    if not risks:
        return 1.0
    return 1.0 + sum(risks) / float(len(risks))


def _defense_factor(world: Any, node: CommsNodeState, cfg: CommsConfig) -> float:
    bias = float(getattr(world, "comms_resilience_spend_bias", 0.0) or 0.0)
    bias = max(-0.5, min(0.5, bias))
    return max(0.0, min(1.0, (0.5 + bias) * cfg.resilience_spend_effect + 0.25 * node.health))


def _apply_transition(node: CommsNodeState, status: str, *, day: int, events: list[dict[str, object]]) -> None:
    if node.status == status:
        return
    node.status = status
    node.status_until_day = day
    events.append({"kind": f"COMMS_{status}", "node": node.node_id, "day": day})


def _update_modifiers(world: Any) -> None:
    world.comms_mod_by_ward = {}
    for node in world.comms_nodes.values():
        mod = CommsModifiers()
        if node.status == "DEGRADED":
            mod.loss_mult = 1.5
            mod.distortion_mult = 1.2
            mod.latency_add_days = 1
        elif node.status == "OUTAGE":
            mod.loss_mult = 3.0
            mod.distortion_mult = 1.5
            mod.latency_add_days = 2
        elif node.status == "JAMMED":
            mod.loss_mult = 4.0
            mod.distortion_mult = 2.5
            mod.intercept_mult = 1.5
            mod.latency_add_days = 2
        world.comms_mod_by_ward[node.ward_id] = mod


def refresh_comms_modifiers(world: Any) -> None:
    ensure_comms_state(world)
    _update_modifiers(world)


def run_comms_day(world: Any, day: int | None = None) -> None:
    cfg = ensure_comms_config(world)
    if not cfg.enabled:
        return
    ensure_comms_state(world)
    _sync_nodes(world)
    metrics = ensure_metrics(world)
    now = getattr(world, "day", 0) if day is None else int(day)
    events: list[dict[str, object]] = []
    for node_id in sorted(world.comms_nodes):
        node = world.comms_nodes[node_id]
        pressure = _ward_risk(world, node.ward_id)
        conflict_pressure = 1.0 + (1.0 if getattr(world, "raid_active", {}) else 0.0)
        defense = _defense_factor(world, node, cfg)
        salt = cfg.deterministic_salt

        if getattr(world, "comms_sabotage_targets", set()):
            if node.node_id in getattr(world, "comms_sabotage_targets", set()):
                _apply_transition(node, "OUTAGE", day=now, events=events)
                node.status_until_day = now + 1
                node.jammer_faction = str(getattr(world, "sabotage_faction", "")) or None
                continue

        if node.status in {"OK"}:
            degrade_chance = cfg.base_degrade_rate * pressure * (1.0 - min(defense, 0.8))
            jam_chance = cfg.jam_rate_war * conflict_pressure * (1.0 - 0.25 * defense)
            roll = _stable_float((node.node_id, now, "degrade"), salt)
            if roll < jam_chance:
                node.status = "JAMMED"
                node.status_until_day = now + 1
                events.append({"kind": "COMMS_JAMMED", "node": node.node_id, "day": now})
            elif roll < degrade_chance:
                _apply_transition(node, "DEGRADED", day=now, events=events)

        if node.status == "DEGRADED":
            outage_roll = _stable_float((node.node_id, now, "outage"), salt)
            if outage_roll < cfg.base_outage_rate * pressure:
                _apply_transition(node, "OUTAGE", day=now, events=events)

        if node.status == "JAMMED" and node.status_until_day >= 0 and now >= node.status_until_day:
            _apply_transition(node, "DEGRADED", day=now, events=events)

        repair_prob = cfg.repair_rate * (1.0 + defense)
        repair_roll = _stable_float((node.node_id, now, "repair"), salt)
        if repair_roll < repair_prob:
            if node.status == "OUTAGE":
                _apply_transition(node, "DEGRADED", day=now, events=events)
            elif node.status in {"DEGRADED", "JAMMED"}:
                _apply_transition(node, "OK", day=now, events=events)

        if _facility_present(world, node.ward_id, node.kind):
            node.health = min(1.0, node.health + 0.02 * (1.0 + defense))
        else:
            node.health = max(0.0, node.health - 0.05)

        node.last_update_day = now

    for evt in events[: cfg.max_events_per_day]:
        record_event(world, evt)
    if events:
        world.comms_events.extend(events[-cfg.max_events_per_day :])
    _update_modifiers(world)
    statuses = [node.status for node in world.comms_nodes.values()]
    metrics.set_gauge("comms.nodes_ok", float(statuses.count("OK")))
    metrics.set_gauge("comms.nodes_degraded", float(statuses.count("DEGRADED")))
    metrics.set_gauge("comms.nodes_outage", float(statuses.count("OUTAGE")))
    metrics.set_gauge("comms.nodes_jammed", float(statuses.count("JAMMED")))


def get_comms_modifiers_for_hop(world: Any, from_ward: str, to_ward: str, channel: str) -> CommsModifiers:
    cfg = ensure_comms_config(world)
    if not cfg.enabled:
        return CommsModifiers()
    ensure_comms_state(world)
    mod = world.comms_mod_by_ward.get(from_ward)
    if mod:
        return mod
    return CommsModifiers()


def relay_path_available(world: Any, path: list[str]) -> bool:
    if len(path) <= 1:
        return True
    cfg = ensure_comms_config(world)
    if not cfg.enabled:
        return True
    ensure_comms_state(world)
    wards = set(path)
    for ward_id, node in world.comms_nodes.items():
        if node.kind != "RELAY":
            continue
        if node.ward_id in wards and node.status == "OUTAGE":
            return False
    return True


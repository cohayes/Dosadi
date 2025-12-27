from __future__ import annotations

"""Border control and customs checks (v1).

This module implements a bounded, deterministic customs layer that can be
applied to logistics deliveries when they cross ward/policy borders.
"""

from dataclasses import dataclass, field, asdict
from hashlib import sha256
from typing import Any, Iterable, Mapping

from dosadi.runtime.institutions import ensure_policy, ensure_state
from dosadi.runtime.crackdown import border_modifiers
from dosadi.runtime.ledger import BLACK_MARKET, STATE_TREASURY, ensure_accounts, transfer
from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.world.factions import pseudo_rand01
from dosadi.runtime.policing import policing_effects


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _phase_key(world: Any) -> str:
    phase_state = getattr(world, "phase_state", None)
    phase_value = getattr(phase_state, "phase", 0)
    try:
        intval = int(getattr(phase_value, "value", phase_value))
    except Exception:
        intval = 0
    return f"P{intval}"


@dataclass(slots=True)
class CustomsConfig:
    enabled: bool = False
    base_inspection_rate: float = 0.05
    base_tariff_rate: float = 0.02
    contraband_detection_base: float = 0.10
    max_checks_per_day: int = 5000
    deterministic_salt: str = "customs-v1"
    phase_multipliers: dict[str, dict[str, float]] = field(
        default_factory=lambda: {
            "P0": {"inspection": 0.0, "tariff": 0.0, "detection": 0.0, "bribery": 0.0},
            "P1": {"inspection": 0.1, "tariff": 0.05, "detection": 0.05, "bribery": 0.05},
            "P2": {"inspection": 0.25, "tariff": 0.15, "detection": 0.15, "bribery": 0.10},
        }
    )


@dataclass(slots=True)
class CustomsEvent:
    day: int
    shipment_id: str
    border_at: str
    from_control: str
    to_control: str
    inspection: bool
    tariff_charged: float
    contraband_found: bool
    bribe_paid: float
    outcome: str
    reason_codes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BorderCrossing:
    border_at: str
    from_control: str
    to_control: str


def ensure_customs_config(world: Any) -> CustomsConfig:
    cfg = getattr(world, "customs_cfg", None)
    if not isinstance(cfg, CustomsConfig):
        cfg = CustomsConfig()
        world.customs_cfg = cfg
    return cfg


def ensure_customs_events(world: Any) -> list[CustomsEvent]:
    events = getattr(world, "customs_events", None)
    if not isinstance(events, list):
        events = []
        world.customs_events = events
    return events


def ensure_customs_counters(world: Any) -> dict[str, int]:
    counters = getattr(world, "customs_counters", None)
    if not isinstance(counters, dict):
        counters = {"checks_today": 0, "checks_day": -1}
        world.customs_counters = counters
    return counters


def _ward_for_node(world: Any, node_id: str | None) -> str:
    survey_map = getattr(world, "survey_map", None)
    if survey_map is None or not node_id:
        return "unknown"
    node = getattr(survey_map, "nodes", {}).get(node_id)
    ward_id = getattr(node, "ward_id", None)
    return str(ward_id) if ward_id is not None else "unknown"


def iter_border_crossings(world: Any, route_nodes: Iterable[str], route_edge_keys: Iterable[str]) -> list[BorderCrossing]:
    crossings: list[BorderCrossing] = []
    nodes = list(route_nodes)
    edges = list(route_edge_keys)
    for idx, edge_key in enumerate(edges):
        if idx >= len(nodes) - 1:
            break
        from_node = nodes[idx]
        to_node = nodes[idx + 1]
        from_control = _ward_for_node(world, from_node)
        to_control = _ward_for_node(world, to_node)
        if from_control != to_control:
            crossings.append(BorderCrossing(border_at=edge_key, from_control=from_control, to_control=to_control))
            continue
        # Detect policy boundary even within same ward
        policy_from = ensure_policy(world, from_control)
        policy_to = ensure_policy(world, to_control)
        if (
            getattr(policy_from, "customs_inspection_bias", 0.0) != getattr(policy_to, "customs_inspection_bias", 0.0)
            or getattr(policy_from, "customs_tariff_bias", 0.0) != getattr(policy_to, "customs_tariff_bias", 0.0)
            or getattr(policy_from, "customs_contraband_bias", 0.0)
            != getattr(policy_to, "customs_contraband_bias", 0.0)
        ):
            crossings.append(BorderCrossing(border_at=edge_key, from_control=from_control, to_control=to_control))
    return crossings


def _phase_multiplier(cfg: CustomsConfig, phase_key: str, dimension: str) -> float:
    return float(cfg.phase_multipliers.get(phase_key, {}).get(dimension, 0.0))


def _effective_tariff_rate(cfg: CustomsConfig, policy, phase_key: str, flags: set[str] | None) -> float:
    base = cfg.base_tariff_rate * (1.0 + float(getattr(policy, "customs_tariff_bias", 0.0)))
    base *= 1.0 + _phase_multiplier(cfg, phase_key, "tariff")
    if flags and "treaty_exempt" in flags:
        return 0.0
    return max(0.0, base)


def _effective_inspection_prob(cfg: CustomsConfig, policy, phase_key: str, *, escorted: bool, flags: set[str] | None) -> float:
    prob = cfg.base_inspection_rate * (1.0 + float(getattr(policy, "customs_inspection_bias", 0.0)))
    prob *= 1.0 + _phase_multiplier(cfg, phase_key, "inspection")
    if escorted:
        prob *= 0.5
    if flags and "suspicious" in flags:
        prob *= 1.5
    if flags and "treaty_exempt" in flags:
        prob *= 0.25
    return _clamp01(prob)


def _contraband_score(delivery) -> float:
    cargo = getattr(delivery, "cargo", None)
    if not cargo and hasattr(delivery, "items"):
        cargo = delivery.items
    if not cargo:
        return 0.0
    contraband_tags = {"NARCOTICS", "WEAPON_PARTS", "STOLEN_GOODS", "UNLICENSED_SUIT_MODS", "RAIDER_SUPPLIES"}
    score = 0.0
    for mat, qty in cargo.items():
        key = str(mat).upper()
        for tag in contraband_tags:
            if tag in key:
                score += 0.15 * max(1.0, float(qty))
    return _clamp01(score)


def _contraband_detection_prob(cfg: CustomsConfig, policy, phase_key: str, *, corruption: float) -> float:
    prob = cfg.contraband_detection_base * (1.0 + float(getattr(policy, "customs_contraband_bias", 0.0)))
    prob *= 1.0 + _phase_multiplier(cfg, phase_key, "detection")
    # Corruption undermines true detection
    prob *= 1.0 - 0.5 * _clamp01(corruption)
    return _clamp01(prob)


def _declared_value(delivery) -> float:
    value = float(getattr(delivery, "declared_value", 0.0) or 0.0)
    if value > 0:
        return value
    items = getattr(delivery, "items", {}) or {}
    return float(sum(float(qty) for qty in items.values()))


def _bribe_amount(tariff: float, declared_value: float) -> float:
    base = 0.25 * declared_value + 0.5 * tariff
    return max(0.0, base)


def _should_allow_bribe(policy, corruption: float) -> bool:
    tolerance = float(getattr(policy, "customs_bribe_tolerance", 0.0))
    return tolerance > 0.0 or corruption > 0.05


def _bribe_success(
    cfg: CustomsConfig,
    policy,
    corruption: float,
    enforcement_budget: float,
    key: str,
    phase_key: str,
    *,
    modifier_mult: float = 1.0,
) -> bool:
    base = _clamp01(float(getattr(policy, "customs_bribe_tolerance", 0.0)))
    base += 0.4 * _clamp01(corruption)
    base -= 0.02 * max(0.0, enforcement_budget)
    base += _phase_multiplier(cfg, phase_key, "bribery")
    return pseudo_rand01(key) < _clamp01(base * modifier_mult)


def _update_metrics(world: Any, *, tariff: float, bribe: float, seized: bool, inspected: bool) -> None:
    metrics = ensure_metrics(world)
    bucket = metrics.gauges.setdefault("customs", {})
    if isinstance(bucket, dict):
        bucket["checks"] = bucket.get("checks", 0) + 1
        bucket["inspections"] = bucket.get("inspections", 0) + (1 if inspected else 0)
        bucket["seizures"] = bucket.get("seizures", 0) + (1 if seized else 0)
        bucket["tariffs_total"] = bucket.get("tariffs_total", 0.0) + float(tariff)
        bucket["bribes_total"] = bucket.get("bribes_total", 0.0) + float(bribe)


def _append_event(world: Any, event: CustomsEvent) -> None:
    events = ensure_customs_events(world)
    events.append(event)
    cfg = ensure_customs_config(world)
    max_keep = max(1, int(cfg.max_checks_per_day))
    if len(events) > max_keep:
        overflow = len(events) - max_keep
        events[:] = events[overflow:]
    record_event(
        world,
        {
            "type": "CUSTOMS_CHECK",
            "day": event.day,
            "shipment_id": event.shipment_id,
            "border": event.border_at,
            "outcome": event.outcome,
        },
    )


def _reset_check_counter(counters: dict[str, int], day: int) -> None:
    if counters.get("checks_day") != day:
        counters["checks_day"] = day
        counters["checks_today"] = 0


def process_customs_crossing(
    world: Any,
    *,
    day: int,
    shipment,
    crossing: BorderCrossing,
) -> CustomsEvent | None:
    cfg = ensure_customs_config(world)
    if not cfg.enabled:
        return None

    counters = ensure_customs_counters(world)
    _reset_check_counter(counters, day)
    if counters["checks_today"] >= max(1, int(cfg.max_checks_per_day)):
        return None

    policy = ensure_policy(world, crossing.to_control)
    inst_state = ensure_state(world, crossing.to_control)
    enforcement_budget = float(getattr(policy, "enforcement_budget_points", 0.0) or 0.0)
    modifiers = border_modifiers(world, crossing.border_at)

    phase_key = _phase_key(world)
    flags = getattr(shipment, "flags", set()) or set()
    tariff_rate = _effective_tariff_rate(cfg, policy, phase_key, flags)
    declared_value = _declared_value(shipment)
    tariff = declared_value * tariff_rate

    escorted = bool(getattr(shipment, "escort_agent_ids", None))
    effects = policing_effects(world, crossing.to_control, day=day)

    inspection_prob = _effective_inspection_prob(cfg, policy, phase_key, escorted=escorted, flags=flags)
    inspection_prob *= float(modifiers.get("inspection_mult", 1.0))
    inspection_prob *= max(0.1, effects.detection_mult)
    inspection_prob = _clamp01(inspection_prob)
    inspect_roll = pseudo_rand01(
        "|".join(
            str(part)
            for part in (
                cfg.deterministic_salt,
                "inspect",
                day,
                getattr(shipment, "shipment_id", getattr(shipment, "delivery_id", "")),
                crossing.border_at,
            )
        )
    )
    inspection = inspect_roll < inspection_prob

    contraband_found = False
    bribe_paid = 0.0
    outcome = "CLEARED"
    reason_codes: list[str] = []

    if inspection:
        score = _contraband_score(shipment)
        detection_prob = _contraband_detection_prob(cfg, policy, phase_key, corruption=getattr(inst_state, "corruption", 0.0))
        detection_prob *= max(0.1, effects.detection_mult)
        detection_prob *= float(modifiers.get("detection_mult", 1.0))
        detection_prob = _clamp01(detection_prob)
        detect_roll = pseudo_rand01(
            "|".join(
                str(part)
                for part in (
                    cfg.deterministic_salt,
                    "detect",
                    day,
                    getattr(shipment, "shipment_id", getattr(shipment, "delivery_id", "")),
                    crossing.border_at,
                )
            )
        )
        contraband_found = score > 0 and detect_roll < detection_prob * score
        if contraband_found:
            reason_codes.append("CONTRABAND")
            smuggling_bribe_map = getattr(shipment, "smuggling_bribe_map", {}) or {}
            smuggling_bribe = float(smuggling_bribe_map.get(crossing.border_at, 0.0))
            if smuggling_bribe > 0:
                bribe_paid = smuggling_bribe
                outcome = "CLEARED"
                reason_codes.append("SMUGGLING_BRIBE")
            elif _should_allow_bribe(policy, getattr(inst_state, "corruption", 0.0)):
                bribe_key = "|".join(
                    str(part)
                    for part in (
                        cfg.deterministic_salt,
                        "bribe",
                        day,
                        getattr(shipment, "shipment_id", getattr(shipment, "delivery_id", "")),
                        crossing.border_at,
                    )
                )
                if _bribe_success(
                    cfg,
                    policy,
                    getattr(inst_state, "corruption", 0.0),
                    enforcement_budget,
                    bribe_key,
                    phase_key,
                    modifier_mult=float(modifiers.get("bribe_mult", 1.0)),
                ):
                    bribe_paid = _bribe_amount(tariff, declared_value)
                    outcome = "CLEARED"
                    reason_codes.append("BRIBE_SUCCESS")
                else:
                    outcome = "SEIZED"
                    reason_codes.append("SEIZED")
            else:
                outcome = "SEIZED"
                reason_codes.append("SEIZED")
    if not inspection and tariff > 0:
        reason_codes.append("TARIFF_ONLY")

    counters["checks_today"] += 1

    ensure_accounts(world)
    if tariff > 0:
        transfer(
            world,
            day=day,
            from_acct=f"acct:ward:{getattr(shipment, 'owner_party', crossing.from_control)}",
            to_acct=f"acct:ward:{crossing.to_control}" if crossing.to_control != "unknown" else STATE_TREASURY,
            amount=tariff,
            reason="CUSTOMS_TARIFF",
            meta={"border": crossing.border_at},
        )
    if bribe_paid > 0:
        transfer(
            world,
            day=day,
            from_acct=f"acct:ward:{getattr(shipment, 'owner_party', crossing.from_control)}",
            to_acct=BLACK_MARKET,
            amount=bribe_paid,
            reason="CUSTOMS_BRIBE",
            meta={"border": crossing.border_at},
        )

    event = CustomsEvent(
        day=day,
        shipment_id=str(getattr(shipment, "shipment_id", getattr(shipment, "delivery_id", ""))),
        border_at=crossing.border_at,
        from_control=crossing.from_control,
        to_control=crossing.to_control,
        inspection=inspection,
        tariff_charged=round(tariff, 6),
        contraband_found=contraband_found,
        bribe_paid=round(bribe_paid, 6),
        outcome=outcome,
        reason_codes=reason_codes,
    )
    _update_metrics(world, tariff=tariff, bribe=bribe_paid, seized=outcome == "SEIZED", inspected=inspection)
    _append_event(world, event)
    return event


def process_delivery_edge(
    world: Any,
    *,
    day: int,
    delivery,
    edge_key: str,
    from_node: str | None,
    to_node: str | None,
) -> None:
    cfg = ensure_customs_config(world)
    if not getattr(cfg, "enabled", False):
        return
    if from_node is None or to_node is None:
        return
    crossing = None
    from_control = _ward_for_node(world, from_node)
    to_control = _ward_for_node(world, to_node)
    if from_control != to_control:
        crossing = BorderCrossing(border_at=edge_key, from_control=from_control, to_control=to_control)
    if crossing is None:
        return
    process_customs_crossing(world, day=day, shipment=delivery, crossing=crossing)


def customs_seed_payload(world: Any) -> dict[str, Any] | None:
    cfg = getattr(world, "customs_cfg", None)
    if not isinstance(cfg, CustomsConfig):
        return None
    events = getattr(world, "customs_events", None)
    payload: dict[str, Any] = {"config": asdict(cfg)}
    if isinstance(events, list):
        payload["events"] = [asdict(evt) for evt in events if isinstance(evt, CustomsEvent)]
    return payload


def load_customs_from_seed(world: Any, payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        return
    cfg_data = payload.get("config") if isinstance(payload, Mapping) else None
    if isinstance(cfg_data, Mapping):
        cfg = CustomsConfig(**cfg_data)
        world.customs_cfg = cfg
    events_raw = payload.get("events") if isinstance(payload, Mapping) else None
    if isinstance(events_raw, list):
        events: list[CustomsEvent] = []
        for item in events_raw:
            if not isinstance(item, Mapping):
                continue
            events.append(CustomsEvent(**item))
        world.customs_events = events

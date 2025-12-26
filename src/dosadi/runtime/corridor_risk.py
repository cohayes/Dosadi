from __future__ import annotations

"""Corridor risk tracking and observation hooks."""

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Dict, Iterable, Mapping, MutableMapping


DEFAULT_ALPHA = 0.2


@dataclass(slots=True)
class CorridorRiskConfig:
    enabled: bool = False
    risk_decay_per_day: float = 0.01
    max_risk: float = 1.0
    incident_weight: float = 0.25
    suit_damage_weight: float = 0.10
    stall_weight: float = 0.05
    hazard_prior_weight: float = 0.30
    min_updates_per_day: int = 0
    max_edges_tracked: int = 5000
    topk_hot_edges: int = 50
    deterministic_salt: str = "corridor-risk-v2"


@dataclass(slots=True)
class EdgeRiskRecord:
    edge_key: str
    risk: float = 0.0
    hazard_prior: float = 0.0
    incidents_lookback: float = 0.0
    suit_damage_ema: float = 0.0
    stall_ema: float = 0.0
    last_updated_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class CorridorRiskLedger:
    edges: Dict[str, EdgeRiskRecord] = field(default_factory=dict)
    hot_edges: list[str] = field(default_factory=list)

    def record(self, edge_key: str, *, hazard_prior: float = 0.0) -> EdgeRiskRecord:
        if edge_key not in self.edges:
            self.edges[edge_key] = EdgeRiskRecord(edge_key=edge_key, hazard_prior=max(0.0, min(1.0, hazard_prior)))
        else:
            rec = self.edges[edge_key]
            if hazard_prior > rec.hazard_prior:
                rec.hazard_prior = min(1.0, hazard_prior)
        return self.edges[edge_key]

    def signature(self) -> str:
        canonical: Mapping[str, Mapping[str, object]] = {
            edge_key: {
                "risk": round(rec.risk, 6),
                "hazard": round(rec.hazard_prior, 6),
                "inc": round(rec.incidents_lookback, 6),
                "suit": round(rec.suit_damage_ema, 6),
                "stall": round(rec.stall_ema, 6),
                "day": rec.last_updated_day,
            }
            for edge_key, rec in sorted(self.edges.items())
        }
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()


def _clamp01(val: float) -> float:
    return max(0.0, min(1.0, val))


def _edge_hazard(world, edge_key: str) -> float:
    survey_map = getattr(world, "survey_map", None)
    if survey_map is None:
        return 0.0
    edge = getattr(survey_map, "edges", {}).get(edge_key)
    if edge is None:
        return 0.0
    return _clamp01(float(getattr(edge, "hazard", 0.0) or 0.0))


def ensure_corridor_risk_config(world) -> CorridorRiskConfig:
    cfg = getattr(world, "risk_cfg", None)
    if not isinstance(cfg, CorridorRiskConfig):
        cfg = CorridorRiskConfig()
        world.risk_cfg = cfg
    return cfg


def ensure_corridor_risk_ledger(world) -> CorridorRiskLedger:
    ledger = getattr(world, "risk_ledger", None)
    if not isinstance(ledger, CorridorRiskLedger):
        ledger = CorridorRiskLedger()
        world.risk_ledger = ledger
    return ledger


def edge_key(a: str, b: str) -> str:
    return "|".join(sorted((str(a), str(b))))


def _decay_value(value: float, decay: float, days_elapsed: int) -> float:
    if days_elapsed <= 0 or decay <= 0:
        return value
    factor = (1.0 - decay) ** max(0, days_elapsed)
    return value * factor


def _update_hot_edges(ledger: CorridorRiskLedger, cfg: CorridorRiskConfig) -> None:
    ranked = sorted(
        ledger.edges.values(),
        key=lambda rec: (-round(rec.risk, 6), rec.edge_key),
    )
    ledger.hot_edges = [rec.edge_key for rec in ranked[: max(0, cfg.topk_hot_edges)]]


def _enforce_cap(ledger: CorridorRiskLedger, cfg: CorridorRiskConfig) -> None:
    max_edges = max(1, int(cfg.max_edges_tracked))
    if len(ledger.edges) <= max_edges:
        return
    to_drop = len(ledger.edges) - max_edges
    victims = sorted(ledger.edges.values(), key=lambda rec: (round(rec.risk, 6), rec.edge_key))
    for rec in victims[:to_drop]:
        ledger.edges.pop(rec.edge_key, None)


def update_edge_risk(
    world,
    edge_key: str,
    *,
    day: int,
    incident_severity: float = 0.0,
    suit_damage: float = 0.0,
    stall: float = 0.0,
) -> None:
    cfg = ensure_corridor_risk_config(world)
    if not getattr(cfg, "enabled", False):
        return

    ledger = ensure_corridor_risk_ledger(world)
    hazard_prior = _edge_hazard(world, edge_key)
    record = ledger.record(edge_key, hazard_prior=hazard_prior)

    days_elapsed = day - record.last_updated_day if record.last_updated_day >= 0 else 0
    record.risk = _decay_value(record.risk, cfg.risk_decay_per_day, days_elapsed)
    record.incidents_lookback = _decay_value(record.incidents_lookback, cfg.risk_decay_per_day, days_elapsed)
    record.suit_damage_ema = _decay_value(record.suit_damage_ema, cfg.risk_decay_per_day, days_elapsed)
    record.stall_ema = _decay_value(record.stall_ema, cfg.risk_decay_per_day, days_elapsed)

    record.incidents_lookback = _clamp01(record.incidents_lookback + _clamp01(incident_severity))
    record.suit_damage_ema = _clamp01(DEFAULT_ALPHA * suit_damage + (1.0 - DEFAULT_ALPHA) * record.suit_damage_ema)
    record.stall_ema = _clamp01(DEFAULT_ALPHA * stall + (1.0 - DEFAULT_ALPHA) * record.stall_ema)

    incident_component = cfg.incident_weight * record.incidents_lookback
    suit_component = cfg.suit_damage_weight * record.suit_damage_ema
    stall_component = cfg.stall_weight * record.stall_ema
    hazard_component = cfg.hazard_prior_weight * record.hazard_prior

    risk_value = hazard_component + incident_component + suit_component + stall_component
    record.risk = _clamp01(min(cfg.max_risk, risk_value))
    record.last_updated_day = day

    _enforce_cap(ledger, cfg)
    _update_hot_edges(ledger, cfg)


def observe_edge_traversal(
    world,
    edge_key: str,
    *,
    day: int,
    suit_damage: float = 0.0,
    stalled: float = 0.0,
) -> None:
    update_edge_risk(world, edge_key, day=day, suit_damage=suit_damage, stall=stalled)


def observe_edge_incident(world, edge_key: str, *, day: int, severity: float = 0.0) -> None:
    update_edge_risk(world, edge_key, day=day, incident_severity=severity)


def risk_for_edge(world, edge_key: str) -> float:
    ledger: CorridorRiskLedger | None = getattr(world, "risk_ledger", None)
    if ledger is None:
        return 0.0
    rec = ledger.edges.get(edge_key)
    if rec is None:
        return 0.0
    base = _clamp01(rec.risk)
    try:
        from dosadi.runtime.crackdown import corridor_modifiers

        mods = corridor_modifiers(world, edge_key)
        return _clamp01(base * float(mods.get("risk_mult", 1.0)))
    except Exception:
        return base


def hot_edges(ledger: CorridorRiskLedger) -> Iterable[str]:
    return tuple(getattr(ledger, "hot_edges", []) or [])


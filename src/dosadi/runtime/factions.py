from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from dosadi.runtime.law_enforcement import interdiction_prob_for_edge
from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.world.factions import (
    Faction,
    FactionSystemConfig,
    FactionSystemState,
    FactionTerritory,
    enforce_claim_cap,
    ensure_faction_territory,
    pseudo_rand01,
    update_claim,
)


@dataclass(slots=True)
class Opportunity:
    kind: str
    target_id: str
    value: float


def _clamp01(val: float) -> float:
    return max(0.0, min(1.0, float(val)))


def _ensure_cfg(world: Any) -> FactionSystemConfig:
    cfg = getattr(world, "faction_cfg", None)
    if not isinstance(cfg, FactionSystemConfig):
        cfg = FactionSystemConfig()
        world.faction_cfg = cfg
    return cfg


def _ensure_state(world: Any) -> FactionSystemState:
    state = getattr(world, "faction_state", None)
    if not isinstance(state, FactionSystemState):
        state = FactionSystemState()
        world.faction_state = state
    return state


def _load_factions(world: Any) -> dict[str, Faction]:
    factions = {}
    raw = getattr(world, "factions", {}) or {}
    for faction_id, value in raw.items():
        if isinstance(value, Faction):
            factions[faction_id] = value
            continue
        name = getattr(value, "name", str(faction_id))
        kind = getattr(value, "archetype", "STATE")
        factions[faction_id] = Faction(
            faction_id=faction_id,
            name=name,
            kind=str(kind),
        )
    return factions


def _risk_opportunities(world: Any) -> Iterable[Opportunity]:
    ledger = getattr(world, "risk_ledger", None)
    if ledger is None or not hasattr(ledger, "edges"):
        return ()
    items = []
    for edge_key, record in getattr(ledger, "edges", {}).items():
        value = float(getattr(record, "risk", 0.0))
        if value <= 0:
            continue
        items.append(Opportunity(kind="edge", target_id=str(edge_key), value=_clamp01(value)))
    return items


def _ward_opportunities(world: Any) -> Iterable[Opportunity]:
    wards = getattr(world, "wards", {}) or {}
    items = []
    for ward_id, ward in wards.items():
        stress = getattr(getattr(ward, "environment", None), "stress", 0.0)
        items.append(Opportunity(kind="ward", target_id=str(ward_id), value=_clamp01(stress / 100.0)))
    return items


def _opportunity_basket(world: Any, *, cfg: FactionSystemConfig) -> list[Opportunity]:
    options = list(_risk_opportunities(world))
    options.extend(_ward_opportunities(world))
    options.sort(key=lambda o: (-o.value, o.kind, o.target_id))
    return options[: max(0, int(cfg.topk_opportunities))]


def _success_probability(faction: Faction, opportunity: Opportunity, world: Any) -> float:
    base = 0.55 if faction.kind.upper() == "STATE" else 0.5
    if opportunity.kind == "edge":
        prob = interdiction_prob_for_edge(world, opportunity.target_id, None)
        base -= prob * 0.35
    if faction.kind.upper() == "RAIDERS":
        base += 0.05
    if opportunity.kind == "ward":
        culture = getattr(world, "culture_by_ward", {}) or {}
        culture_state = culture.get(opportunity.target_id)
        if culture_state is not None:
            norms = getattr(culture_state, "norms", {})
            alignment = getattr(culture_state, "alignment", {})
            anti_state = float(norms.get("norm:anti_state", 0.0))
            anti_raider = float(norms.get("norm:anti_raider", 0.0))
            smuggling = float(norms.get("norm:smuggling_tolerance", 0.0))
            if faction.kind.upper() == "RAIDERS":
                base += 0.08 * smuggling - 0.05 * anti_raider
                base += 0.05 * float(alignment.get("fac:raiders", 0.0))
            else:
                base += 0.08 * anti_raider - 0.06 * smuggling - 0.07 * anti_state
                base += 0.05 * float(alignment.get("fac:state", 0.0))
    return _clamp01(base)


def _apply_outcome(
    *,
    faction: Faction,
    territory: FactionTerritory,
    opportunity: Opportunity,
    success: bool,
    cfg: FactionSystemConfig,
    day: int,
    world: Any,
) -> None:
    delta = cfg.claim_gain_on_success if success else -cfg.claim_loss_on_failure
    bucket = "ward" if opportunity.kind == "ward" else "edge"
    before = territory.wards.get(opportunity.target_id, 0.0) if bucket == "ward" else territory.edges.get(opportunity.target_id, 0.0)
    updated = update_claim(
        territory=territory,
        bucket=bucket,
        key=opportunity.target_id,
        delta=delta,
        day=day,
        cfg=cfg,
    )
    if abs(updated - before) > 1e-9:
        record_event(
            world,
            {
                "kind": "FACTION_CLAIM", 
                "day": day,
                "faction_id": faction.faction_id,
                "bucket": bucket,
                "target": opportunity.target_id,
                "strength": updated,
            },
        )


def _decay_territories(world: Any, cfg: FactionSystemConfig) -> None:
    territories = getattr(world, "faction_territory", {}) or {}
    for territory in territories.values():
        territory.decay(cfg=cfg)


def run_real_factions_for_day(world: Any, *, day: int) -> None:
    cfg = _ensure_cfg(world)
    state = _ensure_state(world)
    if not cfg.enabled or state.last_run_day == day:
        return

    factions = _load_factions(world)
    world.factions = factions
    _decay_territories(world, cfg)

    opportunities = _opportunity_basket(world, cfg=cfg)
    metrics = ensure_metrics(world)
    metrics.inc("factions.count", len(factions))

    for faction_id in sorted(factions.keys()):
        faction = factions[faction_id]
        territory = ensure_faction_territory(world, faction_id)
        actions_taken = 0
        for opportunity in opportunities:
            if actions_taken >= cfg.max_actions_per_faction_per_day:
                break
            prob = _success_probability(faction, opportunity, world)
            key = f"{cfg.deterministic_salt}|{faction.faction_id}|{day}|{opportunity.kind}|{opportunity.target_id}"
            roll = pseudo_rand01(key)
            success = roll <= prob
            _apply_outcome(
                faction=faction,
                territory=territory,
                opportunity=opportunity,
                success=success,
                cfg=cfg,
                day=day,
                world=world,
            )
            actions_taken += 1
            metrics.inc("factions.actions_taken", 1.0)
            metrics.topk_add(
                "factions.top_claims",
                f"{faction.faction_id}:{opportunity.target_id}",
                prob,
                payload={"success": success},
            )
        enforce_claim_cap(territory, cfg=cfg)
        state.actions_taken_today[faction_id] = actions_taken

    state.last_run_day = day


__all__ = ["Opportunity", "run_real_factions_for_day"]

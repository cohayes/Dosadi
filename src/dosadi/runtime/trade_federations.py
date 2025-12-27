"""Trade federation and cartel coordination primitives (v1).

This module implements a lightweight, deterministic model of trade
federations and cartel agreements as outlined in
``D-RUNTIME-0301_Trade_Federations_and_Cartels_v1_Implementation_Checklist``.
It focuses on bounded state, reproducible formation, and simple market
effects that can be composed with the existing market signals pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.world.phases import WorldPhase
from dosadi.world.factions import pseudo_rand01


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _stable_rand(key: str) -> float:
    return pseudo_rand01(key)


@dataclass(slots=True)
class FederationConfig:
    enabled: bool = False
    update_cadence_days: int = 14
    deterministic_salt: str = "federations-v1"
    max_federations_total: int = 12
    max_cartels_total: int = 24
    max_members_per_fed: int = 10
    formation_rate_base: float = 0.002
    cartelization_rate_p2: float = 0.006
    enforcement_strength: float = 0.55
    defection_rate_base: float = 0.03


@dataclass(slots=True)
class Federation:
    fed_id: str
    name: str
    archetype: str
    members: list[str]
    polities: list[str]
    hq_ward_id: str
    influence: float = 0.0
    cohesion: float = 0.5
    treasury: float = 0.0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class CartelAgreement:
    cartel_id: str
    fed_id: str | None
    goods: list[str]
    kind: str
    members: list[str]
    target_price_mult: float = 1.0
    quota_by_member: dict[str, float] = field(default_factory=dict)
    hoard_target_days: int = 0
    enforcement_mode: str = "SOFT"
    start_day: int = 0
    end_day: int = 0
    status: str = "ACTIVE"
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class CartelCompliance:
    cartel_id: str
    member_id: str
    cheat_score: float = 0.0
    penalties_applied: int = 0
    last_update_day: int = -1


ARCHETYPES = [
    "MERCHANT_LEAGUE",
    "ENGINEERS_CONSORTIUM",
    "WATER_AUTHORITY",
    "MILITARY_SUPPLY_COMPACT",
]


def ensure_federation_config(world: Any) -> FederationConfig:
    cfg = getattr(world, "fed_cfg", None)
    if isinstance(cfg, FederationConfig):
        return cfg
    cfg = FederationConfig()
    world.fed_cfg = cfg
    return cfg


def ensure_federations(world: Any) -> dict[str, Federation]:
    feds = getattr(world, "federations", None)
    if isinstance(feds, dict):
        return feds
    feds = {}
    world.federations = feds
    return feds


def ensure_cartels(world: Any) -> dict[str, CartelAgreement]:
    cartels = getattr(world, "cartels", None)
    if isinstance(cartels, dict):
        return cartels
    cartels = {}
    world.cartels = cartels
    return cartels


def ensure_cartel_compliance(world: Any) -> dict[tuple[str, str], CartelCompliance]:
    compliance = getattr(world, "cartel_compliance", None)
    if isinstance(compliance, dict):
        return compliance
    compliance = {}
    world.cartel_compliance = compliance
    return compliance


def ensure_fed_events(world: Any) -> list[dict[str, object]]:
    events = getattr(world, "fed_events", None)
    if isinstance(events, list):
        return events
    events = []
    world.fed_events = events
    return events


def _record_fed_event(world: Any, event_type: str, payload: Mapping[str, object]) -> None:
    events = ensure_fed_events(world)
    entry = {"type": event_type, **payload}
    events.append(entry)
    if len(events) > 500:
        del events[: len(events) - 500]
    record_event(world, {"type": event_type, **payload})


def _faction_score(faction: Any) -> float:
    members = len(getattr(faction, "members", []) or [])
    influence = getattr(getattr(faction, "metrics", None), "econ", None)
    reliability = getattr(influence, "reliability", 0.5) if influence is not None else 0.5
    return _clamp01(0.2 + 0.15 * members + 0.6 * reliability)


def _cohesion_for_cartel(world: Any, cartel: CartelAgreement) -> float:
    if cartel.fed_id:
        fed = ensure_federations(world).get(cartel.fed_id)
        if isinstance(fed, Federation):
            return _clamp01(fed.cohesion)
    return 0.5


def _enforcement_factor(cfg: FederationConfig, cartel: CartelAgreement) -> float:
    base = _clamp01(cfg.enforcement_strength)
    mode = getattr(cartel, "enforcement_mode", "SOFT") or "SOFT"
    if mode == "CUSTOMS":
        return _clamp01(base * 1.2)
    if mode == "COERCIVE":
        return _clamp01(base * 1.4)
    return base * 0.8


def _withheld_fraction(cartel: CartelAgreement) -> float:
    quota_total = sum(cartel.quota_by_member.values()) if cartel.quota_by_member else 1.0
    quota_gap = max(0.0, 1.0 - quota_total)
    hoard_component = min(1.0, max(0, int(cartel.hoard_target_days)) / 60.0)
    return _clamp01(max(quota_gap, hoard_component))


def _active_cartels(world: Any, *, day: int) -> Iterable[CartelAgreement]:
    cartels = ensure_cartels(world)
    for cartel_id in sorted(cartels.keys()):
        cartel = cartels[cartel_id]
        if cartel.status != "ACTIVE":
            continue
        if day < int(getattr(cartel, "start_day", 0)):
            continue
        end_day = int(getattr(cartel, "end_day", 0))
        if end_day and day > end_day:
            continue
        yield cartel


def cartel_price_multiplier(world: Any, *, material: str, day: int) -> float:
    multiplier = 1.0
    for cartel in _active_cartels(world, day=day):
        if material not in cartel.goods:
            continue
        multiplier = max(multiplier, float(max(1.0, cartel.target_price_mult)))
    return multiplier


def cartel_withheld_supply(world: Any, *, material: str, day: int) -> float:
    withheld = 0.0
    for cartel in _active_cartels(world, day=day):
        if material not in cartel.goods:
            continue
        withheld = max(withheld, _withheld_fraction(cartel))
    return _clamp01(withheld)


def apply_cartel_to_market_signal(
    world: Any, *, material: str, demand: float, supply: float, day: int
) -> tuple[float, float, float, float]:
    multiplier = cartel_price_multiplier(world, material=material, day=day)
    withheld = cartel_withheld_supply(world, material=material, day=day)
    adjusted_demand = float(demand) * multiplier
    adjusted_supply = float(supply) * max(0.0, 1.0 - withheld)

    metrics = ensure_metrics(world)
    feds_metrics = metrics.gauges.setdefault("feds", {})
    price_bucket: dict[str, float] = feds_metrics.get("price_mult", {}) or {}
    withheld_bucket: dict[str, float] = feds_metrics.get("withheld", {}) or {}
    price_bucket[material] = multiplier
    withheld_bucket[material] = withheld
    feds_metrics["price_mult"] = price_bucket
    feds_metrics["withheld"] = withheld_bucket
    feds_metrics["avg_price_mult"] = sum(price_bucket.values()) / max(1, len(price_bucket))
    feds_metrics["withheld_supply_proxy"] = sum(withheld_bucket.values()) / max(1, len(withheld_bucket))
    metrics.gauges["feds"] = feds_metrics

    return adjusted_demand, adjusted_supply, multiplier, withheld


def _maybe_form_federation(
    *,
    world: Any,
    day: int,
    cfg: FederationConfig,
    archetype: str,
    candidates: list[tuple[str, float]],
) -> Federation | None:
    if not candidates:
        return None
    capacity_left = max(0, int(cfg.max_federations_total) - len(ensure_federations(world)))
    if capacity_left <= 0:
        return None
    best_score = candidates[0][1]
    rand = _stable_rand(f"{cfg.deterministic_salt}:{archetype}:{day}")
    threshold = cfg.formation_rate_base * best_score
    if rand >= threshold or best_score <= 0.0:
        return None
    members = [fid for fid, _ in candidates[: max(1, int(cfg.max_members_per_fed))]]
    fed_id = f"fed:{archetype.lower()}:{len(ensure_federations(world)) + 1}"
    hq_ward = getattr(world.factions.get(members[0]), "home_ward", "") if members else ""
    polities: list[str] = []
    for fid in members:
        faction = world.factions.get(fid)
        polity = getattr(faction, "home_ward", None)
        if polity:
            polities.append(str(polity))
    fed = Federation(
        fed_id=fed_id,
        name=f"{archetype.title().replace('_', ' ')} {len(ensure_federations(world)) + 1}",
        archetype=archetype,
        members=members,
        polities=sorted(set(polities)),
        hq_ward_id=hq_ward or "",
        influence=min(1.0, best_score),
        cohesion=0.55,
        treasury=0.0,
        last_update_day=day,
    )
    ensure_federations(world)[fed_id] = fed
    _record_fed_event(world, "FEDERATION_FORMED", {"fed_id": fed_id, "archetype": archetype, "members": members, "day": day})
    return fed


def _maybe_form_cartel(
    *, world: Any, day: int, cfg: FederationConfig, fed: Federation | None, goods: list[str]
) -> CartelAgreement | None:
    cartels = ensure_cartels(world)
    if len(cartels) >= cfg.max_cartels_total:
        return None
    archetype = getattr(fed, "archetype", "standalone") if fed else "standalone"
    salt = f"{cfg.deterministic_salt}:cartel:{archetype}:{day}:{len(cartels)}"
    chance = cfg.cartelization_rate_p2
    if _stable_rand(salt) >= chance:
        return None
    members = list(getattr(fed, "members", []) or [])
    if not members:
        members = [fid for fid in sorted(world.factions.keys())[:3]]
    goods_list = sorted(set(goods or ["WATER"]))[:3]
    cartel_id = f"cartel:{goods_list[0].lower()}:{len(cartels) + 1}"
    quota_total = 0.8
    quota = quota_total / max(1, len(members))
    quota_map = {member: quota for member in members}
    cartel = CartelAgreement(
        cartel_id=cartel_id,
        fed_id=getattr(fed, "fed_id", None),
        goods=goods_list,
        kind="PRICE_FLOOR" if goods_list else "QUOTA_ALLOCATION",
        members=members,
        target_price_mult=1.0 + best_effort_score(world, members),
        quota_by_member=quota_map,
        hoard_target_days=7,
        enforcement_mode="CUSTOMS" if fed else "SOFT",
        start_day=day,
        end_day=day + cfg.update_cadence_days,
        status="ACTIVE",
    )
    cartels[cartel_id] = cartel
    _record_fed_event(
        world,
        "CARTEL_CREATED",
        {"cartel_id": cartel_id, "goods": goods_list, "fed_id": cartel.fed_id, "members": members, "day": day},
    )
    return cartel


def best_effort_score(world: Any, members: Iterable[str]) -> float:
    scores = []
    for member in members:
        faction = world.factions.get(member)
        if faction is None:
            continue
        scores.append(_faction_score(faction))
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _update_cartel_compliance(world: Any, *, day: int, cfg: FederationConfig) -> None:
    compliance = ensure_cartel_compliance(world)
    metrics = ensure_metrics(world)
    for cartel in _active_cartels(world, day=day):
        cohesion = _cohesion_for_cartel(world, cartel)
        enforcement = _enforcement_factor(cfg, cartel)
        withheld = _withheld_fraction(cartel)
        for member in cartel.members:
            key = (cartel.cartel_id, member)
            entry = compliance.get(key)
            if entry is None:
                entry = CartelCompliance(cartel_id=cartel.cartel_id, member_id=member)
                compliance[key] = entry
            incentive = max(0.0, cartel.target_price_mult - 1.0) + cfg.defection_rate_base + 0.5 * withheld
            cheat_raw = incentive * (1.0 - 0.4 * cohesion) * (1.0 - 0.6 * enforcement)
            cheat_raw = _clamp01(cheat_raw)
            entry.cheat_score = _clamp01(0.6 * entry.cheat_score + 0.4 * cheat_raw)
            entry.penalties_applied += int(enforcement * 10 if entry.cheat_score > 0.5 else 0)
            entry.last_update_day = day
            if entry.cheat_score > 0.78:
                cartel.status = "BROKEN"
                cartel.end_day = day
                metrics.counters["feds.cartel_breakups"] = metrics.counters.get("feds.cartel_breakups", 0.0) + 1.0
                _record_fed_event(
                    world,
                    "CARTEL_BROKE",
                    {"cartel_id": cartel.cartel_id, "member_id": member, "cheat_score": entry.cheat_score, "day": day},
                )
                break


def run_federations_update(world: Any, *, day: int) -> None:
    cfg = ensure_federation_config(world)
    if not cfg.enabled:
        return
    last = getattr(world, "fed_last_update_day", -1)
    if last >= 0 and day - last < max(1, int(cfg.update_cadence_days)):
        return
    world.fed_last_update_day = day

    factions = getattr(world, "factions", {}) or {}
    candidates: list[tuple[str, float]] = []
    for faction_id in sorted(factions.keys()):
        score = _faction_score(factions[faction_id])
        candidates.append((faction_id, score))
    candidates.sort(key=lambda row: (-row[1], row[0]))

    for archetype in ARCHETYPES:
        _maybe_form_federation(world=world, day=day, cfg=cfg, archetype=archetype, candidates=candidates)

    phase_state = getattr(world, "phase_state", None)
    in_cartel_phase = getattr(getattr(phase_state, "phase", None), "value", 0) >= WorldPhase.PHASE2
    if in_cartel_phase:
        active_goods = sorted(getattr(getattr(world, "market_state", None), "global_signals", {}).keys())
        goods = active_goods or ["WATER", "FOOD"]
        for fed in ensure_federations(world).values():
            _maybe_form_cartel(world=world, day=day, cfg=cfg, fed=fed, goods=goods)
    _update_cartel_compliance(world, day=day, cfg=cfg)


def federation_actor_id(fed: Federation) -> str:
    return fed.fed_id


__all__ = [
    "FederationConfig",
    "Federation",
    "CartelAgreement",
    "CartelCompliance",
    "apply_cartel_to_market_signal",
    "cartel_price_multiplier",
    "cartel_withheld_supply",
    "ensure_federation_config",
    "ensure_federations",
    "ensure_cartels",
    "ensure_cartel_compliance",
    "ensure_fed_events",
    "run_federations_update",
    "federation_actor_id",
]

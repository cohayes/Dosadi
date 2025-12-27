"""Lineages, inheritance, and nepotism helpers (D-RUNTIME-0308 v1).

This module keeps the implementation intentionally lightweight.  Houses are
macro buckets attached to a polity rather than explicit family trees.  The
logic focuses on deterministic, bounded state updates that can bias workforce
allocation without introducing global scans.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from dosadi.runtime.constitution import CONSTRAINT_DIMENSIONS, effective_rights
from dosadi.runtime.local_interactions import hashed_unit_float
from dosadi.runtime.mobility import MobilityConfig, ensure_mobility_config, ensure_polity_mobility_state
from dosadi.runtime.sovereignty import ensure_sovereignty_state
from dosadi.runtime.telemetry import ensure_metrics


@dataclass(slots=True)
class LineageConfig:
    enabled: bool = False
    update_cadence_days: int = 90
    deterministic_salt: str = "lineages-v1"
    max_houses_per_polity: int = 32
    max_edges_per_polity: int = 64
    inheritance_years: int = 25
    nepotism_bias_scale: float = 0.25
    anti_nepotism_scale: float = 0.30


@dataclass(slots=True)
class House:
    house_id: str
    polity_id: str
    name: str
    tier: str
    wealth: float = 0.0
    influence: float = 0.0
    reputation: float = 0.5
    debt: float = 0.0
    members_proxy: int = 0
    head_generation: int = 0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class PatronEdge:
    polity_id: str
    from_house_id: str
    to_domain: str
    strength: float
    mode: str
    exposure: float = 0.0
    last_update_day: int = -1


@dataclass(slots=True)
class LineageState:
    polity_id: str
    houses: dict[str, House] = field(default_factory=dict)
    edges: list[PatronEdge] = field(default_factory=list)
    last_inheritance_year: int = 0
    nepotism_norm: float = 0.0
    last_update_day: int = -1


ROLE_TO_DOMAIN = {
    "SUPERVISOR": "COUNCIL",
    "FOREMAN": "DEPOTS",
    "OFFICER": "COURTS",
    "CLERK": "CUSTOMS",
    "TECHNICIAN": "WORKFORCE",
}


def ensure_lineage_config(world: Any) -> LineageConfig:
    cfg = getattr(world, "lineage_cfg", None)
    if not isinstance(cfg, LineageConfig):
        cfg = LineageConfig()
        world.lineage_cfg = cfg
    return cfg


def ensure_lineage_state(world: Any, polity_id: str) -> LineageState:
    bucket: dict[str, LineageState] = getattr(world, "lineage_by_polity", None) or {}
    state = bucket.get(polity_id)
    if not isinstance(state, LineageState):
        state = LineageState(polity_id=polity_id)
        bucket[polity_id] = state
        world.lineage_by_polity = bucket
    return state


def _polities(world: Any) -> list[str]:
    # Reuse sovereignty mapping when present; otherwise default to world.polity_id.
    polities = sorted(getattr(getattr(world, "sovereignty_state", None), "polities", {}).keys())
    if polities:
        return polities
    default = getattr(world, "polity_id", "polity:default")
    return [default]


def _house_name(polity_id: str, tier: str, idx: int) -> str:
    return f"House {tier.title()} {idx + 1} ({polity_id})"


def _seed_houses(world: Any, polity_id: str, *, day: int, cfg: LineageConfig, mobility_cfg: MobilityConfig) -> None:
    state = ensure_lineage_state(world, polity_id)
    if state.houses:
        return

    mobility_state = ensure_polity_mobility_state(world, polity_id, cfg=mobility_cfg)
    shares = mobility_state.tier_share or {}
    tiers = list(mobility_cfg.tiers)
    remaining = cfg.max_houses_per_polity
    for tier in tiers:
        if remaining <= 0:
            break
        share = max(0.0, float(shares.get(tier, 0.0)))
        count = max(1, int(round(share * cfg.max_houses_per_polity * 0.5)))
        count = min(count, remaining)
        for idx in range(count):
            hid = f"house:{polity_id}:{tier.lower()}:{idx}"
            house = House(
                house_id=hid,
                polity_id=polity_id,
                name=_house_name(polity_id, tier, idx),
                tier=tier,
                wealth=round(10.0 * (1.0 + share) * (1.0 + hashed_unit_float(cfg.deterministic_salt, hid)), 3),
                influence=round(0.05 + 0.45 * share, 3),
                reputation=round(0.45 + 0.25 * share, 3),
                members_proxy=max(5, int(12 * (1.0 + share))),
                last_update_day=day,
            )
            state.houses[hid] = house
            remaining -= 1
            if remaining <= 0:
                break
    state.nepotism_norm = _nepotism_norm(state)


def _nepotism_norm(state: LineageState) -> float:
    if not state.houses:
        return 0.0
    avg_influence = sum(h.influence for h in state.houses.values()) / len(state.houses)
    return max(0.0, min(1.0, avg_influence))


def _update_house_metrics(house: House, *, share: float, day: int) -> None:
    tier_bonus = {
        "ELITE": 1.4,
        "GUILD": 1.25,
        "CLERK": 1.1,
        "SKILLED": 1.0,
        "WORKING": 0.8,
        "UNDERCLASS": 0.6,
    }
    growth = (1.0 + share * 2.0) * tier_bonus.get(house.tier, 1.0)
    house.wealth = round(house.wealth + growth, 3)
    house.influence = max(0.0, min(1.0, round(house.influence + 0.01 + share * 0.05, 3)))
    house.reputation = max(0.0, min(1.0, round(house.reputation + 0.005, 3)))
    house.last_update_day = day


def _update_edges(state: LineageState, *, cfg: LineageConfig, corruption: float, day: int) -> None:
    if not state.houses:
        return
    edges: list[PatronEdge] = []
    house_list = sorted(state.houses.values(), key=lambda h: (-h.influence, h.house_id))
    domains = list(ROLE_TO_DOMAIN.values())
    for idx, house in enumerate(house_list):
        domain = domains[idx % len(domains)]
        strength = max(0.0, min(1.0, 0.1 + house.influence * (0.8 + corruption)))
        edges.append(
            PatronEdge(
                polity_id=state.polity_id,
                from_house_id=house.house_id,
                to_domain=domain,
                strength=round(strength, 3),
                mode="NEPOTISM" if corruption < 0.5 else "PATRONAGE",
                exposure=round(corruption * 0.2, 3),
                last_update_day=day,
            )
        )
        if len(edges) >= cfg.max_edges_per_polity:
            break
    state.edges = edges


def _apply_inheritance(state: LineageState, *, cfg: LineageConfig, day: int) -> None:
    inheritance_interval = max(1, int(cfg.inheritance_years * 365))
    current_year = max(0, int(day / 365))
    if current_year - state.last_inheritance_year < cfg.inheritance_years:
        return
    for house in state.houses.values():
        transfer = max(0.0, house.wealth * 0.15)
        house.wealth = round(house.wealth + transfer, 3)
        house.head_generation += 1
        house.last_update_day = day
    state.last_inheritance_year = current_year


def update_lineages(world: Any, *, day: int) -> None:
    cfg = ensure_lineage_config(world)
    if not cfg.enabled:
        return

    mobility_cfg = ensure_mobility_config(world)
    polities = _polities(world)
    corruption_by_polity = getattr(world, "corruption_index_by_polity", {}) or {}
    metrics = ensure_metrics(world)
    lineage_metrics = getattr(metrics, "gauges", {}).setdefault("lineages", {})
    for polity_id in polities:
        state = ensure_lineage_state(world, polity_id)
        _seed_houses(world, polity_id, day=day, cfg=cfg, mobility_cfg=mobility_cfg)
        if state.last_update_day >= 0 and day - state.last_update_day < cfg.update_cadence_days:
            continue
        mobility_state = ensure_polity_mobility_state(world, polity_id, cfg=mobility_cfg)
        shares = mobility_state.tier_share or {}
        for house in state.houses.values():
            share = float(shares.get(house.tier, 0.0))
            _update_house_metrics(house, share=share, day=day)

        corruption = max(0.0, min(1.0, float(corruption_by_polity.get(polity_id, 0.0))))
        _update_edges(state, cfg=cfg, corruption=corruption, day=day)
        state.nepotism_norm = _nepotism_norm(state) + 0.2 * corruption
        state.nepotism_norm = max(0.0, min(1.0, state.nepotism_norm))
        _apply_inheritance(state, cfg=cfg, day=day)
        state.last_update_day = day

        if isinstance(lineage_metrics, dict):
            if state.houses:
                top_house = max(state.houses.values(), key=lambda h: h.influence)
                lineage_metrics["top_house_influence"] = top_house.influence
            lineage_metrics["houses"] = len(state.houses)
            lineage_metrics["nepotism_norm"] = round(state.nepotism_norm, 3)
            lineage_metrics["nepotism_bias_avg"] = round(
                sum(h.influence for h in state.houses.values()) / max(1, len(state.houses)) * cfg.nepotism_bias_scale,
                3,
            )


def _anti_nepotism_factor(world: Any, polity_id: str, cfg: LineageConfig) -> float:
    rights = effective_rights(world, polity_id, day=getattr(world, "day", 0))
    constraints = getattr(getattr(world, "constitution_by_polity", {}), "get", lambda _: None)(polity_id)
    constraint_values: Mapping[str, float] = {}
    if constraints is not None:
        constraint_values = getattr(constraints, "constraints_current", {})
    scores: list[float] = []
    scores.append(rights.get("due_process", 0.0))
    for dim in CONSTRAINT_DIMENSIONS:
        scores.append(float(constraint_values.get(dim, 0.0)))
    avg = sum(scores) / max(1, len(scores))
    return max(0.0, 1.0 - cfg.anti_nepotism_scale * avg)


def _role_domain(role_kind: str) -> str:
    return ROLE_TO_DOMAIN.get(role_kind.upper(), "WORKFORCE")


def nepotism_bias(world: Any, polity_id: str, candidate_house_id: str, role_kind: str) -> float:
    cfg = ensure_lineage_config(world)
    if not cfg.enabled:
        return 0.0
    state = ensure_lineage_state(world, polity_id)
    house = state.houses.get(candidate_house_id)
    if house is None:
        return 0.0
    anti = _anti_nepotism_factor(world, polity_id, cfg)
    domain = _role_domain(role_kind)
    edge_bonus = sum(
        edge.strength
        for edge in state.edges
        if edge.polity_id == polity_id and edge.from_house_id == candidate_house_id and edge.to_domain == domain
    )
    bias = cfg.nepotism_bias_scale * (house.influence + edge_bonus) * (1.0 + state.nepotism_norm)
    return max(0.0, round(bias * anti, 6))


def lineage_signature(world: Any, polity_id: str, *, day: int) -> str:
    state = ensure_lineage_state(world, polity_id)
    cfg = ensure_lineage_config(world)
    houses = {
        hid: {
            "wealth": round(h.wealth, 3),
            "influence": round(h.influence, 3),
            "generation": h.head_generation,
        }
        for hid, h in sorted(state.houses.items())
    }
    edges = [
        (edge.from_house_id, edge.to_domain, round(edge.strength, 3))
        for edge in sorted(state.edges, key=lambda e: (e.from_house_id, e.to_domain))
    ]
    payload = {
        "cfg": cfg.deterministic_salt,
        "day": int(day),
        "houses": houses,
        "edges": edges,
    }
    return str(payload)


def polity_for_ward(world: Any, ward_id: str) -> str:
    sovereignty = getattr(world, "sovereignty_state", None)
    territory = getattr(sovereignty, "territory", None)
    if territory is not None:
        polity = getattr(getattr(territory, "ward_control", {}), "get", lambda *_: None)(ward_id)
        if polity:
            return polity
    return getattr(world, "polity_id", "polity:default")


__all__ = [
    "LineageConfig",
    "House",
    "PatronEdge",
    "LineageState",
    "update_lineages",
    "nepotism_bias",
    "lineage_signature",
    "polity_for_ward",
    "ensure_lineage_config",
    "ensure_lineage_state",
]

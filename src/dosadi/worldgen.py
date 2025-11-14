"""Seeded world generation aligned with the D-WORLD design briefs.

The routines below implement the requirements from
``docs/latest/03_world/Dosadi_Worldgen.md`` by constructing a 36-ward
sandbox with deterministic-yet-varied stocks, factions, facilities, and
routes.  The generator deliberately mirrors the terminology from the
world design so downstream systems and tests can reference the same
vocabulary.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import cycle
from random import Random
from typing import Dict, List, Mapping, Sequence, Tuple

from .state import (
    AgentState,
    FactionState,
    RouteState,
    WardState,
    WorldState,
)


# ---------------------------------------------------------------------------
# Helper dataclasses for configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RangeFloat:
    low: float
    high: float

    def sample(self, rng: Random) -> float:
        return rng.uniform(self.low, self.high)


@dataclass(frozen=True)
class RangeInt:
    low: int
    high: int

    def sample(self, rng: Random) -> int:
        return rng.randint(self.low, self.high)


@dataclass(frozen=True)
class RingSpec:
    name: str
    count: int
    sealed_probability: float
    env_stress: float
    retention_mu: float
    leak_mu: float
    checkpoint_severity: float
    temp_c: float
    humidity: float
    oxygen: float
    radiation: float


@dataclass(frozen=True)
class StockBand:
    water: RangeFloat
    biomass: RangeFloat
    credits: RangeFloat


@dataclass(frozen=True)
class PolicySpec:
    tax_rate: float
    min_rotation_floor_pct: float


@dataclass(frozen=True)
class FactionBand:
    key: str
    archetype: str
    counts_by_ring: Mapping[str, RangeInt]
    catalog: Sequence[str]
    specialization_tags: Sequence[str] = ()
    mobile_probability: float = 0.0

    def count_for_ring(self, ring: str, rng: Random) -> int:
        if ring not in self.counts_by_ring:
            ring = next(iter(self.counts_by_ring))
        return self.counts_by_ring[ring].sample(rng)


DEFAULT_RINGS: Tuple[RingSpec, ...] = (
    RingSpec(
        name="inner",
        count=6,
        sealed_probability=0.75,
        env_stress=0.20,
        retention_mu=0.9999,
        leak_mu=0.001,
        checkpoint_severity=0.8,
        temp_c=28.0,
        humidity=0.70,
        oxygen=0.215,
        radiation=1.02,
    ),
    RingSpec(
        name="middle",
        count=12,
        sealed_probability=0.45,
        env_stress=0.50,
        retention_mu=0.9950,
        leak_mu=0.01,
        checkpoint_severity=0.5,
        temp_c=31.0,
        humidity=0.62,
        oxygen=0.210,
        radiation=1.08,
    ),
    RingSpec(
        name="outer",
        count=18,
        sealed_probability=0.15,
        env_stress=0.75,
        retention_mu=0.9850,
        leak_mu=0.03,
        checkpoint_severity=0.3,
        temp_c=36.0,
        humidity=0.55,
        oxygen=0.205,
        radiation=1.16,
    ),
)

DEFAULT_STOCKS: Mapping[str, StockBand] = {
    "inner": StockBand(RangeFloat(8_000, 12_000), RangeFloat(1_000, 3_000), RangeFloat(50_000, 120_000)),
    "middle": StockBand(RangeFloat(4_000, 8_000), RangeFloat(600, 2_000), RangeFloat(15_000, 60_000)),
    "outer": StockBand(RangeFloat(1_500, 4_000), RangeFloat(200, 800), RangeFloat(3_000, 20_000)),
}

DEFAULT_POLICY = PolicySpec(tax_rate=0.10, min_rotation_floor_pct=0.005)

DEFAULT_FACTION_BANDS: Tuple[FactionBand, ...] = (
    FactionBand(
        key="guild",
        archetype="GUILD",
        counts_by_ring={
            "inner": RangeInt(3, 6),
            "middle": RangeInt(3, 6),
            "outer": RangeInt(3, 6),
        },
        catalog=(
            "Condensate Guild",
            "Suitwrights",
            "Machining Circle",
            "Kitchens Union",
            "Armory Cooperative",
            "Reclaimer Cartel",
        ),
        specialization_tags=(
            "suit",
            "machining",
            "food",
            "reclaimer",
            "armory",
            "power",
        ),
    ),
    FactionBand(
        key="militia",
        archetype="MILITIA",
        counts_by_ring={
            "inner": RangeInt(1, 2),
            "middle": RangeInt(1, 3),
            "outer": RangeInt(2, 3),
        },
        catalog=(
            "Ward Guard",
            "Reservoir Watch",
            "Spine Sentinels",
            "Tunnel Lancers",
        ),
        specialization_tags=("security",),
    ),
    FactionBand(
        key="civic",
        archetype="CIVIC",
        counts_by_ring={
            "inner": RangeInt(1, 2),
            "middle": RangeInt(1, 2),
            "outer": RangeInt(1, 2),
        },
        catalog=(
            "Clerks Collegium",
            "Clinic Covenant",
            "Shelter Cooperative",
            "Arbitration Satellite",
        ),
        specialization_tags=("civic",),
    ),
    FactionBand(
        key="cult",
        archetype="CULT",
        counts_by_ring={
            "inner": RangeInt(0, 1),
            "middle": RangeInt(0, 2),
            "outer": RangeInt(0, 2),
        },
        catalog=(
            "Witnesses of the Well",
            "Salt Covenant",
            "Night Bloom",
            "Chorus of Rust",
        ),
        specialization_tags=("cult",),
    ),
    FactionBand(
        key="merc",
        archetype="MERCENARY",
        counts_by_ring={
            "inner": RangeInt(0, 1),
            "middle": RangeInt(1, 2),
            "outer": RangeInt(1, 2),
        },
        catalog=(
            "Copper Vultures",
            "Amber Chain",
            "Quiet Reach",
            "Black Cascade",
        ),
        specialization_tags=("escort",),
        mobile_probability=0.4,
    ),
)


@dataclass
class WorldgenConfig:
    """Parameters used to generate a Dosadi sandbox world."""

    seed: int = 7719
    rings: Tuple[RingSpec, ...] = DEFAULT_RINGS
    gate_density: float = 0.6
    smuggle_tunnels: int = 8
    well_location: str = "center-valley"
    faction_bands: Tuple[FactionBand, ...] = DEFAULT_FACTION_BANDS
    stocks: Mapping[str, StockBand] = field(default_factory=lambda: dict(DEFAULT_STOCKS))
    policy: PolicySpec = DEFAULT_POLICY
    royal_auditors_per_ward: int = 1
    enable_agents: bool = True
    agent_roll: RangeInt = RangeInt(10, 40)

    @classmethod
    def minimal(cls, *, seed: int = 0, wards: int = 6) -> "WorldgenConfig":
        ring = RingSpec(
            name="sandbox",
            count=wards,
            sealed_probability=0.5,
            env_stress=0.4,
            retention_mu=0.993,
            leak_mu=0.01,
            checkpoint_severity=0.5,
            temp_c=30.0,
            humidity=0.6,
            oxygen=0.21,
            radiation=1.05,
        )
        stocks = {
            "sandbox": StockBand(RangeFloat(2_000, 5_000), RangeFloat(200, 600), RangeFloat(5_000, 12_000))
        }
        return cls(
            seed=seed,
            rings=(ring,),
            gate_density=0.4,
            smuggle_tunnels=0,
            faction_bands=DEFAULT_FACTION_BANDS,
            stocks=stocks,
            policy=DEFAULT_POLICY,
            royal_auditors_per_ward=1,
            enable_agents=False,
            agent_roll=RangeInt(4, 8),
        )


# ---------------------------------------------------------------------------
# World generation entry point
# ---------------------------------------------------------------------------


def generate_world(config: WorldgenConfig | None = None) -> WorldState:
    """Return a freshly generated :class:`WorldState` following the spec."""

    cfg = config or WorldgenConfig()
    rng = Random(cfg.seed)
    world = WorldState(seed=cfg.seed)
    world.policy.update(
        {
            "tax_rate": cfg.policy.tax_rate,
            "min_rotation_floor_pct": cfg.policy.min_rotation_floor_pct,
            "well_location": cfg.well_location,
        }
    )

    ring_assignments = _create_wards(world, cfg, rng)
    _seed_facilities(world, ring_assignments, rng)
    _build_routes(world, cfg, ring_assignments, rng)
    _seed_factions(world, cfg, ring_assignments, rng)
    if cfg.enable_agents:
        _seed_agents(world, cfg, ring_assignments, rng)
    _derive_scores(world, ring_assignments)
    _seed_day0_events(world)
    return world


# ---------------------------------------------------------------------------
# Wards & environment
# ---------------------------------------------------------------------------


def _create_wards(
    world: WorldState, cfg: WorldgenConfig, rng: Random
) -> Mapping[str, List[WardState]]:
    assignments: Dict[str, List[WardState]] = defaultdict(list)
    index = 1
    for ring_index, spec in enumerate(cfg.rings, start=1):
        for _ in range(spec.count):
            ward = WardState(
                id=f"ward:{index}",
                name=f"Ward {index}",
                ring=ring_index,
                sealed_mode=spec.name.upper(),
                ring_label=spec.name,
            )
            ward.sealed = rng.random() < spec.sealed_probability
            env = ward.environment
            env.temperature = rng.gauss(spec.temp_c, 1.5)
            env.humidity = max(0.2, rng.gauss(spec.humidity, 0.05))
            env.oxygen = max(0.18, rng.gauss(spec.oxygen, 0.003))
            env.radiation = max(0.8, rng.gauss(spec.radiation, 0.05))
            env.stress = min(100.0, max(0.0, spec.env_stress * 100.0 + rng.uniform(-3.0, 3.0)))
            ward.infrastructure.reservoir_retention = max(0.9, rng.gauss(spec.retention_mu, 0.0005))
            ward.infrastructure.facility_leak_rate = max(0.0, rng.gauss(spec.leak_mu, spec.leak_mu * 0.15))
            ward.infrastructure.checkpoint_severity = max(
                0.05, min(1.0, rng.gauss(spec.checkpoint_severity, 0.08))
            )
            ward.infrastructure.royal_audit_intensity = 0.3 + 0.4 / ring_index
            stock_band = cfg.stocks.get(spec.name, cfg.stocks[next(iter(cfg.stocks))])
            ward.stocks.water_liters = stock_band.water.sample(rng)
            ward.stocks.biomass_kg = stock_band.biomass.sample(rng)
            ward.stocks.credits["dosadi-credit"] = stock_band.credits.sample(rng)
            ward.apply_environment()
            assignments[spec.name].append(ward)
            world.register_ward(ward)
            index += 1
    return assignments


def _seed_facilities(
    world: WorldState, assignments: Mapping[str, List[WardState]], rng: Random
) -> None:
    for ring, wards in assignments.items():
        for ward in wards:
            facilities = ward.facilities
            base_kitchens = 1 if ring != "inner" else 2
            base_workshops = 1
            base_clinic = 1 if ring == "inner" else (1 if rng.random() < 0.7 else 0)
            base_reclaimer = 1 if rng.random() < 0.8 else 0
            facilities.update(
                {
                    "kitchen": base_kitchens + (1 if rng.random() < 0.35 else 0),
                    "workshop": base_workshops + (1 if rng.random() < 0.25 else 0),
                    "clinic": base_clinic,
                    "reclaimer": base_reclaimer,
                }
            )
            if ring == "inner":
                facilities["power"] = 1 + (1 if rng.random() < 0.5 else 0)
            if ring != "outer" and rng.random() < 0.4:
                facilities["bazaar"] = 1
            if rng.random() < 0.3:
                facilities["queue"] = 1


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def _add_route_pair(
    world: WorldState,
    origin: WardState,
    destination: WardState,
    *,
    distance: float,
    checkpoint: float,
    escort_risk: float,
    capacity: float,
    hidden: bool,
    route_type: str,
    rng: Random,
) -> None:
    for src, dst in ((origin, destination), (destination, origin)):
        route_id = f"route:{src.id}->{dst.id}:{route_type}:{len(world.routes)}"
        route = RouteState(
            id=route_id,
            origin=src.id,
            destination=dst.id,
            distance_minutes=distance,
            checkpoint_level=max(0.05, min(1.0, checkpoint + rng.uniform(-0.05, 0.05))),
            escort_risk=max(0.0, min(1.0, escort_risk + rng.uniform(-0.03, 0.03))),
            capacity_liters=capacity,
            hidden=hidden,
            route_type=route_type,
            distance_km=distance * 0.6,
            risk=escort_risk,
            surcharge=0.05 if route_type == "OFFICIAL" else 0.12,
        )
        world.register_route(route)


def _build_routes(
    world: WorldState,
    cfg: WorldgenConfig,
    assignments: Mapping[str, List[WardState]],
    rng: Random,
) -> None:
    ring_lookup = {ward.id: ring for ring, wards in assignments.items() for ward in wards}
    ring_order = list(assignments.keys())

    def ring_distance(ring: str) -> float:
        return {"inner": 6.0, "middle": 10.0, "outer": 15.0}.get(ring, 8.0)

    def ring_capacity(ring: str) -> float:
        return {"inner": 600.0, "middle": 420.0, "outer": 260.0}.get(ring, 300.0)

    # Connect wards within each ring in a loop.
    for ring, wards in assignments.items():
        if len(wards) < 2:
            continue
        ordered = list(wards)
        for a, b in zip(ordered, ordered[1:] + ordered[:1]):
            _add_route_pair(
                world,
                a,
                b,
                distance=ring_distance(ring),
                checkpoint=assignments[ring][0].infrastructure.checkpoint_severity,
                escort_risk=0.12 + 0.05 * ring_order.index(ring),
                capacity=ring_capacity(ring),
                hidden=False,
                route_type="OFFICIAL",
                rng=rng,
            )

    # Connect rings radially.
    for idx, ring in enumerate(ring_order[1:], start=1):
        inner_ring = ring_order[idx - 1]
        inner_wards = assignments.get(inner_ring, [])
        outer_wards = assignments.get(ring, [])
        if not inner_wards or not outer_wards:
            continue
        for outer, inner in zip(outer_wards, cycle(inner_wards)):
            _add_route_pair(
                world,
                inner,
                outer,
                distance=(ring_distance(inner_ring) + ring_distance(ring)) / 2,
                checkpoint=(
                    inner.infrastructure.checkpoint_severity + outer.infrastructure.checkpoint_severity
                )
                / 2,
                escort_risk=0.18 + 0.04 * idx,
                capacity=min(ring_capacity(inner_ring), ring_capacity(ring)),
                hidden=False,
                route_type="OFFICIAL",
                rng=rng,
            )

    # Royal spokes from the Well (ward:1) to inner and middle rings.
    well = world.wards.get("ward:1")
    if well:
        for ring in ("inner", "middle"):
            for ward in assignments.get(ring, []):
                if ward.id == well.id:
                    continue
                _add_route_pair(
                    world,
                    well,
                    ward,
                    distance=ring_distance(ring) - 1.5,
                    checkpoint=max(0.4, ward.infrastructure.checkpoint_severity),
                    escort_risk=0.1,
                    capacity=ring_capacity(ring) * 1.5,
                    hidden=False,
                    route_type="ROYAL",
                    rng=rng,
                )

    # Smuggle tunnels.
    candidates = [ward for ring in ring_order if ring != "inner" for ward in assignments.get(ring, [])]
    rng.shuffle(candidates)
    tunnel_pairs = min(cfg.smuggle_tunnels, len(candidates) // 2)
    for idx in range(tunnel_pairs):
        a = candidates[2 * idx]
        b = candidates[2 * idx + 1]
        _add_route_pair(
            world,
            a,
            b,
            distance=ring_distance(ring_lookup[a.id]) * 0.8,
            checkpoint=0.15,
            escort_risk=0.4,
            capacity=120.0,
            hidden=True,
            route_type="SMUGGLE",
            rng=rng,
        )


# ---------------------------------------------------------------------------
# Factions & agents
# ---------------------------------------------------------------------------


def _seed_factions(
    world: WorldState,
    cfg: WorldgenConfig,
    assignments: Mapping[str, List[WardState]],
    rng: Random,
) -> None:
    faction_index = 0
    royal_id = "faction:king"
    if royal_id not in world.factions:
        treasury = FactionState(
            id=royal_id,
            name="Royal Treasury",
            archetype="ROYAL",
            home_ward="ward:1",
        )
        treasury.assets.credits["king-credit"] = 120_000.0
        treasury.loyalty_to_king = 1.0
        world.register_faction(treasury)

    for ring, wards in assignments.items():
        for ward in wards:
            governor = FactionState(
                id=f"faction:lord:{ward.id}",
                name=f"Lord of {ward.name}",
                archetype="GOVERNOR",
                home_ward=ward.id,
            )
            governor.metrics.gov.legitimacy = rng.uniform(0.45, 0.75) - 0.05 * (ward.ring - 1)
            governor.metrics.econ.reliability = rng.uniform(0.4, 0.8)
            governor.loyalty_to_king = rng.uniform(0.55, 0.9) - 0.08 * (ward.ring - 1)
            world.register_faction(governor)
            ward.governor_faction = governor.id

            for band in cfg.faction_bands:
                count = band.count_for_ring(ring, rng)
                cycle_source = list(band.specialization_tags or (band.key,))
                if not cycle_source:
                    cycle_source = [band.key]
                if band.key == "guild":
                    required_order = [spec for spec in ("food", "power", "suit") if spec in cycle_source]
                    plan: List[str] = required_order[:count]
                    idx = 0
                    while len(plan) < count:
                        plan.append(cycle_source[idx % len(cycle_source)])
                        idx += 1
                else:
                    plan = [cycle_source[i % len(cycle_source)] for i in range(count)]
                for spec in plan:
                    faction_index += 1
                    name = rng.choice(band.catalog)
                    faction = FactionState(
                        id=f"faction:{band.key}:{faction_index}",
                        name=f"{name} {ward.name}",
                        archetype=band.archetype,
                        home_ward=ward.id,
                    )
                    faction.metrics.econ.reliability = rng.uniform(0.35, 0.85)
                    faction.metrics.gov.legitimacy = rng.uniform(0.35, 0.7)
                    faction.loyalty_to_king = rng.uniform(0.3, 0.8) - 0.1 * (ward.ring - 1)
                    faction.specialization = spec
                    faction.smuggling_profile["tunnel_affinity"] = rng.uniform(0.0, 0.6)
                    if band.mobile_probability and rng.random() < band.mobile_probability:
                        faction.smuggling_profile["mobile"] = 1.0
                    faction.assets.water_liters = rng.uniform(50.0, 200.0)
                    faction.assets.biomass_kg = rng.uniform(5.0, 40.0)
                    faction.assets.credits["dosadi-credit"] = rng.uniform(2_000.0, 18_000.0)
                    world.register_faction(faction)

            for _ in range(cfg.royal_auditors_per_ward):
                faction_index += 1
                auditor = FactionState(
                    id=f"faction:auditor:{faction_index}",
                    name=f"Royal Auditor {ward.name}",
                    archetype="BUREAUCRAT",
                    home_ward=ward.id,
                )
                auditor.metrics.gov.legitimacy = rng.uniform(0.6, 0.85)
                auditor.loyalty_to_king = rng.uniform(0.75, 0.95)
                world.register_faction(auditor)


def _seed_agents(
    world: WorldState,
    cfg: WorldgenConfig,
    assignments: Mapping[str, List[WardState]],
    rng: Random,
) -> None:
    archetype_affinities = {
        "worker": {"STR": 0.3, "DEX": 0.2, "CON": 0.3, "INT": 0.1, "WILL": 0.1, "CHA": 0.0},
        "guard": {"STR": 0.4, "DEX": 0.3, "CON": 0.3, "INT": 0.1, "WILL": 0.2, "CHA": 0.1},
        "clerk": {"STR": 0.1, "DEX": 0.1, "CON": 0.1, "INT": 0.4, "WILL": 0.3, "CHA": 0.3},
        "reclaimer": {"STR": 0.2, "DEX": 0.3, "CON": 0.2, "INT": 0.3, "WILL": 0.2, "CHA": 0.1},
        "cultist": {"STR": 0.1, "DEX": 0.2, "CON": 0.1, "INT": 0.2, "WILL": 0.4, "CHA": 0.4},
        "smuggler": {"STR": 0.2, "DEX": 0.4, "CON": 0.2, "INT": 0.3, "WILL": 0.3, "CHA": 0.4},
    }
    archetypes = list(archetype_affinities.keys())

    agent_index = 0
    for ring, wards in assignments.items():
        for ward in wards:
            agent_count = cfg.agent_roll.sample(rng)
            for _ in range(agent_count):
                agent_index += 1
                archetype = rng.choice(archetypes)
                faction = rng.choice(list(world.factions.values()))
                agent = AgentState(
                    id=f"agent:{agent_index}",
                    name=f"Agent {agent_index}",
                    faction=faction.id,
                    ward=ward.id,
                )
                for key, value in archetype_affinities[archetype].items():
                    agent.affinities[key] = max(0.0, min(1.0, rng.gauss(value, 0.08)))
                agent.inventory["owned"].append(f"ration:{agent_index}")
                agent.inventory["credits"]["dosadi-credit"] = rng.uniform(25.0, 250.0)
                faction.members.append(agent.id)
                world.register_agent(agent)


# ---------------------------------------------------------------------------
# Derived metrics & events
# ---------------------------------------------------------------------------


def _derive_scores(world: WorldState, assignments: Mapping[str, List[WardState]]) -> None:
    guild_specialisations: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for faction in world.factions.values():
        if faction.specialization and faction.home_ward in world.wards:
            guild_specialisations[faction.home_ward][faction.specialization] += 1

    for ring, wards in assignments.items():
        for ward in wards:
            specs = guild_specialisations.get(ward.id, {})
            total = sum(specs.values()) or 1
            ward.specialisations = {k: v / total for k, v in specs.items()}
            reserve_target = 9_000 if ring == "inner" else (6_000 if ring == "middle" else 3_500)
            ward.need_index = max(0.0, (reserve_target - ward.stocks.water_liters) / reserve_target)
            ward.risk_index = min(
                1.0,
                0.4 * ward.environment.stress / 100.0
                + 0.2 * ward.need_index
                + 0.2 * ward.infrastructure.facility_leak_rate * 20
                + 0.2 * len([r for r in world.routes.values() if r.hidden and r.origin == ward.id]),
            )
            ward.smuggle_risk = min(
                1.0,
                0.2
                + 0.15 * len([r for r in world.routes.values() if r.hidden and r.origin == ward.id])
                + 0.1 * (1.0 - ward.infrastructure.checkpoint_severity),
            )
            ward.rotation_debt = 0.0


def _seed_day0_events(world: WorldState) -> None:
    world.events_outbox.extend(
        [
            "WorldCreated",
            "CreditRateUpdated",
            "MaintenanceTaskQueued",
            "ContractActivated",
        ]
    )


__all__ = ["WorldgenConfig", "generate_world"]

"""Structured world state for the Dosadi simulation.

The module mirrors the schemas defined in
``docs/Dosadi_Global_Schemas_v1.md``.  Dataclasses are used to provide a
type-safe container that is still lightweight and serialisable.  Helper
methods implement recurrent calculations such as environmental stress and
resource aggregation needed for the conservation law described in
``docs/Dosadi_System_Logic_Architecture_v1.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Primitive state building blocks
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class EnvironmentState:
    temperature: float = 35.0
    humidity: float = 1.0
    oxygen: float = 0.21
    radiation: float = 1.0
    water_loss: float = 0.001
    stress: float = 10.0

    def compute_stress(self) -> float:
        """Return an updated environmental stress score.

        The heuristic blends temperature, humidity, oxygen, radiation, and
        maintenance derived from ``Dosadi_Environment_Dynamics_v1``.  It is
        intentionally simple yet captures the non-linearity between the
        variables: extreme heat or radiation rapidly increases the score
        while acceptable ranges keep it bounded.
        """

        temp_factor = max(0.0, (self.temperature - 30.0) / 35.0)
        humidity_factor = max(0.0, 1.0 - min(self.humidity, 2.0) / 2.0)
        oxygen_penalty = max(0.0, (0.21 - self.oxygen) * 200)
        radiation_penalty = max(0.0, self.radiation - 1.0) * 8.0
        stress = 5.0 + 50.0 * temp_factor + 20.0 * humidity_factor
        stress += oxygen_penalty + radiation_penalty
        return max(0.0, min(100.0, stress))


@dataclass(slots=True)
class InfrastructureState:
    maintenance_index: float = 0.8
    subsystems: MutableMapping[str, str] = field(
        default_factory=lambda: {
            "thermal": "OK",
            "condensers": "OK",
            "scrubbers": "OK",
            "shielding": "OK",
            "lighting": "OK",
            "reclaimers": "OK",
        }
    )

    def degrade(self, delta: float) -> None:
        self.maintenance_index = max(0.0, self.maintenance_index - delta)

    def repair(self, delta: float) -> None:
        self.maintenance_index = min(1.0, self.maintenance_index + delta)


@dataclass(slots=True)
class StockState:
    water_liters: float = 0.0
    biomass_kg: float = 0.0
    credits: MutableMapping[str, float] = field(default_factory=dict)

    def delta_water(self, delta: float) -> None:
        self.water_liters = max(0.0, self.water_liters + delta)

    def delta_biomass(self, delta: float) -> None:
        self.biomass_kg = max(0.0, self.biomass_kg + delta)

    def delta_credit(self, currency: str, delta: float) -> None:
        self.credits[currency] = max(0.0, self.credits.get(currency, 0.0) + delta)


# ---------------------------------------------------------------------------
# Social and governance layers
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class GovernanceMetrics:
    legitimacy: float = 0.6
    corruption: float = 0.2

    def apply_delta(self, *, legitimacy: float = 0.0, corruption: float = 0.0) -> None:
        self.legitimacy = _clamp01(self.legitimacy + legitimacy)
        self.corruption = _clamp01(self.corruption + corruption)


@dataclass(slots=True)
class EconomicMetrics:
    reliability: float = 0.5
    exchange_rates: MutableMapping[str, float] = field(default_factory=dict)

    def update_exchange(self, currency: str, value: float) -> None:
        self.exchange_rates[currency] = max(1e-6, value)


@dataclass(slots=True)
class LawMetrics:
    restorative_ratio: float = 0.7
    retributive_index: float = 0.1
    enforcement_latency: float = 600.0
    arbiter_consistency: float = 0.7


@dataclass(slots=True)
class FactionMetrics:
    gov: GovernanceMetrics = field(default_factory=GovernanceMetrics)
    econ: EconomicMetrics = field(default_factory=EconomicMetrics)
    law: LawMetrics = field(default_factory=LawMetrics)


@dataclass(slots=True)
class ReputationState:
    by_audience: MutableMapping[str, float] = field(default_factory=dict)

    def adjust(self, audience: str, delta: float) -> None:
        value = _clamp(-1.0, 1.0, self.by_audience.get(audience, 0.0) + delta)
        self.by_audience[audience] = value


@dataclass(slots=True)
class FactionState:
    id: str
    name: str
    archetype: str
    home_ward: str
    members: List[str] = field(default_factory=list)
    assets: StockState = field(default_factory=StockState)
    metrics: FactionMetrics = field(default_factory=FactionMetrics)
    reputation: ReputationState = field(default_factory=ReputationState)
    contracts_active: List[str] = field(default_factory=list)
    rumor_bank: MutableMapping[str, List[str]] = field(
        default_factory=lambda: {"verified": [], "unverified": []}
    )
    roles: MutableMapping[str, List[str]] = field(
        default_factory=lambda: {"lawyers": [], "stewards": [], "captains": []}
    )

    def total_assets(self) -> Dict[str, float]:
        return {
            "water_liters": self.assets.water_liters,
            "biomass_kg": self.assets.biomass_kg,
            "credits": dict(self.assets.credits),
        }


@dataclass(slots=True)
class SuitState:
    model: str = "Unknown"
    caste: str = "MID"
    integrity: float = 0.9
    seal: float = 0.9
    comfort: float = 0.6
    defense: MutableMapping[str, float] = field(
        default_factory=lambda: {"blunt": 0.3, "slash": 0.3, "pierce": 0.3}
    )
    ratings: MutableMapping[str, float] = field(
        default_factory=lambda: {"heat": 0.8, "chem": 0.6, "rad": 0.5}
    )


@dataclass(slots=True)
class BodyState:
    health: float = 100.0
    water: float = 3.0
    nutrition: float = 2500.0
    stamina: float = 80.0
    mental_energy: float = 80.0
    bladder: float = 0.2
    bowel: float = 0.1
    chronic: Sequence[str] = field(default_factory=tuple)


@dataclass(slots=True)
class SocialState:
    reputation: ReputationState = field(default_factory=ReputationState)
    loyalty: MutableMapping[str, float] = field(default_factory=dict)
    relationships: MutableMapping[str, float] = field(default_factory=dict)
    caste: MutableMapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class MemoryState:
    events: List[str] = field(default_factory=list)
    beliefs: MutableMapping[str, Dict[str, float]] = field(default_factory=dict)
    memes: MutableMapping[str, float] = field(default_factory=dict)

    def decay(self, *, cred_lambda: float, belief_lambda: float, salience_lambda: float) -> None:
        for belief in self.beliefs.values():
            belief["Cred"] = _clamp01(belief.get("Cred", 0.0) * cred_lambda)
            belief["B"] = _clamp01(belief.get("B", 0.0) * belief_lambda)
            belief["Sal"] = _clamp01(belief.get("Sal", 0.0) * salience_lambda)
        for meme, value in list(self.memes.items()):
            self.memes[meme] = _clamp01(value * 0.999)


@dataclass(slots=True)
class DriveState:
    weights: MutableMapping[str, float] = field(
        default_factory=lambda: {
            "Survival": 0.6,
            "Hoard": 0.2,
            "Advancement": 0.2,
        }
    )


@dataclass(slots=True)
class AgentState:
    id: str
    name: str
    faction: str
    ward: str
    body: BodyState = field(default_factory=BodyState)
    suit: SuitState = field(default_factory=SuitState)
    affinities: MutableMapping[str, float] = field(
        default_factory=lambda: {
            "STR": 0.0,
            "DEX": 0.0,
            "CON": 0.0,
            "INT": 0.0,
            "WILL": 0.0,
            "CHA": 0.0,
        }
    )
    inventory: MutableMapping[str, List[str] | Dict[str, float]] = field(
        default_factory=lambda: {
            "worn": [],
            "owned": [],
            "access": [],
            "credits": {},
        }
    )
    social: SocialState = field(default_factory=SocialState)
    memory: MemoryState = field(default_factory=MemoryState)
    drives: DriveState = field(default_factory=DriveState)
    techniques: List[str] = field(default_factory=lambda: ["Barter", "Observe", "Labor"])


@dataclass(slots=True)
class RumorState:
    id: str
    topic: str
    subject_id: str
    content: str
    source_type: str
    source_id: Optional[str]
    credibility: float
    salience: float
    belief_updates: List[Tuple[str, float]] = field(default_factory=list)
    visibility_radius: int = 1
    firsthand: bool = False
    created_tick: int = 0
    last_propagated_tick: int = 0


@dataclass(slots=True)
class ContractObligation:
    what: str
    quantity: float
    quality: str
    location: str
    due: int


@dataclass(slots=True)
class ContractState:
    id: str
    parties: Sequence[str]
    type: str
    obligations: Sequence[ContractObligation]
    consideration: Sequence[Dict[str, object]]
    jurisdiction: str
    status: str = "PENDING"
    created_tick: int = 0
    activated_tick: int = 0
    closed_tick: Optional[int] = None


@dataclass(slots=True)
class CaseState:
    id: str
    contract_id: Optional[str]
    arbiter_tier: str
    parties: Sequence[str]
    evidence: List[str] = field(default_factory=list)
    proceedings: List[Dict[str, object]] = field(default_factory=list)
    outcome: Optional[str] = None


@dataclass(slots=True)
class RouteState:
    """Minimal directed route representation used by logistics systems."""

    id: str
    origin: str
    destination: str
    distance_km: float
    risk: float
    surcharge: float
    escort_jobs: List[str] = field(default_factory=list)
    incidents: List[Dict[str, object]] = field(default_factory=list)
    delivered_volume_liters: float = 0.0

    def record_incident(self, *, kind: str, severity: str, tick: int, notes: str) -> None:
        self.incidents.append(
            {
                "kind": kind,
                "severity": severity,
                "tick": tick,
                "notes": notes,
            }
        )

    def apply_delivery(self, volume_liters: float) -> None:
        self.delivered_volume_liters += volume_liters


@dataclass(slots=True)
class WardState:
    id: str
    name: str
    ring: int
    sealed_mode: str
    environment: EnvironmentState = field(default_factory=EnvironmentState)
    infrastructure: InfrastructureState = field(default_factory=InfrastructureState)
    stocks: StockState = field(default_factory=StockState)
    governor_faction: Optional[str] = None
    newsfeed: List[str] = field(default_factory=list)
    legitimacy: float = 0.55
    facilities: MutableMapping[str, int] = field(default_factory=dict)

    def apply_environment(self) -> None:
        self.environment.stress = self.environment.compute_stress()


# ---------------------------------------------------------------------------
# Global world container
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WorldConfig:
    tick_seconds: float = 0.6


@dataclass
class WorldState:
    tick: int = 0
    minute: int = 0
    day: int = 0
    config: WorldConfig = field(default_factory=WorldConfig)
    wards: MutableMapping[str, WardState] = field(default_factory=dict)
    factions: MutableMapping[str, FactionState] = field(default_factory=dict)
    agents: MutableMapping[str, AgentState] = field(default_factory=dict)
    contracts: MutableMapping[str, ContractState] = field(default_factory=dict)
    cases: MutableMapping[str, CaseState] = field(default_factory=dict)
    rumors: MutableMapping[str, RumorState] = field(default_factory=dict)
    events_outbox: List[str] = field(default_factory=list)
    routes: MutableMapping[str, RouteState] = field(default_factory=dict)
    market_quotes: List[Dict[str, object]] = field(default_factory=list)
    trades: List[Dict[str, object]] = field(default_factory=list)
    labor_postings: List[Dict[str, object]] = field(default_factory=list)
    labor_assignments: List[Dict[str, object]] = field(default_factory=list)
    maintenance_tasks: List[Dict[str, object]] = field(default_factory=list)
    clinic_records: List[Dict[str, object]] = field(default_factory=list)
    law_cases: List[Dict[str, object]] = field(default_factory=list)
    security_reports: List[Dict[str, object]] = field(default_factory=list)

    def register_ward(self, ward: WardState) -> None:
        self.wards[ward.id] = ward

    def register_faction(self, faction: FactionState) -> None:
        self.factions[faction.id] = faction

    def register_agent(self, agent: AgentState) -> None:
        self.agents[agent.id] = agent

    def register_route(self, route: RouteState) -> None:
        self.routes[route.id] = route

    def resource_snapshot(self) -> Dict[str, float]:
        """Return approximate conserved quantities used by audits."""

        water = sum(w.stocks.water_liters for w in self.wards.values())
        water += sum(f.assets.water_liters for f in self.factions.values())
        biomass = sum(w.stocks.biomass_kg for w in self.wards.values())
        biomass += sum(f.assets.biomass_kg for f in self.factions.values())
        information = sum(len(a.memory.events) for a in self.agents.values())
        information += len(self.rumors)
        energy = sum(w.infrastructure.maintenance_index for w in self.wards.values())
        return {
            "Water": water,
            "Biomass": biomass,
            "Information": float(information),
            "Energy": energy,
        }

    def advance_tick(self) -> None:
        self.tick += 1
        if self.tick % 100 == 0:
            self.minute += 1
        if self.tick % 144_000 == 0:
            self.day += 1


def _clamp(lo: float, hi: float, value: float) -> float:
    return max(lo, min(hi, value))


def _clamp01(value: float) -> float:
    return _clamp(0.0, 1.0, value)


__all__ = [
    "AgentState",
    "CaseState",
    "ContractObligation",
    "ContractState",
    "EnvironmentState",
    "FactionState",
    "FactionMetrics",
    "InfrastructureState",
    "MemoryState",
    "RouteState",
    "RumorState",
    "StockState",
    "SuitState",
    "WardState",
    "WorldConfig",
    "WorldState",
]


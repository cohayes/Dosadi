"""Structured world state for the Dosadi simulation.

The module mirrors the schemas defined in
``docs/Dosadi_Global_Schemas_v1.md``.  Dataclasses are used to provide a
type-safe container that is still lightweight and serialisable.  Helper
methods implement recurrent calculations such as environmental stress and
resource aggregation needed for the conservation law described in
``docs/Dosadi_System_Logic_Architecture_v1.md``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import random

from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Set, Tuple

from .admin_log import AdminEventLog
from .law import FacilityProtocolTuning
from .memory.facility_summary import FacilityBeliefSummary
from .world.events import WorldEventLog
from .world.facilities import FacilityLedger
from .world.logistics import LogisticsConfig, LogisticsLedger
from .world.scout_missions import ScoutMissionLedger
from .simulation.snapshots import serialize_state
from .runtime.admin_log import AdminLogEntry
from .runtime.council_metrics import CouncilMetrics, CouncilStaffingConfig
from .runtime.escort_protocols import EscortConfig, EscortState
from .runtime.staffing import StaffingConfig, StaffingState
from .runtime.stockpile_policy import DepotPolicyLedger, StockpilePolicyConfig, StockpilePolicyState
from .runtime.work_details import WorkDetailType
from .runtime.war import RaidOutcome, RaidPlan, WarConfig
from .runtime.incident_engine import IncidentConfig, IncidentState
from .runtime.scouting_config import ScoutConfig
from .runtime.telemetry import DebugConfig, EventRing, Metrics
from .runtime.institutions import InstitutionConfig, WardInstitutionPolicy, WardInstitutionState
from .runtime.corridor_risk import CorridorRiskConfig, CorridorRiskLedger
from .runtime.media import MediaConfig, MediaMessage
from .runtime.espionage import EspionageConfig, IntelOpOutcome, IntelOpPlan
from .runtime.culture_wars import CultureConfig, WardCultureState
from .runtime.education import EducationConfig, WardEducationState
from .runtime.urban import UrbanConfig, WardUrbanState
from .world.corridor_infrastructure import CorridorInfraConfig, CorridorInfraEdge
from .runtime.escort_policy_v2 import EscortPolicyV2Config, EscortPolicyV2State
from .runtime.migration import MigrationConfig, MigrationFlow, WardMigrationState
from .runtime.defense import DefenseConfig, WardDefenseState
from .runtime.market_signals import MarketSignalsConfig, MarketSignalsState
from .runtime.production_runtime import FacilityProductionState, ProductionConfig, ProductionState
from .runtime.smuggling import SmugglingConfig, SmugglingNetworkState
from .agent.memory_crumbs import CrumbStore
from .agent.memory_episodes import EpisodeBuffer
from .agent.memory_stm import STMBoringWinner
from .world.environment import PlaceEnvironmentState
from .world.factions import FactionSystemConfig, FactionSystemState, FactionTerritory, Faction
from .world.phases import PhaseConfig, PhaseState
from .world.discovery import DiscoveryConfig
from .world.extraction import ExtractionLedger
from .world.survey_map import SurveyMap
from .world.construction import ProjectLedger
from .world.expansion_planner import ExpansionPlannerConfig, ExpansionPlannerState
from .world.materials import InventoryRegistry
from .world.water import WellState
from .world.workforce import WorkforceLedger
from .world.incidents import IncidentLedger
from .runtime.focus_mode import FocusConfig, FocusState
from .runtime.extraction_runtime import ExtractionConfig, ExtractionState
from .runtime.maintenance import MaintenanceConfig, MaintenanceLedger, MaintenanceState
from .runtime.faction_interference import InterferenceConfig, InterferenceState
from .runtime.suit_wear import SuitRepairLedger, SuitWearConfig, SuitWearState
from .runtime.ledger import LedgerConfig, LedgerState
from .runtime.labor import BargainingEvent, LaborConfig, LaborOrgState
from .agent.suits import SuitState
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .systems.protocols import ProtocolRegistry
    from .runtime.queues import FacilityQueueState, QueueState
    from .runtime.work_details import WorkDetailType
    from dosadi.agents.core import Goal, GoalType



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
    reservoir_retention: float = 0.99
    facility_leak_rate: float = 0.01
    checkpoint_severity: float = 0.5
    royal_audit_intensity: float = 0.5

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


@dataclass(slots=True)
class SuitServiceLedgerEntry:
    tick: int
    agent_id: str
    faction_id: str
    ward_id: str
    telemetry: Mapping[str, float]
    parts_cost: float
    deferred: bool


@dataclass
class SuitServiceLedger:
    entries: List[SuitServiceLedgerEntry] = field(default_factory=list)
    pending: List[SuitServiceLedgerEntry] = field(default_factory=list)

    def record(
        self,
        *,
        tick: int,
        agent_id: str,
        faction_id: str,
        ward_id: str,
        telemetry: Mapping[str, float],
        parts_cost: float,
        deferred: bool,
    ) -> None:
        entry = SuitServiceLedgerEntry(
            tick=tick,
            agent_id=agent_id,
            faction_id=faction_id,
            ward_id=ward_id,
            telemetry=dict(telemetry),
            parts_cost=max(0.0, parts_cost),
            deferred=deferred,
        )
        self.entries.append(entry)
        self.pending.append(entry)
        if len(self.entries) > 500:
            self.entries = self.entries[-500:]

    def drain_pending(self) -> List[SuitServiceLedgerEntry]:
        drained = list(self.pending)
        self.pending.clear()
        return drained

    def summary(self) -> Dict[str, float]:
        window = self.entries[-100:] if self.entries else []
        parts = sum(entry.parts_cost for entry in window)
        deferred = sum(1.0 for entry in window if entry.deferred)
        return {"parts_cost": parts, "deferred": deferred}


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
    loyalty_to_king: float = 0.5
    smuggling_profile: MutableMapping[str, float] = field(default_factory=dict)
    specialization: Optional[str] = None
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
class LoadoutState:
    """Operational kit reference described in docs/latest/01_agents."""

    primary: Optional[str] = None
    secondary: Optional[str] = None
    support_items: List[str] = field(default_factory=list)
    kit_tags: List[str] = field(default_factory=list)
    readiness: float = 0.65
    signature: str = "LOW"

    def describe(self) -> str:
        primary = self.primary or "-"
        secondary = self.secondary or "-"
        support = ", ".join(self.support_items) or "<none>"
        return f"P:{primary} / S:{secondary} / Support:{support}"


@dataclass(slots=True)
class BodyState:
    """Physiological model that mirrors D-AGENT-0101."""

    health: float = 100.0
    nutrition: float = 2500.0
    hydration: float = 3.0
    stamina: float = 80.0
    energy: float = 80.0
    bladder: float = 0.2
    bowel: float = 0.1
    body_mass: float = 70.0
    activity_level: float = 0.25
    thermoregulation_efficiency: float = 0.85
    nutrition_capacity: float = 3200.0
    hydration_capacity: float = 4.5
    mental_processing_budget: float = 120.0
    mental_processing_used: float = 0.0
    chronic: Sequence[str] = field(default_factory=tuple)

    def hunger_ratio(self) -> float:
        if self.nutrition_capacity <= 0:
            return 1.0
        return _clamp01(1.0 - self.nutrition / self.nutrition_capacity)

    def thirst_ratio(self) -> float:
        if self.hydration_capacity <= 0:
            return 1.0
        return _clamp01(1.0 - self.hydration / self.hydration_capacity)

    def fatigue_ratio(self) -> float:
        return _clamp01(1.0 - self.stamina / 100.0)

    def heat_stress_index(self, env_temp: float, suit_thermal_resistance: float) -> float:
        delta = max(0.0, env_temp - 22.0)
        return max(0.0, delta * (1.0 - suit_thermal_resistance) / max(1e-3, self.thermoregulation_efficiency))

    def cold_stress_index(self, env_temp: float, suit_thermal_resistance: float) -> float:
        delta = max(0.0, 22.0 - env_temp)
        return max(0.0, delta * (1.0 - suit_thermal_resistance) / max(1e-3, self.thermoregulation_efficiency))

    def caloric_demand(self) -> float:
        base_rate = 2_000.0 + 8.0 * (self.body_mass - 70.0)
        return max(0.0, base_rate * (1.0 + 0.5 * self.activity_level))

    def hydration_demand(self) -> float:
        heat_load = self.heat_stress_index(22.0, 0.0)
        return max(0.0, 0.035 * self.body_mass * (1.0 + 0.3 * heat_load))

    def allocate_processing_budget(self, effort: float) -> float:
        remaining = max(0.0, self.mental_processing_budget - self.mental_processing_used)
        spent = min(remaining, max(0.0, effort))
        self.mental_processing_used += spent
        return spent

    def reset_processing_budget(self) -> None:
        self.mental_processing_used = 0.0

    @property
    def mental_energy(self) -> float:
        remaining = max(0.0, self.mental_processing_budget - self.mental_processing_used)
        return 100.0 * remaining / max(1.0, self.mental_processing_budget)

    @mental_energy.setter
    def mental_energy(self, value: float) -> None:
        clamped = _clamp(0.0, 100.0, value)
        remaining = clamped / 100.0 * max(1.0, self.mental_processing_budget)
        self.mental_processing_used = max(0.0, self.mental_processing_budget - remaining)

    @property
    def water(self) -> float:
        return self.hydration

    @water.setter
    def water(self, value: float) -> None:
        self.hydration = max(0.0, value)


@dataclass(slots=True)
class SocialState:
    reputation: ReputationState = field(default_factory=ReputationState)
    loyalty: MutableMapping[str, float] = field(default_factory=dict)
    relationships: MutableMapping[str, float] = field(default_factory=dict)
    caste: MutableMapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class PermitRecord:
    """Identity and permitting record aligning with D-AGENT-0107."""

    id: str
    kind: str
    status: str = "ACTIVE"
    issued_by: Optional[str] = None
    issued_tick: int = 0
    expires_tick: Optional[int] = None
    restrictions: Sequence[str] = field(default_factory=tuple)

    def is_active(self, *, tick: Optional[int] = None) -> bool:
        if self.status.upper() != "ACTIVE":
            return False
        if tick is not None and self.expires_tick is not None:
            return tick <= self.expires_tick
        return True


@dataclass(slots=True)
class IdentityProfile:
    """Agent identity, handles, permits, and trust hooks."""

    handles: List[str] = field(default_factory=list)
    clearance_level: str = "CIVIC"
    permits: MutableMapping[str, PermitRecord] = field(default_factory=dict)
    trust_flags: MutableMapping[str, float] = field(default_factory=dict)
    risk_tags: MutableMapping[str, float] = field(default_factory=dict)

    def add_handle(self, handle: str) -> None:
        if handle not in self.handles:
            self.handles.append(handle)

    def issue_permit(
        self,
        *,
        permit_id: str,
        kind: str,
        issued_by: Optional[str],
        issued_tick: int,
        expires_tick: Optional[int] = None,
        restrictions: Sequence[str] = (),
    ) -> PermitRecord:
        record = PermitRecord(
            id=permit_id,
            kind=kind,
            issued_by=issued_by,
            issued_tick=issued_tick,
            expires_tick=expires_tick,
            restrictions=tuple(restrictions),
        )
        self.permits[permit_id] = record
        return record

    def revoke_permit(self, permit_id: str, *, reason: str | None = None) -> None:
        record = self.permits.get(permit_id)
        if not record:
            return
        record.status = "REVOKED"
        if reason:
            record.restrictions = tuple(list(record.restrictions) + [f"revoked:{reason}"])

    def active_permits(self, *, tick: Optional[int] = None) -> List[PermitRecord]:
        return [record for record in self.permits.values() if record.is_active(tick=tick)]

    def set_trust_flag(self, flag: str, value: float) -> None:
        self.trust_flags[flag] = _clamp01(value)


@dataclass(slots=True)
class MemoryState:
    events: List[str] = field(default_factory=list)
    beliefs: MutableMapping[str, Dict[str, float]] = field(default_factory=dict)
    memes: MutableMapping[str, float] = field(default_factory=dict)
    rumors: MutableMapping[str, "RumorDigest"] = field(default_factory=dict)

    def decay(self, *, cred_lambda: float, belief_lambda: float, salience_lambda: float) -> None:
        for belief in self.beliefs.values():
            belief["Cred"] = _clamp01(belief.get("Cred", 0.0) * cred_lambda)
            belief["B"] = _clamp01(belief.get("B", 0.0) * belief_lambda)
            belief["Sal"] = _clamp01(belief.get("Sal", 0.0) * salience_lambda)
        for meme, value in list(self.memes.items()):
            self.memes[meme] = _clamp01(value * 0.999)
        for rumor in self.rumors.values():
            rumor.credibility = _clamp01(rumor.credibility * cred_lambda)
            rumor.salience = _clamp01(rumor.salience * salience_lambda)


@dataclass(slots=True)
class DriveState:
    """Hierarchical drive vectors aligned with D-AGENT-0101."""

    physiological: MutableMapping[str, float] = field(
        default_factory=lambda: {
            "Apathy": 0.1,
            "Survival": 0.6,
            "Grow": 0.3,
        }
    )
    material: MutableMapping[str, float] = field(
        default_factory=lambda: {
            "Hoard": 0.4,
            "Maintenance": 0.35,
            "Innovation": 0.25,
        }
    )
    social_reputation: MutableMapping[str, float] = field(
        default_factory=lambda: {
            "Dominance": 0.2,
            "Subservience": 0.2,
            "Vengeance": 0.1,
            "Reputation": 0.3,
            "Legacy": 0.2,
        }
    )
    social_relationships: MutableMapping[str, float] = field(
        default_factory=lambda: {
            "Conciliation": 0.4,
            "Paranoia": 0.3,
            "Destruction": 0.3,
        }
    )
    environmental: MutableMapping[str, float] = field(
        default_factory=lambda: {
            "Reclamation": 0.25,
            "Order": 0.25,
            "Curiosity": 0.25,
            "Transcendence": 0.25,
        }
    )
    weights: MutableMapping[str, float] = field(
        default_factory=lambda: {
            "Survival": 0.6,
            "Hoard": 0.2,
            "Advancement": 0.2,
        }
    )

    def normalize(self) -> None:
        for bucket in (
            self.physiological,
            self.material,
            self.social_reputation,
            self.social_relationships,
            self.environmental,
            self.weights,
        ):
            total = sum(bucket.values()) or 1.0
            for key, value in bucket.items():
                bucket[key] = max(0.0, value) / total

    def debug_vector(self) -> Dict[str, float]:
        debug: Dict[str, float] = {}
        for bucket in (
            self.physiological,
            self.material,
            self.social_reputation,
            self.social_relationships,
            self.environmental,
        ):
            debug.update(bucket)
        return debug


@dataclass(slots=True)
class AffectState:
    fear: float = 0.3
    ambition: float = 0.4
    loyalty: float = 0.5
    curiosity: float = 0.4
    stress: float = 0.3


@dataclass(slots=True)
class SkillState:
    skill_id: str
    rank: int = 1
    xp: float = 0.0
    xp_to_next: float = 100.0
    last_used_tick: Optional[int] = None


@dataclass(slots=True)
class DecisionRecord:
    tick: int
    action: str
    payload: Mapping[str, Any]
    survival_score: float
    long_term_score: float
    risk_score: float
    skill_success_prob: float
    top_candidates: Sequence[Mapping[str, Any]] = ()


@dataclass(slots=True)
class KnownAgentState:
    other_agent_id: str
    affinity: float = 0.5
    suspicion: float = 0.2
    threat: float = 0.2
    last_seen_tick: int = 0
    faction: Optional[str] = None
    role: Optional[str] = None


@dataclass(slots=True)
class KnownFacilityState:
    facility_id: str
    ward_id: str
    perceived_safety: float = 0.5
    perceived_usefulness: float = 0.5
    last_visited_tick: int = 0
    tags: Tuple[str, ...] = ()


@dataclass(slots=True)
class RumorDigest:
    rumor_id: str
    topic: str
    credibility: float
    times_heard: int
    first_heard_tick: int
    last_heard_tick: int
    payload_summary: str
    salience: float = 0.5


@dataclass(slots=True)
class AgentState:
    id: str
    name: str
    faction: str
    ward: str
    role: Optional[str] = None
    caste: Optional[str] = None
    identity: IdentityProfile = field(default_factory=IdentityProfile)
    body: BodyState = field(default_factory=BodyState)
    suit: SuitState = field(default_factory=SuitState)
    loadout: LoadoutState = field(default_factory=LoadoutState)
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
    crumbs: CrumbStore = field(default_factory=CrumbStore)
    episodes_daily: EpisodeBuffer = field(default_factory=EpisodeBuffer)
    stm: STMBoringWinner = field(default_factory=lambda: STMBoringWinner(k=24))
    drives: DriveState = field(default_factory=DriveState)
    affect: AffectState = field(default_factory=AffectState)
    techniques: List[str] = field(default_factory=lambda: ["Barter", "Observe", "Labor"])
    skills: MutableMapping[str, SkillState] = field(default_factory=dict)
    known_agents: MutableMapping[str, KnownAgentState] = field(default_factory=dict)
    known_facilities: MutableMapping[str, KnownFacilityState] = field(default_factory=dict)
    decision_trace: List[DecisionRecord] = field(default_factory=list)

    def record_decision(
        self,
        *,
        tick: int,
        action: str,
        payload: Mapping[str, Any],
        survival_score: float,
        long_term_score: float,
        risk_score: float,
        skill_success_prob: float,
        top_candidates: Sequence[Mapping[str, Any]] = (),
        history_limit: int = 25,
    ) -> None:
        entry = DecisionRecord(
            tick=tick,
            action=action,
            payload=dict(payload),
            survival_score=survival_score,
            long_term_score=long_term_score,
            risk_score=risk_score,
            skill_success_prob=skill_success_prob,
            top_candidates=tuple(dict(candidate) for candidate in top_candidates),
        )
        self.decision_trace.append(entry)
        if len(self.decision_trace) > history_limit:
            del self.decision_trace[:-history_limit]


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
    """Directed route representation used by logistics and security systems."""

    id: str
    origin: str
    destination: str
    distance_minutes: float
    checkpoint_level: float
    escort_risk: float
    capacity_liters: float
    hidden: bool = False
    route_type: str = "OFFICIAL"
    distance_km: float = 0.0
    risk: float = 0.0
    surcharge: float = 0.0
    incidents: List[Dict[str, object]] = field(default_factory=list)
    escort_jobs: List[str] = field(default_factory=list)
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
    ring_label: str = ""
    sealed: bool = False
    environment: EnvironmentState = field(default_factory=EnvironmentState)
    infrastructure: InfrastructureState = field(default_factory=InfrastructureState)
    stocks: StockState = field(default_factory=StockState)
    governor_faction: Optional[str] = None
    newsfeed: List[str] = field(default_factory=list)
    legitimacy: float = 0.55
    facilities: MutableMapping[str, int] = field(default_factory=dict)
    loyalty_to_king: float = 0.5
    smuggle_risk: float = 0.1
    need_index: float = 0.0
    risk_index: float = 0.0
    rotation_debt: float = 0.0
    specialisations: MutableMapping[str, float] = field(default_factory=dict)

    def apply_environment(self) -> None:
        self.environment.stress = self.environment.compute_stress()


# ---------------------------------------------------------------------------
# Global world container
# ---------------------------------------------------------------------------


@dataclass
class CrewState:
    crew_id: str
    work_type: WorkDetailType
    member_ids: List[str] = field(default_factory=list)
    leader_id: Optional[str] = None


@dataclass(slots=True)
class WorldConfig:
    tick_seconds: float = 0.6
    ticks_per_minute: int = 100
    minutes_per_day: int = 1440

    @property
    def ticks_per_day(self) -> int:
        return self.ticks_per_minute * self.minutes_per_day


def _protocol_registry_factory():
    from .systems.protocols import ProtocolRegistry

    return ProtocolRegistry()


def _health_config_factory():
    from dosadi.runtime.health import HealthConfig

    return HealthConfig()


@dataclass
class WorldState:
    tick: int = 0
    minute: int = 0
    day: int = 0
    seed: int = 0
    rng: random.Random = field(default_factory=random.Random)
    time_min: int = 0
    config: WorldConfig = field(default_factory=WorldConfig)
    wards: MutableMapping[str, WardState] = field(default_factory=dict)
    factions: MutableMapping[str, Faction | FactionState] = field(default_factory=dict)
    agents: MutableMapping[str, AgentState] = field(default_factory=dict)
    queues: MutableMapping[str, "QueueState"] = field(default_factory=dict)
    contracts: MutableMapping[str, ContractState] = field(default_factory=dict)
    cases: MutableMapping[str, CaseState] = field(default_factory=dict)
    rumors: MutableMapping[str, RumorState] = field(default_factory=dict)
    events_outbox: List[str] = field(default_factory=list)
    events: List[Dict[str, object]] = field(default_factory=list)
    event_log: WorldEventLog = field(default_factory=lambda: WorldEventLog(max_len=5000))
    routes: MutableMapping[str, RouteState] = field(default_factory=dict)
    facilities: MutableMapping[str, Any] = field(default_factory=FacilityLedger)
    places: MutableMapping[str, Any] = field(default_factory=dict)
    survey_map: SurveyMap = field(default_factory=SurveyMap)
    infra_cfg: CorridorInfraConfig = field(default_factory=CorridorInfraConfig)
    infra_edges: MutableMapping[str, CorridorInfraEdge] = field(default_factory=dict)
    discovery_cfg: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    crews: Dict[str, CrewState] = field(default_factory=dict)
    water_tap_sources: Dict[str, str] = field(default_factory=dict)
    facility_queues: MutableMapping[str, "FacilityQueueState"] = field(default_factory=dict)
    protocols: "ProtocolRegistry" = field(default_factory=_protocol_registry_factory)
    nodes: MutableMapping[str, Dict[str, Any]] = field(default_factory=dict)
    edges: MutableMapping[str, Dict[str, Any]] = field(default_factory=dict)
    groups: List[Any] = field(default_factory=list)
    policy: MutableMapping[str, Dict[str, Any]] = field(default_factory=dict)
    market_quotes: List[Dict[str, object]] = field(default_factory=list)
    trades: List[Dict[str, object]] = field(default_factory=list)
    labor_postings: List[Dict[str, object]] = field(default_factory=list)
    labor_assignments: List[Dict[str, object]] = field(default_factory=list)
    desired_work_details: Dict["WorkDetailType", int] = field(default_factory=dict)
    active_work_details: Dict["WorkDetailType", int] = field(default_factory=dict)
    goals: Dict[str, "Goal"] = field(default_factory=dict)
    goals_by_owner: Dict[str, List[str]] = field(default_factory=dict)
    next_goal_seq: int = 0
    maintenance_tasks: List[Dict[str, object]] = field(default_factory=list)
    clinic_records: List[Dict[str, object]] = field(default_factory=list)
    law_cases: List[Dict[str, object]] = field(default_factory=list)
    security_reports: List[Dict[str, object]] = field(default_factory=list)
    suit_service_ledger: SuitServiceLedger = field(default_factory=SuitServiceLedger)
    admin_event_log: AdminEventLog = field(default_factory=AdminEventLog)
    facility_belief_summaries: Dict[str, FacilityBeliefSummary] = field(default_factory=dict)
    facility_protocol_tuning: Dict[str, FacilityProtocolTuning] = field(default_factory=dict)
    metrics: Metrics = field(default_factory=Metrics)
    event_ring: EventRing = field(default_factory=EventRing)
    treaty_cfg: Any = None
    treaties: Dict[str, Any] = field(default_factory=dict)
    treaty_penalties: Dict[str, float] = field(default_factory=dict)
    debug_cfg: DebugConfig = field(default_factory=DebugConfig)
    council_metrics: CouncilMetrics = field(default_factory=CouncilMetrics)
    council_staffing_config: CouncilStaffingConfig = field(default_factory=CouncilStaffingConfig)
    ledger_cfg: LedgerConfig = field(default_factory=LedgerConfig)
    ledger_state: LedgerState = field(default_factory=LedgerState)
    inst_cfg: InstitutionConfig = field(default_factory=InstitutionConfig)
    inst_policy_by_ward: Dict[str, WardInstitutionPolicy] = field(default_factory=dict)
    inst_state_by_ward: Dict[str, WardInstitutionState] = field(default_factory=dict)
    urban_cfg: UrbanConfig = field(default_factory=UrbanConfig)
    urban_by_ward: Dict[str, WardUrbanState] = field(default_factory=dict)
    culture_cfg: CultureConfig = field(default_factory=CultureConfig)
    culture_by_ward: Dict[str, WardCultureState] = field(default_factory=dict)
    education_cfg: EducationConfig = field(default_factory=EducationConfig)
    education_by_ward: Dict[str, WardEducationState] = field(default_factory=dict)
    migration_cfg: MigrationConfig = field(default_factory=MigrationConfig)
    migration_by_ward: Dict[str, WardMigrationState] = field(default_factory=dict)
    migration_flows: List[MigrationFlow] = field(default_factory=list)
    health_cfg: "HealthConfig" = field(default_factory=_health_config_factory)
    health_by_ward: Dict[str, "WardHealthState"] = field(default_factory=dict)
    health_events: List["HealthEvent"] = field(default_factory=list)
    admin_logs: Dict[str, AdminLogEntry] = field(default_factory=dict)
    next_admin_log_seq: int = 0
    well: WellState = field(default_factory=WellState)
    inventories: InventoryRegistry = field(default_factory=InventoryRegistry)
    place_environment: Dict[str, PlaceEnvironmentState] = field(default_factory=dict)
    enf_cfg: Any = None
    enf_policy_by_ward: Dict[str, Any] = field(default_factory=dict)
    enf_state_by_ward: Dict[str, Any] = field(default_factory=dict)
    runtime_config: Any = None
    belief_config: Any = None
    belief_state: Any = None
    agents_with_new_signals: Set[str] = field(default_factory=set)
    basic_suit_stock: int = 0
    service_facilities: Dict[str, List[str]] = field(default_factory=dict)
    logistics: LogisticsLedger = field(default_factory=LogisticsLedger)
    logistics_cfg: LogisticsConfig = field(default_factory=LogisticsConfig)
    stock_cfg: StockpilePolicyConfig = field(default_factory=StockpilePolicyConfig)
    stock_state: StockpilePolicyState = field(default_factory=StockpilePolicyState)
    stock_policies: DepotPolicyLedger = field(default_factory=DepotPolicyLedger)
    market_cfg: MarketSignalsConfig = field(default_factory=MarketSignalsConfig)
    market_state: MarketSignalsState = field(default_factory=MarketSignalsState)
    escort_cfg: EscortConfig = field(default_factory=EscortConfig)
    escort_state: EscortState = field(default_factory=EscortState)
    ideology_cfg: Any = None
    ideology_by_ward: Dict[str, Any] = field(default_factory=dict)
    religion_cfg: Any = None
    sects: Dict[str, Any] = field(default_factory=dict)
    religion_by_ward: Dict[str, Any] = field(default_factory=dict)
    media_cfg: MediaConfig = field(default_factory=MediaConfig)
    media_in_flight: Dict[str, MediaMessage] = field(default_factory=dict)
    media_inbox_by_ward: Dict[str, deque[str]] = field(default_factory=dict)
    media_inbox_by_faction: Dict[str, deque[str]] = field(default_factory=dict)
    media_stats: Dict[str, float] = field(default_factory=dict)
    next_media_seq: int = 0
    delivery_due_queue: List[tuple[int, str]] = field(default_factory=list)
    carriers_available: int = 1
    next_carrier_seq: int = 0
    central_depot_node_id: str = "loc:depot-water-1"
    last_proto_council_tuning_day: int = -1
    last_promotion_check_tick: int = 0
    projects: ProjectLedger = field(default_factory=ProjectLedger)
    stockpiles: Dict[str, float] = field(default_factory=dict)
    phase_cfg: PhaseConfig = field(default_factory=PhaseConfig)
    phase_state: PhaseState = field(default_factory=PhaseState)
    logistics_loss_rate: float = 0.0
    expansion_planner_cfg: ExpansionPlannerConfig = field(default_factory=ExpansionPlannerConfig)
    expansion_planner_state: ExpansionPlannerState = field(
        default_factory=lambda: ExpansionPlannerState(next_plan_day=0)
    )
    scout_missions: ScoutMissionLedger = field(default_factory=ScoutMissionLedger)
    scout_cfg: ScoutConfig = field(default_factory=ScoutConfig)
    next_mission_seq: int = 0
    workforce: WorkforceLedger = field(default_factory=WorkforceLedger)
    staffing_cfg: StaffingConfig = field(default_factory=StaffingConfig)
    staffing_state: StaffingState = field(default_factory=StaffingState)
    suit_cfg: SuitWearConfig = field(default_factory=SuitWearConfig)
    suit_state: SuitWearState = field(default_factory=SuitWearState)
    suit_repairs: SuitRepairLedger = field(default_factory=SuitRepairLedger)
    incidents: IncidentLedger = field(default_factory=IncidentLedger)
    incident_cfg: IncidentConfig = field(default_factory=IncidentConfig)
    incident_state: IncidentState = field(default_factory=IncidentState)
    intf_cfg: InterferenceConfig = field(default_factory=InterferenceConfig)
    intf_state: InterferenceState = field(default_factory=InterferenceState)
    focus_cfg: FocusConfig = field(default_factory=FocusConfig)
    focus_state: FocusState = field(default_factory=FocusState)
    maint_cfg: MaintenanceConfig = field(default_factory=MaintenanceConfig)
    maint_state: MaintenanceState = field(default_factory=MaintenanceState)
    maintenance: MaintenanceLedger = field(default_factory=MaintenanceLedger)
    labor_cfg: LaborConfig = field(default_factory=LaborConfig)
    labor_orgs_by_ward: dict[str, list[LaborOrgState]] = field(default_factory=dict)
    labor_events: list[BargainingEvent] = field(default_factory=list)
    prod_cfg: ProductionConfig = field(default_factory=ProductionConfig)
    prod_state: ProductionState = field(default_factory=ProductionState)
    fac_prod: dict[str, FacilityProductionState] = field(default_factory=dict)
    mat_cfg: object | None = None
    mat_state: object | None = None
    construction_cfg: object | None = None
    extraction: ExtractionLedger = field(default_factory=ExtractionLedger)
    risk_cfg: CorridorRiskConfig = field(default_factory=CorridorRiskConfig)
    risk_ledger: CorridorRiskLedger = field(default_factory=CorridorRiskLedger)
    escort2_cfg: EscortPolicyV2Config = field(default_factory=EscortPolicyV2Config)
    escort2_state: EscortPolicyV2State = field(default_factory=EscortPolicyV2State)
    extract_cfg: ExtractionConfig = field(default_factory=ExtractionConfig)
    faction_cfg: FactionSystemConfig = field(default_factory=FactionSystemConfig)
    faction_state: FactionSystemState = field(default_factory=FactionSystemState)
    faction_territory: dict[str, FactionTerritory] = field(default_factory=dict)
    extract_state: ExtractionState = field(default_factory=ExtractionState)
    tech_cfg: object | None = None
    tech_state: object | None = None
    smuggling_cfg: SmugglingConfig = field(default_factory=SmugglingConfig)
    smuggling_by_faction: dict[str, SmugglingNetworkState] = field(default_factory=dict)
    war_cfg: WarConfig = field(default_factory=WarConfig)
    raid_active: dict[str, RaidPlan] = field(default_factory=dict)
    raid_history: list[RaidOutcome] = field(default_factory=list)
    corridor_stress: dict[str, float] = field(default_factory=dict)
    collapsed_corridors: set[str] = field(default_factory=set)
    espionage_cfg: EspionageConfig = field(default_factory=EspionageConfig)
    intel_ops_active: dict[str, IntelOpPlan] = field(default_factory=dict)
    intel_ops_history: list[IntelOpOutcome] = field(default_factory=list)
    counterintel_by_ward: dict[str, float] = field(default_factory=dict)
    defense_cfg: DefenseConfig = field(default_factory=DefenseConfig)
    ward_defense: dict[str, WardDefenseState] = field(default_factory=dict)
    deterrence_cfg: object | None = None
    relationships: dict[str, object] = field(default_factory=dict)

    def register_ward(self, ward: WardState) -> None:
        self.wards[ward.id] = ward

    def register_faction(self, faction: FactionState) -> None:
        self.factions[faction.id] = faction

    def register_agent(self, agent: AgentState) -> None:
        self.agents[agent.id] = agent

    def next_goal_id(self, prefix: str = "goal") -> str:
        self.next_goal_seq += 1
        return f"{prefix}:{self.next_goal_seq}"

    def register_goal(self, goal: "Goal") -> None:
        self.goals[goal.goal_id] = goal
        owner_list = self.goals_by_owner.setdefault(goal.owner_id, [])
        if goal.goal_id not in owner_list:
            owner_list.append(goal.goal_id)

    def get_goal(self, goal_id: str) -> Optional["Goal"]:
        return self.goals.get(goal_id)

    def goals_for_owner(self, owner_id: str, goal_type: Optional["GoalType"] = None) -> List["Goal"]:
        from dosadi.agents.core import GoalType as CoreGoalType  # Local import to avoid cycles

        ids = self.goals_by_owner.get(owner_id, [])
        results = [self.goals[g_id] for g_id in ids if g_id in self.goals]
        if goal_type is None:
            return results
        target_type = goal_type if isinstance(goal_type, CoreGoalType) else CoreGoalType(goal_type)
        return [g for g in results if g.goal_type == target_type]

    def register_queue(self, queue: "QueueState") -> None:
        self.queues[queue.queue_id] = queue

    def get_queue(self, queue_id: str) -> Optional["QueueState"]:
        return self.queues.get(queue_id)

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

    def to_snapshot(self) -> Dict[str, Any]:
        """Serialise the world into deterministic primitives."""

        return serialize_state(self)

    def advance_tick(self) -> None:
        self.tick += 1
        ticks_per_minute = max(1, int(self.config.ticks_per_minute))
        minutes_per_day = max(1, int(self.config.minutes_per_day))

        if self.tick % ticks_per_minute == 0:
            self.minute += 1
            self.time_min = self.minute
            if self.minute > 0 and self.minute % minutes_per_day == 0:
                self.day += 1

    def advance_ticks(self, count: int) -> None:
        if count <= 0:
            return
        for _ in range(count):
            self.advance_tick()

    def advance_minutes(self, minutes: int) -> None:
        if minutes <= 0:
            return
        self.advance_ticks(minutes * max(1, int(self.config.ticks_per_minute)))


def minute_tick(state: WorldState) -> None:
    """Advance the state by one simulation minute."""

    state.advance_minutes(1)


def day_tick(state: WorldState) -> None:
    """Advance the state by one simulation day."""

    state.advance_minutes(max(1, int(state.config.minutes_per_day)))


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
    "Faction",
    "FactionSystemConfig",
    "FactionSystemState",
    "FactionMetrics",
    "InfrastructureState",
    "LedgerConfig",
    "LedgerState",
    "MemoryState",
    "RouteState",
    "RumorState",
    "SuitServiceLedger",
    "SuitServiceLedgerEntry",
    "StockState",
    "SuitState",
    "WardState",
    "WorldConfig",
    "WorldState",
    "day_tick",
    "minute_tick",
]


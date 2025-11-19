"""Admin debug snapshots and lightweight CLI renderer.

The module implements the snapshot contracts defined in
``docs/latest/09_interfaces/D-INTERFACE-0001_Admin_Debug_Dashboard_Overview_v0.md``
and consumes the enriched agent schema from ``docs/latest/01_agents``.  The
helpers keep the runtime read-only and provide a tiny UI primitive for notebook
or CLI exploration without forcing a specific frontend stack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import fmean
from typing import Any, List, Mapping, MutableMapping, Optional, Sequence

from ..state import AgentState, KnownAgentState, KnownFacilityState, WorldState


# ---------------------------------------------------------------------------
# Snapshot data classes (mirroring D-INTERFACE-0001)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WardSummary:
    ward_id: str
    name: str
    population_tier1: int
    population_tier2_plus: int
    avg_hunger: float
    avg_fear: float
    avg_fatigue: float
    enforcement_level: float
    recent_events_count: int


@dataclass(slots=True)
class WorldSnapshot:
    tick: int
    total_agents: int
    total_facilities: int
    ward_summaries: List[WardSummary]
    global_metrics: MutableMapping[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class FacilitySnapshot:
    facility_id: str
    ward_id: str
    name: str
    kind: str
    capacity: int
    current_occupancy: int
    queue_length: int
    enforcement_presence: float
    recent_events: List[str] = field(default_factory=list)


@dataclass(slots=True)
class WardSnapshot:
    tick: int
    ward_id: str
    name: str
    population_tier1: int
    population_tier2_plus: int
    avg_hunger: float
    avg_fear: float
    avg_fatigue: float
    enforcement_level: float
    facilities: List[FacilitySnapshot]
    metrics: MutableMapping[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class DriveStateDebug:
    hunger: float
    thirst: float
    fatigue: float
    fear: float
    ambition: float
    loyalty: float
    curiosity: float


@dataclass(slots=True)
class DecisionTraceEntry:
    tick: int
    chosen_action_kind: str
    chosen_action_payload: Mapping[str, Any]
    survival_score: float
    long_term_score: float
    risk_score: float
    skill_success_prob: float
    top_candidates: Sequence[Mapping[str, Any]]


@dataclass(slots=True)
class RumorDebugEntry:
    rumor_id: str
    topic_token: str
    credibility: float
    times_heard: int
    first_heard_tick: int
    last_heard_tick: int
    payload_summary: str


@dataclass(slots=True)
class KnownAgentDebug:
    other_agent_id: str
    affinity: float
    suspicion: float
    threat: float
    last_seen_tick: int
    faction: Optional[str]
    role: Optional[str]


@dataclass(slots=True)
class KnownFacilityDebug:
    facility_id: str
    ward_id: str
    perceived_safety: float
    perceived_usefulness: float
    last_visited_tick: int
    tags: Sequence[str]


@dataclass(slots=True)
class SkillDebugEntry:
    skill_id: str
    rank: int
    xp: float
    xp_to_next: float
    last_used_tick: Optional[int]


@dataclass(slots=True)
class IdentityDebugSnapshot:
    handles: Sequence[str]
    clearance_level: str
    active_permits: Sequence[str]
    trust_flags: Mapping[str, float]


@dataclass(slots=True)
class LoadoutDebugSnapshot:
    primary: Optional[str]
    secondary: Optional[str]
    support_items: Sequence[str]
    kit_tags: Sequence[str]
    readiness: float
    signature: str


@dataclass(slots=True)
class AgentDebugSnapshot:
    tick: int
    agent_id: str
    name: Optional[str]
    ward_id: str
    facility_id: Optional[str]
    role: Optional[str]
    faction: Optional[str]
    caste: Optional[str]
    health: float
    hunger: float
    thirst: float
    fatigue: float
    drives: DriveStateDebug
    last_decision: Optional[DecisionTraceEntry]
    recent_decisions: List[DecisionTraceEntry]
    known_agents: List[KnownAgentDebug]
    known_facilities: List[KnownFacilityDebug]
    rumors: List[RumorDebugEntry]
    skills: List[SkillDebugEntry]
    identity: IdentityDebugSnapshot
    loadout: LoadoutDebugSnapshot


# ---------------------------------------------------------------------------
# Snapshot builders
# ---------------------------------------------------------------------------


def snapshot_world_state(world: WorldState) -> WorldSnapshot:
    ward_summaries: List[WardSummary] = []
    total_facilities = 0
    hunger_values: List[float] = []
    fear_values: List[float] = []
    fatigue_values: List[float] = []

    for ward in world.wards.values():
        agents = [agent for agent in world.agents.values() if agent.ward == ward.id]
        tier2 = [agent for agent in agents if _is_tier2(agent)]
        hunger = [_agent_hunger(agent) for agent in agents]
        fear = [_agent_fear(agent) for agent in agents]
        fatigue = [_agent_fatigue(agent) for agent in agents]
        hunger_values.extend(hunger)
        fear_values.extend(fear)
        fatigue_values.extend(fatigue)
        recent_events = len(ward.newsfeed[-15:])
        total_facilities += len(ward.facilities)
        ward_summaries.append(
            WardSummary(
                ward_id=ward.id,
                name=ward.name,
                population_tier1=len(agents) - len(tier2),
                population_tier2_plus=len(tier2),
                avg_hunger=fmean(hunger) if hunger else 0.0,
                avg_fear=fmean(fear) if fear else 0.0,
                avg_fatigue=fmean(fatigue) if fatigue else 0.0,
                enforcement_level=_clamp01(ward.infrastructure.checkpoint_severity),
                recent_events_count=recent_events,
            )
        )

    global_metrics = {
        "avg_hunger": fmean(hunger_values) if hunger_values else 0.0,
        "avg_fear": fmean(fear_values) if fear_values else 0.0,
        "avg_fatigue": fmean(fatigue_values) if fatigue_values else 0.0,
        "water_reserves": sum(ward.stocks.water_liters for ward in world.wards.values()),
        "biomass_reserves": sum(ward.stocks.biomass_kg for ward in world.wards.values()),
    }

    return WorldSnapshot(
        tick=world.tick,
        total_agents=len(world.agents),
        total_facilities=total_facilities,
        ward_summaries=ward_summaries,
        global_metrics=global_metrics,
    )


def snapshot_ward(world: WorldState, ward_id: str) -> WardSnapshot:
    ward = world.wards[ward_id]
    agents = [agent for agent in world.agents.values() if agent.ward == ward.id]
    tier2 = [agent for agent in agents if _is_tier2(agent)]
    hunger = [_agent_hunger(agent) for agent in agents]
    fear = [_agent_fear(agent) for agent in agents]
    fatigue = [_agent_fatigue(agent) for agent in agents]

    facilities: List[FacilitySnapshot] = []
    for facility_id, capacity in ward.facilities.items():
        occupancy = _estimate_occupancy(capacity, ward.need_index)
        queue = max(0, occupancy - capacity)
        facilities.append(
            FacilitySnapshot(
                facility_id=f"{ward.id}:{facility_id}",
                ward_id=ward.id,
                name=facility_id.replace("_", " ").title(),
                kind=facility_id.upper(),
                capacity=capacity,
                current_occupancy=min(capacity, occupancy),
                queue_length=queue,
                enforcement_presence=_clamp01(ward.infrastructure.checkpoint_severity),
                recent_events=ward.newsfeed[-5:],
            )
        )

    metrics = {
        "need_index": ward.need_index,
        "risk_index": ward.risk_index,
        "smuggle_risk": ward.smuggle_risk,
    }

    return WardSnapshot(
        tick=world.tick,
        ward_id=ward.id,
        name=ward.name,
        population_tier1=len(agents) - len(tier2),
        population_tier2_plus=len(tier2),
        avg_hunger=fmean(hunger) if hunger else 0.0,
        avg_fear=fmean(fear) if fear else 0.0,
        avg_fatigue=fmean(fatigue) if fatigue else 0.0,
        enforcement_level=_clamp01(ward.infrastructure.checkpoint_severity),
        facilities=facilities,
        metrics=metrics,
    )


def snapshot_agent_debug(world: WorldState, agent_id: str, max_history: int = 10) -> AgentDebugSnapshot:
    agent = world.agents[agent_id]
    hunger = _agent_hunger(agent)
    thirst = _agent_thirst(agent)
    fatigue = _agent_fatigue(agent)
    drives = _drive_debug(agent)
    decisions = list(agent.decision_trace[-max_history:])
    decision_entries = [_decision_entry(record) for record in decisions]
    last_decision = decision_entries[-1] if decision_entries else None

    known_agents = [
        KnownAgentDebug(
            other_agent_id=record.other_agent_id,
            affinity=record.affinity,
            suspicion=record.suspicion,
            threat=record.threat,
            last_seen_tick=record.last_seen_tick,
            faction=record.faction,
            role=record.role,
        )
        for record in agent.known_agents.values()
    ]
    known_agents.sort(key=lambda record: record.affinity, reverse=True)

    known_facilities = [
        KnownFacilityDebug(
            facility_id=record.facility_id,
            ward_id=record.ward_id,
            perceived_safety=record.perceived_safety,
            perceived_usefulness=record.perceived_usefulness,
            last_visited_tick=record.last_visited_tick,
            tags=list(record.tags),
        )
        for record in agent.known_facilities.values()
    ]
    known_facilities.sort(key=lambda record: record.perceived_usefulness, reverse=True)

    rumors = [
        RumorDebugEntry(
            rumor_id=rumor.rumor_id,
            topic_token=rumor.topic,
            credibility=rumor.credibility,
            times_heard=rumor.times_heard,
            first_heard_tick=rumor.first_heard_tick,
            last_heard_tick=rumor.last_heard_tick,
            payload_summary=rumor.payload_summary,
        )
        for rumor in agent.memory.rumors.values()
    ]
    rumors.sort(key=lambda entry: entry.credibility, reverse=True)

    skills = [
        SkillDebugEntry(
            skill_id=skill.skill_id,
            rank=skill.rank,
            xp=skill.xp,
            xp_to_next=skill.xp_to_next,
            last_used_tick=skill.last_used_tick,
        )
        for skill in agent.skills.values()
    ]
    skills.sort(key=lambda entry: entry.rank, reverse=True)

    active_permits = [
        f"{record.kind}:{record.id}"
        for record in agent.identity.active_permits(tick=world.tick)
    ]
    identity_debug = IdentityDebugSnapshot(
        handles=tuple(agent.identity.handles),
        clearance_level=agent.identity.clearance_level,
        active_permits=tuple(active_permits),
        trust_flags=dict(agent.identity.trust_flags),
    )
    loadout_debug = LoadoutDebugSnapshot(
        primary=agent.loadout.primary,
        secondary=agent.loadout.secondary,
        support_items=tuple(agent.loadout.support_items),
        kit_tags=tuple(agent.loadout.kit_tags),
        readiness=_clamp01(agent.loadout.readiness),
        signature=agent.loadout.signature,
    )

    return AgentDebugSnapshot(
        tick=world.tick,
        agent_id=agent.id,
        name=agent.name,
        ward_id=agent.ward,
        facility_id=None,
        role=agent.role,
        faction=agent.faction,
        caste=agent.caste or agent.suit.caste,
        health=_clamp01(agent.body.health / 100.0),
        hunger=hunger,
        thirst=thirst,
        fatigue=fatigue,
        drives=drives,
        last_decision=last_decision,
        recent_decisions=decision_entries,
        known_agents=known_agents[:5],
        known_facilities=known_facilities[:5],
        rumors=rumors[:5],
        skills=skills[:5],
        identity=identity_debug,
        loadout=loadout_debug,
    )


# ---------------------------------------------------------------------------
# UI Helpers
# ---------------------------------------------------------------------------


class AdminDebugView:
    """Render snapshots into simple ASCII panels."""

    def render_world(self, snapshot: WorldSnapshot) -> str:
        lines = [f"Tick {snapshot.tick:,} | Agents: {snapshot.total_agents} | Facilities: {snapshot.total_facilities}"]
        lines.append("Ward | Tier1 | Tier2+ | Hunger | Fear | Fatigue | Enforcement | Events")
        for ward in sorted(snapshot.ward_summaries, key=lambda summary: summary.ward_id):
            lines.append(
                f"{ward.ward_id:>4} | {ward.population_tier1:5} | {ward.population_tier2_plus:6} | "
                f"{ward.avg_hunger:0.2f} | {ward.avg_fear:0.2f} | {ward.avg_fatigue:0.2f} | "
                f"{ward.enforcement_level:0.2f} | {ward.recent_events_count}"
            )
        metric_line = " | ".join(f"{key}={value:0.2f}" for key, value in snapshot.global_metrics.items())
        lines.append(f"Metrics: {metric_line}")
        return "\n".join(lines)

    def render_ward(self, snapshot: WardSnapshot) -> str:
        lines = [f"Ward {snapshot.name} ({snapshot.ward_id}) @ tick {snapshot.tick}"]
        lines.append(
            f"Pop: T1={snapshot.population_tier1} T2+={snapshot.population_tier2_plus} | "
            f"Hunger={snapshot.avg_hunger:0.2f} Fear={snapshot.avg_fear:0.2f} Fatigue={snapshot.avg_fatigue:0.2f}"
        )
        for facility in snapshot.facilities:
            lines.append(
                f" - {facility.name}: occ={facility.current_occupancy}/{facility.capacity} "
                f"queue={facility.queue_length} enforcement={facility.enforcement_presence:0.2f}"
            )
        metric_line = ", ".join(f"{key}={value:0.2f}" for key, value in snapshot.metrics.items())
        lines.append(f"Metrics: {metric_line}")
        return "\n".join(lines)

    def render_agent(self, snapshot: AgentDebugSnapshot) -> str:
        lines = [f"Agent {snapshot.agent_id} ({snapshot.name})"]
        lines.append(
            f"Ward={snapshot.ward_id} Role={snapshot.role or '-'} Faction={snapshot.faction or '-'} Caste={snapshot.caste or '-'}"
        )
        lines.append(
            f"Vitals: health={snapshot.health:0.2f} hunger={snapshot.hunger:0.2f} "
            f"thirst={snapshot.thirst:0.2f} fatigue={snapshot.fatigue:0.2f}"
        )
        lines.append(
            f"Drives: fear={snapshot.drives.fear:0.2f} ambition={snapshot.drives.ambition:0.2f} "
            f"loyalty={snapshot.drives.loyalty:0.2f} curiosity={snapshot.drives.curiosity:0.2f}"
        )
        if snapshot.identity.handles:
            lines.append("Handles: " + ", ".join(snapshot.identity.handles))
        lines.append(
            f"Clearance={snapshot.identity.clearance_level} Permits={', '.join(snapshot.identity.active_permits) or '<none>'}"
        )
        if snapshot.identity.trust_flags:
            trust = ", ".join(
                f"{flag}:{value:0.2f}" for flag, value in snapshot.identity.trust_flags.items()
            )
            lines.append("Trust: " + trust)
        if snapshot.last_decision:
            lines.append(
                f"Last decision @{snapshot.last_decision.tick}: {snapshot.last_decision.chosen_action_kind}"
                f" survival={snapshot.last_decision.survival_score:0.2f}"
            )
        loadout_support = ", ".join(snapshot.loadout.support_items) or "<none>"
        kit_tags = ", ".join(snapshot.loadout.kit_tags) or "<none>"
        lines.append(
            f"Loadout primary={snapshot.loadout.primary or '-'} secondary={snapshot.loadout.secondary or '-'} "
            f"support={loadout_support} readiness={snapshot.loadout.readiness:0.2f}"
        )
        lines.append(f"Kit tags: {kit_tags} signature={snapshot.loadout.signature}")
        if snapshot.known_agents:
            lines.append("Known agents: " + ", ".join(entry.other_agent_id for entry in snapshot.known_agents))
        if snapshot.rumors:
            lines.append("Rumors: " + ", ".join(entry.payload_summary for entry in snapshot.rumors))
        return "\n".join(lines)

    def render_dashboard(
        self,
        world: WorldState,
        *,
        ward_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> str:
        world_snapshot = snapshot_world_state(world)
        lines = [self.render_world(world_snapshot)]
        if ward_id and ward_id in world.wards:
            lines.append("")
            lines.append(self.render_ward(snapshot_ward(world, ward_id)))
        if agent_id and agent_id in world.agents:
            lines.append("")
            lines.append(self.render_agent(snapshot_agent_debug(world, agent_id)))
        return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _agent_hunger(agent: AgentState) -> float:
    return agent.body.hunger_ratio()


def _agent_thirst(agent: AgentState) -> float:
    return agent.body.thirst_ratio()


def _agent_fatigue(agent: AgentState) -> float:
    return agent.body.fatigue_ratio()


def _agent_fear(agent: AgentState) -> float:
    return _clamp01(agent.affect.fear)


def _drive_debug(agent: AgentState) -> DriveStateDebug:
    hunger = _agent_hunger(agent)
    thirst = _agent_thirst(agent)
    fatigue = _agent_fatigue(agent)
    return DriveStateDebug(
        hunger=hunger,
        thirst=thirst,
        fatigue=fatigue,
        fear=_clamp01(agent.affect.fear),
        ambition=_clamp01(agent.affect.ambition),
        loyalty=_clamp01(agent.affect.loyalty),
        curiosity=_clamp01(agent.affect.curiosity),
    )


def _decision_entry(record: Any) -> DecisionTraceEntry:
    return DecisionTraceEntry(
        tick=record.tick,
        chosen_action_kind=record.action,
        chosen_action_payload=dict(record.payload),
        survival_score=record.survival_score,
        long_term_score=record.long_term_score,
        risk_score=record.risk_score,
        skill_success_prob=record.skill_success_prob,
        top_candidates=[dict(candidate) for candidate in record.top_candidates],
    )


def _estimate_occupancy(capacity: int, need_index: float) -> int:
    load = capacity * (0.4 + need_index * 0.8)
    return max(0, int(load))


def _is_tier2(agent: AgentState) -> bool:
    caste = (agent.caste or agent.suit.caste or "").upper()
    tier2_castes = {"ADMIN", "ROYAL", "GUILD", "CAPTAIN", "GUARD", "ENGINEER"}
    return caste in tier2_castes


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


__all__ = [
    "AdminDebugView",
    "AgentDebugSnapshot",
    "DecisionTraceEntry",
    "DriveStateDebug",
    "FacilitySnapshot",
    "IdentityDebugSnapshot",
    "KnownAgentDebug",
    "KnownFacilityDebug",
    "RumorDebugEntry",
    "SkillDebugEntry",
    "WardSnapshot",
    "WardSummary",
    "WorldSnapshot",
    "snapshot_agent_debug",
    "snapshot_ward",
    "snapshot_world_state",
]

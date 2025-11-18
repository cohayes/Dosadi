---
title: Perception_and_Memory_Python_Skeleton
doc_id: D-AGENT-0005-SKEL
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0002   # Agent_Decision_Rule_v0
  - D-AGENT-0004   # Agent_Action_API_v0
  - D-AGENT-0005   # Perception_and_Memory_v0
  - D-RUNTIME-0001 # Simulation_Timebase
---

```python
"""
D-AGENT-0005 Perception_and_Memory_v0
Core data structures and APIs for agent perception & memory.

Depends on:
- D-AGENT-0001 Agent_Core_Schema_v0
- D-AGENT-0002 Agent_Decision_Rule_v0
- D-AGENT-0004 Agent_Action_API_v0
- D-RUNTIME-0001 Simulation_Timebase
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# ---------------------------------------------------------------------------
# Perception snapshot types (world -> agent input)
# ---------------------------------------------------------------------------

@dataclass
class VisibleAgent:
    agent_id: str
    faction_id: Optional[str]
    role_tags: List[str]          # e.g. ["GUARD", "CLERK", "SOUP_STAFF"]
    location_id: str
    zone_id: Optional[str]
    posture: Optional[str]        # e.g. "IDLE", "WORKING", "PATROLLING"
    apparent_status: Dict[str, Any]  # e.g. {"armed": True, "wounded": False}


@dataclass
class VisibleFacility:
    facility_id: str
    facility_type: str            # e.g. "SOUP_KITCHEN", "BUNKHOUSE", "CLINIC"
    ward_id: Optional[str]
    open_for_services: Dict[str, bool]   # e.g. {"MEAL": True, "BED": False}
    enforcement_presence: float          # 0..1 summary of visible authority


@dataclass
class PerceptionSnapshot:
    tick: int
    location_id: str
    zone_id: Optional[str]
    visible_agents: List[VisibleAgent]
    visible_facilities: List[VisibleFacility]
    ambient_risk: float                  # 0..1 local environmental threat
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Memory core schema
# ---------------------------------------------------------------------------

@dataclass
class AgentBelief:
    agent_id: str
    last_seen_tick: int
    last_seen_location_id: str
    last_seen_zone_id: Optional[str]
    suspicion: float       # 0..1 (0 = fully trusted, 1 = highly suspicious)
    affinity: float        # -1..1 (-1 = enemy, 0 = neutral, 1 = ally)
    threat: float          # 0..1 (0 = harmless, 1 = lethal)
    confidence: float      # 0..1 (belief is current & well-founded)


@dataclass
class FacilityBelief:
    facility_id: str
    facility_type: str
    last_visited_tick: int
    perceived_safety: float    # 0..1 (0 = deadly, 1 = very safe)
    perceived_access: float    # 0..1 (likelihood of being served/allowed in)
    enforcement_level: float   # 0..1 (visible authority presence)
    confidence: float          # 0..1


@dataclass
class Rumor:
    rumor_id: str
    topic_token: str                   # e.g. "BANDIT_ATTACK", "INSPECTION_SOON"
    source_agent_id: Optional[str]
    target_agent_id: Optional[str]
    target_facility_id: Optional[str]
    payload: Dict[str, Any]
    first_heard_tick: int
    last_heard_tick: int
    credibility: float                 # 0..1
    times_heard: int


@dataclass
class ConversationEvent:
    tick: int
    speaker_id: str
    listener_id: str
    topic_token: str                   # e.g. "RUMOR", "TRADE", "THREAT"
    payload: Dict[str, Any]
    perceived_sincerity: float         # 0..1 estimate of honesty


@dataclass
class Memory:
    """
    Agent memory container as specified in D-AGENT-0005.
    Intended to live on Agent as `agent.memory: Memory`.
    """
    tick_last_updated: int = 0
    known_agents: Dict[str, AgentBelief] = field(default_factory=dict)
    known_facilities: Dict[str, FacilityBelief] = field(default_factory=dict)
    rumors: Dict[str, Rumor] = field(default_factory=dict)

    # -------------------------------------------------------------------
    # Observation updates
    # -------------------------------------------------------------------

    def update_from_observation(self, snapshot: PerceptionSnapshot) -> None:
        """
        Merge a new perception snapshot into memory.

        - Updates existing AgentBelief / FacilityBelief entries.
        - Creates new ones for newly seen agents/facilities.
        - Adjusts confidence and freshness.
        """
        self.tick_last_updated = snapshot.tick

        for va in snapshot.visible_agents:
            self._update_agent_from_visible(va, snapshot)

        for vf in snapshot.visible_facilities:
            self._update_facility_from_visible(vf, snapshot)

        # TODO: optional handling of snapshot.ambient_risk at location-level

    def _update_agent_from_visible(
        self,
        va: VisibleAgent,
        snapshot: PerceptionSnapshot,
    ) -> None:
        belief = self.known_agents.get(va.agent_id)

        if belief is None:
            # TODO: define proper initial_suspicion/threat/confidence functions
            belief = AgentBelief(
                agent_id=va.agent_id,
                last_seen_tick=snapshot.tick,
                last_seen_location_id=snapshot.location_id,
                last_seen_zone_id=snapshot.zone_id,
                suspicion=self._initial_suspicion(va, snapshot),
                affinity=0.0,
                threat=self._initial_threat(va, snapshot),
                confidence=self._initial_confidence_from_sighting(va, snapshot),
            )
            self.known_agents[va.agent_id] = belief
            return

        # Update existing belief
        belief.last_seen_tick = snapshot.tick
        belief.last_seen_location_id = snapshot.location_id
        belief.last_seen_zone_id = snapshot.zone_id
        belief.confidence = min(1.0, belief.confidence + self._delta_conf_seen(va, snapshot))

        # TODO: optionally nudge suspicion/threat based on va.role_tags, posture, etc.

    def _update_facility_from_visible(
        self,
        vf: VisibleFacility,
        snapshot: PerceptionSnapshot,
    ) -> None:
        belief = self.known_facilities.get(vf.facility_id)

        if belief is None:
            belief = FacilityBelief(
                facility_id=vf.facility_id,
                facility_type=vf.facility_type,
                last_visited_tick=snapshot.tick,
                perceived_safety=self._initial_facility_safety(vf, snapshot),
                perceived_access=self._initial_facility_access(vf, snapshot),
                enforcement_level=vf.enforcement_presence,
                confidence=self._initial_confidence_from_facility(vf, snapshot),
            )
            self.known_facilities[vf.facility_id] = belief
            return

        belief.last_visited_tick = snapshot.tick
        belief.enforcement_level = vf.enforcement_presence
        belief.confidence = min(1.0, belief.confidence + self._delta_conf_seen_facility(vf, snapshot))
        # TODO: optional nudges to perceived_safety / perceived_access

    # -------------------------------------------------------------------
    # Conversation updates
    # -------------------------------------------------------------------

    def update_from_conversation(self, event: ConversationEvent) -> None:
        """
        Merge a conversation into memory.

        - Creates or updates Rumor entries (when topic_token indicates).
        - Adjusts AgentBelief for the speaker (credibility, suspicion, affinity).
        - Optionally adjusts beliefs about targets in payload.
        """
        self.tick_last_updated = max(self.tick_last_updated, event.tick)

        if event.topic_token.upper() == "RUMOR":
            self._ingest_rumor_event(event)

        # Speaker belief always updated/created
        self._ensure_agent_belief(event.speaker_id, event.tick)

        # TODO: track speaker credibility over time, adjust suspicion/affinity
        # based on later confirmation/contradiction of rumors.

    def _ingest_rumor_event(self, event: ConversationEvent) -> None:
        rumor_key = self._derive_rumor_id(event)

        rumor = self.rumors.get(rumor_key)
        if rumor is None:
            rumor = Rumor(
                rumor_id=rumor_key,
                topic_token=event.topic_token,
                source_agent_id=event.speaker_id,
                target_agent_id=event.payload.get("target_agent_id"),
                target_facility_id=event.payload.get("target_facility_id"),
                payload=event.payload,
                first_heard_tick=event.tick,
                last_heard_tick=event.tick,
                credibility=self._initial_rumor_credibility(event),
                times_heard=1,
            )
            self.rumors[rumor_key] = rumor
            return

        rumor.last_heard_tick = event.tick
        rumor.times_heard += 1
        rumor.credibility = self._update_rumor_credibility(rumor, event)

    # -------------------------------------------------------------------
    # Suspicion / trust adjustments
    # -------------------------------------------------------------------

    def adjust_suspicion(self, agent_id: str, delta: float, reason: str, tick: int) -> None:
        belief = self._ensure_agent_belief(agent_id, tick)
        belief.suspicion = _clamp(belief.suspicion + delta, 0.0, 1.0)
        # TODO: optionally record last reason / tick for debugging

    def adjust_affinity(self, agent_id: str, delta: float, reason: str, tick: int) -> None:
        belief = self._ensure_agent_belief(agent_id, tick)
        belief.affinity = _clamp(belief.affinity + delta, -1.0, 1.0)

    def adjust_threat(self, agent_id: str, delta: float, reason: str, tick: int) -> None:
        belief = self._ensure_agent_belief(agent_id, tick)
        belief.threat = _clamp(belief.threat + delta, 0.0, 1.0)

    # -------------------------------------------------------------------
    # Facility outcome hooks
    # -------------------------------------------------------------------

    def note_facility_visit(self, facility_id: str, tick: int, outcome: str) -> None:
        """
        Update facility belief based on a visit outcome.

        outcome examples:
        - "SERVED_MEAL"
        - "DENIED_ENTRY"
        - "ATTACKED"
        - "SHELTERED"
        """
        belief = self._ensure_facility_belief_stub(facility_id, tick)

        # TODO: map outcome -> deltas for perceived_safety, perceived_access, confidence
        # Example:
        # if outcome == "SERVED_MEAL":
        #     belief.perceived_access = _clamp(belief.perceived_access + 0.05, 0.0, 1.0)
        # elif outcome == "DENIED_ENTRY":
        #     belief.perceived_access = _clamp(belief.perceived_access - 0.1, 0.0, 1.0)
        #     belief.perceived_safety = _clamp(belief.perceived_safety - 0.02, 0.0, 1.0)
        # etc.

    # -------------------------------------------------------------------
    # Decay / forgetting
    # -------------------------------------------------------------------

    def decay(self, current_tick: int, params: Dict[str, Any]) -> None:
        """
        Apply time-based decay to beliefs and rumors.

        params may include:
        - "agent_belief_half_life"
        - "facility_belief_half_life"
        - "rumor_half_life"
        - "min_confidence_threshold"
        """
        self.tick_last_updated = current_tick

        # TODO: implement decay functions; for now these are placeholders.
        # Suggested approach:
        #   - compute time_since_seen / visited / heard
        #   - apply exponential decay to confidence / credibility
        #   - prune entries below min thresholds

    # -------------------------------------------------------------------
    # Read-side query helpers (for decision rule)
    # -------------------------------------------------------------------

    def get_known_agents_nearby(self, location_id: str, radius: Optional[int] = None) -> List[AgentBelief]:
        """
        Return beliefs about agents likely to be nearby.

        For v0, this can be a simple filter on last_seen_location_id.
        More advanced versions can reason about wards / adjacency.
        """
        # TODO: respect radius / ward geometry when available.
        return [
            belief
            for belief in self.known_agents.values()
            if belief.last_seen_location_id == location_id
        ]

    def get_belief_about_agent(self, agent_id: str) -> Optional[AgentBelief]:
        return self.known_agents.get(agent_id)

    def get_facility_belief(self, facility_id: str) -> Optional[FacilityBelief]:
        return self.known_facilities.get(facility_id)

    def get_safe_facilities(self, min_safety: float, min_access: float) -> List[FacilityBelief]:
        """
        Return facilities above given safety/access thresholds.
        """
        return [
            belief
            for belief in self.known_facilities.values()
            if belief.perceived_safety >= min_safety
            and belief.perceived_access >= min_access
        ]

    def get_high_credibility_rumors(self, min_credibility: float) -> List[Rumor]:
        return [r for r in self.rumors.values() if r.credibility >= min_credibility]

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _ensure_agent_belief(self, agent_id: str, tick: int) -> AgentBelief:
        belief = self.known_agents.get(agent_id)
        if belief is None:
            belief = AgentBelief(
                agent_id=agent_id,
                last_seen_tick=tick,
                last_seen_location_id="UNKNOWN",
                last_seen_zone_id=None,
                suspicion=0.5,
                affinity=0.0,
                threat=0.5,
                confidence=0.1,
            )
            self.known_agents[agent_id] = belief
        return belief

    def _ensure_facility_belief_stub(self, facility_id: str, tick: int) -> FacilityBelief:
        belief = self.known_facilities.get(facility_id)
        if belief is None:
            belief = FacilityBelief(
                facility_id=facility_id,
                facility_type="UNKNOWN",
                last_visited_tick=tick,
                perceived_safety=0.5,
                perceived_access=0.5,
                enforcement_level=0.0,
                confidence=0.1,
            )
            self.known_facilities[facility_id] = belief
        return belief

    # --- default / placeholder scoring fns -----------------------------

    def _initial_suspicion(self, va: VisibleAgent, snapshot: PerceptionSnapshot) -> float:
        # TODO: use role_tags, posture, ambient_risk, faction alignment, etc.
        return 0.5

    def _initial_threat(self, va: VisibleAgent, snapshot: PerceptionSnapshot) -> float:
        # TODO: use apparent_status["armed"], role_tags, etc.
        return 0.5

    def _initial_confidence_from_sighting(self, va: VisibleAgent, snapshot: PerceptionSnapshot) -> float:
        return 0.5

    def _delta_conf_seen(self, va: VisibleAgent, snapshot: PerceptionSnapshot) -> float:
        return 0.05

    def _initial_facility_safety(self, vf: VisibleFacility, snapshot: PerceptionSnapshot) -> float:
        # TODO: use ambient_risk, enforcement_presence, prior experiences
        return 0.5

    def _initial_facility_access(self, vf: VisibleFacility, snapshot: PerceptionSnapshot) -> float:
        # TODO: use facility_type, open_for_services, faction, etc.
        return 0.5

    def _initial_confidence_from_facility(self, vf: VisibleFacility, snapshot: PerceptionSnapshot) -> float:
        return 0.5

    def _delta_conf_seen_facility(self, vf: VisibleFacility, snapshot: PerceptionSnapshot) -> float:
        return 0.05

    def _derive_rumor_id(self, event: ConversationEvent) -> str:
        """
        Derive a stable rumor id from topic + target payload.
        For v0, a simple string key is fine.
        """
        topic = event.topic_token
        tgt_agent = event.payload.get("target_agent_id", "")
        tgt_fac = event.payload.get("target_facility_id", "")
        return f"{topic}:{tgt_agent}:{tgt_fac}"

    def _initial_rumor_credibility(self, event: ConversationEvent) -> float:
        # TODO: use perceived_sincerity + speaker credibility when available.
        return event.perceived_sincerity

    def _update_rumor_credibility(self, rumor: Rumor, event: ConversationEvent) -> float:
        # TODO: more nuanced update (e.g. Bayesian-like aggregation).
        alpha = 0.5
        return _clamp(
            alpha * rumor.credibility + (1 - alpha) * event.perceived_sincerity,
            0.0,
            1.0,
        )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x
"""
```

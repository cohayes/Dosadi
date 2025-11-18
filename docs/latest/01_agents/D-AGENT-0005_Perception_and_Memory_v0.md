---
title: Perception_and_Memory_v0
doc_id: D-AGENT-0005
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0002   # Agent_Decision_Rule_v0
  - D-AGENT-0004   # Agent_Action_API_v0
  - D-RUNTIME-0001 # Simulation_Timebase
---

# 1. Purpose

This document defines the **Perception & Memory** subsystem for Dosadi agents.

It specifies:

- What information agents can **perceive** each tick.
- How that information is **stored, updated, and decayed** in `agent.memory`.
- How `agent.memory` is **exposed** to the decision rule (D-AGENT-0002).
- How actions like `OBSERVE_AREA` and `TALK_TO_AGENT` (D-AGENT-0004) modify memory.

This provides the backbone for:

- Local situational awareness (who is nearby, what facilities are active).
- Medium-term knowledge of **safe/dangerous places** and **trusted/suspicious people**.
- A basic substrate for later systems (rumor propagation, skills/learning, planning).

---

# 2. Design Goals & Constraints

1. **Local & bounded**  
   - Agents do not have global omniscience.
   - All knowledge originates from **perception**, **conversation**, or **inference** over these.

2. **Cheap to query, bounded in size**  
   - Decisions must query memory quickly each tick.
   - Memory should be bounded per agent (via decay/aggregation), not unbounded logs.

3. **Imperfect & lossy**  
   - Agents can forget, misremember, or hold outdated beliefs.
   - Later docs may introduce explicit noise/false beliefs; v0 focuses on **decay** and **staleness**.

4. **Suspicion-aware**  
   - Agents track basic **suspicion/trust** values for:
     - Other agents
     - Facilities / zones
   - These values drive loyalty- and risk-related behavior.

5. **Action-integrated**  
   - The perception & memory system is driven by:
     - `OBSERVE_AREA`
     - `TALK_TO_AGENT`
     - Movement and service actions that implicitly confirm/update location knowledge.

6. **Implementation-friendly**  
   - Concrete Python dataclasses and method signatures suitable for Codex.
   - Runtime/world provides raw perceptual input; `Memory` handles integration.

---

# 3. Perception Pipeline Overview

Perception is split into:

1. **World → PerceptionSnapshot**  
   - The world generates a **snapshot** of what the agent can see/hear in its vicinity for a given tick.

2. **PerceptionSnapshot → Memory.update_from_observation**  
   - The agent merges the snapshot into its long-lived `memory`.

3. **Conversation events → Memory.update_from_conversation**  
   - Social actions (e.g. `TALK_TO_AGENT`) generate structured conversation events.
   - Memory ingests these as rumors/facts/beliefs.

4. **Decay step**  
   - Once per tick (or phase), memory is decayed:
     - Confidence in old information goes down.
     - Highly stale entries may be pruned.

5. **Decision queries**  
   - D-AGENT-0002 queries `agent.memory` via a small, stable API to:
     - Find **safe facilities**,
     - Pick **trusted contacts**,
     - Evaluate **suspicion** and **threat levels** in the local area.

---

# 4. Data Model

## 4.1 Perception Snapshot (from world)

The runtime/world must provide a structured perception snapshot for an agent:

```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class VisibleAgent:
    agent_id: str
    faction_id: str | None
    role_tags: List[str]  # e.g. ["GUARD", "CLERK", "SOUP_STAFF"]
    location_id: str
    zone_id: str | None
    posture: str | None       # e.g. "IDLE", "WORKING", "PATROLLING"
    apparent_status: Dict[str, Any]  # e.g. {"armed": True, "wounded": False}

@dataclass
class VisibleFacility:
    facility_id: str
    facility_type: str       # e.g. "SOUP_KITCHEN", "BUNKHOUSE", "CLINIC"
    ward_id: str | None
    open_for_services: Dict[str, bool]  # e.g. {"MEAL": True, "BED": False}
    enforcement_presence: float         # 0..1 summary of visible authority

@dataclass
class PerceptionSnapshot:
    tick: int
    location_id: str
    zone_id: str | None
    visible_agents: List[VisibleAgent]
    visible_facilities: List[VisibleFacility]
    ambient_risk: float       # local environmental threat level 0..1
    metadata: Dict[str, Any]  # mode, radius, noise parameters, etc.
```

This is the output of:

```python
def get_visible_state(agent, radius, mode) -> PerceptionSnapshot:
    ...
```

as referenced by `OBSERVE_AREA` in D-AGENT-0004.

## 4.2 Memory Core Schema

`agent.memory` is a structured object with the following top-level fields:

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class AgentBelief:
    agent_id: str
    last_seen_tick: int
    last_seen_location_id: str
    last_seen_zone_id: Optional[str]
    suspicion: float        # 0..1 (0 = fully trusted, 1 = highly suspicious/dangerous)
    affinity: float         # -1..1 (negative = disliked, positive = liked/ally)
    threat: float           # 0..1 (perceived capacity to harm)
    confidence: float       # 0..1 (certainty that this model is accurate)

@dataclass
class FacilityBelief:
    facility_id: str
    facility_type: str
    last_visited_tick: int
    perceived_safety: float     # 0..1 (0 = deadly, 1 = very safe)
    perceived_access: float     # 0..1 (how likely the agent is to be served/allowed in)
    enforcement_level: float    # 0..1 (visibility of authorities)
    confidence: float           # 0..1

@dataclass
class Rumor:
    rumor_id: str
    topic_token: str            # e.g. "BANDIT_ATTACK", "INSPECTION_SOON"
    source_agent_id: Optional[str]
    target_agent_id: Optional[str]
    target_facility_id: Optional[str]
    payload: Dict[str, Any]
    first_heard_tick: int
    last_heard_tick: int
    credibility: float          # 0..1
    times_heard: int

@dataclass
class Memory:
    tick_last_updated: int
    known_agents: Dict[str, AgentBelief] = field(default_factory=dict)
    known_facilities: Dict[str, FacilityBelief] = field(default_factory=dict)
    rumors: Dict[str, Rumor] = field(default_factory=dict)
```

> **Note:**  
> `D-AGENT-0001` should define `agent.memory: Memory` (or equivalent).  
> This doc specifies its internal structure and update API.

---

# 5. Memory Update API

Codex should implement the following methods on `Memory` (or equivalent module-level functions).

## 5.1 Update from Observation

```python
class Memory:
    ...

    def update_from_observation(self, snapshot: PerceptionSnapshot) -> None:
        """
        Merge a new perception snapshot into memory.

        - Updates existing AgentBelief / FacilityBelief entries.
        - Creates new entries when new agents/facilities are seen.
        - Adjusts confidence and freshness fields.
        """
```

### 5.1.1 Agent update logic (example rules)

For each `VisibleAgent` in `snapshot.visible_agents`:

```text
IF agent_id not in known_agents:
    known_agents[agent_id] := AgentBelief(
        agent_id=agent_id,
        last_seen_tick=snapshot.tick,
        last_seen_location_id=location_id,
        last_seen_zone_id=zone_id,
        suspicion=initial_suspicion(visible_agent),
        affinity=0.0,
        threat=initial_threat(visible_agent),
        confidence=initial_confidence(visible_agent)
    )

ELSE:
    belief := known_agents[agent_id]
    belief.last_seen_tick := snapshot.tick
    belief.last_seen_location_id := location_id
    belief.last_seen_zone_id := zone_id

    # Sightings generally increase confidence that the agent exists/behaves as modeled:
    belief.confidence := min(1.0, belief.confidence + DELTA_CONF_SEEN)

    # Suspicion/threat may be nudged based on role_tags, posture, enforcement context, etc.
    # (e.g. guards in a crackdown might raise threat)
```

Concrete constants like `DELTA_CONF_SEEN` are runtime tunables.

### 5.1.2 Facility update logic (example rules)

For each `VisibleFacility` in `snapshot.visible_facilities`:

```text
IF facility_id not in known_facilities:
    known_facilities[facility_id] := FacilityBelief(
        facility_id=facility_id,
        facility_type=facility_type,
        last_visited_tick=snapshot.tick,
        perceived_safety=initial_safety(visible_facility),
        perceived_access=initial_access(visible_facility),
        enforcement_level=visible_facility.enforcement_presence,
        confidence=initial_confidence(visible_facility)
    )

ELSE:
    belief := known_facilities[facility_id]
    belief.last_visited_tick := snapshot.tick
    belief.enforcement_level := visible_facility.enforcement_presence
    belief.confidence := min(1.0, belief.confidence + DELTA_CONF_SEEN)

    # perceived_safety / perceived_access may be nudged based on ambient_risk, 
    # whether the agent is harmed / helped when here (handled by runtime hooks).
```

Runtime may also hook into facility interactions (e.g. being refused service, attacked, sheltered) to adjust `perceived_safety` and `perceived_access`.

---

## 5.2 Update from Conversation

`TALK_TO_AGENT` actions (D-AGENT-0004) should generate structured conversation events that memory can ingest:

```python
@dataclass
class ConversationEvent:
    tick: int
    speaker_id: str
    listener_id: str
    topic_token: str       # e.g. "RUMOR", "TRADE", "THREAT", etc.
    payload: Dict[str, Any]
    perceived_sincerity: float  # 0..1 estimate of honesty
```

Memory API:

```python
class Memory:
    ...

    def update_from_conversation(self, event: ConversationEvent) -> None:
        """
        Merge a conversation into memory.

        - Creates or updates Rumor entries.
        - Adjusts AgentBelief for the speaker (credibility, suspicion, affinity).
        - Optionally adjusts beliefs about target agents/facilities.
        """
```

### 5.2.1 Rumor handling (example rules)

Given `event` where topic is `"RUMOR"`:

```text
rumor_key := derive_rumor_id(event.payload)  # e.g. hash of topic + target

IF rumor_key not in rumors:
    rumors[rumor_key] := Rumor(
        rumor_id=rumor_key,
        topic_token=event.topic_token,
        source_agent_id=event.speaker_id,
        target_agent_id=event.payload.get("target_agent_id"),
        target_facility_id=event.payload.get("target_facility_id"),
        payload=event.payload,
        first_heard_tick=event.tick,
        last_heard_tick=event.tick,
        credibility=initial_credibility(event),
        times_heard=1
    )
ELSE:
    r := rumors[rumor_key]
    r.last_heard_tick := event.tick
    r.times_heard += 1

    # Multiple corroborating sources increase credibility; repeated from same
    # dubious speaker may not.
    r.credibility := update_credibility(r, event)
```

### 5.2.2 Speaker credibility & suspicion

For the `speaker_id`:

```text
belief := known_agents.get(speaker_id) or create_default_belief(speaker_id)

# If rumor later proves true/false (runtime/logic determines), credibility adjustments
# feed back into suspicion and affinity:

IF event.perceived_sincerity is high AND rumor later confirmed TRUE:
    decrease_suspicion(speaker_id)
    increase_affinity(speaker_id)

IF rumor later confirmed FALSE maliciously:
    increase_suspicion(speaker_id)
    decrease_affinity(speaker_id)
```

The mechanisms for “confirmed TRUE/FALSE” are left to higher-level logic; this doc ensures there is a place to store and adjust such beliefs.

---

# 6. Suspicion & Trust Model

Suspicion and trust are central to Dosadi’s loyalty-as-long-term-self-interest framing.

## 6.1 AgentBelief fields

- `suspicion: float (0..1)`  
  - 0 = fully trusted, 1 = extremely suspicious.
- `affinity: float (-1..1)`  
  - -1 = strongly disliked/enemy, 0 = neutral, 1 = strongly liked/ally.
- `threat: float (0..1)`  
  - 0 = harmless, 1 = lethal/highly dangerous.
- `confidence: float (0..1)`  
  - Confidence that the above values are well-founded and up-to-date.

## 6.2 Update hooks

Codex should implement utility methods:

```python
class Memory:
    ...

    def adjust_suspicion(self, agent_id: str, delta: float, reason: str, tick: int) -> None: ...
    def adjust_affinity(self, agent_id: str, delta: float, reason: str, tick: int) -> None: ...
    def adjust_threat(self, agent_id: str, delta: float, reason: str, tick: int) -> None: ...
```

These should:

- Clamp values within their ranges.
- Optionally record a simple audit trail (e.g. last reason and tick).

These methods are called by:

- Conversation logic (e.g. betrayal, loyalty tests).
- Runtime events (e.g. someone saving your life, attacking you).
- Higher-level social systems.

---

# 7. Decay / Forgetting

To keep memory bounded and imperfect, `Memory` includes a decay step invoked by the runtime once per tick (or per phase):

```python
class Memory:
    ...

    def decay(self, current_tick: int, params) -> None:
        """
        Apply time-based decay to beliefs and rumors.

        params may include:
        - agent_belief_half_life
        - facility_belief_half_life
        - rumor_half_life
        - min_confidence_threshold
        """
```

### 7.1 Example decay behavior

- For each `AgentBelief`:
  - If `current_tick - last_seen_tick` > threshold:
    - Gradually reduce `confidence`.
    - Optionally damp `affinity` and `suspicion` toward neutral values over long periods.

- For each `FacilityBelief`:
  - If `current_tick - last_visited_tick` is large:
    - Reduce `confidence`.
    - Slightly regress `perceived_safety` / `perceived_access` toward neutral (0.5).

- For each `Rumor`:
  - Reduce `credibility` over time if not corroborated.
  - If `credibility` and `confidence` drop below thresholds, delete the rumor.

This ensures agents naturally forget and re-normalize in changing environments.

---

# 8. Decision Rule Query API

To keep D-AGENT-0002 simple, `Memory` exposes a read-only query layer tuned for decision-making.

Suggested methods:

```python
class Memory:
    ...

    def get_known_agents_nearby(self, location_id: str, radius: int | None = None) -> List[AgentBelief]:
        """Return beliefs about agents likely to be nearby (recently seen at this location/ward)."""

    def get_belief_about_agent(self, agent_id: str) -> AgentBelief | None:
        """Return the belief record for a given agent, if any."""

    def get_facility_belief(self, facility_id: str) -> FacilityBelief | None:
        """Return the belief record for a given facility, if any."""

    def get_safe_facilities(self, min_safety: float, min_access: float) -> List[FacilityBelief]:
        """Return facilities above given safety/access thresholds."""

    def get_high_credibility_rumors(self, min_credibility: float) -> List[Rumor]:
        """Return rumors deemed credible enough to act upon."""
```

The decision rule can use these to:

- Avoid facilities deemed unsafe.
- Prefer facilities where `perceived_access` is high.
- Avoid or stalk agents based on `suspicion`, `threat`, and `affinity`.
- Act on rumors (e.g. seek opportunities, avoid crackdowns).

---

# 9. Integration with Actions (D-AGENT-0004)

The following actions are primary drivers of perception & memory:

1. **OBSERVE_AREA**
   - Calls `world.get_visible_state(...)` → `PerceptionSnapshot`.
   - Then calls `agent.memory.update_from_observation(snapshot)`.

2. **TALK_TO_AGENT**
   - `world.process_conversation(...)` generates `ConversationEvent` for each participant.
   - Each agent calls `agent.memory.update_from_conversation(event)`.

3. **MOVE_TO_FACILITY / MOVE_WITHIN_FACILITY / PERFORM_JOB / REQUEST_SERVICE**
   - On success, runtime should call helper hooks:
     - `memory.note_facility_visit(facility_id, tick, outcome)` to adjust safety/access.
     - `memory.adjust_suspicion` / `adjust_affinity` for agents involved in positive/negative interactions.

### 9.1 Helper hooks

```python
class Memory:
    ...

    def note_facility_visit(self, facility_id: str, tick: int, outcome: str) -> None:
        """
        Update facility belief based on a visit outcome.

        outcome examples:
        - "SERVED_MEAL"
        - "DENIED_ENTRY"
        - "ATTACKED"
        - "SHELTERED"
        """
```

Runtime defines mapping from `outcome` → deltas to `perceived_safety`, `perceived_access`.

---

# 10. Roadmap & Extensions

Future docs will extend this base:

- **D-AGENT-0006_Skills_and_Learning_v0**
  - Modulate perception (what gets seen) and memory (how much is stored/forgotten) via skills:
    - e.g. `Perception`, `Recall`, `Paranoia`, `Streetwise`.
  - Introduce learning curves based on repeated exposures and job tasks.

- **D-AGENT-0007_Rumor_and_Gossip_Dynamics_v0**
  - Implements the multi-point rumor framework already discussed (loyalty as long-term self-interest, safe rumor zones, etc.).
  - Builds on `Rumor` structure and conversation hooks defined here.

- **World-level geometry & FOV doc (TBD)**
  - Formalizes **vision cones**, occlusion, and stealth.
  - Defines parameters for `radius`, `mode`, and noise in `PerceptionSnapshot`.

The v0 Perception & Memory system in this document aims to be stable enough that Codex implementations can be **extended, not discarded**, as Dosadi’s cognitive layer grows more sophisticated.

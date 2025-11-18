---
title: Admin_Debug_Dashboard_Overview_v0
doc_id: D-INTERFACE-0001
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-RUNTIME-0001   # Simulation_Timebase
  - D-AGENT-0000     # Agent_System_Overview_v1
  - D-AGENT-0001     # Agent_Core_Schema_v0
  - D-AGENT-0002     # Agent_Decision_Rule_v0
  - D-AGENT-0003     # Agent_Drives_v0
  - D-AGENT-0004     # Agent_Action_API_v0
  - D-AGENT-0005     # Perception_and_Memory_v0
  - D-AGENT-0006     # Skills_and_Learning_v0
  - D-AGENT-0007     # Rumor_and_Gossip_Dynamics_v0
---

# 1. Purpose

This document defines the **Admin / Debug Dashboard** interface for the Dosadi simulation.

The goal is to provide a **developer-only “god view”** that can:

- Inspect **world state** at multiple zoom levels (world → ward → facility → agent).
- Explain **why agents act the way they do** (decision traces, drives, beliefs).
- Surface **aggregates and metrics** for testing and tuning.
- Allow **controlled interventions** (spawn agents, trigger events) in later versions.

This doc focuses on the **logic and data contracts** (snapshots, APIs) that other tools
(Jupyter notebooks, CLI tools, web dashboards, or in-engine overlays) can use.

Player-facing UI is explicitly **out-of-scope** for this document.

---

# 2. Non-Goals & Constraints

## 2.1 Non-goals

This interface is **not** intended to:

- Provide polished UX or player-friendly visuals.
- Serve as a secure, multi-user admin tool.
- Enforce permissions, access control, or full audit logging (that’s for law/info_security pillars).
- Describe low-level rendering (HTML/React, Unity UI, etc.).

## 2.2 Constraints

- **Read-first, write-later**:
  - v0 focuses on *read-only* snapshots and logs for debugging.
  - Simple world manipulations may be added later (e.g. spawn agent, tweak param) as explicit, separate APIs.

- **Low coupling**:
  - World + agents expose **stable snapshot functions**.
  - Multiple admin UI implementations can be built on top (CLI, notebook, web).

- **Tick-aware**:
  - Snapshots are **tagged by tick** (per D-RUNTIME-0001).
  - Admin queries should not mutate state.

- **Performance aware**:
  - Snapshots may be **partial or sampled** in large simulations.
  - The interface should support optional “filter” parameters to limit scope.

---

# 3. Concept: Three Zoom Levels

Admin inspection is organized into three conceptual zoom levels:

1. **World / Ward view (macro)**  
   - Global time, sim controls, ward-level aggregates.
2. **Facility / Queue view (meso)**  
   - Status of key facilities (soup kitchens, bunkhouses, checkpoints).
3. **Agent inspector (micro)**  
   - Deep introspection into a single agent’s drives, memory, skills, rumors, and decisions.

The logic API reflects this structure via distinct snapshot types.

---

# 4. Snapshot Data Structures

This section defines the **read-only data structures** the world should expose.
Actual implementation types can be dataclasses, Pydantic models, or plain dicts, but
their fields should match the shapes below.

## 4.1 WorldSnapshot (macro)

Represents a high-level snapshot of the world at a given tick.

```python
@dataclass
class WardSummary:
    ward_id: str
    name: str
    population_tier1: int          # number of "ordinary" agents
    population_tier2_plus: int     # higher-tier actors
    avg_hunger: float              # 0..1
    avg_fear: float                # 0..1
    avg_fatigue: float             # 0..1
    enforcement_level: float       # 0..1 (effective)
    recent_events_count: int       # events in last N ticks (crackdowns, shortages, etc.)


@dataclass
class WorldSnapshot:
    tick: int
    total_agents: int
    total_facilities: int
    ward_summaries: list[WardSummary]
    global_metrics: dict[str, float]  # e.g. {"avg_hunger": ..., "avg_fear": ...}
```

### Required world function

```python
def snapshot_world_state() -> WorldSnapshot:
    ...
```

Notes:

- `ward_summaries` are the primary feed for world/ward dashboards and heatmaps.
- `global_metrics` are a flexible bucket for tracking experiment-level stats.

---

## 4.2 WardSnapshot & FacilitySnapshot (meso)

### 4.2.1 FacilitySnapshot

Represents key facilities within a ward from an admin perspective.

```python
@dataclass
class FacilitySnapshot:
    facility_id: str
    ward_id: str
    name: str
    kind: str                     # e.g. "SOUP_KITCHEN", "BUNKHOUSE", "GARRISON", "OFFICE"
    capacity: int                 # max occupancy or service capacity
    current_occupancy: int        # inside count
    queue_length: int             # waiting outside / in queue
    enforcement_presence: float   # 0..1
    recent_events: list[str]      # human-readable event labels for last N ticks
```

### 4.2.2 WardSnapshot

Describes a single ward, including its facilities and basic aggregates.

```python
@dataclass
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
    facilities: list[FacilitySnapshot]
    # Optional additional aggregates for debugging:
    metrics: dict[str, float]     # e.g. "arrests_last_100_ticks", "jobs_completed"
```

### Required world function

```python
def snapshot_ward(ward_id: str) -> WardSnapshot:
    ...
```

Notes:

- This snapshot is used for:
  - Facility/queue dashboards,
  - Quick scanning of hot spots in a ward.

---

## 4.3 AgentDebugSnapshot (micro)

Central structure for agent-level introspection, combining multiple agent pillar docs.

```python
@dataclass
class DriveStateDebug:
    hunger: float
    thirst: float
    fatigue: float
    fear: float
    ambition: float
    loyalty: float
    curiosity: float
    # Additional drives can be added as needed.


@dataclass
class DecisionTraceEntry:
    tick: int
    chosen_action_kind: str
    chosen_action_payload: dict[str, Any]
    survival_score: float
    long_term_score: float
    risk_score: float
    skill_success_prob: float
    # Optional: truncated list of candidate actions for deep dives
    top_candidates: list[dict[str, Any]]  # {kind, payload, total_score} per candidate


@dataclass
class RumorDebugEntry:
    rumor_id: str
    topic_token: str
    credibility: float
    times_heard: int
    first_heard_tick: int
    last_heard_tick: int
    payload_summary: str   # short string based on payload (e.g. "CRACKDOWN@W12 soon")


@dataclass
class KnownAgentDebug:
    other_agent_id: str
    affinity: float
    suspicion: float
    threat: float
    last_seen_tick: int
    faction: str | None
    role: str | None


@dataclass
class KnownFacilityDebug:
    facility_id: str
    ward_id: str
    perceived_safety: float
    perceived_usefulness: float
    last_visited_tick: int
    tags: list[str]  # e.g. ["SOUP", "SAFE_AT_NIGHT"]


@dataclass
class SkillDebugEntry:
    skill_id: str
    rank: int
    xp: float
    xp_to_next: float
    last_used_tick: int | None


@dataclass
class AgentDebugSnapshot:
    tick: int
    agent_id: str
    name: str | None
    ward_id: str
    facility_id: str | None
    role: str | None          # e.g. "PATRON", "GUARD", "STAFF"
    faction: str | None
    caste: str | None

    # State
    health: float             # 0..1
    hunger: float             # 0..1
    thirst: float             # 0..1
    fatigue: float            # 0..1

    # Drives and decision context
    drives: DriveStateDebug
    last_decision: DecisionTraceEntry | None
    recent_decisions: list[DecisionTraceEntry]

    # Memory / social graph
    known_agents: list[KnownAgentDebug]
    known_facilities: list[KnownFacilityDebug]
    rumors: list[RumorDebugEntry]

    # Skills
    skills: list[SkillDebugEntry]
```

### Required world function

```python
def snapshot_agent_debug(agent_id: str, max_history: int = 10) -> AgentDebugSnapshot:
    ...
```

Notes:

- `recent_decisions` is a sliding window (e.g. last 10 ticks) to keep data manageable.
- This snapshot is intentionally **denormalized** and verbose for human debugging.

---

# 5. Admin API (Read-Only, v0)

From a tooling perspective, we want a simple, stable **read-only admin API**.

## 5.1 Python-level interface

Recommended location: `interfaces/admin_debug.py` (or similar).

```python
# Macro
def snapshot_world_state() -> WorldSnapshot: ...
def snapshot_ward(ward_id: str) -> WardSnapshot: ...

# Meso
def snapshot_facility(facility_id: str) -> FacilitySnapshot: ...
# (Optional convenience; facility data is also visible via WardSnapshot.)

# Micro
def snapshot_agent_debug(agent_id: str, max_history: int = 10) -> AgentDebugSnapshot: ...
```

These functions should be:

- **Side-effect free** (no simulation mutation).
- **Cheap enough** to call at debugging cadences:
  - e.g. every N ticks for world snapshots,
  - on-demand for agent snapshots.

## 5.2 Optional HTTP / JSON interface

When you want a web dashboard, expose a thin HTTP layer over these functions, e.g.:

- `GET /admin/world` → `WorldSnapshot`
- `GET /admin/ward/{ward_id}` → `WardSnapshot`
- `GET /admin/agent/{agent_id}` → `AgentDebugSnapshot`
- Optional filters:
  - `?max_history=5`
  - `?metrics=...` or `?compact=true`

The **schema** should remain aligned with the dataclasses above; transport details are flexible.

---

# 6. Logging & Event Streams

In addition to snapshots, the admin system benefits from **structured logs** for:

- Anomalies,
- Rare decisions,
- Rumor resolution,
- Critical events.

## 6.1 Event types (suggested)

Examples:

- `AGENT_DECISION`  
  `tick, agent_id, chosen_action_kind, total_score, hunger, fear, facility_id`

- `RUMOR_SPREAD`  
  `tick, speaker_id, listener_id, rumor_id, topic, credibility_before, credibility_after`

- `RUMOR_RESOLVED`  
  `tick, rumor_id, resolved_true, affected_agent_ids[]`

- `FACILITY_EVENT`  
  `tick, facility_id, event_type="CRACKDOWN" | "SHORTAGE" | "FIGHT"`

- `AGENT_DEATH` / `AGENT_DETAINED`  
  `tick, agent_id, cause, facility_id`

## 6.2 Log transport

v0 recommendation:

- Write to a structured log (e.g. JSONL file, or in-memory ring buffer).
- Provide simple hooks:

```python
def get_recent_events(event_type: str | None = None, limit: int = 100) -> list[dict]:
    ...
```

This lets notebooks or dashboards:

- Show a **local event stream** for a ward or facility.
- Filter for specific debugging scenarios (“show all RUMOR_RESOLVED events in last 1000 ticks”).

---

# 7. Minimal Usable Slice (v0)

To keep scope sane, v0 Admin Debug should target:

1. **WorldSnapshot + WardSnapshot**
   - Enough to render:
     - tick,
     - ward list with populations and avg hunger/fear,
     - key facilities per ward with queues and occupancy.

2. **AgentDebugSnapshot (reduced)**
   - At minimum:
     - location, role, faction,
     - drives,
     - last decision (with scores),
     - top 5 known_agents & known_facilities,
     - top 5 rumors by credibility.

3. **Basic logging**
   - `AGENT_DECISION` for a sampled subset of agents,
   - `RUMOR_SPREAD` for rumor-based TALK events,
   - `FACILITY_EVENT` for crackdowns and shortages.

With these, you can:

- Open a notebook or simple CLI tool,
- Pull snapshots,
- Inspect “weird” agents,
- See whether decision rules and rumors are behaving plausibly.

---

# 8. Integration Points & Future Extensions

## 8.1 Integration hooks

To support this interface, the world should:

- Keep lightweight **aggregates** per ward:
  - running sums of drives, population counts, event counts.
- Maintain **decision_trace** per agent:
  - a small ring buffer storing `DecisionTraceEntry`.
- Expose **read-only views** for:
  - `known_agents`, `known_facilities`, `rumors`, `skills`.

## 8.2 Potential v1+ extensions

- **Admin interventions**:
  - Spawn/delete agent,
  - Force rumor injection,
  - Trigger crackdown or shortage event,
  - Adjust parameters (time-limited overrides).

- **Visualization helpers**:
  - Precomputed heatmaps (2D grid arrays per ward),
  - Graph representations of rumor networks or faction networks.

- **Replay / time travel**:
  - Checkpointing snapshots for replay of specific ticks/episodes.
  - Useful for debugging rare failures or emergent scenarios.

---

# 9. Summary

D-INTERFACE-0001 defines:

- The **snapshot contracts** and basic admin APIs that any debugging UI can use.
- A clear separation between:
  - **core simulation logic** (world, agents) and
  - **dev tooling** (dashboards, notebooks, logs).
- A concrete path for:
  - Quick CLI / notebook tools first,
  - Later richer web or in-engine dashboards,
  - Without refactoring core systems.

This doc should be used by Codex and future-you as the **reference** when:

- Adding new debug fields to agents or wards,
- Building new admin surfaces,
- Ensuring all tools speak the same “debug language” about the simulation.

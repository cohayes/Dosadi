---
title: Queue_Mechanics_MVP
doc_id: D-RUNTIME-0202
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-01
depends_on:
  - D-RUNTIME-0001  # Simulation_Timebase
  - D-RUNTIME-0200  # Founding_Wakeup_MVP_Runtime_Loop_v0
  - D-SCEN-0001     # Wakeup_Scenario_Prime_v0
  - D-WORLD-0100    # Habitat_Layout_Prime_v0
  - D-AGENT-0020    # Unified_Agent_Model_v0
  - D-AGENT-0022    # Agent_Goal_Stack_MVP_v0
  - D-MEMORY-0102   # Episode_Data_Structures_and_Buffers_v0
  - D-MEMORY-0203   # Episode_Scoring_and_Defaults_v0
  - D-MEMORY-0204   # Episode_Tag_Catalog_MVP_v0
---

# 02_runtime · Queue Mechanics MVP v0 (D-RUNTIME-0202)

## 1. Purpose & Scope

This document specifies the **minimum viable queue mechanics** used in the
Founding Wakeup and early Golden Age baseline:

- What a queue is as a runtime object.
- How agents join, wait, and are processed.
- How queue ticks are scheduled relative to movement and decision ticks.
- How queue outcomes are translated into episodes using the EpisodeFactory and
  QueueEpisodeEmitter.

The goal is to support:

- Wakeup Scenario Prime (D-SCEN-0001):
  - suit issue queue,
  - assignment queue,
  - optional med triage and exception queues.
- A clean bridge between **world topology** (D-WORLD-0100),
  **agent goals** (D-AGENT-0022), and **episodic memory** (D-MEMORY-0102/0204).

This is a **design/runtime spec**. Implementation details (module names, minor
types) can vary as long as behavior matches this document.

---

## 2. Queue Data Model

### 2.1 QueueState

Each logical queue is represented by a `QueueState` record with at least:

- `queue_id: str`
  - Stable id, e.g. `queue:suit-issue`, `queue:assignment`.
- `location_id: str`
  - Node id where the queue line actually forms, e.g.
    - `queue:suit-issue:front`,
    - `queue:assignment:front`.
- `associated_facility: Optional[str]`
  - Facility that services the queue (if any), e.g. `fac:suit-issue-1`.
- `priority_rule: QueuePriorityRule`
  - Enum controlling ordering (see §2.2).
- `processing_rate: int`
  - Number of **agents per process cycle** the queue can service.
- `process_interval_ticks: int`
  - Minimum ticks between processing steps for this queue (e.g. 100 ticks).
- `state: QueueLifecycleState`
  - ACTIVE / PAUSED / CANCELED.
- `agents_waiting: List[AgentID]`
  - Ordered list representing the current line.
- `stats` (optional v0):
  - `total_processed`, `total_denied`,
  - rolling `avg_wait_ticks`, `max_wait_ticks`,
  - used later by Tier-3 pattern readers.

Queues live in a runtime registry (e.g. `WorldState.queues`), keyed by `queue_id`.

### 2.2 PriorityRule & LifecycleState

MVP enums:

- `QueuePriorityRule`:
  - `FIFO` — simple time-based first-in-first-out.
  - `SEVERITY` — used for med triage; higher severity → earlier service.
  - `ROLE_BIASED` — used for assignment or suit queues; critical roles get a
    small priority bonus.
- `QueueLifecycleState`:
  - `ACTIVE` — normal operation.
  - `PAUSED` — no processing; agents can still be waiting.
  - `CANCELED` — queue is shut down; agents should be flushed with `queue_canceled`
    episodes and removed.

The MVP implementation only needs `FIFO` and `ACTIVE`; others can be added as
stubs and fleshed out later.

### 2.3 Per-agent Queue Tracking

Each agent’s participation in queues is tracked by:

- `AgentState` having at most **one active queue membership** at a time:
  - `current_queue_id: Optional[str]`,
  - `queue_join_tick: Optional[int]`.

Rules:

- An agent with `current_queue_id is not None` is considered “in line” and
  will not auto-join another queue until they leave or are processed.
- `queue_join_tick` is used to compute wait times for stats and, optionally,
  goal relevance for episodes.

Implementation MAY also keep a reverse map in `QueueState` from `agent_id` to
join metadata, but `queue_join_tick` is sufficient for MVP.

---

## 3. Queue Lifecycle

### 3.1 Joining a Queue

An agent **joins** a queue when all of the following hold:

1. Agent’s active goal suggests this queue as a means to progress, e.g.:
   - `Goal(kind="get_suit", target_location_id="fac:suit-issue-1")` →
     join `queue:suit-issue`.
2. Agent is physically located at or adjacent to the queue’s `location_id`:
   - e.g. agent at `queue:suit-issue:front`.
3. `QueueState.state == ACTIVE`.
4. Agent is not already in a queue (`current_queue_id is None`).

Joining logic:

- Append agent to `QueueState.agents_waiting` (subject to capacity checks, if
  such exist in the world model).
- Set on `AgentState`:
  - `current_queue_id = queue_id`,
  - `queue_join_tick = current_tick`.

If the queue has a **hard capacity**, and adding another agent would exceed it,
the agent is **refused entry**; this can later result in an episode
(`queue_denied` with `channel=DIRECT`) or a different behavior depending on
scenario.

### 3.2 Processing a Queue (Serve/Denied)

At most once per `process_interval_ticks` for a given queue:

1. Determine **eligible agents**:
   - `waiting = QueueState.agents_waiting`.
   - Optionally filter out agents who have left the location or become invalid.
2. Rank the waiting agents according to `priority_rule`:
   - `FIFO`:
     - preserve the order in `agents_waiting` (assumed by insertion time).
   - `SEVERITY`:
     - sort by a severity key (e.g. health flags) descending.
   - `ROLE_BIASED`:
     - sort by `(role_priority, join_index)` where `role_priority` is derived
       from role/skill tags and `join_index` preserves FIFO fairness.
3. Select up to `processing_rate` agents from the front of the ranked list:
   - `served_agents` = first N,
   - `remaining_agents` = rest.
4. For each `served_agent`:
   - Remove from `agents_waiting`,
   - Clear `current_queue_id` and `queue_join_tick` on `AgentState`,
   - Apply queue-specific **service effect** (e.g. mark suit as acquired,
     assign job/bunk, etc.),
   - Trigger appropriate episodes via `QueueEpisodeEmitter.queue_served(...)`.
5. For agents not selected but still waiting:
   - They remain in `agents_waiting` for next processing cycle.

In MVP, **denials** are triggered only by explicit conditions:

- queue runs out of required resource (e.g. no suits left),
- queue state is changed to `CANCELED`,
- or a scenario-specific rule (e.g. agent is ineligible).

Denials are handled in §3.3.

### 3.3 Cancellations & Denials

**Cancellation**: when `QueueState.state` transitions to `CANCELED`:

- All agents in `agents_waiting`:
  - are removed,
  - have `current_queue_id` and `queue_join_tick` cleared,
  - receive `queue_canceled` episodes via the emitter.

**Denial**: when an individual agent cannot be served normally, but the queue
remains operational, e.g.:

- Suit queue: no suits remaining when an agent reaches the front.
- Assignment queue: failure to assign due to policy or configuration.

Denial handling:

- Agent is removed from `agents_waiting`,
- `current_queue_id` and `queue_join_tick` cleared,
- `QueueEpisodeEmitter.queue_denied(...)` is called for that agent,
- Agent’s goals may be updated (e.g. new sub-goal to seek help, or to rejoin
  after some time) — outside the scope of this document.

### 3.4 Leaving or Abandoning a Queue

Agents may **leave** a queue voluntarily or under behavior rules (e.g.
impatience, panic). MVP support:

- Agent explicitly decides to `LEAVE_QUEUE` (behavior policy), which sets:
  - `current_queue_id = None`,
  - `queue_join_tick = None`,
  - removes them from `QueueState.agents_waiting` if present.
- No episode is required for leaving in v0; later we may add tags like
  `queue_abandoned` or frustration-related episodes.

---

## 4. Runtime Cadence & Integration

### 4.1 Tick Types

To keep the runtime manageable and extensible, we define **conceptual cadences**
(D-RUNTIME-0200 gives broader context):

- **Movement ticks**:
  - Agents can move along edges (`Location` graph) every `movement_interval_ticks`
    (e.g. every 10 ticks).
- **Decision ticks**:
  - Agents evaluate goals and choose actions (including `JOIN_QUEUE` or `LEAVE_QUEUE`)
    every `decision_interval_ticks` (e.g. every 50–100 ticks).
- **Queue processing ticks**:
  - Each queue processes at most once every `process_interval_ticks` as per its
    configuration (e.g. 100–200 ticks).

In code, a single global `tick` can drive all of these, with modulo checks:

```python
if tick % movement_interval_ticks == 0:
    step_agent_movement(world, tick)

if tick % decision_interval_ticks == 0:
    step_agent_decisions(world, tick)

if tick % queue_interval_ticks == 0:
    process_all_queues(world, tick)
```

Queue processing MAY have its own interval, or share the decision cadence if
that simplifies implementation.

### 4.2 `process_all_queues` and `process_queue`

MVP runtime helpers:

- `process_all_queues(world: WorldState, tick: int) -> None`:
  - Iterate over all queues in `world.queues.values()`:
    - If the queue is `ACTIVE` and
      `tick - queue.last_processed_tick >= queue.process_interval_ticks`:
      - call `process_queue(world, queue, tick)`.

- `process_queue(world: WorldState, queue: QueueState, tick: int) -> None`:
  - Implements the steps in §3.2 and §3.3:
    - selects eligible `served_agents` (and optionally `denied_agents`),
    - applies queue-specific side effects (resource changes, assignments),
    - uses `QueueEpisodeEmitter` to emit `queue_served`/`queue_denied`/`queue_canceled` episodes,
    - updates `queue.last_processed_tick`.

All queue-specific policy (suit stock, assignment logic) should be implemented
in **queue-type-specific helpers**, called by `process_queue`.

---

## 5. Queue Policies by Type (MVP)

This section sketches the **queue-specific** side effects expected in Wakeup
Scenario Prime (D-SCEN-0001). Implementation can be partial; suit and
assignment queues are the highest priority.

### 5.1 Suit Issue Queue (`queue:suit-issue`)

- **Purpose**:
  - Agents in this queue seek to acquire a basic personal suit.
- **Priority**:
  - `priority_rule = FIFO` in MVP.
- **Processing**:
  - For each `served_agent`:
    - If suit stock is available:
      - decrement suit stock,
      - mark agent as having `has_basic_suit = True`,
      - progress/complete the `get_suit` goal,
      - emit `queue_served` via `QueueEpisodeEmitter.queue_served(...)`.
    - Else:
      - treat as **denied** (see §3.3),
      - emit `queue_denied`.

### 5.2 Assignment Queue (`queue:assignment`)

- **Purpose**:
  - Assign roles, bunks, and initial ration entitlements.
- **Priority**:
  - MVP: `priority_rule = FIFO`.
  - Future: `ROLE_BIASED` can give mild preference to critical-skill colonists.
- **Processing**:
  - For each `served_agent`:
    - Assign a work role (can be random or affinity-weighted),
    - Assign a bunk (map to one of `pod:*`),
    - Set ration band fields for the agent (if modeled),
    - mark `get_assignment`/`secure_bunk` goals as progressed/completed,
    - emit `queue_served`.

### 5.3 Med Triage Queue (`queue:med-triage`)

- **Purpose**:
  - Handle agents with apparent health anomalies after wake.
- **Priority**:
  - `priority_rule = SEVERITY`.
- **Processing** (MVP stub):
  - For each `served_agent`:
    - Run a simple health check / flag update,
    - Potentially assign med-related goals or limitations,
    - Optionally emit episodes (in later versions) tied to med outcomes.

### 5.4 Exception Queue (`queue:exception`)

- **Purpose**:
  - Manage disruptive agents via holding area / discipline.
- **Priority**:
  - Implementation-dependent; MVP can leave as `FIFO`.
- **Processing** (MVP stub):
  - For each `served_agent`:
    - Keep them in `fac:holding-1` for a time, apply mild penalties,
    - Future integration with guard/steward episodes:
      - `guard_help`, `guard_brutal`, `steward_unfair`.

In MVP, med and exception queues MAY be partially or fully stubbed (with no
side effects beyond wait/placement). Suit and assignment queues are required
for a functional wakeup pipeline.

---

## 6. Queue Episodes Integration

Queue mechanics are the **primary** source of the following episode tags in
the early game (D-MEMORY-0204):

- `queue_served`
- `queue_denied`
- `queue_canceled`
- `queue_fight`

Implementation uses the helper introduced previously:

- `QueueEpisodeEmitter` in `dosadi.runtime.queue_episodes` (or similar).

### 6.1 Emission Sites

Episodes should be emitted:

- In `process_queue`:
  - For each **served** agent:
    - call `queue_episode_emitter.queue_served(...)`.
  - For each **denied** agent:
    - call `queue_episode_emitter.queue_denied(...)`.
- In queue cancellation logic:
  - When `QueueState.state` transitions to `CANCELED`:
    - call `queue_episode_emitter.queue_canceled(...)` with all affected agents.
- In conflict handling logic near queues:
  - When a fight or serious altercation occurs at a queue’s `location_id`:
    - call `queue_episode_emitter.queue_fight(...)` with:
      - `involved_agents`,
      - `observers` (everyone else in line and possibly nearby corridor).

### 6.2 Observers & Location

For all queue episodes:

- `queue_location_id` SHOULD be the queue’s `location_id`, e.g.
  - `queue:suit-issue:front`.
- **Observers**:
  - At minimum, all other agents in `QueueState.agents_waiting` at that moment.
  - Optionally, agents in adjacent corridor nodes (e.g. `corr:suit`) can be
    included as observers for fights and cancellations.

The EpisodeFactory (D-MEMORY-0203) will:

- Set `importance`, `reliability`, and `emotion` fields,
- Annotate episodes with owner’s current goal and `goal_relevance`.

---

## 7. Implementation Notes & Constraints

- Queue mechanics should be implemented in **runtime** modules (e.g.
  `dosadi.runtime.queues`), not inside scenario builders or world layout code.
- Wakeup Scenario Prime (D-SCEN-0001) should only:
  - construct initial queues (with ids, locations, and configs),
  - seed agent goals and positions,
  - leave behavior to the runtime.
- All hard-coded ids MUST match:
  - D-WORLD-0100 (locations),
  - D-SCEN-0001 (queue ids),
  - D-MEMORY-0204 (episode tags).

Future extensions (not required for MVP):

- multi-lane queues,
- queue splitting / merging,
- dynamic priority rules based on protocols,
- Tier-3 protocol edits that change `processing_rate` or `priority_rule`,
- queue metrics flowing into Tier-3 “pattern-of-patterns” analysis.

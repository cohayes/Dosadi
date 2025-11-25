---
title: Episode_Schema_and_Memory_Behavior
doc_id: D-MEMORY-0002
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-MEMORY-0001  # Episode_Management_System_v0
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0006   # Agent_Attributes_and_Skills_v0
  - D-AGENT-0023   # Agent_Goal_System_v0
---

# 15_memory · Episode Schema and Memory Behavior v0 (D-MEMORY-0002)

## 1. Purpose & Scope

This document specifies:

1. A **conceptual schema** for episodes as the core memory unit in Dosadi.
2. How episodes are:
   - encoded into an agent's personal memory,
   - reinforced or weakened over time,
   - decayed and compressed into **patterns**,
   - with these processes concentrated in **rest cycles** (sleep / downtime).
3. How personal patterns shape:
   - an agent's perception of **places**, people, and protocols,
   - and, at higher tiers, auditor expectations of what is "normal" or
     "unusual" in records.

This is a **conceptual behavior spec**. Numerical weights and concrete data
structures are left for implementation documents.

D-MEMORY-0002 assumes the episode framework in D-MEMORY-0001 and the goal
system in D-AGENT-0023.

---

## 2. Episode Schema (Conceptual)

### 2.1 Core Episode Fields

At minimum, an episode represents a **meaningful attempt to pursue a goal in
context** and its outcome.

A canonical episode structure includes:

- **episode_id**
  - unique identifier (local or global).

- **time**
  - simulation tick or time range when the episode occurred.

- **location_ref**
  - reference to where this took place:
    - ward / zone / corridor / facility / pod, etc.

- **actors**
  - primary agent(s) involved:
    - `subject_agent_id` (initiator / focal agent),
    - `other_agent_ids` (allies, opponents, bystanders).

- **goal_link**
  - which goal the subject agent believed they were pursuing:
    - reference to an active goal instance (D-AGENT-0023),
    - or `None` for incidental/ambient experiences (e.g. witnessing a riot).

- **context_snapshot**
  - minimal subset of world state relevant to the decision:
    - environment: heat band, contamination, sealed/unsealed, etc.
    - social: crowd size, local authority presence, CI stance, pod tensions.
    - resource: ration availability, water level, work quotas, etc.

- **actions_taken**
  - list of key actions or decisions by the subject agent:
    - skill checks (e.g. Oratory, Negotiation, Suit_Maintenance),
    - protocol references (which protocol they followed or defied),
    - notable deviations ("ignored line order", "bypassed safety step").

- **outcome**
  - categorical summary plus optional rich detail:
    - label: success / partial_success / failure / catastrophe,
    - consequences: changes in status, injuries, resource gains/losses,
      suspicion, promotions, punishments.

- **salience_scores**
  - internal impact scores for the subject agent:
    - emotional intensity (fear, pain, pride, humiliation),
    - novelty (first time vs common pattern),
    - goal relevance (how closely it touched a high-priority goal).

- **source & reliability**
  - where this episode comes from for a given agent:
    - `source`: self_experience / archive / rumor / protocol_story / visual_mark,
    - `reliability`: internal belief about its accuracy (dynamic, not fixed).

- **tags**
  - simple labels for fast indexing:
    - e.g. `"food_hall"`, `"exo_bay"`, `"shaft_9"`, `"patrol_B"`,
      `"queue_conflict"`, `"ration_shortfall"`, `"purge_rumor"`.

This schema is shared across **personal memory**, **archives**, and **rumor
projections**, though not all fields will be filled at all times.

### 2.2 Extended Fields (Optional)

Additional fields may be added as needed:

- **protocol_trace**
  - which protocol(s) were activated or relevant,
  - whether the agent followed or deviated from them.
- **auditor_annotations**
  - later commentary by Tier-2/3 observers (e.g. safety officers, clerks).
- **visual_marker_ref**
  - links to graffiti, posters, or signage associated with this episode
    (e.g. a warning symbol painted near a corridor after a collapse).
- **linkage**
  - relationships to other episodes:
    - part_of (larger incident),
    - response_to (retaliation, follow-up),
    - precursor_of (lead-up to later crisis).

These fields primarily matter for higher-tier analysis and later phases of
development.

---

## 3. Agent-Level Memory Store

Each agent maintains a **personal memory store**: a limited, noisy subset of
episodes and patterns that they can recall and use when choosing actions.

### 3.1 Memory Contents

At any given time, an agent's memory can be thought of as containing:

1. **Raw episodes**
   - relatively detailed records of specific events the agent experienced
     directly or internalized from trusted channels.

2. **Compressed patterns / beliefs**
   - summaries like:
     - "Food hall K is risky at night."
     - "Patrol_B is more violent than Patrol_C."
     - "Shaft 9 is unsafe under high heat and minimal crew."
   - encoded as parameterized rules derived from many similar episodes.

3. **Pointers to external memory**
   - knowledge that:
     - "This journal page contains the detail I need."
     - "The pod's wall chart tracks our water debt."
   - allows the agent to act as if they remember more than they hold
     internally, by retrieving it from logs when needed.

### 3.2 Memory Capacity & Pressure

Agents have **bounded memory capacity**, which may depend on:

- attributes (e.g. INT, WIL),
- personality (inclination to track detail vs live in the moment),
- role (Tier-3 agents often *choose* to shoulder more informational load).

When capacity pressure rises:

- low-salience episodes are dropped more aggressively,
- high-salience episodes and patterns are protected and reinforced,
- some agents turn to **journaling / ledgers** as external storage.

---

## 4. Encoding Episodes (Awake Phase)

When an agent experiences an event, they first create a **fresh episode
candidate**.

### 4.1 Encode Decision

Not every event becomes a stored episode. Encoding depends on:

- **Goal relevance**
  - Events tightly connected to current high-priority goals are favored:
    - survival, kin protection, status, critical work outcomes, etc.

- **Emotional salience**
  - Fear, pain, humiliation, pride, relief, awe all increase encoding
    probability and strength.

- **Novelty**
  - First-time experiences encode more strongly than a 100th repetition,
    unless something disruptive changes.

- **Social framing**
  - If an event is highly discussed in the pod/guild, its significance is
    reinforced:
    - "Everyone is talking about the incident; I *should* remember it."

Episodes that fail to clear a minimal threshold may be immediately discarded
or only encoded as a very low-weight trace.

### 4.2 Initial Strength & Bias

If an episode is encoded, it receives an initial **strength** based on the
factors above.

It can also be encoded with a **bias**:
- If the agent is highly paranoid, the same episode may be remembered as
  more threatening.
- If the agent is highly communal, events involving betrayal or solidarity
  get extra weight.

Initial strength and bias are **starting points**; they will be modified
during rest cycles.

---

## 5. Rest Cycles: Reinforcement, Decay & Compression

To mirror human-like memory, the heavy lifting of memory management occurs
during **rest cycles** (sleep / downtime).

A rest cycle is a period where the agent is not actively acting but their
internal processes can:

- replay recent episodes,
- integrate them with older ones,
- reinforce or weaken patterns,
- forget low-value information.

### 5.1 Rest Cycle Operations

During each rest cycle, an agent's memory runs roughly through:

1. **Replay & reinforcement**
   - Recently encoded episodes are replayed with probability proportional to
     their initial strength.
   - Episodes that align strongly with active or enduring goals are more
     likely to be replayed.
   - Each replay:
     - slightly increases the episode's strength,
     - strengthens or updates associated patterns.

2. **Conflict resolution & weakening**
   - If new episodes contradict existing patterns (e.g. a usually safe food
     hall serves bad rations):
     - the agent may weaken the old pattern,
     - or reinterpret the new episode as an exception, depending on bias.

3. **Decay & pruning**
   - Episodes that:
     - are rarely replayed,
     - have low salience,
     - and are weakly tied to any active goals,
     slowly decay in strength.
   - Once below a threshold, they are either:
     - dropped entirely,
     - or preserved only as part of a compressed pattern.

4. **Compression into patterns**
   - Repeatedly co-occurring episodes (same place, similar context, similar
     outcomes) are clustered into **patterns**:
     - "Corridor 12 near the exo-bay is dangerous at night."
     - "Auditor R is unusually lenient."
   - Concrete parameters emerge:
     - time windows, locations, roles, thresholds (e.g. crowd size above
       which trouble starts).

The overall effect is that **each night** an agent moves:

- from raw experience →
- to durable beliefs about:
  - places (safe, risky, profitable),
  - people (trustworthy, harsh, exploitable),
  - protocols (effective, burdensome, ignorable).

### 5.2 Pattern Emergence & Place Perception

Patterns profoundly shape how agents **perceive places**:

- A corridor with many negative episodes during nights becomes
  "dangerous_at_night" in an agent's map, even if daytime episodes are fine.
- A food hall with consistent fair treatment becomes
  "trusted_ration_source".

Different agents can hold different pattern maps based on:

- where they've been,
- what they've seen,
- what they've heard and believed,
- and which goals they emphasize.

This leads to **heterogeneous subjective maps** of the same physical city.

### 5.3 Auditor Norms & Anomaly Detection

Tier-2 and Tier-3 agents (auditors, stewards) use patterns over **logged
episodes** to build expectations of what is "normal" for:

- a ward or corridor,
- a pod or guild,
- a protocol or process.

During their rest/analysis cycles, they:

- form patterns from archived episodes (e.g. typical ranges of ration
  deviation, injury rates, report frequencies),
- flag individuals or places whose recorded behavior drifts too far from
  those norms.

This makes **anomaly detection** an emergent side-effect of the same
pattern-forming machinery used by ordinary agents, just applied at a
different scale and data volume.

---

## 6. Journals & Externalization of Memory

### 6.1 Motivations for Journaling

Agents whose roles or personalities demand higher fidelity memory may choose
to offload episodes into **external records**:

- council clerks,
- guild recorders,
- meticulous stewards,
- or simply highly conscientious individuals.

Journaling is a deliberate action that trades:

- a short-term cost (time, effort, possible risk if writing sensitive
  material),
- for long-term benefits:
  - more accurate recall,
  - ability to share episodes precisely,
  - personal or institutional prestige as a source of truth.

### 6.2 What Gets Journaled

Typically, agents journal:

- **high-impact episodes**:
  - near-misses, major conflicts, protocol changes, important deals.
- **representative samples**:
  - a few typical days to illustrate a pattern,
  - especially for future audits or negotiations.
- **personally significant events**:
  - promotions, betrayals, critical discoveries,
  - episodes involving kin or key allies/enemies.

The journal entries themselves can be thought of as **episode copies or
distillations** stored in an external archive.

### 6.3 Future Extensions (Ciphered Journals)

In late development phases, some journals may be:

- **ciphered or encoded** to protect sensitive patterns:
  - cartel logistics,
  - internal corruption records,
  - blackmail material.

Ciphering does not change the conceptual role of journaling; it only modifies
who can read the episodes. Implementation of cipher systems can be treated as
an extension to the INFO_SECURITY pillar and is **not required** for early
versions of the Episode Management System.

---

## 7. Visual Media as Episodic Anchors

Visual media provide a powerful way to **anchor episodes in place** and
amplify their transmission.

### 7.1 Graffiti, Posters, and Symbols

Examples:

- A skull stencil near a corridor where multiple accidents have occurred.
- A guild emblem marking a territory as "ours".
- A poster urging:
  - "Report hoarders to the council",
  - "Join the garrison",
  - "Trust in the ration board".

These visuals function as:

- prompts that **recall** past episodes for those who know the backstory,
- **compressed carriers** of protocol-like messages ("Don’t go there",
  "Behave like this"),
- signals of control or influence by particular groups.

### 7.2 Visuals in the Episode Schema

An episode may include:

- a **visual_marker_ref** field:
  - referencing graffiti or posted material encountered during the episode,
  - or newly created as a result of the episode.

Visual markers thus become:

- local, persistent artifacts that influence how future agents encode and
  interpret episodes in that area,
- a bridge between **episodic memory** and **place identity** in the world.

---

## 8. Summary & Future Work

D-MEMORY-0002 defines:

- a shared episode schema,
- how agents encode, reinforce, weaken, decay, and compress episodes,
- with rest cycles as the main period for memory maintenance,
- how patterns shape perceptions of places, people, and protocols,
- and how journaling and visual media extend memory beyond the individual.

Future documents SHOULD:

- define a **concrete data representation** for episodes and patterns
  (e.g. Python classes, YAML schemas),
- specify **quantitative rules** for encoding thresholds, decay rates,
  reinforcement strength, and pattern formation,
- integrate episodes and patterns more tightly with:
  - **action selection** (how beliefs are consulted when choosing what to do),
  - **protocol evolution** (how clusters of episodes trigger protocol
    creation or revision),
  - **rumor mechanics** (how episodes are selected, distorted, and broadcast),
  - and **info-security** (who controls archives, journals, and visuals).

D-MEMORY-0002 is the behavioral foundation for all such work: the spine
connecting moment-to-moment experience, long-term belief formation, and the
evolution of Dosadi's institutional memory.

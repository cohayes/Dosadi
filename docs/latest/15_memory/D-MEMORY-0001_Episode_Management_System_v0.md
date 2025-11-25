---
title: Episode_Management_System
doc_id: D-MEMORY-0001
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-24
depends_on:
  - D-AGENT-0001  # Agent_Core_Schema_v0
  - D-AGENT-0006  # Agent_Attributes_and_Skills_v0
  - D-AGENT-0023  # Agent_Goal_System_v0
---

# 15_memory · Episode Management System v0 (D-MEMORY-0001)

## 1. Purpose & Pillar Scope

This document defines the **Episode Management System** that underpins how
Dosadi agents capture, record, store, access, and distribute information
over time.

It establishes:

- **Episodes** as the core memory unit.
- A unified information model with multiple **channels**:
  - personal memory,
  - shared archives,
  - written protocols,
  - and rumors/stories.
- How different **tiers of agents** (1, 2, 3) interact with that shared
  information fabric.
- A high-level development path intended to **survive from early prototypes
  through to final, large-scale simulation**.

This pillar is concerned with the **language of information** in Dosadi:
how reality is turned into records, how those records are compressed into
usable instructions, and how they circulate socially.

---

## 2. Core Concept: The Episode

### 2.1 Definition

The **episode** is the atomic unit of memory in the Dosadi simulation.

At its core, an episode is:

> a structured record of "something that happened" in context.

A minimal episode includes:

- **Context snapshot**
  - relevant world state (location, time, environment conditions),
  - roles/agents involved,
  - salient systemic parameters (stress, security posture, etc.).
- **Intent / goal link**
  - what goal the initiating agent was pursuing, if any.
- **Actions taken**
  - key decisions or actions chosen by the agent(s).
- **Outcome**
  - success / failure / partial success,
  - side-effects and consequences (injury, promotion, suspicion, etc.).
- **Metadata**
  - source (personal experience, archive, rumor),
  - time of recording,
  - reliability flags and tags.

Every time an agent meaningfully pursues a goal (D-AGENT-0023), they create at
least one episode. Episodes are the raw feedstock for **learning**, 
**protocol design**, and **rumor content**.

### 2.2 Single Representation, Multiple Channels

The key design principle:

> One underlying episode representation, many **views** and **channels**.

All of the following are different projections of the same conceptual object:

- **Personal memory**
  - A subset of episodes an agent has experienced or adopted, often compressed
    into gists or heuristics.
- **Archive documents**
  - Episodes stored in a shared, more durable form, often grouped, annotated
    and tagged.
- **Written protocols**
  - Highly distilled patterns derived from many episodes, expressed as
    "if X then do Y" procedures.
- **Rumors and stories**
  - Noisy, biased re-tellings of episodes that move through social networks.

By keeping a single stable episode schema beneath these, the system avoids
splintering into incompatible mechanisms for memory, archives, and rumor.

---

## 3. Tiers as Information Load Profiles

Tiers describe how much information an agent **must handle** and **can handle**
to successfully perform their social role. They all operate over the same
episode substrate, but with different **interfaces**.

### 3.1 Tier-1: Workers & Frontline Actors

Tier-1 agents are the bulk of the population: workers, rank-and-file militia,
clerks, routine service staff.

They primarily interact with:

- **Written protocols** relevant to their current station and task,
- Their own **recent personal episodes** (near misses, successes),
- Local **rumors** and instructions from superiors.

Their decision loop is typically:

1. Read/apply **applicable protocols** for their job.
2. Adjust behavior slightly based on recent, salient personal episodes.
3. Optionally weigh rumors if they strongly contradict lived experience.

Tier-1 agents do **not** query archives directly in most cases and do not need
to carry large precedent libraries in their heads. Their information language
is shallow but broad: protocols + fresh gossip + immediate experience.

### 3.2 Tier-2: Foremen, NCOs, Shift Leads

Tier-2 agents carry responsibility for crews, pods, shifts, or specific
operational domains.

They see everything Tier-1 sees **plus**:

- Aggregated incident logs and **local episode histories** for their domain,
- Limited **archive search** within their remit (e.g. "incidents in shaft 9
  last month").

Their behavior:

- Starts from written protocols,
- Uses additional episode history to **adapt or temporarily override** those
  protocols when reality diverges,
- Generates new logs and incident records that may later influence protocol
  revisions.

Tier-2 roles are the main bridge between raw episodes and stable, institutional
knowledge for a given sector.

### 3.3 Tier-3: Designers, Stewards, Commanders

Tier-3 agents sit atop the informational machinery.

They have access to:

- Broader **archives** across time and space,
- Summary metrics and dashboards,
- Protocol libraries and their justifications (episode sets they were derived
  from).

They:

- Author and revise **protocols**,
- Define or adjust policy and long-horizon goals,
- May trigger investigations or systemic changes based on long-run patterns
  in episodes (e.g. rising accident rates under certain conditions).

Tier-3 roles thus act as **model-builders** and **language designers** for the
rest of the population: they decide which patterns get compressed into
readable steps, and which stay buried in obscure reports.

---

## 4. Written Protocols as an Information DSL

### 4.1 Purpose

Written protocols are the **most visible manifestation** of the episode
management system. They are the wall-posted instructions, checklists, and
SOPs that Tier-1 and Tier-2 agents actually see and follow.

They exist to:

- Convert complex, historical episode patterns into **simple, actionable
  steps**,
- Standardize behavior across many workers without requiring deep historical
  understanding,
- Provide a stable default behavior that is usually good enough and safer
  than improvisation.

### 4.2 Structural Pattern

A protocol is treated as a small **domain-specific language (DSL)** over
current context and available actions.

Canonical shape:

- **WHEN**: conditions on context  
  (task type, environment characteristics, time, location properties,
  security posture, etc.)
- **IF**: safety or exception checks  
  (thresholds exceeded, equipment missing, contradictory orders)
- **THEN**: ordered steps  
  (actions, who executes them, in what sequence)
- **ELSE**: fallback behavior  
  (escalate to supervisor, halt operation, switch to a secondary protocol)

Example pattern (informal):

> WHEN `task_type == "shaft_maintenance"` AND `env.heat > threshold`  
> THEN `reduce crew size`, `extend rest intervals`, `require suit_type >= 2`  
> ELSE `use standard_maintenance_protocol`

Protocols should key off **properties** rather than hard-coded IDs, so they
survive map evolution and ward reconfiguration. For instance, keying to:

- sealed vs unsealed zone,
- contamination level,
- heat/pressure bands,
- garrison presence,

rather than "Ward 07" directly.

### 4.3 Relation to Episodes and Archives

Each protocol is backed by:

- a set of **episodes** that motivated its creation or update,
- commentary or analysis in the archives that explains *why* it exists.

For most agents, protocols are **opaque**: they see the "how" but not the
full "why". Tier-2 and Tier-3 agents can reach deeper:

- Tier-2 may know partial history and adjust on the fly.
- Tier-3 may inspect the underlying episodes and re-author the protocol
  when conditions change.

This gives a clean separation between:

- **usable instruction** (wall poster),
- and **explanatory history** (archive depth).

---

## 5. Rumors & Stories as a Noisy Channel

Rumors and stories represent a **social projection** of episodes.

From the episode management perspective:

- A rumor is a **compressed, biased episode** (or protocol change) traveling
  through the social graph.
- Storytellers select episodes for:
  - emotional punch,
  - social relevance,
  - status value,
  - narrative coherence,
  rather than strict accuracy.

Rumors therefore:

- Expose agents to patterns and warnings **before** archives or protocols
  formally catch up,
- But do so with variable reliability.

The same episode may be visible as:

- a dry incident report in an archive,
- a single line in a protocol revision,
- and a dramatic story about "the time shaft 9 almost killed us all" told in
  a food hall.

Agents weigh rumor evidence differently based on personality and role:

- high-curiosity, high-paranoia agents may give rumors more weight,
- others treat them as background noise unless repeatedly confirmed.

Rumor mechanics are thus a **read-only, noisy API** into the same underlying
episode fabric.

---

## 6. Memory Strategies & Externalization

Agents have limited internal memory and adopt different **memory strategies**
based on attributes, personality, goals, and tier.

Patterns include:

- **Pure internal memory**
  - retain only episodes that strongly support current, high-priority goals,
  - forget most unrelated or low-impact experiences.
- **Journals and logs**
  - high-INT, high-learning or meticulous agents record episodes externally:
    notebooks, ledgers, shift logs, wall charts,
  - these become local or formal **archive entries**.
- **Delegated memory**
  - leaders offload detail to subordinates or protocols,
  - they retain only compressed heuristics ("shaft 9 is fragile; we use
    Protocol B").
- **Bardic / storyteller memory**
  - high-CHA, performance-oriented agents retain episodes with high story
    value,
  - these fuel social performances and rumor propagation and serve as
    another form of externalization (memory as shared narrative).

From the system's viewpoint, these are all different ways of:

- selecting which episodes to retain strongly,
- deciding where to store them (internal vs external),
- and choosing which to **share** or replay.

---

## 7. Development Roadmap for the Episode System

To keep this pillar stable across project phases, the Episode Management
System should develop in modular stages.

### 7.1 Phase A: Personal Episodes Only

- Implement a minimal episode schema:
  - context, action, goal link, outcome, basic tags.
- Agents use episodes only for **personal learning**:
  - adjust future decisions based on their own past successes and failures.

No shared archive, protocols, or rumors are required at this stage.

### 7.2 Phase B: Shared Archive Layer

- Introduce a simple **archive store** of episodes.
- Allow specific roles to:
  - write episodes to the archive (logs, incident reports),
  - read subsets of archived episodes based on domain or queries.

Tier-3-like agents can now reason over patterns that exceed an individual
lifespan or narrow domain of experience.

### 7.3 Phase C: Protocol DSL

- Define a compact protocol representation with WHEN / IF / THEN / ELSE
  structure keyed to world properties.
- Hard-code an initial set of protocols (in e.g. YAML/JSON).
- Tier-1 agents rely primarily on protocols for their task behavior.
- Tier-2 and Tier-3 agents can draft or suggest protocol changes, even if
  early versions are updated manually.

This introduces **institutionalized learning**: episodes → policy → protocol.

### 7.4 Phase D: Rumor Projection

- Implement a mechanism that samples episodes or protocol changes and
  generates **rumor objects**:
  - compressed, biased summaries,
  - attached to agents with specific sharing behaviors.
- Allow agents to incorporate rumor evidence with lower weight and higher
  variance based on personality traits (e.g. credulity, curiosity, paranoia).

This creates a fast, informal channel alongside the slower, formal archive
and protocol channels.

### 7.5 Phase E: Tightening Tier Interfaces

- Make information access explicit per tier:
  - who can read what in the archive,
  - who can see drafts vs final protocols,
  - who can safely spread or interrogate rumors.
- Implement differing **view functions** for each tier, all backed by the
  same episode store and protocol DSL.

### 7.6 Phase F: Optimization & Refinement

- Optimize storage and retrieval strategies for episodes and protocols only
  if needed for scale.
- Maintain **backwards compatibility** for the episode schema and protocol
  DSL so earlier content and behaviors remain valid.

At full maturity, the Episode Management System becomes the backbone of:

- agent learning,
- institutional knowledge,
- standard operating procedures,
- and the rumor/gossip ecology that gives Dosadi its living, unstable feel.

---

## 8. Relation to Other Pillars

This pillar is tightly coupled to:

- **01_agents**
  - episode generation is driven by agent actions, goals, and perceptions.
- **02_runtime / campaign**
  - large-scale patterns of episodes define campaign phases, stress,
    legitimacy, and fragmentation trajectories.
- **08_info_security**
  - control over archives, protocols, and rumor suppression or injection
    defines much of the information power structure.
- **13_industry / MIL / LAW**
  - each sector contributes its own characteristic episodes, protocols, and
    failure modes.

D-MEMORY-0001 should be treated as the **genesis document** for all further
work on memory, learning, archives, protocols, and rumor mechanics in Dosadi.

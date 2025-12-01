---
title: Episode_Tag_Catalog_MVP
doc_id: D-MEMORY-0204
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-MEMORY-0102  # Episode_Data_Structures_and_Buffers_v0
  - D-MEMORY-0203  # Episode_Scoring_and_Defaults_v0
  - D-RUNTIME-0200 # Founding_Wakeup_MVP_Runtime_Loop_v0
  - D-RUNTIME-0201 # Golden_Age_Daily_Rhythms_and_Shifts_v0
  - D-AGENT-0020   # Unified_Agent_Model_v0
---

# 15_memory · Episode Tag Catalog MVP v0 (D-MEMORY-0204)

## 1. Purpose & Scope

This document defines the **initial catalog of episode `summary_tag` values**
used in the Founding Wakeup / early Golden Age MVP. It is the glue between:

- runtime/world events (queues, guards, stewards, protocols, body signals),
- the episodic memory system (`Episode`, `EpisodeBuffers`),
- and the scoring defaults defined in D-MEMORY-0203.

For each tag, we specify:

- a short description,
- typical `EpisodeChannel` values,
- typical `EpisodeTargetType` and what `target_id` should point to,
- the kinds of world events / actions that should emit this tag.

This is an MVP catalog. Additional tags may be defined later as the simulation
gains complexity (e.g. guilds, exo-bays, Well anomalies).

---

## 2. Tag Fields & Conventions

Each tag entry follows this schema:

- **Tag**: the `Episode.summary_tag` string.
- **Description**: short English description.
- **Channels**: typical `EpisodeChannel` values for this tag.
- **Target**:
  - `target_type`: typical `EpisodeTargetType`,
  - `target_id`: what entity identifier should be used (agent, place, faction, etc.).
- **Emitted When**: which world events or agent actions should create episodes
  with this tag.

Tags are **case-sensitive** strings. For MVP, all tags are lowercase with
underscores (e.g. `queue_served`, `guard_brutal`).

---

## 3. Queue & Ration Tags

Early Golden Age daily life revolves around movement and queues for rations
(food, water, basic supplies). These tags cover the most common queue episodes.

### 3.1 `queue_served`

- **Description**: The agent successfully receives rations/services in a queue.
- **Channels**:
  - `DIRECT` (agent is the one served),
  - `OBSERVED` (agent witnesses others being served smoothly).
- **Target**:
  - `target_type`: `PLACE`,
  - `target_id`: queue location or facility id (e.g. `loc:queue-pod-1`).
- **Emitted When**:
  - A queue-processing event awards rations/services to this agent (DIRECT).
  - Optionally, nearby agents who are watching can receive OBSERVED episodes.

### 3.2 `queue_denied`

- **Description**: The agent is denied rations/services at a queue.
- **Channels**:
  - `DIRECT` (primary case),
  - `OBSERVED` (others witness denial).
- **Target**:
  - `target_type`: `PLACE`,
  - `target_id`: queue location id.
- **Emitted When**:
  - A queue-processing event explicitly denies service to this agent
    (no ration, turned away, arrives too late).

### 3.3 `queue_canceled`

- **Description**: A queue is closed or canceled before the agent is served.
- **Channels**:
  - `DIRECT` (agent is in the queue that gets canceled),
  - `OBSERVED` (nearby agents watching the disruption).
- **Target**:
  - `target_type`: `PLACE`,
  - `target_id`: queue location id.
- **Emitted When**:
  - A queue-handling process forcibly ends a queue (e.g. lack of supplies,
    security issue) with agents still waiting.

### 3.4 `queue_fight`

- **Description**: A fight or serious altercation breaks out in or near a queue.
- **Channels**:
  - `DIRECT` (agent personally involved / struck / shoved),
  - `OBSERVED` (agent witnesses the fight).
- **Target**:
  - `target_type`: `PLACE` (primary),
  - `target_id`: queue location id.
- **Emitted When**:
  - A combat/altercation event is triggered within the spatial bounds of
    a queue location or immediately adjacent corridors.

---

## 4. Guard & Steward Behavior Tags

These tags describe how authority figures behave in local interactions. They
are key seeds for PersonBeliefs and FactionBeliefs about legitimacy, brutality,
and trustworthiness.

### 4.1 `guard_help`

- **Description**: A guard assists or protects the agent or another colonist.
- **Channels**:
  - `DIRECT` (agent receives help),
  - `OBSERVED` (agent sees a guard help someone else),
  - `REPORT` (formal report about helpful guard behavior).
- **Target**:
  - `target_type`: `PERSON`,
  - `target_id`: guard agent_id (the helper).
- **Emitted When**:
  - Guard actions explicitly protect the agent (breaking up a fight in their favor,
    escorting them, providing information or aid),
  - OR assist someone else, visible to the observing agent.

### 4.2 `guard_fair`

- **Description**: Guard enforces rules in a clear, consistent, non-cruel way.
- **Channels**:
  - `DIRECT` (guard applies rules to the agent fairly),
  - `OBSERVED`,
  - `REPORT`.
- **Target**:
  - `target_type`: `PERSON`,
  - `target_id`: guard agent_id (the enforcer).
- **Emitted When**:
  - A guard resolves a dispute or enforces queue/space rules without obvious bias
    or brutality, as judged by the runtime.

### 4.3 `guard_brutal`

- **Description**: Guard uses excessive force, intimidation, or cruelty.
- **Channels**:
  - `DIRECT` (agent is target of brutality),
  - `OBSERVED`,
  - `REPORT`,
  - `RUMOR` (stories of guard brutality).
- **Target**:
  - `target_type`: `PERSON`,
  - `target_id`: guard agent_id (the aggressor).
- **Emitted When**:
  - Guard actions cause serious harm, humiliation, or unnecessary escalation,
    beyond what a minimal enforcement action would require.

### 4.4 `steward_help`

- **Description**: A steward/shift supervisor helps the agent or others.
- **Channels**:
  - `DIRECT`,
  - `OBSERVED`,
  - `REPORT`.
- **Target**:
  - `target_type`: `PERSON`,
  - `target_id`: steward agent_id.
- **Emitted When**:
  - A steward intervenes to solve a problem, provide extra resources, or shield
    a worker from punishment in a way that is locally perceived as helpful.

### 4.5 `steward_unfair`

- **Description**: Steward acts in a biased, neglectful, or capricious way.
- **Channels**:
  - `DIRECT`,
  - `OBSERVED`,
  - `REPORT`,
  - `RUMOR`.
- **Target**:
  - `target_type`: `PERSON`,
  - `target_id`: steward agent_id.
- **Emitted When**:
  - A steward grants or denies access, assignments, or protection in ways that
    clearly contradict stated rules or norms, as judged by the runtime.

---

## 5. Accident & Infrastructure Hazard Tags

These capture non-intentional hazards in corridors, bays, and pods.

### 5.1 `accident_minor`

- **Description**: A minor accident occurs (small fall, bump, near-miss).
- **Channels**:
  - `DIRECT` (agent is involved),
  - `OBSERVED`.
- **Target**:
  - `target_type`: `PLACE`,
  - `target_id`: location id (corridor, bay, pod section).
- **Emitted When**:
  - A low-severity accident event fires (short-term pain, no lasting injury)
    in the agent’s vicinity.

### 5.2 `accident_major`

- **Description**: A major accident or incident occurs (serious fall, equipment
  failure, significant injury).
- **Channels**:
  - `DIRECT`,
  - `OBSERVED`,
  - `REPORT`.
- **Target**:
  - `target_type`: `PLACE`,
  - `target_id`: location id (corridor, bay, pod section).
- **Emitted When**:
  - A high-severity accident event fires with meaningful injury or sustained
    environmental hazard.

---

## 6. Protocol & Rule Tags

These tags are used when agents encounter formal rules, directives, or protocol
changes in the environment.

### 6.1 `read_protocol_move_restricted`

- **Description**: Agent learns about a protocol restricting movement (e.g. no
  access beyond a certain corridor or ward without permission).
- **Channels**:
  - `PROTOCOL` (reading a notice, hearing a formal announcement),
  - `REPORT` (being briefed).
- **Target**:
  - `target_type`: `PROTOCOL`,
  - `target_id`: protocol id (e.g. `proto:move:ward-1-restrictions`).
- **Emitted When**:
  - The agent reads a posted directive or is formally told about a new or
    existing movement restriction.

### 6.2 `read_protocol_queue_rules`

- **Description**: Agent learns about protocol changes for queues (e.g. priority
  groups, new time windows, ration limits).
- **Channels**:
  - `PROTOCOL`,
  - `REPORT`.
- **Target**:
  - `target_type`: `PROTOCOL`,
  - `target_id`: queue-related protocol id.
- **Emitted When**:
  - The agent reads/accesses a posted queue/ration rule or attends a briefing
    where such rules are explained.

---

## 7. Body Signal Tags

These tags represent episodes where the agent notices its own internal state.
They are usually emitted by a body/health subsystem rather than world events.

### 7.1 `body_thirst_mild` / `body_thirst_moderate` / `body_thirst_severe`

- **Description**: Agent experiences mild/moderate/severe thirst.
- **Channels**:
  - `BODY_SIGNAL`.
- **Target**:
  - `target_type`: `SELF`,
  - `target_id`: agent_id (optional; may be left `None` since owner is implicit).
- **Emitted When**:
  - Health/physical subsystem detects hydration level crossing thresholds.

### 7.2 `body_hunger_mild` / `body_hunger_moderate` / `body_hunger_severe`

- **Description**: Agent experiences mild/moderate/severe hunger.
- **Channels**:
  - `BODY_SIGNAL`.
- **Target**:
  - `target_type`: `SELF`.
- **Emitted When**:
  - Nutrition stores cross configured hunger thresholds.

### 7.3 `body_fatigue_mild` / `body_fatigue_moderate` / `body_fatigue_severe`

- **Description**: Agent experiences mild/moderate/severe fatigue.
- **Channels**:
  - `BODY_SIGNAL`.
- **Target**:
  - `target_type`: `SELF`.
- **Emitted When**:
  - Sleep deficit or sustained wakefulness exceeds thresholds appropriate to
    this agent’s role and physiology.

### 7.4 `body_pain_mild` / `body_pain_moderate` / `body_pain_severe`

- **Description**: Agent experiences pain at varying intensities (injury,
  strain, illness).
- **Channels**:
  - `BODY_SIGNAL`.
- **Target**:
  - `target_type`: `SELF`.
- **Emitted When**:
  - Injury or sustained stress values exceed thresholds.

### 7.5 `body_heat_stress_mild` / `body_heat_stress_moderate` / `body_heat_stress_severe`

- **Description**: Agent experiences heat-related discomfort/stress.
- **Channels**:
  - `BODY_SIGNAL`.
- **Target**:
  - `target_type`: `SELF`.
- **Emitted When**:
  - Environmental + suit conditions produce heat load above defined thresholds.

---

## 8. Rumor & Report Variants (Meta-Use of Tags)

For this MVP catalog, **tags remain the same across channels**:

- A guard brutality story told as a rumor still uses `guard_brutal`,
  but with:
  - `channel = RUMOR`,
  - lower `reliability`,
  - importance driven by threat and novelty.
- A steward unfairness episode coming via a formal report still uses
  `steward_unfair`, but with:
  - `channel = REPORT`,
  - moderate `reliability` by default.

Implementations MUST NOT create separate tags like `guard_brutal_rumor` or
`guard_brutal_report`; the distinction is carried by `Episode.channel` and
`Episode.reliability`.

---

## 9. Usage Notes for EpisodeFactory & Runtime

When implementing `EpisodeFactory` (see D-MEMORY-0203) and wiring episodes
into runtime code, this catalog SHOULD be used as the reference for:

- **Which tags** can be emitted for a given class of events,
- **Which target_type/target_id** combinations to set,
- **Which channels** to use for each case.

Recommended pattern:

1. World event → lightweight classifier → `(summary_tag, target_type, target_id)`.
2. `EpisodeFactory.build_from_event(...)` uses:
   - `summary_tag` to select severity / emotion defaults,
   - `channel` and `summary_tag` to set `importance`, `reliability`,
   - owner’s current goal to set `goal_relevance`,
   - and structural fields (owner, tick, location, event_id).

This keeps the runtime focused on **what happened**, while memory modules are
responsible for **how agents feel about it and whether they remember it**.

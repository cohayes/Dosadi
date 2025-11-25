---
title: Agent_Goals_and_Episodic_Memory
doc_id: D-AGENT-0021
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-AGENT-0020   # Agent_Model_Foundation
  - D-RUNTIME-0001 # Simulation_Timebase
---

# 1. Purpose and Scope

This document specifies the **Goal** and **Episodic Memory** systems for all Dosadi agents across tiers (1 / 2 / 3).

It defines:

- The **data structures** for:
  - Per-agent and group/council **Goals**.
  - Per-agent **Episodes** (episodic memory).
  - Lightweight **Pattern/Belief** records derived from episodes.
- The **lifecycle** of goals and episodes.
- How **proto-councils** (and later councils, guild heads, cartel stewards) use episodes to:
  - Set group information-gathering and mitigation goals.
  - Author and revise **protocols** (rules, procedures).

These mechanisms must:

- Run from **Founding Wakeup** (all colonists Tier-1) to late-phase cartel politics without rule changes.
- Obey the **No Deus Ex Machina** constraint:
  - No external “designer” interventions beyond initial conditions.
  - All changes to behavior arise from agent logic, world mechanics, and feedback loops.

This document is part of the **Agents** pillar and assumes the canonical agent model defined in `D-AGENT-0020`.


# 2. Concept Overview

## 2.1 Goals as structured contracts

A **Goal** is a structured commitment: *“I will try to make X true, under Y constraints.”*

- Goals are stored per-agent as a **goal stack/list**.
- Goals are also stored per **group** (e.g. proto-council, guild committee) when acting collectively.
- Goals have:
  - A **type** (e.g. acquire resource, gather information, author protocol).
  - A **target** payload (typed data for what success means).
  - A **priority** (how deeply it matters to the owner).
  - An **urgency** (how time-sensitive it feels).
  - A **status** (pending, active, completed, failed, abandoned, blocked).

Agents choose actions each tick by:

1. Selecting a **focus goal** (priority × urgency × personality).
2. Generating options to advance that goal.
3. Executing actions, then updating the goal and associated episodes.

## 2.2 Episodic memory as lived experience

An **Episode** is “how one agent experienced an event.” It is not global truth; it is **subjective**:

- Multiple agents may share the same underlying `event_id` but have distinct episodes.
- Each episode captures:
  - Context (where/when).
  - Participants and roles.
  - What happened, and how it related to the agent’s goals.
  - Emotional tone, perceived risk, perceived reliability.
  - How the agent came to know about it (direct perception, rumor, protocol, report).

Episodes are:

- The **input** for learning patterns/beliefs.
- The **payload** for rumor and reports.
- The **raw material** from which Tier-3 actors author protocols.

## 2.3 Patterns / beliefs as compressed episodes

The simulation maintains a lightweight **Pattern/Belief** layer:

- **Place beliefs** (this corridor is dangerous at night).
- **Person beliefs** (this steward is fair, bribeable, cruel, incompetent).
- **Protocol beliefs** (this rule is enforced / selectively enforced / theater).
- **Faction beliefs** (this guild protects members; this cartel punishes defectors).

Patterns are updated periodically by scanning episodes and adjusting scores like:

- `danger_score`, `trust_score`, `enforcement_score`, etc.

Agents consult patterns:

- When evaluating options for a goal (risk, opportunity).
- When deciding whether to obey or ignore a protocol.
- When interpreting new rumors or reports (confirmation, contradiction).

Patterns are **not** omniscient; they are subjective, per-agent (or per-group), and may conflict.


# 3. Goal Model

## 3.1 Goal object structure

Canonical shape (pseudo-JSON):

```jsonc
Goal {
  "id": "goal:12345",
  "owner_id": "agent:42",          // or "group:council:alpha"

  "parent_goal_id": null,          // optional, for hierarchies

  "goal_type": "ACQUIRE_RESOURCE", // enum-like (see 3.2)
  "description": "Get two good meals today",

  "target": {                      // typed payload; schema depends on goal_type
    "resource_type": "food_ration",
    "quantity": 2,
    "quality": "good",
    "time_window": [80, 200]       // ticks where it matters
  },

  "priority": 0.75,                // 0–1, importance to owner identity
  "urgency": 0.60,                 // 0–1, how soon it must be addressed
  "horizon": "SHORT",              // SHORT | MEDIUM | LONG

  "status": "ACTIVE",              // PENDING | ACTIVE | COMPLETED |
                                   // FAILED | ABANDONED | BLOCKED

  "created_at_tick": 80,
  "deadline_tick": 200,            // optional
  "last_updated_tick": 81,

  "origin": "INTERNAL_STATE",      // INTERNAL_STATE | ORDER | PROTOCOL |
                                   // GROUP_DECISION | OPPORTUNITY
  "source_ref": null,              // protocol id, order episode id, etc.

  "success_conditions": [],        // implementation-defined predicates
  "failure_conditions": [],        // implementation-defined predicates

  "assigned_to": ["agent:42"],     // group goals: multiple assignees

  "tags": ["survival", "food"]
}
```

Simulation implementations may store `success_conditions` / `failure_conditions` as references to code, rule ids, or structured predicates rather than strings. The conceptual requirement is:

- Goals know **when** they should count as satisfied or failed.
- Status changes are driven by observable world state and episodes.

## 3.2 Goal types (non-exhaustive)

Examples (to be refined as implementation matures):

- **Survival and maintenance**
  - `MAINTAIN_SURVIVAL` (high-level daily survival).
  - `ACQUIRE_RESOURCE` (food, water, meds, tools).
  - `SECURE_SHELTER` (safe bunk, pod access).
  - `AVOID_THREAT` (avoid dangerous corridors, patrols).

- **Social and positional**
  - `PROTECT_AGENT` (protect child, partner, podmate).
  - `IMPROVE_STATUS` (gain guild apprenticeship, promotion, better bunk).
  - `MAINTAIN_REPUTATION` (avoid disgrace, maintain “reliable” status).
  - `FORM_RELATIONSHIP` (gain ally, patron, subordinate).

- **Information and cognition**
  - `GATHER_INFORMATION` (scout, census, map hazards).
  - `CLARIFY_UNCERTAINTY` (resolve conflicting rumor).
  - `REMEMBER_AND_RECORD` (journaling, archive update).

- **Organizational / Tier-3**
  - `ORGANIZE_GROUP` (form patrol, scout squad, task force).
  - `AUTHOR_PROTOCOL` (draft rules, procedures).
  - `ENFORCE_PROTOCOL` (patrol, inspections, penalties).
  - `ALLOCATE_RESOURCES` (rations, suits, tools).
  - `STABILIZE_REGION` (reduce unrest, accident rates).

Implementations should treat `goal_type` as an extensible enum, but keep core semantics aligned with the above categories.

## 3.3 Priority, urgency, and horizon

- **priority**: long-run importance, tied to identity & personality.
  - High ambition → higher priority on status/authority goals.
  - High communalism → higher priority on group welfare goals.

- **urgency**: perceived time pressure.
  - Approaches 1.0 as deadlines near or risks spike.
  - Can rise sharply when a new episode signals imminent danger.

- **horizon**:
  - `SHORT`: minutes–hours (eat, avoid patrol, find tonight’s bunk).
  - `MEDIUM`: days–weeks (secure apprenticeship, stabilize pod).
  - `LONG`: weeks–years (build dynasty, reshape ward politics).

The decision loop should use a function like:

```text
goal_score = f(priority, urgency, horizon, personality, current_state)
```

to select a **focus goal** each tick.

## 3.4 Goal lifecycle

1. **Creation**
   - From **internal state**:
     - Hunger, thirst, fatigue, fear → survival and maintenance goals.
   - From **episodes**:
     - Episodes with high negative valence and risk → new avoidance or mitigation goals.
   - From **orders / protocols**:
     - Reading a protocol or receiving an order → imported goals.
   - From **group decisions**:
     - Council goal → cloned to per-agent goals for assignees.

2. **Activation**
   - Goal transitions to `ACTIVE` when:
     - It is selected as a focus goal, or
     - Preconditions are met (e.g. scheduled start).

3. **Progress tracking**
   - Actions incrementally adjust an internal **progress metric**.
   - Relevant episodes are linked back via `goals_involved` in the episode record.

4. **Resolution**
   - `COMPLETED`: success conditions met.
   - `FAILED`: failure conditions met.
   - `ABANDONED`: owner intentionally drops it.
   - `BLOCKED`: temporarily impossible (e.g. corridor sealed, key resource gone).

5. **After-effects**
   - Resolution creates episodes about **success/failure** of the goal.
   - Patterns/beliefs update:
     - Success can increase perceived efficacy and self-efficacy.
     - Failure can increase caution, resentment, or fatalism depending on personality.

## 3.5 Hierarchies and subgoals

Goals form trees via `parent_goal_id`:

- Example:
  - Parent: `MAINTAIN_SURVIVAL_TODAY`
    - Child: `ACQUIRE_RESOURCE` (two good meals).
    - Child: `AVOID_THREAT` (dangerous corridors).
    - Child: `MAINTAIN_RELATIONSHIP` (stay on good terms with podmates).

The agent:

- Selects a **parent goal** (e.g. survival).
- Chooses/activates a **child subgoal** (e.g. acquire food) for immediate action.
- Updates parent progress based on child outcomes.

## 3.6 Group and council goals

Group goals are identical to agent goals, with:

- `owner_id = "group:<type>:<id>"`.
- Multiple entries in `assigned_to`.

Example proto-council goal:

```jsonc
{
  "id": "goal:council-alpha:001",
  "owner_id": "group:council:alpha",
  "goal_type": "GATHER_INFORMATION",
  "description": "Map corridors and hazard zones within 4 hops of Well.",
  "target": {
    "region_type": "corridor_network",
    "radius_hops": 4
  },
  "priority": 0.95,
  "urgency": 0.80,
  "horizon": "SHORT",
  "status": "ACTIVE",
  "origin": "GROUP_DECISION",
  "assigned_to": ["agent:scout-1", "agent:scout-2", "agent:scribe-1"],
  "tags": ["founding-phase", "mapping", "safety"]
}
```

Implementations may allow **group goals** to:

- Feed into individual agents’ goal stacks as imported goals.
- Track aggregated progress from multiple agents.


# 4. Episodic Memory Model

## 4.1 Episode object structure

Canonical shape (pseudo-JSON):

```jsonc
Episode {
  "id": "ep:agent42:000123",
  "owner_id": "agent:42",

  "event_id": "ev:000123",          // shared across witnesses when known
  "tick_start": 120,
  "tick_end": 130,

  "location_id": "loc:corridor-7A",
  "context_tags": ["night-cycle", "low-traffic"],

  "source_type": "DIRECT",          // DIRECT | HEARD_RUMOR | READ_PROTOCOL |
                                    // RECEIVED_ORDER | RECEIVED_REPORT |
                                    // WATCHED_THEATER
  "source_agent_id": "agent:42",    // who told you, authored protocol, etc.

  "participants": [
    {
      "agent_id": "agent:42",
      "role": "self",
      "perceived_disposition": "afraid"
    },
    {
      "agent_id": "agent:77",
      "role": "patrol_guard",
      "perceived_disposition": "hostile"
    }
  ],

  "event_type": "PATROL_INTERDICTION",
  "summary": "Stopped by patrol and shaken down for water chits.",

  "goals_involved": [
    {
      "goal_id": "goal:survive-today:42",
      "pre_status": "ACTIVE",
      "post_status": "ACTIVE",
      "delta_progress": -0.1
    },
    {
      "goal_id": "goal:avoid-dangerous-corridors:42",
      "pre_status": "PENDING",
      "post_status": "ACTIVE",
      "delta_progress": 0.0
    }
  ],

  "outcome": {
    "success": false,
    "injury": false,
    "losses": {
      "water_chits": 3
    },
    "gains": {}
  },

  "emotion": {
    "valence": -0.8,                // -1 bad to +1 good
    "arousal": 0.9,                 // 0 calm to 1 intense
    "dominant_feeling": "fear"
  },

  "perceived_risk": 0.85,           // subjective risk level
  "perceived_reliability": 0.95,    // how true the owner thinks this is

  "pattern_updates": [],            // optional linkbacks to belief updates

  "privacy": "PRIVATE",             // PRIVATE | SHAREABLE | RUMOR_FODDER
  "tags": ["patrol", "extortion", "corridor-7A"]
}
```

Notes:

- `source_type` and `perceived_reliability` distinguish direct experience from rumor, propaganda, etc.
- `goals_involved` links episodes to specific goals in the owner’s goal stack, enabling goal-conditioned learning.
- `emotion` and `perceived_risk` give episodes “teeth” in future decision-making (fear, anger, pride, shame, etc.).

## 4.2 Episode creation sources

Episodes are created when:

- The agent **acts**:
  - Every meaningful action can produce an episode about its outcome.
- The agent **observes**:
  - Accidents, conflicts, distributions, ceremonies, punishments.
- The agent **hears / reads**:
  - Rumor from another agent.
  - Formal or informal report.
  - Protocol or posted notice.
- The agent **participates in group decisions**:
  - Council meetings, hearings, trials, negotiations.

Implementations should avoid creating episodes for trivial events; instead, use thresholds:

- Only create episodes when:
  - A goal is materially advanced or harmed, **or**
  - Emotion/arousal passes a minimum threshold, **or**
  - The event is tagged as structurally important (protocol read, order received).

## 4.3 Rumors, reports, protocols as episodes

Rather than separate systems:

- A **rumor** is an episode with:
  - `source_type = HEARD_RUMOR`.
  - `source_agent_id =` rumor-teller.
  - Typically lower `perceived_reliability`.

- A **report** is:
  - For the reporter: an episode with `source_type = DIRECT`.
  - For the receiver (e.g. steward or council member): a new episode with
    - `source_type = RECEIVED_REPORT`,
    - `source_agent_id =` reporter agent or office.

- A **protocol** is:
  - Authored by a Tier-3 agent based on many episodes.
  - When another agent reads it, they create an episode:
    - `event_type = READ_PROTOCOL`,
    - `source_type = READ_PROTOCOL`,
    - with a link to the `protocol_id` in the `target` or `tags`.

All three are just different **ways episodes move through the social graph**, with differing reliability and framing.

## 4.4 Privacy and shareability

`privacy` field suggests how the agent is inclined to treat the episode:

- `PRIVATE`: Highly sensitive, shameful, incriminating, or strategically guarded.
- `SHAREABLE`: Can be retold as story, report, or gossip under some conditions.
- `RUMOR_FODDER`: Likely to be embellished and widely shared.

This does **not** strictly enforce behavior (agents can betray their own preferences), but it informs social logic:

- High communal + trusting agents may share more `SHAREABLE` episodes.
- Paranoid or strategic agents may hoard even some `SHAREABLE` knowledge.


# 5. Pattern / Belief Layer

## 5.1 Place beliefs

Example structure:

```jsonc
PlaceBelief {
  "id": "belief:place:corridor-7A:agent42",
  "owner_id": "agent:42",
  "place_id": "loc:corridor-7A",

  "danger_score": 0.80,            // 0–1
  "enforcement_score": 0.90,       // how tightly rules are enforced here
  "opportunity_score": 0.20,       // chance to profit

  "last_updated_tick": 130,
  "supporting_episodes": [
    "ep:agent42:000123",
    "ep:agent42:000099"
  ]
}
```

## 5.2 Person, protocol, and faction beliefs

Patterns can be similarly defined:

- **PersonBelief**
  - `trust_score`, `fairness_score`, `bribeability_score`, `cruelty_score`.
- **ProtocolBelief**
  - `enforcement_score` (how likely violation is punished).
  - `bias_score` (perceived bias for/against certain classes/factions).
  - `burden_score` (how costly compliance feels).
- **FactionBelief**
  - `protectiveness_score` (how well they protect members).
  - `vengefulness_score` (severity of punishment for betrayal).
  - `corruption_score` (likelihood of bribes working).

Beliefs are **per-agent** by default; group-level beliefs (e.g. council, guild board) can be maintained separately if needed.

## 5.3 Pattern update process (conceptual)

On some cadence (e.g. every N ticks):

1. Collect recent episodes for an agent.
2. Group them by:
   - place, person, protocol, faction, etc.
3. For each group:
   - Compute frequency, severity, and average perceived_risk / valence.
4. Adjust the relevant belief scores via:
   - Exponential moving average, Bayesian update, or similar.

Beliefs should not swing wildly on a single episode unless:

- The episode is extremely severe (e.g. near death, catastrophic loss), **or**
- Personality traits (e.g. high paranoia) amplify sensitivity.

Episodes that contribute to belief updates can have their ids recorded in `supporting_episodes` for traceability.


# 6. Proto-Council Goal Setting from Episodes

This section defines how early **proto-councils** use these primitives to:

- Aggregate episodes from multiple pods.
- Generate **group goals** (especially information-gathering).
- Author and refine **protocols**.

## 6.1 Councils as groups and meeting episodes

### 6.1.1 Representation

- Each **spokesperson** is a normal agent with a role such as `POD_REPRESENTATIVE`.
- A **proto-council** is represented as:
  - `group:council:<id>` with:
    - membership list,
    - group-level goals,
    - optional group-level beliefs (e.g. about regions).

### 6.1.2 Meeting episodes

When spokespeople meet at shared choke points (e.g. depots):

- Each participant creates an `Episode` with `event_type = COUNCIL_MEETING`.
- The episode includes references to **shared incidents**:

```jsonc
{
  "event_type": "COUNCIL_MEETING",
  "summary": "Shared reports of corridor accidents and missing colonists.",
  "tags": ["meeting", "hazard-sharing", "founding-phase"],
  "shared_incident_refs": [
    "ep:pod3:injury-1",
    "ep:pod7:missing-1"
  ]
}
```

These meeting episodes are the **input** to council-level pattern recognition.

## 6.2 Council-level pattern extraction

At intervals (or after a meeting):

1. Collect all **incident episodes** referenced in meeting episodes within a time window.
2. Bucket incidents by:
   - `location_id` (corridor, junction, depot).
   - `event_type` (injury, disappearance, patrol conflict, heat stress).
   - Optional: time of cycle, type of agents affected.

3. For each bucket, compute:
   - `frequency`: count of incidents.
   - `severity`: average severity (injury/death, resource loss).
   - `confidence`: average `perceived_reliability`.

4. Combine into a **risk score**:

```text
risk_score = w_freq * normalized_frequency
           + w_sev  * normalized_severity
           + w_conf * normalized_confidence
```

5. Identify buckets where:
   - `risk_score > threshold_high` → candidate for **mitigation** and **information** goals.
   - `risk_score` unknown / low-data but incidents are weird/ambiguous → candidate for **targeted investigation** goals.

## 6.3 Generating council information goals

From high-risk or high-uncertainty buckets, councils create `GATHER_INFORMATION` goals, e.g.:

```jsonc
{
  "id": "goal:council-alpha:map-001",
  "owner_id": "group:council:alpha",
  "goal_type": "GATHER_INFORMATION",
  "description": "Map and risk-assess corridors 2A–7A after multiple incidents.",
  "target": {
    "locations": ["loc:corridor-2A", "loc:corridor-3A", "loc:corridor-7A"],
    "required_confidence": 0.75
  },
  "priority": 0.90,
  "urgency": 0.85,
  "horizon": "SHORT",
  "status": "ACTIVE",
  "origin": "GROUP_DECISION",
  "assigned_to": ["agent:scout-1", "agent:scout-2", "agent:scribe-1"],
  "tags": ["founding-phase", "mapping", "safety"]
}
```

These group goals are then **cloned** or **projected** into per-agent goal stacks for:

- `scout` roles,
- escort/guard roles,
- scribe/record-keeper roles.

## 6.4 From information goals to protocols

As scouts and guards act:

1. They generate episodes:
   - `SCOUTING_RUN`, `FOUND_HAZARD`, `SAFE_PATH_FOUND`, `PATROL_ENCOUNTER`.
2. These episodes are reported back (directly or via scribes), producing:
   - Meeting episodes (`COUNCIL_MEETING`) and receiver episodes (`RECEIVED_REPORT`).

Council-level logic re-runs pattern extraction:

- Now with more **direct, higher-confidence** episodes.
- Risk scores and confidence for specific locations increase or decrease.

When risk and confidence cross a protocol threshold:

- The council creates an `AUTHOR_PROTOCOL` goal:

```jsonc
{
  "id": "goal:council-alpha:proto-guard-001",
  "owner_id": "group:council:alpha",
  "goal_type": "AUTHOR_PROTOCOL",
  "description": "Draft movement rules for corridor 7A and surrounding junctions.",
  "target": {
    "protocol_type": "TRAFFIC_AND_SAFETY",
    "covered_locations": ["loc:corridor-7A", "loc:junction-7A-7B"]
  },
  "priority": 0.80,
  "horizon": "MEDIUM",
  "origin": "GROUP_DECISION"
}
```

When this goal is completed:

1. A **Protocol** entity (see Law/Protocols docs) is created.
2. Agents who read or are briefed on the protocol create `READ_PROTOCOL` episodes.
3. PlaceBeliefs and ProtocolBeliefs begin to incorporate:
   - Perceived enforcement.
   - Perceived fairness/bias.
   - Perceived effectiveness.

All of this is achieved via the same **Goal + Episode + Pattern** machinery, without any external “god-logic.”

## 6.5 Long-run continuity

The same pattern holds across phases:

- Phase 0:
  - Council information goals focus on mapping, basic hazards, initial rationing.
- Phase 1:
  - Information goals include Well output measurements, shrinkage in margins, unrest signals.
  - Protocol goals tighten discipline and rationing.
- Phase 2:
  - Information goals include black-market flows, cartel incidents, loyalty slippage.
  - Protocol goals include crackdowns, targeted leniency, narcotic controls, surveillance.

Only incident types and parameters change. The underlying logic does not.


# 7. Integration with Agent Decision Loop

The Agent Decision Loop (see `D-AGENT-0020`) uses this doc as follows:

1. **Select focus goal**
   - Evaluate goals by:
     - `priority`, `urgency`, `horizon`,
     - agent personality and physical/psych state,
     - relevant patterns/beliefs.

2. **Recall relevant episodes**
   - Filter the agent’s episodes for:
     - matching `goal_id`, `event_type`, `tags`, `location`, and/or participants.
   - Weight by:
     - recency, emotional arousal, perceived reliability, and severity.

3. **Evaluate options**
   - Simulate or estimate:
     - risk using PlaceBelief/PersonBelief/ProtocolBelief scores.
     - expected goal progress, costs, and social impact.

4. **Act and record**
   - Execute chosen action.
   - Create an Episode capturing:
     - outcome,
     - changes to goals,
     - emotional response,
     - perceived risk.

5. **Update goals and beliefs**
   - Adjust goal progress and possibly status (complete/fail/blocked).
   - Periodically update patterns/beliefs from accumulated episodes.

This closes the loop from **Goals → Actions → Episodes → Patterns → Goals**, and from **individual experiences** to **emergent protocols** at higher tiers.


# 8. Implementation Notes (Non-Normative)

- The schemas here are **conceptual contracts**, not strict database schemas.
  - Implementations may flatten or split tables as needed.
- Carefully tune:
  - Episode creation thresholds,
  - Pattern update cadence,
  - Risk/priority calculation functions,
  to keep the simulation performant and behaviorally rich.
- For early prototypes:
  - Start with a small subset of goal types and episode fields.
  - Expand as needed once the core loop behaves plausibly.

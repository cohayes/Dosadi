---
title: Episode_Scoring_and_Defaults
doc_id: D-MEMORY-0203
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-MEMORY-0001  # Episode_Management_System_v0
  - D-MEMORY-0002  # Episode_Schema_and_Memory_Behavior_v0
  - D-MEMORY-0003  # Episode_Transmission_Channels_v0
  - D-MEMORY-0004  # Belief_System_and_Tiered_Memory_v0
  - D-MEMORY-0102  # Episode_Data_Structures_and_Buffers_v0
  - D-RUNTIME-0201 # Golden_Age_Daily_Rhythms_and_Shifts_v0
  - D-AGENT-0020   # Unified_Agent_Model_v0
---

# 15_memory · Episode Scoring and Defaults v0 (D-MEMORY-0203)

## 1. Purpose & Scope

This document defines **semantic defaults** for key fields on `Episode` and
provides a simple, extensible rule-set for how episodes are scored for
promotion and retention.

It is an implementation companion to D-MEMORY-0102 (episode shapes) and is
intended to guide creation of an `episode_factory` (or similar helper) in the
codebase, without prescribing where episodes must be generated.

Specifically, it defines:

- How the existing promotion score
  (`importance + 0.5 * goal_relevance + 0.5 * emotion.threat`) is intended
  to be interpreted.
- Default ranges for:
  - `importance`,
  - `reliability`,
  - `emotion` (valence, arousal, threat),
  across different `EpisodeChannel` values.
- Default semantics for a small set of core verbs / `summary_tag` values
  used in the Founding Wakeup / Golden Age MVP.
- A minimal scheme for setting `goal_relevance` based on overlap between the
  episode and the current focus goal.
- A recommended `EpisodeFactory` abstraction for later implementation.

This document is **descriptive** and **guiding**; it does not directly mandate
code structure, but Codex SHOULD follow it when implementing concrete scoring.

---

## 2. Promotion Score Reminder

Per the current implementation, `AgentState.promote_short_term_episodes()`
computes a simple promotion score:

```python
score = (
    episode.importance
    + 0.5 * episode.goal_relevance
    + 0.5 * episode.emotion.threat
)
```

and promotes an episode from `short_term` to `daily` when, for example,

```python
if score >= 0.6:
    self.episodes.promote_to_daily(episode)
```

Intended semantics:

- `importance` ~ **raw salience** (how striking this felt).
- `goal_relevance` ~ **task relevance** (how much this mattered for what the
  agent was trying to do).
- `emotion.threat` ~ **danger signal** (how unsafe this felt).

The defaults defined below are meant to ensure that:

- Routine, low-stakes episodes usually **do not** pass 0.6.
- Strongly negative or goal-relevant episodes almost always do.
- Strong body-signal episodes (e.g. thirst, pain) have a high chance to be
  promoted, even without external danger.

The exact threshold (0.6) is v0 and may be tuned in later runtime docs.

---

## 3. Channel Semantics

This section defines **default value ranges** for `importance` and `reliability`
for each `EpisodeChannel` (see D-MEMORY-0102). These are **starting points**;
future work may refine them based on traits, roles, or beliefs about sources.

### 3.1 DIRECT

> The agent experienced this event personally via its own senses.

- `reliability`: **0.8–0.9** by default.
- `importance`:
  - base: 0.3,
  - add severity bump based on verb/summary_tag (see §4).
- `emotion`:
  - `threat` determined mainly by verb/summary_tag and outcome:
    - harmful or near-miss events: 0.7–1.0,
    - minor or neutral events: 0.0–0.3.

### 3.2 BODY_SIGNAL

> Internal state (hunger, thirst, pain, fatigue, heat/cold stress).

- `reliability`: **0.9** by default.
- `importance`: proportional to symptom intensity:
  - mild: 0.3–0.4,
  - moderate: 0.5–0.7,
  - severe: 0.8–1.0.
- `emotion`:
  - `valence`: negative proportional to intensity (-0.3 to -1.0),
  - `threat`:
    - hunger/fatigue: 0.2–0.7,
    - extreme thirst / breathing issues / severe heat: 0.5–1.0.

These episodes often have both high `importance` and `goal_relevance` when
the agent’s current goal relates to basic survival needs.

### 3.3 OBSERVED

> The agent watched an event that affected others, not directly itself.

- `reliability`: **0.7** by default.
- `importance`:
  - close, clearly visible events: 0.5–0.7,
  - distant or ambiguous events: 0.2–0.4.
- `emotion`:
  - `threat`:
    - if targets are similar peers in similar circumstances: 0.5–0.8,
    - distant or low-stakes: 0.1–0.4.

### 3.4 REPORT

> Structured message from a known agent (e.g. worker → steward, steward → council).

In future, `reliability` should depend on a `PersonBelief` about the source;
for now we assume a moderate default.

- `reliability`: **0.6–0.7**.
- `importance`:
  - base: 0.4,
  - +0.2–0.4 if content is clearly dangerous or high-impact.
- `emotion`:
  - typically lower arousal and threat than DIRECT/OBSERVED,
  - the agent is hearing *about* danger rather than being in it.

### 3.5 RUMOR

> Informal, low-structure hearsay from undefined or low-trust sources.

- `reliability`: **0.2–0.4**.
- `importance`:
  - base: 0.2–0.3,
  - +0.3–0.5 if rumor content is highly threatening or personally relevant.
- `emotion`:
  - `threat` can be high even when `reliability` is low,
  - this naturally generates uncertain but potentially impactful beliefs.

### 3.6 PROTOCOL

> Information received from a written or spoken protocol, directive, or rule.

- `reliability`: **0.7–0.8** (rules are “real” until contradicted).
- `importance`:
  - base: 0.3,
  - +0.3–0.5 if the protocol obviously affects current or common goals
    (movement, queue behavior, rations, access).
- `emotion`:
  - valence: mildly negative or neutral (constraint),
  - threat: 0.2–0.6 if protocol implies harsher punishments or restrictions.

---

## 4. Verb / Summary Tag Defaults

This section defines default semantics for a **small set of core verbs /
`summary_tag` values** expected in the Founding Wakeup / early Golden Age
scenarios. These values are meant as guidelines with sensible ranges, not
exact constants.

### 4.1 Hazard / Violence Nearby

Representative tags:

- `"queue_fight"`, `"fight"`,
- `"guard_cruelty"`, `"guard_beat"`,
- `"accident_minor"`, `"accident_major"`.

For DIRECT or close OBSERVED episodes:

- `importance`:
  - 0.7–1.0 (depending on severity).
- `emotion.valence`:
  - -0.7 to -1.0.
- `emotion.arousal`:
  - 0.7–1.0.
- `emotion.threat`:
  - minor accident / brief scuffle: 0.5–0.7,
  - major fight / serious injury: 0.8–1.0.
- `outcome`:
  - if the owner is injured: `HARM`,
  - if the owner narrowly escapes: `NEAR_MISS`,
  - if only observing: typically `NEUTRAL` with high threat.

These episodes should almost always exceed the promotion threshold.

### 4.2 Queue Outcomes (Food / Water)

Representative tags:

- `"queue_served"`, `"queue_smooth"`,
- `"queue_denied"`, `"queue_canceled"`.

For rations/water queues, agents commonly have goals like “eat” or “get water.”

- If served (success):
  - `importance`: 0.4–0.6,
  - `emotion.valence`: +0.4 to +0.7,
  - `emotion.threat`: 0.1–0.3,
  - `outcome`: `SUCCESS`.

- If denied/canceled (failure):
  - `importance`: 0.6–0.9,
  - `emotion.valence`: -0.5 to -0.8,
  - `emotion.threat`: 0.4–0.7,
  - `outcome`: `FAILURE` or `NEAR_MISS`.

If the current focus goal concerns food/water, `goal_relevance` SHOULD be set
high (see §5), ensuring these episodes are strong candidates for promotion.

### 4.3 Guard & Steward Behavior

Representative tags:

- `"guard_help"`, `"guard_fair"`, `"guard_brutal"`,
- `"steward_help"`, `"steward_unfair"`.

- Helpful/fair behavior:
  - `importance`: 0.4–0.6,
  - `emotion.valence`: +0.5,
  - `emotion.threat`: 0.1–0.3,
  - `outcome`: `HELP`.

- Unfair/brutal behavior:
  - `importance`: 0.6–0.9,
  - `emotion.valence`: -0.6 to -0.9,
  - `emotion.threat`: 0.4–0.8,
  - `outcome`: `HARM` (if victim is owner) or `NEUTRAL` with high threat if
    observed but not directly suffered.

These episodes are primary seeds for:

- `PersonBelief.trustworthiness` and `threat_level` (guards, stewards),
- `FactionBelief.brutality` and `legitimacy` (garrison, council, pods).

### 4.4 Protocol Reading

Representative tags:

- `"read_protocol_move_restricted"`,
- `"read_protocol_queue_rules"`,
- similar protocol-related codes.

Defaults:

- `importance`:
  - base: 0.3,
  - +0.3–0.5 if the protocol clearly interferes with common actions
    (movement, queueing, rations) or current goal.
- `emotion.valence`:
  - modestly negative unless obviously beneficial.
- `emotion.threat`:
  - 0.3–0.6 if new punishments or restrictions are implied,
  - otherwise near 0.0–0.2.
- `outcome`: `NEUTRAL`.

These episodes primarily feed into `ProtocolBelief` and, via those, into
future decision-making.

### 4.5 Body Signals

Representative tags:

- `"body_thirst"`, `"body_hunger"`,
- `"body_pain"`, `"body_fatigue"`,
- `"body_heat_stress"`, etc.

Intensity buckets → suggested defaults:

- Mild:
  - `importance`: 0.3–0.4,
  - `emotion.valence`: -0.3,
  - `emotion.threat`: 0.2–0.3.

- Moderate:
  - `importance`: 0.5–0.7,
  - `emotion.valence`: -0.6,
  - `emotion.threat`: 0.4–0.6.

- Severe:
  - `importance`: 0.8–1.0,
  - `emotion.valence`: -0.9 to -1.0,
  - `emotion.threat`: 0.7–1.0 (especially for thirst/heat).

When the current goal explicitly targets body needs (eat, drink, rest, cool
down), `goal_relevance` SHOULD be set high, making these episodes strong
drivers of behavior and belief about personal vulnerability and safety.

---

## 5. Goal Relevance Semantics

`goal_relevance` represents how strongly an episode matters for the agent's
**current focus goal** (see D-AGENT-0023). It is distinct from `importance`
and `threat`, which are more purely emotional/salience measures.

### 5.1 Overlap Heuristics

A simple v0 scheme for computing `goal_relevance`:

1. **Location overlap**

   - If `episode.location_id` matches the goal's primary location target
     (e.g. a facility, corridor, or ward the agent is trying to reach or
     operate in), add **0.5–0.7** to `goal_relevance`.

2. **Resource / domain overlap**

   - If the goal is about a basic need (food, water, rest) and the episode's
     `summary_tag` concerns queues, rations, or sleeping space, add
     **0.4–0.7**.

3. **Target overlap**

   - If the goal explicitly concerns a particular agent (seek, help, avoid)
     and `episode.target_id` equals that agent_id, add **0.6–0.8**.

`goal_relevance` SHOULD then be clamped to [0.0, 1.0].

In v0, it is acceptable for many episodes to have `goal_relevance = 0.0`,
particularly when the current goal is unrelated to the observed event.

### 5.2 Integration Point

When generating an Episode for an agent, episode-creation logic SHOULD:

- inspect the agent’s current focus goal (if any),
- apply the above overlap checks,
- set `episode.goal_relevance` before scoring for promotion.

Future work MAY:

- incorporate personality traits (e.g. curious agents treat more things as
  goal-relevant),
- let high WIL agents maintain more goal-relevant episodes in daily buffers.

---

## 6. EpisodeFactory Abstraction (Design Suggestion)

To avoid scattering literal numbers and ad-hoc field settings across the code,
implementations SHOULD centralize episode creation in a small utility, e.g.:

```python
class EpisodeFactory:
    """Helper to build scored Episode instances from world events."""

    def __init__(self, rng: Random):
        self.rng = rng

    def build_from_event(
        self,
        owner: AgentState,
        event: WorldEvent,
        channel: EpisodeChannel,
        now_tick: int,
    ) -> Episode:
        ...
```

Responsibilities of such a factory:

1. **Set channel defaults**

   - Initialize `reliability` and base `importance` according to §3.

2. **Apply verb / summary_tag semantics**

   - Based on the event type and view, set:
     - `verb`,
     - `summary_tag`,
     - `outcome`,
     - `emotion` (valence/arousal/threat),
     - additional increments to `importance`.

3. **Compute goal relevance**

   - Inspect the owner's current focus goal (if any),
   - set `goal_id` and `goal_relevance` via §5 rules.

4. **Attach structural fields**

   - `owner_agent_id`, `tick`, `location_id`,
   - `target_type`, `target_id`, `event_id` (if applicable),
   - `channel`, `source_agent_id` (for REPORT, RUMOR).

The factory can use a small mapping of `summary_tag` → severity parameters,
stored in a simple dict inside the module. This keeps the main runtime code free
of scattered numeric constants.

---

## 7. Implementation Notes (Non-binding)

When Codex or a human implements these semantics, they SHOULD:

- Start with a **small subset** of verbs/summary_tags:
  - queue events,
  - basic hazards,
  - guard/steward interactions,
  - protocol reads,
  - body signals.
- Implement rough numeric ranges (e.g. 0.3, 0.6, 0.9) rather than trying to
  overfit exact values.
- Keep the logic easily discoverable and configurable:
  - centralize constants in one module,
  - prefer simple tables over deeply nested conditionals.

Later documents (D-MEMORY-03xx, D-RUNTIME-03xx) may refine these mappings based
on observed simulation behavior (e.g. too few vs too many episodes surviving to
daily buffers, over- or under-reaction to certain stimuli).

---
title: Work_Preferences_And_Crew_Churn_MVP
doc_id: D-RUNTIME-0224
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-08
depends_on:
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0212   # Initial_Work_Detail_Taxonomy_MVP
  - D-RUNTIME-0213   # Work_Detail_Behaviors_MVP_Scout_And_Inventory
  - D-RUNTIME-0214   # Council_Metrics_And_Staffing_Response_MVP
  - D-RUNTIME-0219   # Needs_Stress_And_Performance_MVP
  - D-RUNTIME-0221   # Work_History_Specialization_And_Proto_Guilds_MVP
  - D-RUNTIME-0222   # Promotion_And_Tier_Evolution_MVP
  - D-RUNTIME-0223   # Supervisor_Reporting_And_Council_Input_MVP
  - D-AGENT-0020     # Canonical_Agent_Model
  - D-AGENT-0022     # Agent_Core_State_Shapes
  - D-MEMORY-0102    # Episode_Representation
  - D-MEMORY-0200    # Belief_System_Overview
---

# Work Preferences and Crew Churn (MVP) — D-RUNTIME-0224

## 1. Purpose & scope

This document specifies a minimal loop where agents form preferences for
different work types and occasionally try to change jobs, producing:

- stable crews for work that feels tolerable and meaningful,
- chronic churn in roles that are punishing or undersupported,
- a basis for proto-guild identities and labour tension.

Loop (MVP):

1. Each agent accumulates work history (D-RUNTIME-0221).
2. After each completed shift, the agent updates a work preference score
   for that work type based on how the shift felt (stress, morale, tagged
   episodes).
3. Once per “day”, the agent evaluates whether to stay in their current
   work or desire a transfer to some other work type.
4. Council staffing (assign_work_crews) respects preferences softly when
   filling crews, increasing stability where preference and need align.

Scope (MVP):

- Preferences are simple numeric scores per WorkDetailType.
- Transfer requests are not hard constraints; council can override.
- No explicit labour actions yet (strikes, refusal); just preferences that
  bias assignment.

This layer sits on top of work history, stress/morale, and council staffing
without adding new political systems.

## 2. Agent-level work preferences

### 2.1 Structures

Extend the work-history / agent modules with:

- WorkPreference:
  - preference: float in [-1.0, 1.0], meaning dislike/neutral/like.
  - recent_enjoyment: float in [-1.0, 1.0], an exponential moving average
    of how recent shifts in this work type felt.
  - samples: integer count of how many shifts have been folded in.

- WorkPreferences:
  - per_type: map from WorkDetailType to WorkPreference.
  - helper get_or_create(work_type) to ensure an entry exists.

These are storage only; update logic is defined in section 3.

### 2.2 AgentState extensions

Add to AgentState:

- work_preferences: WorkPreferences, default empty.
- desired_work_type: optional WorkDetailType indicating the work type this
  agent would prefer to move into. This is an expression, not a guarantee;
  council can ignore it if needs are acute.

Interpretation:

- work_history tells you what the agent has done.
- work_preferences tells you how they feel about that work.
- desired_work_type is the current best candidate for “where I’d rather be”.

## 3. Updating preferences from shift experience

### 3.1 Shift-completion hook

Wherever a work detail marks its shift as complete (incrementing shift count,
recomputing proficiency, and setting goal status to COMPLETED), we hook in
a preference update.

On shift completion for work type T:

1. Compute a shift enjoyment score in [-1.0, 1.0].
2. Call an update helper that nudges WorkPreference for T toward that score.

### 3.2 Computing shift enjoyment

MVP enjoyment is derived from current physical state as a proxy for how the
shift felt:

- Start from morale_level in [0, 1], mapped into a roughly [-0.2, +0.8]
  baseline.
- Subtract a penalty proportional to stress_level in [0, 1].
- Clamp the result into [-1.0, 1.0].

This gives:

- positive enjoyment when morale is decent and stress is low,
- negative enjoyment when stress is high and morale is poor.

In later revisions, this can be refined using episodes tagged as incidents,
queues, or strain, but for MVP stress + morale are sufficient.

### 3.3 Preference update rule

Given enjoyment_score in [-1, 1] for work_type:

- Fetch WorkPreference wp for that type from AgentState.work_preferences.
- Update recent_enjoyment via an exponential moving average with weight
  alpha (e.g. 0.2).
- Move preference slightly toward recent_enjoyment using another factor
  beta (e.g. 0.1).
- Clamp preference to [-1.0, 1.0].
- Increment samples.

Result: a smoothly-evolving preference that drifts toward the smoothed
experience of doing that work, without oscillating wildly from shift to
shift.

## 4. Daily “stay or request transfer” decision

### 4.1 Cadence

We introduce constants such as:

- PREFERENCE_REVIEW_INTERVAL_TICKS (e.g. 120000, once per “day”).
- NEGATIVE_PREFERENCE_THRESHOLD (e.g. -0.3).
- POSITIVE_PREFERENCE_THRESHOLD (e.g. +0.3).

We reuse agent.total_ticks_employed as a soft clock: only agents who have
been around long enough will regularly reconsider their work.

### 4.2 Identifying current work type

For the purpose of preference review, we define an agent’s current primary
work type as:

- if they are a supervisor with supervisor_work_type set, use that.
- otherwise, the work type with the largest work_history.ticks value.

If no such type exists (e.g. very new agent), skip review.

### 4.3 Decision logic

Once per review interval (checked using total_ticks_employed modulo the
interval), for an agent with a defined current_work_type:

1. Read current_pref = preference for current_work_type.
2. If current_pref > NEGATIVE_PREFERENCE_THRESHOLD:
   - The agent is not strongly unhappy.
   - If current_pref > POSITIVE_PREFERENCE_THRESHOLD, set desired_work_type
     to current_work_type (explicitly reinforcing that choice).
   - Otherwise, leave desired_work_type unchanged.
3. If current_pref <= NEGATIVE_PREFERENCE_THRESHOLD:
   - The agent is unhappy with current work, so we look for alternatives.
   - Find the work type with the highest preference strictly greater than
     current_pref.
   - If no alternative beats current_pref, set desired_work_type to None.
   - If some alternative is better, set desired_work_type to that work type.

This is deliberately conservative: agents only shift desire away from their
current niche if another niche genuinely looks better.

## 5. Incorporating preferences into crew assignment

### 5.1 Extending the suitability score

D-RUNTIME-0221 defines assign_work_crews, which currently scores agents for
each work type based on:

- proficiency (from work_history),
- morale_level,
- stress_level.

We extend this scoring function with:

- pref: WorkPreference.preference for that work type, in [-1, 1],
- desired_bonus: a small positive bump if desired_work_type equals this
  work type.

Example composition (conceptual):

- Base score = 0.6 * proficiency + 0.2 * morale - 0.2 * stress
- Add 0.2 * pref to tilt toward work agents like.
- Add desired_bonus (e.g. +0.1) if this is their explicitly desired work.

The exact weights are tunable; the intent is:

- proficiency and need still dominate,
- preferences nudge assignment when there is slack or multiple viable
  candidates.

### 5.2 Behavioural consequences

With this score:

- Agents who have consistently good experiences in a work type will slowly
  accumulate positive preference and be more likely to remain assigned there.
- Agents who have negative experiences will find their preference drifting
  downward and will be pulled into other work types if they exist.
- If an agent has a preferred alternative and the council has any slack,
  that preference has a non-trivial chance of being respected.

Over time, this should yield:

- stable, specialized crews in decent conditions,
- churn in harsh roles,
- natural variation in who ends up where, even with identical initial
  parameters.

## 6. Optional: episodes and beliefs around work preference

This MVP does not require new episode types, but we can sketch an optional
extension for later:

- Emit a low-importance episode whenever a preference for a work type
  changes by more than some delta (e.g. 0.2).
- That episode is self-focused, with tags indicating work, the work type
  name, and preference change (e.g. “work”, “kitchen”, “preference”).

These episodes will be compressed into self-beliefs during sleep cycles,
eventually leading to beliefs like “I am a water handler”, “inventory work
burns me out”, etc. For now this is left as a future enhancement.

## 7. Integration order & boundaries

### 7.1 Recommended implementation order

1. Add WorkPreference and WorkPreferences structures and wire them into
   AgentState.
2. Implement the preference update helper and hook it into shift-completion
   points for all relevant work details.
3. Implement the shift enjoyment calculation based on stress and morale.
4. Implement the daily review helper (maybe_update_desired_work_type) and
   call it in the per-agent update loop.
5. Extend assign_work_crews to incorporate preference and desired_work_type
   into its scoring.

### 7.2 Simplifications

- There is no explicit refusal to work or strike behaviour; preferences only
  bias assignment and desired_work_type.
- Transfer desire is recomputed from preferences; we do not yet model
  explicit negotiations with supervisors or council.
- Preferences do not directly alter performance; stress/morale and
  specialization already model this indirectly.

Once D-RUNTIME-0224 is implemented, the colony should exhibit meaningful
labour flows driven by how work feels to agents, laying the groundwork for
guild formation, privilege gradients, and resentment to emerge from the same
mechanics that drive productivity and survival.

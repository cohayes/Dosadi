---
title: Proto_Council_Protocol_Tuning_MVP
doc_id: D-LAW-0014
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-02
depends_on:
  - D-SCEN-0002   # Founding Wakeup Scenario
  - D-RUNTIME-0200   # Founding Wakeup Simulation Loop MVP
  - D-AGENT-0020   # Canonical Agent Model
  - D-AGENT-0022   # Agent Core (Python Shapes)
  - D-MEMORY-0102  # Episode Representation
  - D-MEMORY-0205  # Aggregated Beliefs & Facility Scores
---

# Proto Council Protocol Tuning (MVP)

## 1. Purpose & scope

This document specifies how the **proto council** in the Founding Wakeup scenario perceives
aggregate belief differences and responds with **small protocol adjustments**.

Scope is intentionally narrow:

- Phase: **Golden Age / Founding Wakeup** only.
- Actors: The initial **proto council** (tier-2-ish emergent body).
- Powers: Can only make **tiny, local protocol tweaks** to movement, access, and staffing.
- Goal: Reduce perceived risk and friction while preserving perceived fairness and legitimacy.

This MVP is *not* a full law system. It is a thin layer that:

1. Reads **aggregated place beliefs + simple metrics**.
2. Identifies a few **“hot” facilities** (queues, risks, resentment).
3. Proposes **bounded protocol changes**.
4. Records those changes and their subsequent **effects on beliefs**.

Later phases can expand the same loop to more powerful councils, guilds, and formal law bodies.


## 2. Conceptual frame

From D-LAW-0010 (Civilization risk loop), the basic pattern is:

1. **Individuals** form groups to reduce risk.
2. **Groups** coordinate assets to identify risk.
3. **Councils** author protocols to reduce those risks.

The proto council is the *first* instance of step 3. It operates under strict constraints:

- **No omniscience**: council only sees what is reported / logged.
- **No magic fixes**: it only adjusts existing knobs in small increments.
- **No hard-coded morality**: “good” protocols are those that reduce resentful episodes
  and near-miss / harm rates, as *experienced* by agents.

This keeps the loop compatible with future eras: the same logic can be scaled up to dukes,
guild councils, or cartel boards simply by widening the information and lever sets.


## 3. Inputs: what the proto council can see

### 3.1 Facility-level aggregates

Each tracked facility (pods, corridors, depots, crucial junctions, queue locations) exposes
a **summary view** derived from agent place beliefs and episodes (see D-MEMORY-0205):

- `safety_score` (0–1): low = many harm/threat episodes; high = calm, safe.
- `comfort_score` (0–1): crowding, heat, waiting, noise, smell, etc.
- `fairness_score` (0–1): perception of rules being predictable / non-arbitrary.
- `queue_pressure` (0–1): how often queues are long or slow.
- `incident_rate`: normalized count of harm / near-miss episodes per time window.

These are computed periodically from:

- **Episodes** tagged with `PLACE` and appropriate verbs (`QUEUE_DENIED`, `SHOVE`, `GUARD_HELPED`).
- **Belief updates**: agents updating their place beliefs with safety/fairness impressions.

The proto council does *not* see individual-level beliefs; it only sees these coarse aggregates.


### 3.2 Simple world metrics

For this MVP, the council can also see simple, low-cost metrics such as:

- Population by pod / facility (approximate).
- Average waiting time in key queues (if we have queue objects).
- Number of guards/volunteers assigned to facilities (if implemented).

These are treated as “instrument readings” alongside belief-derived scores.


## 4. Attention: how the proto council notices problems

The council periodically runs a **“scan & sort”** step on facilities:

1. Consider all facilities with any activity in the last window.
2. Compute a **problem score** for each facility, e.g.:

   ```text
   problem_score = w_safety * (1 - safety_score)
                 + w_fairness * (1 - fairness_score)
                 + w_queue * queue_pressure
                 + w_incident * normalized_incidents
   ```

3. Sort facilities by `problem_score` descending.
4. Take the top **K** facilities (small K, e.g. 3–5 for MVP) for discussion.

Weights `w_*` are small, configurable constants in the runtime / scenario config.

Outcome: the council does *not* try to fix everything at once; it chooses a short list of
“worst spots” to focus on during each decision window.


## 5. Levers: what can actually be tuned

To keep MVP complexity bounded, the proto council only has access to a small set of
**protocol knobs**, all of which are local and reversible.

Examples:

1. **Queue discipline knobs**

   - `max_queue_length` per facility (when exceeded, new arrivals are redirected).
   - `queue_priority_rule` (e.g. “injured first; children second; then arrival order”).

2. **Access & routing knobs**

   - `allow_bypass` from certain corridors to alternative depots.
   - `one_way` vs `two_way` flow in narrow corridors.

3. **Presence / staffing knobs** (if guard / volunteer agents exist)

   - `minimum_guard_presence` in a facility during peak hours.
   - `steward_on_duty_required` for specific risk-prone operations.

4. **Information knobs**

   - `post_protocol_summary` at the facility (yes/no, simple text or pictogram).
   - `queue_status_board` presence (coarse estimate of wait time / order).

Each knob has:

- A **current value** (e.g. `max_queue_length = 12`).
- A **safe range** (e.g. 5–20).
- A **step size** for tuning (e.g. ±2 per change).

The MVP rule: **each council cycle may adjust only a small number of knobs**, and only
by one step each.


## 6. Decision logic: mapping problems to knobs

For each “hot” facility selected in §4, the proto council:

1. Identifies the dominant problem components:

   - If `safety_score` is very low → prioritize **presence** and **access** knobs.
   - If `queue_pressure` is high but safety/fairness are OK → adjust **queue** knobs.
   - If `fairness_score` is low → consider **information** + clarifying priority rules.

2. Generates a small set of **candidate protocol changes** that are:

   - **Local**: they apply only to this facility or its immediate neighbors.
   - **Incremental**: change value by a single step toward the hypothesized fix.
   - **Explainable**: can be clearly described in a simple protocol summary.

3. Applies a simple **risk/benefit heuristic**:

   - Would this change plausibly reduce the most frequent negative episodes?
   - Does it create obvious new risks (e.g. overloading an alternate corridor)?
   - Is it within allowed `min/max` bounds for that knob?

4. Chooses at most `M` changes per decision window (e.g. `M = 2`).

The resulting changes are emitted as **protocol diff records** and applied to the
world’s protocol registry.


## 7. Recording changes and tracking effects

Every applied protocol change should produce at least one **protocol-related episode** for
the proto council’s own episodic memory, and optionally for affected agents:

- For the council agents:

  - Episodes like `PROTO_TWEAK_APPLIED` with `target_type=PLACE` and tags describing:
    - Facility id
    - Knob name
    - Old value → new value

- For ordinary agents (if they encounter the updated place):

  - `READ_PROTOCOL` or `HEARD_RULE_CHANGE` events when they see postings or hear announcements.
  - Regular local episodes (e.g. **shorter** waits or **fewer** incidents) that will
    eventually shift their place beliefs.

Over time, we can analyze:

- **Did safety/comfort/fairness scores move in the intended direction?**
- **Did incident rates around that facility go down?**
- **Did resentment episodes decrease?**

For MVP, we only need coarse tracking, but the structure should allow richer analytics later.


## 8. Cadence & limits

To avoid thrashing and overfitting, protocol tuning is intentionally slow:

- Council decision cadence: e.g. **once per simulation “day”** in the Founding wakeup loop.
- Limit of **K facilities** examined and **M changes** applied per decision.
- Simple refractory period: a facility that just received a change might be
  temporarily deprioritized for further changes (e.g. a “cooldown” of a few days),
  unless incident rates spike dramatically.

This helps ensure:

- Protocols have time to produce observable effects.
- The world does not feel like it is constantly rewriting the rules under agents’ feet.


## 9. MVP implementation notes

For Codex / implementation:

- Represent protocol knobs as small, typed records (e.g. `ProtocolKnob` dataclass)
  attached to facilities and/or global movement protocol configs.
- Implement a **council tuning function** that:
  - Reads aggregated facility scores + metrics from the world state.
  - Computes facility problem scores.
  - Chooses a small set of candidate knob changes.
  - Applies them and emits protocol diff episodes.
- Keep the tuning logic **parameterized** via scenario config so later scenarios can:
  - Turn tuning *off*.
  - Use different weights / cadences.
  - Expand the set of knobs and decision heuristics.

The guiding principle: **small, explainable, reversible adjustments** driven by the
same beliefs and episodes that all agents use. No external “designer magic,” only the
proto council acting within its limited horizon and tools.

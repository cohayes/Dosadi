---
title: Place_Belief_Updates_From_Queue_Episodes_MVP
doc_id: D-MEMORY-0205
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-02
depends_on:
  - D-MEMORY-0004   # Memory_Tiers_and_Belief_Archetypes
  - D-MEMORY-0102   # Episode_Data_Structures_and_Buffers_v0
  - D-MEMORY-0203   # Episode_Scoring_and_Defaults_v0
  - D-MEMORY-0204   # Episode_Tag_Catalog_MVP_v0
  - D-RUNTIME-0202  # Queue_Mechanics_MVP_v0
  - D-WORLD-0100    # Habitat_Layout_Prime_v0
  - D-SCEN-0001     # Wakeup_Scenario_Prime_v0
---

# 04_memory · Place Belief Updates From Queue Episodes MVP (D-MEMORY-0205)

## 1. Purpose & Scope

This document specifies how **queue-related episodes** update an agent’s
**place beliefs** in the early wakeup / Golden Age baseline.

Scope:

- Define the minimal `PlaceBelief` fields relevant to queues.
- Map queue episode tags (`queue_served`, `queue_denied`, `queue_canceled`,
  `queue_fight`) to updates on those fields.
- Describe how episode meta-data (importance, reliability, channel) and agent
  attributes modulate the update strength.
- Provide a concrete algorithm suitable for implementation in
  `PlaceBelief.update_from_episode(...)`.

This is an MVP focused on queues at facilities such as:

- `fac:suit-issue-1` (suit depot),
- `fac:assign-hall-1` (assignment hall),
- their queue-front nodes (`queue:*:front`).

Later documents can extend this approach to more episode types and belief
dimensions.

---

## 2. PlaceBelief: Fields Relevant to Queues

### 2.1 Core Fields

For MVP queue interactions, each `PlaceBelief` SHOULD expose at least:

- `fairness_score: float`
  - Perceived fairness of treatment at this place.
  - Range suggested: `[-1.0, +1.0]`, where:
    - `-1.0` = extremely unfair,
    - `0.0` = neutral/unknown,
    - `+1.0` = consistently fair.
- `efficiency_score: float`
  - Perceived speed / smoothness with which the place handles its work.
  - Range: `[-1.0, +1.0]`, where:
    - `-1.0` = extremely slow/inefficient,
    - `0.0` = neutral/unknown,
    - `+1.0` = consistently fast/effective.
- `safety_score: float`
  - Perceived personal safety at this place.
  - Range: `[-1.0, +1.0]`, where:
    - `-1.0` = dangerous / volatile,
    - `0.0` = neutral/unknown,
    - `+1.0` = very safe.
- `congestion_score: float`
  - Perceived crowding / jam-prone nature of the place.
  - Range: `[-1.0, +1.0]`, where:
    - `-1.0` = always empty / underused,
    - `0.0` = neutral/unknown,
    - `+1.0` = heavily crowded / jam-prone.
- `reliability_score: float`
  - Perceived reliability with respect to *getting what one comes for*.
  - Range: `[-1.0, +1.0]`, where:
    - `-1.0` = rarely works / often fails,
    - `0.0` = neutral/unknown,
    - `+1.0` = nearly always works.

Initialize all of these to `0.0` (unknown/neutral) unless scenario-specific
defaults are provided.

### 2.2 Internal Update Parameters

Internally, `PlaceBelief` SHOULD use a **smoothing factor** for EMA-style
updates:

- `alpha: float` (0.0–1.0)
  - Controls how quickly new evidence moves the belief.
  - Suggested default: `alpha = 0.1` (new evidence contributes ~10% of the
    final value per update).

Implementation detail:

```python
def _nudge(self, field_name: str, impact: float, alpha: float = 0.1) -> None:
    old = getattr(self, field_name, 0.0)
    new = old * (1.0 - alpha) + impact * alpha
    # Clamp to [-1.0, +1.0]
    new = max(-1.0, min(1.0, new))
    setattr(self, field_name, new)
```

The exact `alpha` can be adjusted by tier or attributes, but this helper
illustrates the intended behavior.

---

## 3. Mapping Queue Episodes to Belief Impacts

We assume that queue-related episodes are created via
`QueueEpisodeEmitter` (see D-RUNTIME-0202 and D-MEMORY-0204), with tags such
as:

- `queue_served`
- `queue_denied`
- `queue_canceled`
- `queue_fight`

These episodes refer to either:

- the **queue-front node** (`queue:*:front`), or
- the **facility node** (`fac:*`) associated with the queue.

`PlaceBelief.update_from_episode(...)` MUST interpret these tags and adjust
belief fields accordingly.

### 3.1 General Scaling Factors

For any episode `ep`, define:

- `base_importance = ep.importance` (0.0–1.0; see D-MEMORY-0203),
- `base_reliability = ep.reliability` (0.0–1.0),
- `channel_multiplier` from `ep.channel`:
  - DIRECT: `1.0`
  - OBSERVED: `0.75`
  - REPORT: `0.6`
  - RUMOR: `0.4`
  - PROTOCOL: `0.5`
  - BODY_SIGNAL: `1.0` (not expected for queue tags, but safe default),
- `arousal_multiplier` from `ep.emotion.arousal` (0.0–1.0):
  - `0.5 + 0.5 * ep.emotion.arousal` (0.5–1.0).

Then define an **overall episode weight**:

```text
episode_weight = base_importance * base_reliability
                 * channel_multiplier * arousal_multiplier
```

If `episode_weight` is extremely low (`< 0.01`), the update MAY be skipped.

### 3.2 Owner vs Observer Impact

For queue episodes, the update logic distinguishes between:

- **Owner**: the agent whose personal `Episode` record this is (served/denied
  participant).
- **Observer**: an agent who observed the event and received an `OBSERVED`
  episode.

We encode this difference by scaling the **raw impact** values:

- For the **owner**:
  - `owner_scale = 1.0`
- For an **observer**:
  - `observer_scale = 0.5`

The actual change applied is:

```text
impact_applied = base_impact * episode_weight * role_scale
```

where `base_impact` is tag-specific (see below).

### 3.3 Impacts for `queue_served`

Interpretation: “the place did what it was supposed to do.”

For the **served agent (owner)** at the queue’s place:

- `fairness_score`: `+0.2`
- `efficiency_score`: between `+0.05` and `+0.2` depending on wait time.
- `reliability_score`: `+0.1`

Observers at the same place receive half impact.

Implementation sketch:

```python
if "queue_served" in ep.tags:
    # Base impacts before scaling
    fairness_base = +0.2
    # If the episode has a 'wait_ticks' detail, map it:
    wait = ep.details.get("wait_ticks", 0)
    # Simple mapping: fast service gives higher efficiency impact
    if wait <= 50:
        efficiency_base = +0.2
    elif wait <= 200:
        efficiency_base = +0.1
    else:
        efficiency_base = +0.05

    reliability_base = +0.1

    scale = owner_scale_or_observer_scale  # see §3.2
    weight = episode_weight                # see §3.1

    self._nudge("fairness_score",   fairness_base   * weight * scale)
    self._nudge("efficiency_score", efficiency_base * weight * scale)
    self._nudge("reliability_score", reliability_base * weight * scale)
```

### 3.4 Impacts for `queue_denied`

Interpretation: “I came here, waited, and did not get what I needed.”

For the **denied agent (owner)**:

- `fairness_score`: `-0.4`
- `reliability_score`: `-0.4`
- `safety_score`: optionally `-0.05` to `-0.1` if the denial is harsh
  (`ep.emotion.threat` high).

For observers:

- Roughly half those magnitudes.

Implementation sketch:

```python
if "queue_denied" in ep.tags:
    fairness_base = -0.4
    reliability_base = -0.4

    # Optional safety penalty if denial felt threatening
    safety_base = -0.1 * ep.emotion.threat  # -0.1 at max threat

    scale = owner_scale_or_observer_scale
    weight = episode_weight

    self._nudge("fairness_score",    fairness_base   * weight * scale)
    self._nudge("reliability_score", reliability_base * weight * scale)
    if safety_base != 0.0:
        self._nudge("safety_score", safety_base * weight * scale)
```

### 3.5 Impacts for `queue_canceled`

Interpretation: “this place wasted my time / changed plans mid-stream.”

For affected agents (owner/observers share same pattern, but owner_scale vs
observer_scale still applies):

- `efficiency_score`: `-0.3`
- `reliability_score`: `-0.3`
- `fairness_score`: `-0.1` (mild unfairness perception).

Implementation sketch:

```python
if "queue_canceled" in ep.tags:
    efficiency_base = -0.3
    reliability_base = -0.3
    fairness_base = -0.1

    scale = owner_scale_or_observer_scale
    weight = episode_weight

    self._nudge("efficiency_score",  efficiency_base  * weight * scale)
    self._nudge("reliability_score", reliability_base * weight * scale)
    self._nudge("fairness_score",    fairness_base    * weight * scale)
```

### 3.6 Impacts for `queue_fight`

Interpretation: “this place is volatile / dangerous,” and possibly linked to
overcrowding or unfair treatment.

For all nearby agents (participants and observers), with owner/observer scaling:

- `safety_score`: `-0.6`
- `congestion_score`: `+0.1` (mild signal that it feels cramped / tense).
- `fairness_score`: small negative (e.g. `-0.1`) if the fight is associated
  with perceived unfairness (e.g. guard brutality) — this can be encoded via
  additional tags like `guard_brutal` in `ep.tags`.

Implementation sketch:

```python
if "queue_fight" in ep.tags:
    safety_base = -0.6
    congestion_base = +0.1
    fairness_base = -0.1 if "guard_brutal" in ep.tags else 0.0

    scale = owner_scale_or_observer_scale
    weight = episode_weight

    self._nudge("safety_score",      safety_base      * weight * scale)
    self._nudge("congestion_score",  congestion_base  * weight * scale)
    if fairness_base != 0.0:
        self._nudge("fairness_score", fairness_base * weight * scale)
```

---

## 4. Agent Attribute Modulation

At MVP, agent attributes only mildly modulate belief updates. This can be
implemented either inside `PlaceBelief._nudge` or at the call site in
`update_from_episode`.

Recommended simple rule:

- High `INT` and `WIL`:
  - slightly lower `alpha` (beliefs move more slowly overall),
  - but weight high-reliability episodes more (implicitly already handled
    by `episode_weight`).

For a practical MVP, it is acceptable to:

- Use a **fixed alpha** per tier, e.g.:
  - Tier-1: `alpha = 0.15` (beliefs move quickly, more volatile).
  - Tier-2: `alpha = 0.1`.
  - Tier-3: `alpha = 0.05` (beliefs move slowly, more stable).

`PlaceBelief` can receive `owner_tier` at construction or read from the owner
agent when updating; implementation details are left to code.

Trauma-specific behaviors are deferred to a later document.

---

## 5. PlaceBelief.update_from_episode: Algorithm Summary

`PlaceBelief.update_from_episode(ep: Episode, *, role_scale: float = 1.0)`
(or equivalent signature) SHOULD:

1. **Check location/target**:
   - If `ep.location_id` does not match this `place_id`, and `ep.target_id`
     does not match this `place_id`, return immediately.
2. **Compute episode_weight** (§3.1).
3. **Determine role scale** (§3.2):
   - `role_scale = 1.0` for owner episodes,
   - `role_scale = 0.5` for observer episodes.
4. For each queue-related tag in `ep.tags`:
   - Apply the corresponding impact rules:
     - `queue_served`: fairness, efficiency, reliability (§3.3).
     - `queue_denied`: fairness, reliability, safety (§3.4).
     - `queue_canceled`: efficiency, reliability, fairness (§3.5).
     - `queue_fight`: safety, congestion, fairness (§3.6).
   - For each impacted field, call `_nudge(field_name, base_impact * episode_weight * role_scale)`.
5. Clamp all scores to `[-1.0, +1.0]` (handled inside `_nudge`).

This logic is **additive**: multiple tags on a single episode can contribute
in one call, and episodes accumulate over time via EMA.

---

## 6. Integration & Future Extensions

### 6.1 Integration Points

- `AgentState.record_episode` already calls `update_beliefs_from_episode(ep)`.
- That method resolves or creates the relevant `PlaceBelief` and calls
  `place_belief.update_from_episode(ep, role_scale=...)`.
- `QueueEpisodeEmitter` must ensure that queue episodes:
  - have the correct `location_id` (`queue:*:front` or `fac:*`),
  - include relevant tags (`queue_served`, `queue_denied`, etc.),
  - optionally include `wait_ticks` in `details` for efficiency estimates.

### 6.2 Future Extensions (Out of Scope for MVP)

- Different belief dimensions for other episode categories (guards, stewards,
  med bays, exo-bays, guild halls).
- Richer use of agent attributes and trauma in modulating belief updates.
- Tier-3 “pattern-of-patterns” entities reading aggregate place beliefs across
  agents to fuel protocol changes.
- Integration with pathing and goal selection:
  - e.g. agents choosing between multiple depots based on their place beliefs.

This document focuses solely on the **first layer**: how queue interactions
shape place beliefs at the individual agent level.

---
title: Episode_Verbs_For_Initial_Work_Details_MVP
doc_id: D-MEMORY-0210
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-02
depends_on:
  - D-MEMORY-0102  # Episode_Representation
  - D-RUNTIME-0212 # Initial_Work_Detail_Taxonomy_MVP
  - D-MEMORY-0205  # Place_Belief_Updates_From_Queue_Episodes_MVP_v0
---

# Episode Verbs for Initial Work Details (MVP) — D-MEMORY-0210

## 1. Purpose & scope

This document defines a **small, standardized set of episode verbs** emitted by
the **initial work details** from D-RUNTIME-0212.

Goals:

- Give each work detail a **recognizable footprint** in episodic memory.
- Make it obvious how episodes should update:
  - **PlaceBeliefs** (safety, comfort, fairness, congestion, reliability),
  - **resource knowledge**,
  - and proto-council awareness via reports/ledgers.
- Keep the verb set **small but expressive**, so pattern-mining stays cheap.

Scope (MVP):

- Only verbs tied directly to the early work details:
  - SCOUT_INTERIOR / EXTERIOR
  - INVENTORY_STORES / STORES_STEWARD
  - ENV_CONTROL_DETAIL / SUIT_INSPECTION_DETAIL
  - FOOD_PROCESSING_DETAIL / WATER_HANDLING_DETAIL
  - SCRIBE_DETAIL / DISPATCH_DETAIL
- Focus on:
  - canonical verb name,
  - target type,
  - typical channel,
  - suggested tags + details,
  - intended belief updates.

---

## 2. General conventions

- `Episode.verb` is an **UPPER_SNAKE_CASE** string.
- `Episode.summary_tag` is a shorter, human-ish code (“interior_scout”, “crate_opened”).
- `Episode.target_type` is a coarse category from `EpisodeTargetType`:
  - SELF, PERSON, PLACE, FACTION, PROTOCOL, OBJECT, RESOURCE, OTHER.
- `Episode.tags` is a small set of strings used for clustering; tags are
  lowercase snake_case.
- `Episode.details` is a tiny structured payload (ints/floats/strings) with a
  few agreed keys per verb, but *never* large blobs.

Where we say “belief updates”, we’re specifying **what a later consolidation
function should do**, not that the episode itself performs the update.


---

## 3. Scout & survey verbs

### 3.1 SCOUT_PLACE

**Used by**: SCOUT_INTERIOR, SCOUT_EXTERIOR

- **verb**: `SCOUT_PLACE`
- **target_type**: PLACE
- **typical channel**: DIRECT (agent experiences it) or OBSERVED
- **summary_tag**: `"scout_place"`
- **tags**:
  - `{"scout", "mapping"}`
  - optionally `{"interior"}` or `{"exterior"}`
- **details** (suggested keys):
  - `{"hazard_level": 0–1, "visibility": 0–1, "distance_from_pod": float}`
  - `{"note": "short free-text label"}`

**Belief updates**:

- For target place’s `PlaceBelief`:
  - `safety_score` shifts up/down based on `hazard_level` and emotion.threat.
  - `comfort_score` may shift based on temperature / crowding notes, if present.
  - For exterior sites, we may also mark “mapped = True” in some separate structure.

---

### 3.2 CORRIDOR_CROWDING_OBSERVED

**Used by**: SCOUT_INTERIOR (and later, any work passing through busy corridors)

- **verb**: `CORRIDOR_CROWDING_OBSERVED`
- **target_type**: PLACE
- **channel**: DIRECT or OBSERVED
- **summary_tag**: `"corridor_crowding"`
- **tags**:
  - `{"corridor", "crowding", "queue_like"}`
- **details**:
  - `{"estimated_density": 0–1, "estimated_wait_ticks": int}`

**Belief updates**:

- For target place (corridor/junction):
  - increase `congestion_score` based on `estimated_density`.
  - if emotional valence is negative and arousal high → small hit to `comfort_score`.


### 3.3 HAZARD_FOUND

**Used by**: SCOUT_EXTERIOR, ENV_CONTROL_DETAIL, WATER_HANDLING_DETAIL

- **verb**: `HAZARD_FOUND`
- **target_type**: PLACE or RESOURCE (depending on context)
- **channel**: DIRECT
- **summary_tag**: `"hazard_found"`
- **tags**:
  - `{"hazard", "risk"}` plus subtype tags such as `{"structural"}`, `{"toxic_air"}`.
- **details**:
  - `{"hazard_type": "string", "severity": 0–1}`

**Belief updates**:

- For place:
  - decrease `safety_score` proportional to `severity`.
- Emotion:
  - set `threat` high; may also mark for stronger retention (importance).


---

## 4. Inventory & stores verbs

### 4.1 CRATE_OPENED

**Used by**: INVENTORY_STORES

- **verb**: `CRATE_OPENED`
- **target_type**: OBJECT or RESOURCE
- **channel**: DIRECT
- **summary_tag**: `"crate_opened"`
- **tags**:
  - `{"inventory", "crate", "resource_discovery"}`
- **details**:
  - `{"crate_id": "str", "resource_type": "str", "quantity": float}`

**Belief / knowledge updates**:

- Mainly informs **resource ledgers** rather than place beliefs.
- Optionally, can nudge `reliability_score` for the storage PLACE upward if
  supplies are consistently found where expected.


### 4.2 RESOURCE_STOCKED

**Used by**: INVENTORY_STORES, WATER_HANDLING_DETAIL, FOOD_PROCESSING_DETAIL

- **verb**: `RESOURCE_STOCKED`
- **target_type**: PLACE (store / depot)
- **channel**: DIRECT
- **summary_tag**: `"resource_stocked"`
- **tags**:
  - `{"inventory", "stocking"}`
- **details**:
  - `{"resource_type": "str", "quantity": float}`

**Belief updates**:

- For storage place:
  - slight increase in `reliability_score` (“this store is actually stocked”).


### 4.3 QUEUE_SERVED and QUEUE_DENIED

**Used by**: STORES_STEWARD, FOOD_PROCESSING_DETAIL, WATER_HANDLING_DETAIL

We standardize names for common queue outcomes.

#### QUEUE_SERVED

- **verb**: `QUEUE_SERVED`
- **target_type**: PLACE (queue front) or SELF (for “I was served”)
- **channel**: DIRECT
- **summary_tag**: `"queue_served"`
- **tags**:
  - `{"queue", "served"}`
- **details**:
  - `{"wait_ticks": int, "resource_type": "optional"}`

**Belief updates**:

- For queue place:
  - increase `reliability_score`.
  - slightly adjust `congestion_score` based on `wait_ticks`.
  - if wait was short, small boost to `comfort_score`.

#### QUEUE_DENIED

- **verb**: `QUEUE_DENIED`
- **target_type**: PLACE (queue front) and/or PERSON (steward)
- **channel**: DIRECT
- **summary_tag**: `"queue_denied"`
- **tags**:
  - `{"queue", "denied"}` plus maybe `{"perceived_unfair"}`
- **details**:
  - `{"reason": "string", "wait_ticks": int}`

**Belief updates**:

- For place:
  - decrease `fairness_score`, especially if emotion.valence is very negative.
  - potential small increase in `congestion_score` if wait was long.


### 4.4 DISPUTE_AT_STORES

**Used by**: STORES_STEWARD, SCRIBE_DETAIL (reporting)

- **verb**: `DISPUTE_AT_STORES`
- **target_type**: PLACE (store) or PERSON (other party)
- **channel**: DIRECT or REPORT
- **summary_tag**: `"dispute_at_stores"`
- **tags**:
  - `{"dispute", "tension", "stores"}`
- **details**:
  - `{"parties_involved": int, "escalated": bool}`

**Belief updates**:

- For store place:
  - if frequent, reduce `fairness_score` and `comfort_score`.
- For council/record keepers:
  - may weight store as a “problem spot” when scanning incidents.


---

## 5. Environment & suit verbs

### 5.1 ENV_NODE_TUNED

**Used by**: ENV_CONTROL_DETAIL

- **verb**: `ENV_NODE_TUNED`
- **target_type**: PLACE
- **channel**: DIRECT
- **summary_tag**: `"env_node_tuned"`
- **tags**:
  - `{"environment", "tuning", "airflow"}`
- **details**:
  - `{"delta_comfort": float, "delta_safety": float}` (signed, small).

**Belief updates**:

- For place:
  - apply `delta_comfort` and `delta_safety` to corresponding scores.
- Optional: downstream, body-signal episodes in that place become less negative.


### 5.2 ENV_NODE_FAILURE

**Used by**: ENV_CONTROL_DETAIL, SCOUT_INTERIOR

- **verb**: `ENV_NODE_FAILURE`
- **target_type**: PLACE
- **channel**: DIRECT or REPORT
- **summary_tag**: `"env_node_failure"`
- **tags**:
  - `{"environment", "failure", "risk"}`
- **details**:
  - `{"severity": 0–1}`

**Belief updates**:

- For place:
  - reduce `safety_score`, `comfort_score` proportional to severity.
- Emotion:
  - high threat, negative valence to encourage retention.


### 5.3 SUIT_TUNED

**Used by**: SUIT_INSPECTION_DETAIL

- **verb**: `SUIT_TUNED`
- **target_type**: PERSON or OBJECT (suit)
- **channel**: DIRECT
- **summary_tag**: `"suit_tuned"`
- **tags**:
  - `{"suit", "maintenance", "safety"}`
- **details**:
  - `{"improvement": 0–1}`

**Belief updates**:

- Not a place belief; more of a **self-belief** (“my suit is reliable”).
- May reduce agent’s internal threat perception when outside.


### 5.4 SUIT_FAILURE_NEAR_MISS

**Used by**: SUIT_INSPECTION_DETAIL, SCOUT_EXTERIOR

- **verb**: `SUIT_FAILURE_NEAR_MISS`
- **target_type**: PERSON
- **channel**: DIRECT
- **summary_tag**: `"suit_failure_near_miss"`
- **tags**:
  - `{"suit", "near_miss", "risk"}`
- **details**:
  - `{"severity": 0–1, "outside": bool}`

**Belief updates**:

- For **places** where this occurs:
  - slight hit to `safety_score` (environment is unforgiving).
- For **self-belief** about own suit:
  - large hit to perceived suit reliability.


---

## 6. Food & water verbs

### 6.1 FOOD_SERVED

**Used by**: FOOD_PROCESSING_DETAIL, STORES_STEWARD (if food is rationed from stores)

- **verb**: `FOOD_SERVED`
- **target_type**: PLACE (mess hall) or SELF
- **channel**: DIRECT
- **summary_tag**: `"food_served"`
- **tags**:
  - `{"food", "meal", "queue"}`
- **details**:
  - `{"wait_ticks": int, "calories_estimate": float}`

**Belief updates**:

- For mess hall place:
  - increase `reliability_score`.
  - adjust `congestion_score` based on `wait_ticks`.
  - if emotion.valence is positive, small bump to `comfort_score`.


### 6.2 FOOD_SHORTAGE_EPISODE

**Used by**: FOOD_PROCESSING_DETAIL, SCRIBE_DETAIL (report)

- **verb**: `FOOD_SHORTAGE_EPISODE`
- **target_type**: PLACE
- **channel**: DIRECT or REPORT
- **summary_tag**: `"food_shortage"`
- **tags**:
  - `{"food", "shortage", "queue"}`
- **details**:
  - `{"turned_away_count": int}`

**Belief updates**:

- For mess hall place:
  - reduce `reliability_score` and `fairness_score`.
  - can increase `queue_pressure` via consolidation if frequent.


### 6.3 BARREL_MOVED

**Used by**: WATER_HANDLING_DETAIL

- **verb**: `BARREL_MOVED`
- **target_type**: RESOURCE or PLACE
- **channel**: DIRECT
- **summary_tag**: `"barrel_moved"`
- **tags**:
  - `{"water", "logistics", "barrel"}`
- **details**:
  - `{"from": "place_id", "to": "place_id", "volume": float}`

**Belief / knowledge updates**:

- Mostly feeds logistic ledgers, but repeated reliable movements can boost
  `reliability_score` for depots along the path.


### 6.4 LEAK_FOUND

**Used by**: WATER_HANDLING_DETAIL, SCOUT_INTERIOR

- **verb**: `LEAK_FOUND`
- **target_type**: PLACE or RESOURCE
- **channel**: DIRECT
- **summary_tag**: `"leak_found"`
- **tags**:
  - `{"water", "loss", "risk"}`
- **details**:
  - `{"severity": 0–1, "estimated_loss": float}`

**Belief updates**:

- For place:
  - reduce `safety_score` (infrastructure is failing) and maybe `reliability_score`.
- For council metrics:
  - strong signal for “problem facility” in water handling.


### 6.5 WATER_LOSS_INCIDENT

**Used by**: WATER_HANDLING_DETAIL, SCRIBE_DETAIL

- **verb**: `WATER_LOSS_INCIDENT`
- **target_type**: PLACE
- **channel**: REPORT or DIRECT
- **summary_tag**: `"water_loss_incident"`
- **tags**:
  - `{"water", "loss_incident", "risk"}`
- **details**:
  - `{"volume_lost": float, "cause": "string"}`

**Belief updates**:

- For place:
  - reduce `reliability_score`, possibly `fairness_score` if blame is perceived.


---

## 7. Knowledge & coordination verbs

### 7.1 REPORT_RECEIVED

**Used by**: SCRIBE_DETAIL

- **verb**: `REPORT_RECEIVED`
- **target_type**: PLACE or OTHER (depending on content)
- **channel**: REPORT
- **summary_tag**: `"report_received"`
- **tags**:
  - `{"report", "scribe"}`
- **details**:
  - `{"source_agent_id": "str", "topic": "string"}`

**Belief updates**:

- This is more about **credibility** of sources; may update **person beliefs**
  later. For now, it is a key **information chain marker**.


### 7.2 MAP_UPDATED

**Used by**: SCRIBE_DETAIL

- **verb**: `MAP_UPDATED`
- **target_type**: PLACE
- **channel**: PROTOCOL or REPORT
- **summary_tag**: `"map_updated"`
- **tags**:
  - `{"map", "infrastructure"}`
- **details**:
  - `{"place_id": "str"}`

**Belief updates**:

- Signals that the proto council’s **world model** has improved; the episode
  itself mostly informs higher-tier pattern tracking.


### 7.3 LEDGER_UPDATED

**Used by**: SCRIBE_DETAIL, INVENTORY_STORES, WATER_HANDLING_DETAIL

- **verb**: `LEDGER_UPDATED`
- **target_type**: RESOURCE or PLACE
- **channel**: PROTOCOL or REPORT
- **summary_tag**: `"ledger_updated"`
- **tags**:
  - `{"ledger", "inventory"}`
- **details**:
  - `{"entry_type": "str", "delta_quantity": float}`

**Belief updates**:

- Primarily informs **resource patterns**; may later influence trust in record
  keepers or storerooms.


### 7.4 ASSIGNMENT_GIVEN

**Used by**: DISPATCH_DETAIL

- **verb**: `ASSIGNMENT_GIVEN`
- **target_type**: PERSON (assignee)
- **channel**: DIRECT
- **summary_tag**: `"assignment_given"`
- **tags**:
  - `{"assignment", "work_detail"}`
- **details**:
  - `{"work_detail_type": "str"}`

**Belief updates**:

- For the assignment hall place:
  - can increase `reliability_score` if agents feel work is predictable.


### 7.5 ASSIGNMENT_DISPUTE

**Used by**: DISPATCH_DETAIL, SCRIBE_DETAIL

- **verb**: `ASSIGNMENT_DISPUTE`
- **target_type**: PLACE (hall) or PERSON (dispatcher)
- **channel**: DIRECT or REPORT
- **summary_tag**: `"assignment_dispute"`
- **tags**:
  - `{"dispute", "assignment"}`
- **details**:
  - `{"escalated": bool}`

**Belief updates**:

- For assignment hall place:
  - frequent disputes reduce `fairness_score` and `comfort_score`.


---

## 8. Implementation notes (for EpisodeFactory)

When implementing these verbs:

- Prefer tiny helpers on `EpisodeFactory` like:

  - `create_scout_place_episode(...)`
  - `create_queue_served_episode(...)`
  - `create_food_served_episode(...)`
  - etc.

- Each helper should:
  - set `verb`, `target_type`, `summary_tag`, minimal `tags`,
  - populate the relevant `details` keys,
  - set a reasonable `importance` seed and emotion snapshot.

- Consolidation code (sleep / belief updates) can then switch on `verb` +
  `tags` to adjust corresponding `PlaceBelief` fields as described above.

D-MEMORY-0210 is the **vocabulary layer**; specific update formulas live in
the consolidation modules (e.g., extending D-MEMORY-0205’s logic beyond
queues into environment, food halls, and water handling.

---
title: Habitat_Layout_Prime
doc_id: D-WORLD-0100
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-01
depends_on:
  - D-RUNTIME-0001  # Simulation_Timebase
  - D-SCEN-0001     # Wakeup_Scenario_Prime_v0
---

# 03_world · Habitat Layout Prime v0 (D-WORLD-0100)

## 1. Purpose & Scope

This document defines the **minimal spatial layout** for the initial Dosadi
habitat in the Golden Age Baseline, sufficient to:

- Support Wakeup Scenario Prime (D-SCEN-0001),
- Host the core queues (wakeup, med, suit, assignment, exception),
- Provide a simple but extensible graph of pods, corridors, and facilities
  that can scale into a full city over centuries.

The focus is on **topology and ids**, not visual fidelity. It is intended to
drive both the Python simulation (world graph) and, later, a Unity front-end.

---

## 2. High-Level Structure

At tick 0, the inhabited world consists of:

- A **central Well core** (sealed, inaccessible to colonists),
- A ring of **bunk pod blocks** around the core,
- A small set of **primary corridors** that connect pods to shared facilities,
- A handful of **shared facilities** (med bay, suit issue, assignment hall,
  canteen) and an **exception/holding area**.

Conceptually, everything sits inside a cylindrical or spherical habitat shell
sunk deep around the Well. In v0 we treat it as a simple 2D graph.

---

## 3. Node Types & Naming

We model the habitat as a set of nodes with stable ids, grouped by type:

- **Core / utility**:
  - `core:well` — the Well core (no direct colonist access in v0).
- **Pods** (sleeping blocks):
  - `pod:A`, `pod:B`, `pod:C`, `pod:D` (configurable count).
- **Corridors**:
  - `corr:main-core` — primary ring/spine near the core.
  - `corr:med` — spur toward med bay.
  - `corr:suit` — spur toward suit depot.
  - `corr:assign` — spur toward assignment hall.
  - `corr:canteen` — spur toward canteen (optional in v0).
  - `corr:holding` — spur toward exception/holding.
- **Facilities**:
  - `fac:med-bay-1` — medical bay & triage area.
  - `fac:suit-issue-1` — basic suit issue depot.
  - `fac:assign-hall-1` — assignment & admin hall.
  - `fac:canteen-1` — initial ration bay / canteen (optional usage in v0).
  - `fac:holding-1` — exception / holding area.
- **Queue front areas** (optional explicit nodes):
  - `queue:suit-issue:front` — standing area in front of suit depot.
  - `queue:assignment:front` — standing area in front of assign hall.
  - `queue:med-triage:front` — med waiting area.

Queues themselves will have their own logical `queue_id`s (see D-SCEN-0001);
these front nodes serve as their spatial anchor points.

All ids follow the `kind:name` convention already used in other docs.

---

## 4. Topology (Edges)

We treat movement as happening along edges connecting nodes. For v0, we define
an undirected graph (movement is symmetric) with edges like:

- Pods ↔ main corridor
  - `pod:A` ↔ `corr:main-core`
  - `pod:B` ↔ `corr:main-core`
  - `pod:C` ↔ `corr:main-core`
  - `pod:D` ↔ `corr:main-core`
- Main corridor ↔ corridor spurs
  - `corr:main-core` ↔ `corr:med`
  - `corr:main-core` ↔ `corr:suit`
  - `corr:main-core` ↔ `corr:assign`
  - `corr:main-core` ↔ `corr:canteen`
  - `corr:main-core` ↔ `corr:holding`
- Corridor spurs ↔ facilities
  - `corr:med` ↔ `fac:med-bay-1`
  - `corr:suit` ↔ `fac:suit-issue-1`
  - `corr:assign` ↔ `fac:assign-hall-1`
  - `corr:canteen` ↔ `fac:canteen-1`
  - `corr:holding` ↔ `fac:holding-1`
- Corridors ↔ queue fronts (if modeled as separate nodes)
  - `corr:med` ↔ `queue:med-triage:front`
  - `corr:suit` ↔ `queue:suit-issue:front`
  - `corr:assign` ↔ `queue:assignment:front`

In code, this can be represented as an adjacency mapping, e.g.:

```python
graph = {
    "pod:A": {"corr:main-core"},
    "pod:B": {"corr:main-core"},
    "pod:C": {"corr:main-core"},
    "pod:D": {"corr:main-core"},
    "corr:main-core": {
        "pod:A", "pod:B", "pod:C", "pod:D",
        "corr:med", "corr:suit", "corr:assign", "corr:canteen", "corr:holding",
    },
    "corr:med": {"corr:main-core", "fac:med-bay-1", "queue:med-triage:front"},
    "corr:suit": {"corr:main-core", "fac:suit-issue-1", "queue:suit-issue:front"},
    "corr:assign": {"corr:main-core", "fac:assign-hall-1", "queue:assignment:front"},
    "corr:canteen": {"corr:main-core", "fac:canteen-1"},
    "corr:holding": {"corr:main-core", "fac:holding-1"},
    "fac:med-bay-1": {"corr:med"},
    "fac:suit-issue-1": {"corr:suit"},
    "fac:assign-hall-1": {"corr:assign"},
    "fac:canteen-1": {"corr:canteen"},
    "fac:holding-1": {"corr:holding"},
    "queue:med-triage:front": {"corr:med"},
    "queue:suit-issue:front": {"corr:suit"},
    "queue:assignment:front": {"corr:assign"},
}
```

The exact code structure lives in the world implementation, not in this doc; the
above is illustrative.

---

## 5. Environmental Conditions

For each node we define **environmental flags** that matter for suits,
body signals, and risk:

- `sealed`: fully controlled environment, breathable air.
- `hostile`: harsh atmosphere; unprotected exposure is dangerous.
- `conditioned`: partially controlled; safe with basic suits but stressful.
- `density_baseline`: expected crowding when simulation is “calm”.

Suggested v0 defaults:

- `pod:*`:
  - `sealed = True`
  - `hostile = False`
  - `conditioned = True`
  - `density_baseline = low`
- `corr:main-core` and `corr:*`:
  - `sealed = False`
  - `hostile = True` (outside pod doors)
  - `conditioned = True` (local mitigations; basic suits required)
  - `density_baseline = medium`
- `fac:med-bay-1`, `fac:suit-issue-1`, `fac:assign-hall-1`, `fac:canteen-1`:
  - `sealed = False`
  - `hostile = False`
  - `conditioned = True`
  - `density_baseline = medium/high` depending on facility.
- `fac:holding-1`:
  - `sealed = True`
  - `hostile = False`
  - `conditioned = minimal` (comfort intentionally low)
  - `density_baseline = low`.

In code, these can be captured in a `Location`/`Place` data structure with
fields used by body/health subsystems to emit `body_heat_stress_*` and similar
episodes.

---

## 6. Queue Anchors & Movement Flows

We tie Wakeup Scenario Prime’s queues (D-SCEN-0001) to concrete locations:

- Wake queue:
  - Not tied to a dedicated node; agents are effectively in `pod:*` and then
    step into `corr:main-core` as they wake.
- Med triage queue:
  - `queue_id = "queue:med-triage"`,
  - `location_id = "queue:med-triage:front"`,
  - physically adjacent to `corr:med` and `fac:med-bay-1`.
- Suit issue queue:
  - `queue_id = "queue:suit-issue"`,
  - `location_id = "queue:suit-issue:front"`,
  - adjacent to `corr:suit` and `fac:suit-issue-1`.
- Assignment queue:
  - `queue_id = "queue:assignment"`,
  - `location_id = "queue:assignment:front"`,
  - adjacent to `corr:assign` and `fac:assign-hall-1`.
- Exception queue (if implemented):
  - `queue_id = "queue:exception"`,
  - `location_id` can be represented as a waiting zone inside `fac:holding-1`
    or as a separate node like `queue:exception:front` adjacent to `corr:holding`.

**Typical wakeup path for a colonist**:

1. Start in `pod:A` (sleeping).
2. Wake, step into `corr:main-core`.
3. Move via `corr:med` toward med triage (if flagged).
4. Move via `corr:suit` to `queue:suit-issue:front` and then `fac:suit-issue-1`.
5. Move via `corr:assign` to `queue:assignment:front` and `fac:assign-hall-1`.
6. Eventually move to assigned bunk (one of the `pod:*` nodes) or work posts
   (not yet defined in v0).

This path provides multiple opportunities for **episode generation**:

- crowding and delays in corridors,
- queue outcomes,
- guard/steward behaviors near bottlenecks,
- body signals under mild environmental stress.

---

## 7. Capacity & Crowding Parameters

Each node can expose simple capacity/crowding hints for future use in:

- hazard generation,
- discomfort/body signals,
- belief updates about safety and comfort.

Suggested fields:

- `max_occupancy_soft`: recommended max number of agents,
- `max_occupancy_hard`: absolute cap (beyond this, movement or queuing is blocked),
- `crowding_thresholds`:
  - e.g. `[0.3, 0.6, 0.9]` of soft capacity for mild/moderate/high crowding.

Illustrative defaults:

- `pod:*`:
  - soft = 40, hard = 50.
- `corr:main-core`:
  - soft = 100, hard = 150.
- `corr:*` spurs:
  - soft = 40, hard = 60.
- `fac:*` (med, suit, assign, canteen):
  - soft = 60, hard = 90.
- `queue:*:front` nodes:
  - soft = 30, hard = 45.

These parameters can be tuned in configuration files; this doc only suggests
initial values.

---

## 8. Extensibility & Future Growth

Habitat Layout Prime is intentionally small. Future documents can:

- Add sub-corridors and additional pod blocks:
  - `pod:E`, `pod:F`, new spur corridors, additional med bays, etc.
- Define industrial, maintenance, and exo-bay areas as new `fac:*` nodes:
  - `fac:exo-bay-1`, `fac:workshop-1`, `fac:farm-1`, etc.
- Introduce vertical levels or rings:
  - `level:core`, `level:mid`, `level:outer`, with cross-level connectors.

All such expansions should:

- Preserve existing ids used in this document (for backward compatibility),
- Extend the same graph model and environmental flag scheme,
- Maintain the Well core as the ultimate resource anchor (even if indirect).

---

## 9. Implementation Notes (Non-binding)

When implementing this layout in code, Codex SHOULD:

- Create a world module, e.g. `dosadi.world.layout_prime`, that exposes:
  - a function like `build_habitat_layout_prime(config) -> WorldLayout`,
  - where `WorldLayout` minimally includes:
    - node ids,
    - adjacency mapping,
    - per-node environment flags and capacities.
- Ensure node ids in the layout exactly match those used in:
  - Wakeup Scenario Prime (D-SCEN-0001),
  - the queue episode helpers (e.g. `queue:suit-issue:front`),
  - any scenario generators.

This document is the source of truth for **names and connectivity**. Detailed
physics, rendering, and high-fidelity environmental simulation are deferred
to later world and engine documents.

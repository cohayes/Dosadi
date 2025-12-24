---
title: Resource_Extraction_Sites_v1_Implementation_Checklist
doc_id: D-RUNTIME-0256
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-25
depends_on:
  - D-RUNTIME-0234   # Survey Map v1
  - D-RUNTIME-0236   # Expansion Planner v1
  - D-RUNTIME-0238   # Logistics Delivery v1
  - D-RUNTIME-0240   # Construction Workforce Staffing v1
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0243   # Event → Memory Router v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0251   # Construction Materials Economy v1
  - D-RUNTIME-0252   # Facility Types & Recipes v1
  - D-RUNTIME-0255   # Exploration & Discovery v1
---

# Resource Extraction Sites v1 — Implementation Checklist

Branch name: `feature/resource-extraction-sites-v1`

Goal: turn “discovered resource tags” into real, deterministic **daily material flows** by introducing:
- extraction sites attached to SurveyMap nodes (derived from discovery tags),
- simple yields (materials/day) that land into local inventories,
- staffing (optional v1) and minimal incidents (downtime) hooks,
- planner signals so expansion builds depots/workshops near productive sites,
- events → memory → beliefs to shape route choice and politics.

This is the “exploration pays off” bridge from Discovery → Economy → Construction.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Feature flag default OFF.** With flag OFF, no new material flows occur.
2. **Deterministic yields.** Same seed/state → same daily outputs.
3. **Bounded compute.** Iterate only over known extraction sites (not all nodes, not all agents).
4. **Save/Load safe.** Site state serializes; old snapshots load.
5. **Integrates with inventories.** Outputs go to InventoryRegistry owners.
6. **Tested.** Determinism, caps, snapshot roundtrip, and planner integration.

---

## 1) Concept model

### 1.1 Site types
A resource extraction site is a lightweight entity at a node:
- `SCRAP_FIELD` → produces `SCRAP_INPUT` or directly `SCRAP_METAL` / `PLASTICS`
- `SALVAGE_CACHE` → produces small trickle of mixed parts
- `BRINE_POCKET` → (later) water-related outputs; v1 can produce `SEALANT` precursor or “salts”
- `THERMAL_VENT` → (later) power/heat; v1 can reduce facility downtime risk (optional)

In v1, keep it simple: focus on scrap/salvage that fuels construction.

### 1.2 Ownership and inventories
Each site has an inventory owner_id:
- `site:{site_id}`

A site can either:
- deposit outputs into its own inventory (recommended), or
- deposit directly to nearest depot inventory (optional)

Recommended v1:
- deposit to site inventory; logistics must pick it up to be useful.

### 1.3 Yield cadence
Yields occur **once per day** as part of the daily pipeline.

---

## 2) Implementation Slice A — Data structures

Create `src/dosadi/world/extraction.py`

**Deliverables**
- `class SiteKind(Enum): SCRAP_FIELD, SALVAGE_CACHE, BRINE_POCKET, THERMAL_VENT`

- `@dataclass(slots=True) class ExtractionSite:`
  - `site_id: str`
  - `kind: SiteKind`
  - `node_id: str`
  - `created_day: int`
  - `richness: float = 0.5`           # 0..1
  - `depletion: float = 0.0`          # 0..1 (v1 optional; can keep constant)
  - `down_until_day: int = -1`        # incident hook
  - `tags: set[str] = field(default_factory=set)`
  - `notes: dict[str, object] = field(default_factory=dict)`

- `@dataclass(slots=True) class ExtractionLedger:`
  - `sites: dict[str, ExtractionSite]`
  - `sites_by_node: dict[str, list[str]]`
  - `def signature(self) -> str`

Store on world:
- `world.extraction: ExtractionLedger`

Snapshot it.

---

## 3) Implementation Slice B — Site creation from discovery tags

When new nodes are discovered (0255), they may have `resource_tags` and `resource_richness`.

### B1. Tag → site mapping
Create sites deterministically:
- if node has tag `scrap_field` → create `SiteKind.SCRAP_FIELD`
- if node has tag `salvage_cache` → create `SiteKind.SALVAGE_CACHE`
- (optional) `brine_pocket` → BRINE_POCKET
- (optional) `thermal_vent` → THERMAL_VENT

### B2. Stable site IDs
Deterministic and collision-safe:
- `site_id = f"site:{node_id}:{kind.value}"`

### B3. One-time creation guard
If site already exists for that (node_id, kind), do nothing.

Emit event:
- `EXTRACTION_SITE_CREATED` with node_id, site_id, kind, richness.

---

## 4) Implementation Slice C — Yield tables + deterministic yield function

Create `src/dosadi/runtime/extraction_runtime.py`

**Deliverables**
- `@dataclass(slots=True) class ExtractionConfig:`
  - `enabled: bool = False`
  - `max_units_per_day_global: int = 10000`
  - `max_units_per_site_per_day: int = 200`
  - `yield_jitter: float = 0.15`            # 0..0.5
  - `phase2_yield_mult: float = 0.90`       # scarcity pressure
  - `auto_pickup_requests: bool = True`
  - `pickup_min_batch: int = 20`
  - `deterministic_salt: str = "extract-v1"`

- `@dataclass(slots=True) class ExtractionState:`
  - `last_run_day: int = -1`

Add to world:
- `world.extract_cfg`, `world.extract_state`

Snapshot them.

### C1. Yield table (base yields)
Define a small table in code:

- SCRAP_FIELD:
  - produces `SCRAP_INPUT: 30 * richness` (or directly SCRAP_METAL/PLASTICS)
- SALVAGE_CACHE:
  - produces `FASTENERS: 4 * richness`, `SEALANT: 2 * richness`, `SCRAP_METAL: 6 * richness`
- BRINE_POCKET (optional):
  - produces `SEALANT: 1 * richness` (placeholder)
- THERMAL_VENT (optional):
  - yields none (v1), but can emit a tag/event for later.

Use integer rounding rules deterministically.

### C2. Deterministic jitter
For each site/day/material:
- `u = hashed_unit_float("yield", salt, site_id, str(day), material_name)`
- `mult = 1 - yield_jitter + (2*yield_jitter*u)`  # in [1-j, 1+j]
- yield = round(base * mult), clamped

### C3. Depletion (optional v1)
Optional:
- reduce yield by `(1 - depletion)`
- increase depletion slowly

---

## 5) Implementation Slice D — Daily yield runner

Implement:
- `def run_extraction_for_day(world, *, day: int) -> None`

Rules:
- iterate sites in deterministic order (site_id sorted)
- skip if `site.down_until_day >= day`
- compute yields per table + jitter + phase multiplier
- enforce per-site cap and global cap deterministically
- deposit outputs into:
  - owner_id = `site:{site_id}`
  - `world.inventories.inv(owner_id).add(material, qty)`

Emit events:
- `EXTRACTION_YIELD` (site_id, kind, node_id, outputs, day)
- optionally `EXTRACTION_SITE_DOWN` if skipped due to downtime

Telemetry counters updated.

---

## 6) Implementation Slice E — Pickup logistics (optional but recommended)

If `auto_pickup_requests`:
- when a site inventory exceeds `pickup_min_batch`,
  - create a delivery request from site inventory owner to nearest depot inventory owner.

### E1. Choose depot deterministically
- prefer depots (FacilityKind.DEPOT) by nearest node/ward if known; else pick first depot by facility_id.

### E2. Avoid duplicate pickups
- store `site.notes["pending_pickup_delivery_id"]`
- only create a new pickup if none pending.

### E3. Delivery payload
- include `pickup_site_id`, `node_id`, `materials`, `priority="extraction"`

On delivery completion:
- remove materials from site inventory (source)
- add to depot inventory (destination)

---

## 7) Planner integration (why sites matter)

### 7.1 Expansion scoring
Add “resource bonus” into Expansion Planner scoring:
- SCRAP_FIELD > SALVAGE_CACHE > others
- daily yield volume can add bonus if tracked
- route risk adds penalty

### 7.2 Construction priorities
Decision Hooks may prioritize:
- building a depot/workshop near the top-yield site,
- additional scouts if shortages persist.

---

## 8) Incidents integration (minimal)

Support downtime field `down_until_day`.
Optional later: incident engine can set downtime via deterministic draws.

---

## 9) Events → Memory → Beliefs

Router crumbs:
- `resource-site:{kind}:{node_id}`
- `site-reliability:{site_id}` (from down events)

Beliefs can later influence escorts, routing, and investment.

---

## 10) Save/Load requirements

Snapshot must include:
- extraction ledger + site fields + notes
- extract_cfg/state

Old snapshots:
- extraction ledger defaults empty
- config disabled

---

## 11) Telemetry

Counters:
- `metrics["extraction"]["sites"]`
- `metrics["extraction"]["units_produced"]`
- `metrics["extraction"]["units_capped_site"]`
- `metrics["extraction"]["units_capped_global"]`
- `metrics["extraction"]["pickups_requested"]`
- `metrics["extraction"]["pickups_completed"]`

---

## 12) Tests (must-have)

Create `tests/test_extraction_sites.py`.

### T1. Flag off = no yields
- enabled=False → inventories unchanged.

### T2. Deterministic yields
- same world clone → same yields and inventory signatures.

### T3. Cap enforcement
- set small per-site/global caps; ensure deterministic capping.

### T4. Site creation from discovery tag
- discovered node with scrap_field tag → site created with stable id.

### T5. Pickup request creation bounded + no duplicates
- site inventory above threshold → one pickup request created; rerun day → no duplicates.

### T6. Delivery completion transfers materials
- complete pickup delivery; site inventory decreases; depot inventory increases.

### T7. Snapshot roundtrip
- save mid-yield/pending pickup; load; continue; identical final signature.

---

## 13) Codex Instructions (verbatim)

### Task 1 — Add extraction ledger + site schema
- Create `src/dosadi/world/extraction.py` with SiteKind, ExtractionSite, ExtractionLedger
- Add `world.extraction` to snapshots

### Task 2 — Create sites from discovery tags
- On node discovery (or post-discovery hook), map resource tags to sites deterministically
- Use stable `site:{node_id}:{kind}` IDs and avoid duplicates
- Emit EXTRACTION_SITE_CREATED event

### Task 3 — Add extraction runtime
- Create `src/dosadi/runtime/extraction_runtime.py` with ExtractionConfig/State
- Implement deterministic yield tables with hashed jitter and caps
- Deposit yields into `site:{site_id}` inventories and emit EXTRACTION_YIELD events

### Task 4 — Optional pickup logistics
- If enabled, create bounded pickup delivery requests from site inventories to depots
- Avoid duplicate pickup requests and ensure delivery completion transfers materials

### Task 5 — Planner integration + tests
- Add resource bonus into Expansion Planner scoring
- Add `tests/test_extraction_sites.py` implementing T1–T7
- Add telemetry counters

---

## 14) Definition of Done

- `pytest` passes.
- With enabled=False: no behavior change.
- With enabled=True:
  - sites are created deterministically from discovery tags,
  - daily yields are deterministic and capped,
  - outputs land in inventories and can be picked up via deliveries,
  - expansion planning reacts to discovered productive sites,
  - save/load works mid-cycle.

---

## 15) Next slice after this

**Depot Network & Stockpile Policy v1** (min/max thresholds, pull/push rules),
so extraction output flows reliably into the construction economy.

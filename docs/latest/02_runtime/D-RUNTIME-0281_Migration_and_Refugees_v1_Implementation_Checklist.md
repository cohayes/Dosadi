---
title: Migration_and_Refugees_v1_Implementation_Checklist
doc_id: D-RUNTIME-0281
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0231   # Save/Load Seed Vault
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0259   # Expansion Planner v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0271   # Governance Failure Incidents v1
  - D-RUNTIME-0278   # War & Raids v1
  - D-RUNTIME-0280   # Diplomatic Deterrence v1
---

# Migration & Refugees v1 — Implementation Checklist

Branch name: `feature/migration-refugees-v1`

Goal: model population movement under collapse/war/scarcity so that:
- refugees pressure safe wards,
- legitimacy and culture shift via demographic stress,
- corridor topology and ward specializations evolve,
- the empire’s political map changes without needing micro agent travel for everyone.

v1 uses macro population “flows,” not individual migration agents.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same migration flows.
2. **Bounded.** Compute flows over TopK corridors and wards; no global heavy routing scans.
3. **Capacity-aware.** Wards have intake capacity; overflow causes camps/unrest.
4. **Composable.** War, corridor collapse, customs, and institutions affect flows.
5. **Political impact.** Migration changes culture norms and legitimacy/unrest.
6. **Tested.** Flow computation, capacity, effects, persistence.

---

## 1) Concept model

Each ward maintains a macro “population load” and a “displacement pressure”:
- shocks (raids, corridor collapse, famine, governance failures) create displacement
- displaced people choose destinations based on:
  - safety (risk),
  - accessibility (corridors),
  - acceptance (institutions/culture),
  - resource availability (markets/stockpiles).

Migration is represented as daily/weekly flows between wards.

---

## 2) Data structures

Create `src/dosadi/runtime/migration.py`

### 2.1 Config
- `@dataclass(slots=True) class MigrationConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 3`        # compute flows every N days
  - `neighbor_topk: int = 12`
  - `route_topk: int = 24`
  - `max_total_movers_per_update: int = 5000`
  - `deterministic_salt: str = "migration-v1"`
  - `camp_decay_per_day: float = 0.02`   # camps resolve slowly if resources improve

### 2.2 Ward migration state
- `@dataclass(slots=True) class WardMigrationState:`
  - `ward_id: str`
  - `pop: int = 0`                 # macro population count (or proxy)
  - `displaced: int = 0`           # people currently seeking relocation
  - `camp: int = 0`                # overflow not absorbed (refugee camp proxy)
  - `intake_capacity: int = 0`     # how many displaced can be absorbed per update
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

### 2.3 Flow record (bounded)
- `@dataclass(slots=True) class MigrationFlow:`
  - `day: int`
  - `from_ward: str`
  - `to_ward: str`
  - `movers: int`
  - `reason_codes: list[str]`

World stores:
- `world.migration_cfg`
- `world.migration_by_ward: dict[str, WardMigrationState]`
- `world.migration_flows: list[MigrationFlow]` (bounded)

Persist migration states in snapshots and seeds; flow history bounded and optional in seeds.

---

## 3) Initial population and capacity

Where pop comes from:
- v1 can initialize each ward pop from scenario params or a simple distribution.

Intake capacity computed from:
- housing facilities (0272 / facility types),
- food/water stockpile surplus (0257/0263),
- institutional openness policy (add dial),
- enforcement stability (0265),
- corridor accessibility (0261),
- disease pressure (optional later).

Add institution policy dials:
- `refugee_intake_bias` (-0.5..+0.5)
- `border_closure_bias` (-0.5..+0.5) (affects willingness to accept + customs friction)

---

## 4) Displacement generation (sources of refugees)

Each update, increase displaced for a ward based on shock signals:
- corridor collapse nearby (0278 stress/collapse): `DISPLACEMENT_CORRIDOR_COLLAPSE`
- raids on ward or inbound lifelines: `DISPLACEMENT_RAIDS`
- severe shortages (0263): `DISPLACEMENT_FAMINE`
- governance failures (0271): `DISPLACEMENT_UNREST`
- disease (future): `DISPLACEMENT_DISEASE`

Displacement rate is deterministic and bounded:
- displaced += int(pop * shock_factor) capped
- plus camp spillover if camp grew too large.

---

## 5) Destination selection (bounded neighbor graph)

We do not solve a global min-cost flow problem.

For each origin ward with displaced > 0:
1) consider TopK neighbor wards (by corridor adjacency and travel feasibility)
2) score each destination:
- safety score: inverse of corridor risk + raid pressure
- resource score: market surplus / stockpile
- acceptance score: openness policy + culture affinity (0270)
- accessibility: corridor availability (collapsed corridors block)
3) allocate movers deterministically:
- softmax-ish deterministic allocation or greedy fill by score,
- stop when origin displaced exhausted or global cap reached.

Apply customs/border closure effects:
- if border_control policy hostile (0275/0270), reduce effective acceptance or add delays.

---

## 6) Applying flows (capacity + camps)

When movers arrive:
- if destination has intake capacity:
  - absorbed into pop
- else:
  - overflow goes to destination camp:
    - camps increase unrest and disease risk (future),
    - camps increase smuggling and black market exposure (optional later).

Origin ward:
- displaced decreases,
- pop decreases only if you choose to model actual moving population counts.
v1 recommendation:
- treat displaced as moving “load” and keep pop stable initially, OR move pop directly if you want demographics.
Pick one and keep consistent; simplest is moving pop.

---

## 7) Political effects

Migration should shift:
- legitimacy/unrest (0269/0271):
  - high camp and rapid influx increase unrest
  - successful absorption with supplies can increase legitimacy
- culture norms (0270):
  - repeated influx can shift xenophobia, cooperation, smuggling tolerance
- faction power (0266):
  - camps can become recruitment pools for raiders or rebels (optional v2)

Keep v1 minimal:
- camps increase unrest,
- openness policy trades off unrest vs labor/economic growth.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["migration"]["total_displaced"]`
- `metrics["migration"]["total_camp"]`
- `metrics["migration"]["flows_count"]`
- `metrics["migration"]["movers_total"]`

TopK:
- wards with biggest camps
- biggest origin wards by displaced
- biggest destination wards by influx

Cockpit:
- ward migration page: pop, displaced, camp, intake_capacity, recent inflow/outflow
- flow log (recent N)
- “pressure map”: where displacement is being generated and where it’s accumulating

Events:
- `DISPLACEMENT_SPIKE`
- `REFUGEE_FLOW`
- `CAMP_GROWTH`
- `CAMP_RESOLVED`

---

## 9) Persistence / seed vault

Export stable:
- `seeds/<name>/migration.json` with pop/displaced/camp per ward (sorted).

---

## 10) Tests (must-have)

Create `tests/test_migration_refugees_v1.py`.

### T1. Determinism
- same shocks and corridor availability → same flows.

### T2. Capacity and camps
- when intake capacity exceeded, overflow becomes camp.

### T3. Corridor collapse blocks flows
- collapsed corridor reduces destination accessibility and reroutes/blocks flows.

### T4. Political effects
- camp growth increases unrest deterministically (bounded).

### T5. Boundedness
- flows are capped; neighbor_topk respected.

### T6. Snapshot roundtrip
- pop/displaced/camp persist and continue deterministically.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add migration module + ward migration state
- Create `src/dosadi/runtime/migration.py` with MigrationConfig, WardMigrationState, MigrationFlow
- Add world.migration_by_ward and bounded migration_flows to snapshots + seeds

### Task 2 — Compute displacement and flows on cadence
- Generate displaced from raids, shortages, governance failures, and corridor collapse signals
- For each origin, consider TopK neighbors and compute deterministic destination scores
- Allocate movers with capacity constraints and global cap

### Task 3 — Apply political/cultural effects
- Camps increase unrest; absorption can increase legitimacy if resources permit
- Emit events and telemetry

### Task 4 — Cockpit + tests
- Add migration cockpit pages and metrics/topK
- Add `tests/test_migration_refugees_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - shocks generate displacement,
  - refugees move deterministically through available corridors,
  - camps form when capacity is exceeded and increase unrest,
  - migration state persists into seeds,
  - cockpit explains population pressure and flow dynamics.

---

## 13) Next slice after this

**Urban Growth & Zoning v1** — convert migration pressure into construction:
- new housing/utility projects,
- ward specialization,
- and long-run city morphology driven by population movement.

---
title: Smuggling_Networks_v1_Implementation_Checklist
doc_id: D-RUNTIME-0276
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0231   # Save/Load Seed Vault
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0263   # Economy Market Signals v1
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0275   # Border Control & Customs v1
---

# Smuggling Networks v1 — Implementation Checklist

Branch name: `feature/smuggling-networks-v1`

Goal: model contraband supply chains explicitly so that:
- raiders/criminal factions route goods through “soft borders,”
- bribe budgets are allocated strategically (not random),
- enforcement can learn where to focus,
- corruption and culture (smuggling tolerance) become economically meaningful.

v1 is system-level smuggling, not individual black-market NPCs.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same smuggling choices and outcomes.
2. **Bounded.** TopK routes, TopK borders, TopK commodities; no global scans.
3. **End-to-end.** Smuggling creates shipments that interact with customs and enforcement.
4. **Auditable.** We can explain “why this route was chosen.”
5. **Persisted.** Network state belongs in seed vault (empire identity).
6. **Tested.** Route selection, bribe allocation, adaptation to crackdowns, persistence.

---

## 1) Concept model

A smuggling network is a **faction-operated policy** that decides, per day:
- what contraband commodities to move,
- from which source nodes to which demand nodes,
- which corridor routes to use,
- how much to spend on bribery/cover,
- how to adapt to enforcement crackdowns.

We represent a network as a small state vector per faction:
- preferred borders,
- route risk estimates,
- bribe budget allocation strategy,
- recent outcomes.

---

## 2) Data structures

Create `src/dosadi/runtime/smuggling.py`

### 2.1 Config
- `@dataclass(slots=True) class SmugglingConfig:`
  - `enabled: bool = False`
  - `max_active_factions: int = 8`
  - `max_shipments_per_day: int = 12`
  - `commodity_topk: int = 8`
  - `route_topk: int = 24`
  - `border_topk: int = 24`
  - `learning_rate: float = 0.15`
  - `deterministic_salt: str = "smuggling-v1"`

### 2.2 Smuggling state per faction
- `@dataclass(slots=True) class SmugglingEdgeStats:`
  - `edge_id: str`                         # corridor_id or border_id
  - `risk_est: float = 0.5`                # 0..1 (seizure / interdiction)
  - `cost_est: float = 0.1`                # tariffs/bribes/fees proxy
  - `last_update_day: int = -1`

- `@dataclass(slots=True) class SmugglingNetworkState:`
  - `faction_id: str`
  - `commodity_prefs: dict[str, float] = field(default_factory=dict)`
  - `preferred_borders: dict[str, float] = field(default_factory=dict)`
  - `edge_stats: dict[str, SmugglingEdgeStats] = field(default_factory=dict)` # bounded
  - `bribe_budget_fraction: float = 0.15`
  - `last_run_day: int = -1`
  - `recent_outcomes: list[dict[str, object]] = field(default_factory=list)`  # bounded

World stores:
- `world.smuggling_cfg`
- `world.smuggling_by_faction: dict[str, SmugglingNetworkState]`

Snapshot + seed vault include smuggling state.

---

## 3) Smuggling commodities (v1 list)

Align with customs (0275):
- `UNLICENSED_SUIT_MODS`
- `NARCOTICS`
- `WEAPON_PARTS` (in-world abstract)
- `STOLEN_GOODS`
- `RAIDER_SUPPLIES`

Each commodity has:
- value density (value per unit),
- demand drivers (shortage, war pressure, corruption),
- seizure penalty (loss impact).

Keep it as a dict in the module.

---

## 4) Demand and source modeling (cheap)

### 4.1 Demand nodes
Demand arises where:
- culture smuggling_tolerance is high (0270),
- shortages exist for a related good (0263),
- corruption high (0269),
- raider influence present (0266).

Compute per-ward demand score per commodity and keep TopK wards.

### 4.2 Source nodes
Sources arise where:
- raider influence/territory strong (0266),
- production of precursors exists (0272 facilities),
- blackmarket budget flows high (0273 / 0275 bribes).

Compute per-ward source score per commodity and keep TopK sources.

---

## 5) Route selection (TopK, deterministic)

For each faction (up to max_active_factions):
1) Determine daily bribe budget:
- from ledger account `acct:fac:<faction_id>` and bribe_budget_fraction
2) For top commodities by preference:
- pick a source ward from TopK sources
- pick a demand ward from TopK demand
- evaluate TopK candidate routes using existing routing (0261/0248)
3) Score routes using edge_stats:
- expected_loss = sum(risk_est * value)
- expected_cost = sum(cost_est * value)
- choose best route deterministically (score, then route_id tie-break).

Bounded:
- never evaluate more than route_topk candidate routes.

---

## 6) Bribe allocation (strategic, not random)

Given chosen routes and total bribe budget:
- allocate bribe spend to “soft borders”:
  - high bribery tolerance (0275 policy),
  - moderate risk (bribery can help),
  - frequently traversed by chosen routes.

Deterministic allocation:
- border_priority = traffic_weight * (1 - risk_est) * bribe_tolerance * smuggling_norm
- allocate proportionally; cap per border.

Represent on shipment as:
- `smuggling_bribe_budget_total`
- `smuggling_bribe_map: dict[border_id, amount]`

Customs (0275) consults this:
- if shipment carries bribe map and border_id matches, increase bribe success / reduce seizure prob (bounded).

---

## 7) Generating smuggling shipments

Smuggling creates logistics shipments:
- `owner_party = party:fac:<faction_id>`
- cargo tagged contraband (by commodity)
- flags include `smuggling:true`

Shipments still face:
- corridor predation risk,
- customs checks,
- seizures/delays.

---

## 8) Learning/adaptation (simple online updates)

After shipments resolve (delivered/delayed/seized):
- update edge_stats for traversed borders/edges:
  - risk_est moves toward observed outcome (1 if seized, 0 if successful)
  - cost_est moves toward observed tariffs/bribes fractionally
Use `learning_rate`, clamp.

Bound edge_stats:
- keep only TopK most-used edges; evict least recently used deterministically.

---

## 9) Integration points

### 9.1 Customs (0275)
- customs reads smuggling flags and bribe map
- bribes are ledger transfers to blackmarket/corrupt accounts

### 9.2 Ledger (0273)
- bribes spend faction budget
- successful deliveries yield profit:
  - post_tx to faction account reason `SMUGGLING_PROFIT`
v1 can treat profit as transfer from `acct:blackmarket` if funded, or via an allowed “mint” reason.

### 9.3 Enforcement (0265)
- optional: crackdown planner later uses smuggling telemetry to target borders

### 9.4 Culture/Institutions (0270/0269)
- smuggling tolerance increases demand and bribe effectiveness
- higher audit capacity reduces bribery tolerance over time (optional v2)

---

## 10) Telemetry + cockpit

Metrics:
- `metrics["smuggling"]["shipments_created"]`
- `metrics["smuggling"]["delivered"]`
- `metrics["smuggling"]["seized"]`
- `metrics["smuggling"]["bribes_spent"]`
- `metrics["smuggling"]["profit"]`

TopK:
- hottest smuggling routes
- hottest borders (smuggling traffic)
- factions by success rate

Cockpit:
- per faction: commodities, routes, success rate, bribe spend
- border heatmap overlay with customs stats
- explainability: “route chosen because risk_est X, cost_est Y, demand Z”

Events:
- `SMUGGLING_SHIPMENT_CREATED`
- `SMUGGLING_SHIPMENT_SEIZED`
- `SMUGGLING_ROUTE_UPDATE`

---

## 11) Persistence / seed vault

Export stable:
- `seeds/<name>/smuggling.json` sorted by faction_id, with bounded edge_stats.

---

## 12) Tests (must-have)

Create `tests/test_smuggling_networks_v1.py`.

### T1. Determinism
- same budgets + signals → same shipments/routes/bribe allocations.

### T2. Boundedness
- edge_stats bounded; route evaluation bounded; shipments/day capped.

### T3. Bribe allocation influences customs outcomes (bounded)
- with bribe map, seizure probability decreases vs baseline deterministically.

### T4. Learning updates
- repeated seizures on a border increase risk_est and routes shift away.

### T5. Ledger integration
- bribes reduce faction balance; profits increase (allowed reason codes).

### T6. Snapshot roundtrip
- network state persists and continues deterministically after load.

---

## 13) Codex Instructions (verbatim)

### Task 1 — Add smuggling module + state
- Create `src/dosadi/runtime/smuggling.py` with SmugglingConfig and SmugglingNetworkState
- Add world.smuggling_by_faction to snapshots + seed vault persisted layer
- Add stable export `smuggling.json`

### Task 2 — Demand/source scoring + route selection
- Compute TopK demand and source wards per commodity
- Select TopK routes between them using existing routing
- Choose routes deterministically using edge_stats risk/cost estimates
- Cap shipments per day

### Task 3 — Bribe allocation + shipment creation
- Allocate bribe budgets to borders deterministically
- Create shipments with contraband flags and bribe map
- Wire customs to consult bribe map and post bribe ledger transfers

### Task 4 — Outcome feedback (learning)
- On shipment resolution, update edge_stats risk/cost estimates with learning_rate
- Evict least-used edges deterministically

### Task 5 — Telemetry + tests
- Cockpit panels + metrics/topK
- Add `tests/test_smuggling_networks_v1.py` (T1–T6)

---

## 14) Definition of Done

- `pytest` passes.
- With enabled=True:
  - criminal factions generate contraband shipments strategically,
  - bribery is targeted and interacts with customs,
  - enforcement pressure can shift routes over time,
  - profits/bribes flow through the ledger,
  - network state persists into 200-year seeds,
  - cockpit can explain smuggling dynamics.

---

## 15) Next slice after this

**Crackdown Strategy v1** — an enforcement meta-planner that:
- allocates patrols/audits to the most damaging borders,
- anticipates smuggler adaptation,
- and creates the “cat-and-mouse” loop across centuries.

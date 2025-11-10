# **Worldgen v1 — 36‑Ward Sandbox**

Seeded generator for an initial playable Dosadi world consistent with Core Systems v2, Environment Dynamics v1, Governance & Law v1, Barrel Cascade v1, Agent Action API v1, and the Tick Loop.

> Deterministic given `worldgen.seed`. Output populates **SVR**: World, Wards, Routes, Factions, Facilities, Agents (optional), and Policy knobs.

---

## 0) Design Goals

1. **Deterministic Variety** — same seed → same city; different seeds feel distinct but plausible.  
2. **Playable From Day 1** — stocks, routes, and a few standing contracts so the cascade has traction.  
3. **Gradiented Scarcity** — environment harshness and retention vary by ring and ward quality.  
4. **Hooks Everywhere** — black‑market nodes, arbiters, reclaimers present from the start.

---

## 1) Global Params

```yaml
worldgen:
  seed: 7719
  wards: 36
  rings:
    inner: {count: 6,   sealed_p: 0.75, env_S: 0.20, retention_mu: 0.9999, leak_mu: 0.001}
    middle:{count: 12,  sealed_p: 0.45, env_S: 0.50, retention_mu: 0.9950, leak_mu: 0.01}
    outer: {count: 18,  sealed_p: 0.15, env_S: 0.75, retention_mu: 0.9850, leak_mu: 0.03}
  well_location: "center-valley"     # alternatives: 'rise', 'offset-east'
  routes:
    gate_density: 0.6
    checkpoint_severity: {inner: 0.8, middle: 0.5, outer: 0.3}
    smuggle_tunnels: 8               # clandestine connections added after official gates
  factions:
    per_ward: {guilds: 3-6, militias: 1-3, civic: 1-2, cults: 0-2, mercs: 0-2}
    royal_auditors_per_ward: 1
  stocks:
    water_L: {inner: 8000-12000, middle: 4000-8000, outer: 1500-4000}
    biomass_kg: {inner: 1000-3000, middle: 600-2000, outer: 200-800}
    credits: {inner: 50000-120000, middle: 15000-60000, outer: 3000-20000}
  policy:
    tax_rate: 0.10
    min_rotation_floor_pct: 0.005
```

Ranges use seed‑driven draws; `env_S` is environmental stress baseline.

---

## 2) Ward Layout & Environment

- Arrange wards in **3 rings** around Ward #1 (The Well). Index clockwise for determinism.  
- For each ward `w`:
  - **Seal Type**: `sealed ∼ Bernoulli(sealed_p_by_ring)`; sealed wards get roof canopies and higher HVAC efficiency.  
  - **Env Baselines**: `temp`, `humidity`, `o2`, `rad`, `env_S` drawn around ring means with small noise.  
  - **Retention & Leak**: reservoir `retention`, facility `leak_rate` from ring `retention_mu` / `leak_mu` with noise and quality tags.  
  - **Checkpoints**: gates with `severity` from ring policy; more severe → higher transit time and bribery rate.

---

## 3) Routes Graph

- **Official Gates**: connect each ward to 2–4 neighbors with bidirectional edges; each edge has:
  - `distance_mins` (travel time baseline), `checkpoint_lvl`, and `escort_risk` (used by security loop).  
- **Smuggle Tunnels**: add `smuggle_tunnels` hidden edges across rings, with high detection risk and capacity caps.  
- **Royal Spokes**: guaranteed high‑capacity paths from Ward #1 to each inner/middle duke seat.

---

## 4) Factions Seeding

Per ward:
- **Governor Faction**: one `Lord_of_Ward_w` with starting `GovLegit_w ∈ [0.45, 0.75]` and `Reliab_w ∈ [0.40, 0.80]` (ring‑weighted).  
- **Guilds**: 3–6 from a catalog (suit repair, machining, kitchens, reclaim micro‑plants, armory, powerworks). Assign **specialization `Spec_w`** weights by sampling, ensuring network coverage (at least 1 food, 1 power, 1 repair per ward).  
- **Militias/Mercs**: 1–3 groups; quality and size vary with ring; some mercs are **mobile** (operate across wards).  
- **Civic Collectives**: 1–2 (clerks, clinics, shelters, arbitration satellites).  
- **Mystic Cults**: 0–2 with narcotic preferences and doctrine tags; may boost legitimacy locally yet clash with governors.  
- **Royal Auditors**: at least 1 `Clerk/Auditor` presence per ward (bureaucratic network).

Attributes:
- **Legitimacy Drivers**: civic service coverage & recent rulings; initialize from ring priors plus small random events.  
- **Reliability R**: seeded from catalog archetype; contract history empty but priors differ.  
- **Loyalty to King**: draw `Loyal_w`; may be low for outer wards to seed tension.  
- **SmuggleRisk_w**: derived from routes (tunnel proximity), militia laxity, and cult presence.

---

## 5) Facilities & Capacities

- **Reservoir(s)** per ward with `cap_L` and `retention`. Outer wards have smaller caps.  
- **Power**: mix of solar/biofuel baseline; inner wards may have geo/nuclear nodes flagged **critical**.  
- **Kitchens**: at least one per ward; output rations with tiered efficiency.  
- **Reclaimer**: micro reclaim in most wards; 2–4 **regional reclaimers** with higher efficiency.  
- **Workshops**: suit repair, machining, armory; with upgrade slots for later installs.  
- **Clinics**: quality gradient; inner wards have advanced medicine.

Each facility has a **maintenance score** `infra.M ∈ [0,1]` and a small initial backlog of maintenance tasks.

---

## 6) Initial Stocks & Contracts

- **Stocks**: draw from `stocks` ranges; apply ring multipliers and small correlations (wealthier wards hold more credits and better suits).  
- **Standing Contracts**:
  - A few **food** supply lines from middle → outer wards.  
  - **Maintenance** contracts for critical inner power nodes.  
  - **Escort** contracts for barrel routes to 3–5 wards at Day 1.  
  - One **black‑market** tokenized job (small) to ensure covert path is tested.

---

## 7) Agents (Optional Seed)

For quick runs, seed 10–40 agents per ward:
- Mix of **workers**, **guards**, **clerks**, **reclaimers**, **cultists**, **smugglers**.  
- Drives and affinities drawn from ring‑biased priors.  
- Suits: distribution by caste; outer wards skew to scavenger suits with low `Seal` and `Comf`.

---

## 8) Derived Scores & Risk

Compute:
- `Spec_w` from guild catalog concentrations.  
- `Need_w` from `target_reserve` minus `reserve_w`.  
- `Risk_w` from env stress, crime incidents baseline (from routes), and facility faults.  
- `LeakRate_w` from infra.M and ring priors.  
- `SmuggleRisk_w` from tunnels + militia laxity.  
- `RotationDebt_w = 0` initially (or seed small variation for more interesting first cascade).

---

## 9) Emissions for Day 0

Upon completing worldgen:
- Emit `WorldCreated` (PUBLIC) with map summary (rings, sealed counts).  
- Emit `ContractActivated` for standing contracts.  
- Emit `MaintenanceTaskQueued` for initial faults.  
- Emit `CreditRateUpdated` snapshot by ward (baseline).

---

## 10) Pseudocode

```python
def generate_world(cfg, seed):
    rng = Seeded(seed)
    W = init_world()
    rings = bake_rings(cfg, rng)   # assign wards to inner/middle/outer
    for w in W.wards:
        set_env(w, rings[w], rng)
        set_seal_and_retention(w, rings[w], rng)
        add_facilities(w, rings[w], rng)
        seed_factions(w, rings[w], rng)
        seed_agents(w, rings[w], rng)           # optional
        set_stocks(w, rings[w], rng)
        derive_scores(w)
    build_routes(W, cfg.routes, rng)
    seed_standing_contracts(W, rng)
    enqueue_day0_events(W)
    return W
```

---

## 11) Policy Knobs (Tuning)

```yaml
worldgen_tuning:
  spec_bias_inner: 0.15     # inner wards more specialized
  spec_bias_outer: 0.05
  militia_laxity_outer: 0.20
  cult_presence_outer: 0.25
  royal_audit_intensity_by_ring:
    inner: 0.7
    middle: 0.5
    outer: 0.3
  tunnel_detection_prob: 0.12
  checkpoint_bribe_mu: 0.08
```

---

## 12) Sanity Checks

- Conservation: sum of stocks nonnegative; reservoirs not over capacity.  
- Coverage: each ward has at least one kitchen & workshop; each ring has at least one high‑efficiency reclaimer.  
- Connectivity: route graph connected; barrel routes from Well to each ring.  
- Balance: not more than 25% of wards below safety threshold on Day 0 (unless testing a crisis seed).

---

## 13) Export

- Save **JSON** blobs: `world.json`, `wards.json`, `routes.json`, `factions.json`, `facilities.json`, `contracts.json`, `agents.json` (optional).  
- Include schema version & hash for loader compatibility.

---

### End of Worldgen v1

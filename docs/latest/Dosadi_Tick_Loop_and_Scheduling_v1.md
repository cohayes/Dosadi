# **Tick Loop & Scheduling v1**

Deterministic time-stepping for Dosadi. This spec defines **update order**, **queues**, **priorities**, and **rollups** so Codex can implement a reproducible engine.

> **Tick = 0.6 s** · **100 ticks = 1 minute** · Single-threaded deterministic core with queued events.  
> All modules must be **idempotent** and use the bus (**Event & Message Taxonomy v1**).

---

## 0) Design Goals

1. **Determinism**: same seed → same run.  
2. **Isolation**: modules communicate only via events and shared state getters/setters.  
3. **Reproducibility**: fixed ordering and stable RNG streams.  
4. **Observability**: per-phase logs, metrics, and checkpoints.  
5. **Performance**: O(N) passes per tick; heavier work batched to minute cadence.

---

## 1) Global Cadence

- **Tick (0.6 s)**: fine-grained physics/suit wear, micro-events, short queues.  
- **Minute (100 ticks)**: physiology rollups, decay/integrators, pricing smoothers, reliability/legitimacy updates.  
- **Day (144k ticks)**: cascade, taxes, audits, meme aging.

---

## 2) Update Order (per Tick)

Within each tick, phases run in **fixed sequence**; each phase consumes the **event inbox** and may append to the **outbox** for the next phase or later ticks.

1. **Input & Scheduling Phase**  
   - Advance `tick`.  
   - Read deferred jobs due this tick (timers, TTL expiries).  
   - Seed RNG streams for this tick (`seed_base + tick`).

2. **Environment & Infrastructure Phase**  
   - Update ward env fields (`temp`, `hum`, `o2`, `rad`, `env.S`) from active faults and maintenance status.  
   - Emit env events (`HeatSurgeProgress`, `PowerBrownoutTick`) if needed.

3. **Perception & Visibility Phase**  
   - Apply sensor/visibility penalties (e.g., `DustIngress`).  
   - Stage **witness stubs** for PUBLIC events emitted last tick (no memory writes yet).

4. **Agent Micro-Act Phase** *(optional micro-actions at sub-minute cadence)*  
   - Resolve immediate actions that do not require minute rollups (e.g., step movement, start job, toggle device).  
   - Modify local state only; defer heavy effects to minute boundary.

5. **Combat & Security Phase**  
   - Process security triggers (ambush start, seizure start).  
   - Emit `EscortAmbushed`, `AssetSeized`, `MilitiaDeployed` if conditions met.  
   - Apply instantaneous damage/asset deltas; queue law hooks.

6. **Law & Contract Phase (Reactive)**  
   - Consume breach/late triggers already in inbox.  
   - Open/advance `ArbiterCase` if thresholds crossed.  
   - Emit `ContractDisputed`, `BountyPosted` per rules.

7. **Event Dispatch Phase**  
   - Deliver **ALL** events queued so far this tick to subscribers in **priority order** (CRITICAL → HIGH → NORMAL → LOW).  
   - Idempotency required: consumers keep a `seen_event` set.  
   - Events with `ttl` expired are dropped (logged).

8. **Logging & Metrics Phase**  
   - Append tick metrics (counts, latencies).  
   - Optionally sample state for debug traces (configurable).

> **No state that belongs to minute/day cadence is updated in tick phases (except combat/security immediates).**

---

## 3) Update Order (per Minute)

Triggered by `MinuteTick` after tick phases complete (i.e., on ticks 99, 199, …). Execute in order:

1. **Physiology Rollup** (agents)  
   - Hydration/Nutrition burn, Stamina/ME changes, Health penalties/recovery (**Scoring v1 §1**).  
   - Suit decay/repair application (**Scoring v1 §2**).

2. **Production & Maintenance**  
   - Apply completed work orders; update `infra.M`; emit `MaintenanceCompleted` and `ProductionReported`.

3. **Contracts State Machine**  
   - Transition (`ACTIVE→FULFILLED|LATE|DISPUTED|BREACHED`).  
   - Update faction **Reliability R** (**Scoring v1 §4**).  
   - Emit lifecycle events (`ContractFulfilled`, `ContractLate`, …).

4. **Governance & Legitimacy**  
   - Compute legitimacy deltas (**Scoring v1 §3**).  
   - Emit `LegitimacyRecalculated` diffs if changed beyond epsilon.

5. **Risk Pricing & Markets**  
   - Compute price premiums & collateral (**Scoring v1 §5**).  
   - Update `CreditRateUpdated` if rates cross thresholds.

6. **Rumor & Perception Consolidation**  
   - Convert witness stubs → `RumorEmitted` with credibility/salience.  
   - Update agent beliefs, meme increments (**Scoring v1 §6**).

7. **Reputation & Fear Update**  
   - Apply accumulated deltas (**Scoring v1 §7**).  
   - Decay per **SVR v1**.

8. **Minute Logging & Checkpoint (optional)**  
   - Write snapshot per configured cadence (e.g., every 10 minutes).

---

## 4) Update Order (per Day)

Triggered by `DayTick` after minute work completes:

1. **Barrel Cascade Planner & Issue**  
   - Compute `Score_w` (**Scoring v1 §8**), choose targets; emit `BarrelCascadeIssued`.  
   - Seed mandate contracts, post civic notices or tokenized black‑market offers per Law spec.

2. **Taxes & Audits**  
   - Levy official transfer skims; update stocks.  
   - Randomized audit schedule (deterministic stream) → emit findings.

3. **Meme/Rep Long Decay**  
   - Apply slow decays, clamp floors.

4. **Daily Summary Export**  
   - KPI rollups, CSV/JSON dumps for analysis.

---

## 5) Queues & Priorities

- **Per-tick inbox**: four priority sub‑queues (CRITICAL, HIGH, NORMAL, LOW).  
- Enqueue rule: emitters set priority; the dispatcher drains in that order.  
- **Deferred queue**: (tick, event) pairs for future delivery.  
- **Idempotency**: All consumers must check `seen_event[event_id]`.

**Recommended priorities**  
- CRITICAL: combat damage, safety shutdowns, `ArbiterRulingIssued` with retributive orders.  
- HIGH: environment faults, seizures, succession events.  
- NORMAL: contract lifecycle, market updates, maintenance.  
- LOW: rumor emissions, cosmetic notices.

---

## 6) Conflict Resolution & Atomicity

- **Single-writer rule** per state shard (e.g., one module authoritatively updates `gov.L`).  
- **Read‑after‑write** visibility: changes in a phase are visible to later phases within the same tick/minute.  
- **Tie‑breakers**: If two actions contest the same resource in the same phase, resolve by:  
  1) priority (module policy), then 2) deterministic ordering by `(issuer_id, event_id)` lexicographical.  
- **Atomic transfers**: water/credits move via two‑entry ledger (`from−=x; to+=x`) guarded by a single atomic function.

---

## 7) Randomness & Seeds

- Global seed `S0`. Per‑system streams: `S_env`, `S_agents`, `S_market`, `S_law`, … derived via `hash(S0, system_key)`.  
- Per‑tick derivation: `S_system_tick = hash(S_system, tick)`.  
- All sampling (e.g., audit selection, ambush chance) must use the correct stream to stay reproducible.

---

## 8) Timers, TTL, and Alarms

- `ttl` decremented at **Event Dispatch Phase**; zero → drop with log.  
- Alarms (e.g., `expected_downtime_ticks`) enqueue a “resolve” event at `tick+Δ`.  
- Contract deadlines enqueue LATE/DISPUTE checks at due tick (+ grace if configured).

---

## 9) Save/Load & Checkpoints

- **Light checkpoint**: minute-level snapshot of core tables (World, Wards, Factions, Agents, Contracts).  
- **Heavy checkpoint**: includes queues, RNG states, and partial case ledgers for exact resume.  
- File format: JSONL or Parquet (configurable); include engine version + schema hashes.

---

## 10) Testing Hooks

- **Scenario harness**: load initial state + scripted events → assert end-state deltas.  
- **Invariants**: nonnegative stocks; conservation (`draw − taxes − leaks − deliveries − reclaim >= 0`); no double‑spend.  
- **Golden runs**: fixed seed, snapshot diffs stable across commits.

---

## 11) Minimal Scheduler Pseudocode

```python
def run_tick(world):
    world.tick += 1
    rng_seed_all(world.tick)

    # 1) Input & Scheduling
    due = dequeue_deferred(world.tick)
    inbox = merge_events(due, world.inbox)

    # 2) Environment & Infrastructure
    env_update(world)
    env_events = env_emit(world)

    # 3) Perception & Visibility staging
    vis_stubs = stage_witnesses(world, inbox + env_events)

    # 4) Agent micro-acts
    agent_micro(world)

    # 5) Combat & Security
    sec_events = security_step(world, inbox)

    # 6) Law & Contract (reactive)
    law_events = law_reactive(world, inbox + sec_events)

    # 7) Dispatch (priority order)
    dispatch(world, env_events + vis_stubs + sec_events + law_events)

    # 8) Logging
    log_tick(world)

    # Minute boundary?
    if world.tick % 100 == 99:
        run_minute(world)

def run_minute(world):
    physiology_rollup(world)
    production_and_maintenance(world)
    contracts_step(world)
    governance_update(world)
    market_pricing(world)
    rumor_and_perception(world)
    reputation_and_fear(world)
    minute_checkpoint(world)

def run_day(world):
    cascade_planner(world)
    taxes_and_audits(world)
    long_decay(world)
    export_daily(world)
```

---

## 12) Config Skeleton

```yaml
engine:
  tick_seconds: 0.6
  minute_ticks: 100
  day_ticks: 144000
  priorities: [CRITICAL, HIGH, NORMAL, LOW]
  dispatch_batch_size: 1000
  epsilon_legitimacy_diff: 0.01
  checkpoint:
    minute_every: 10
    include_rng: true

rng_seeds:
  base: 123456
  env: 111
  agents: 222
  market: 333
  law: 444
```

---

### End of Tick Loop & Scheduling v1

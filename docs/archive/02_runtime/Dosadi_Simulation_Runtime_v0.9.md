---
title: Simulation_Runtime
doc_id: D-RUNTIME-0002
version: 0.9.0
status: draft
owners: [cohayes]
depends_on: [D-RUNTIME-0001]
last_updated: 2025-11-11
---
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

---

# Dosadi System Logic Architecture
**Purpose:** Defines the governing logical and mathematical principles underlying all Dosadi simulation layers.  

## 1. Conservation Law — The Law of Closed Causality

### Purpose
Dosadi is a sealed ecosystem: every action must trace back to a finite, measurable resource.  
This law ensures the simulation has no “magic.” All events are consequences of conservation and loss.

### Core Principle
Every conserved quantity \( X \in \{Water, Energy, Information, Biomass\} \) evolves by:
\[
X_{t+1} = X_t + P - C - L + R
\]
Where:
- \(P\): production (extraction, generation, discovery)  
- \(C\): consumption (use, investment)  
- \(L\): loss (decay, theft, inefficiency)  
- \(R\): reclamation (recycling, reuse, entropy recovery)

**Invariant:**  
\[
\sum_{all\ entities} X_{t+1} = constant
\]
except where explicitly reduced by irreversible entropy (e.g., radiation, waste heat).

### Hierarchical Conservation
Each tier (King → Lord → Guild → Citizen) tracks its own conservation balance, which aggregates upward:
\[
X_{King} = \sum X_{Lords}
\]
Losses propagate upward as deficits and downward as austerity measures or coercion.

### Design Implication
This law provides the baseline for balancing: every subsystem (economic, informational, or biological) must show measurable flows.  
Integrity checks verify closure at each tick — the “heartbeat” of Dosadi’s realism.

---

## 2. Recursive Hierarchy — The Fractal Order of Power

### Purpose
Dosadi’s social structure is **self-similar** across scales.  
Each ward, guild, or individual is a smaller copy of the planetary macro-system, bound by the same logic of extraction, retention, and coercion.

### The Fractal Rule
At any scale \( s \), an entity \( e_s \) is defined by:
\[
e_s = (I_s, O_s, L_s)
\]
representing inflows, outflows, and losses.  
Each entity minimizes \( L_s \) by organizing subordinate entities \( e_{s-1} \) beneath it.  
This recursive process creates *nested hierarchies of entropy management.*

### Law of Mimetic Governance
Every subordinate structure imitates its superior’s organization:
- The **King’s Court** → template for all thrones and councils.  
- The **Reclamation Guild** → template for all recycling enterprises.  
- Small crews and families mirror command, tribute, and enforcement.

### Collapse Cascade
When a high-level node collapses (e.g., a Duke’s ward), its sub-nodes lose structural coherence:
\[
\Delta Stability_{child} = k \cdot \Delta Stability_{parent}
\]
with \( k \in (0,1) \) defining dependency.  
Instability propagates downward exponentially, but not instantly — enabling partial resilience and rebellion.

---

## 3. Power Equilibrium Law — The Thermodynamics of Authority

### Purpose
Power on Dosadi is not moral; it is thermodynamic — the ability to delay entropy by organizing resources and information.  
This law governs *why hierarchies exist and why they fail.*

### Power as Energy Potential
Define an entity’s power \( P \) as:
\[
P = \beta_W W + \beta_E E + \beta_I I
\]
Where:
- \(W\): control over water resources  
- \(E\): access to usable energy  
- \(I\): possession of accurate information  
- \(\beta\) coefficients represent contextual importance.

Power must be *spent* to preserve order.  
The **cost of order** \( C \) is the energy needed for social coherence, security, and propaganda.

### Stability Equation
\[
S = P - C
\]
- If \(S > 0\): expansion possible.  
- If \(S = 0\): equilibrium.  
- If \(S < 0\): instability or collapse.

### Equilibrium Feedbacks
- Water scarcity \(W ↓\) reduces \(P\).  
- Propaganda or narcotics can temporarily lower \(C\).  
- Information loss sharply decreases \(I\), triggering “informational implosions.”

This formula ties hydraulic, energetic, and informational systems together under one rule of political physics.

---

## 4. Efficiency as Virtue — The Moral Geometry of Survival

### Purpose
Dosadi’s morality derives not from justice but from *efficiency*.  
Virtue is the minimization of waste.

### Efficiency Metric
Retention ratio \( R \in [0,1] \):  
\[
R = \frac{Output\ Value}{Input\ Value}
\]
High \(R\) → elite status and legitimacy.  
Low \(R\) → waste and moral failure.

### Ascension Gradient
| Tier | Efficiency Range (R) | Social Label |
|------|----------------------|---------------|
| King / Elite | 0.999–1.0 | Perfect |
| High Lord | 0.99–0.999 | Pure |
| Middle Guild | 0.95–0.99 | Competent |
| Lower Class | 0.8–0.95 | Wasteful |
| Outcast | <0.8 | Leaky |

### Efficiency-Entropy Paradox
Perfect efficiency halts change; imperfection drives adaptation.  
\[
Growth = f(R) = -a(R - R^*)^2 + G_{max}
\]
Optimal efficiency \(R^*\) < 1 → maximum vitality.  
This mirrors the “optimal corruption” curve: both describe balance between order and decay.

---

## 5. Transaction Logic — The Grammar of Exchange

### Purpose
All interactions—trade, bribery, loyalty, rumor—are transactions.  
They redistribute resources and reshape the *trust topology* of the world.

### Transaction State Machine
| Phase | Description | Possible Failure Mode |
|-------|--------------|-----------------------|
| Offer | Intent broadcast | Ignored, intercepted |
| Binding | Mutual agreement | False binding, coercion |
| Fulfillment | Transfer executed | Theft, substitution |
| Verification | Outcome checked | Misreporting, delay |

### Trust Function
\[
T_{ij}(t+1) = \alpha T_{ij}(t) + (1 - \alpha) O_{ij}(t)
\]
Where \(O_{ij}\) = success score (0–1).  
\(\alpha\) = memory inertia (0.8–0.95).  

### Network Stability
Mean contract density:
\[
\rho = \frac{2E}{N(N-1)}
\]
If \(\rho\) falls below threshold → economic paralysis.  
Each successful contract reduces entropy; failed ones amplify it.

---

## 6. Rumor Propagation and Uncertainty — The Weather of Information

### Purpose
Information moves faster than water but decays more easily.  
It determines decision quality, fear, and coordination potential.

### Information Field Model
\[
I_x(t+1) = I_x(t)(1 - \sigma_x) + \sum_{y \in N(x)} k_{yx} I_y(t) - \eta_x
\]
- \(\sigma_x\): volatility (chaos, narcotics).  
- \(k_{yx}\): transmission efficiency.  
- \(\eta_x\): noise injection (propaganda).

High \(\sigma\) = rumor storm; low \(\sigma\) = factual calm.

### Rumor Humidity
\[
H_r = \frac{U}{I + U}
\]
High humidity → panic, mob events.  
Low humidity → rational coordination.

### Cognitive Temperature
Agents have temperature \( \theta \): ambiguity tolerance.  
Stress increases \( \theta \), fueling rumor contagion.  
Information fidelity thus couples directly to resource scarcity.

---

## 7. Incentive Inversion Law — The Logic of Corruption

### Purpose
Absolute order is fragile. Controlled instability sustains adaptability.  
Therefore, incentives sometimes invert: corruption becomes functional.

### Inversion Probability
\[
p_{inv} = \gamma \frac{E_a}{P_a + \epsilon}
\]
- \(E_a\): local entropy exposure.  
- \(P_a\): power reserve.  
- \(\gamma\): moral flexibility coefficient.

High entropy, low power → betrayal equilibrium.

### The Reclaimer Paradox
Reclaimers profit from decay yet maintain order—**entropy regulators.**  
They exemplify adaptive corruption maintaining systemic balance.

### Functional Corruption
Some corruption \(C^*\) yields maximum global stability:
\[
Stability = f(C) = -a(C - C^*)^2 + S_{max}
\]
Beyond \(C^*\): collapse. Below \(C^*\): rigidity and revolt.

---

## Summary Table: Systemic Laws

| Law | Core Variable | Systemic Goal | Failure Mode | Analogue |
|------|----------------|----------------|----------------|----------------------|
| Conservation | Resource balance \(X_t\) | Maintain closure | Leak / unsourced gain | Thermodynamics |
| Recursive Hierarchy | Structural depth | Stability by imitation | Cascade collapse | Fractals / Bureaucracy |
| Power Equilibrium | \(S = P - C\) | Maintain surplus of power | Exhaustion / revolt | Energy economics |
| Efficiency as Virtue | Retention \(R\) | Legitimacy through performance | Waste / corruption | Meritocracy entropy |
| Transaction Logic | Trust \(T_{ij}\) | Reduce entropy through cooperation | Betrayal | Network theory |
| Rumor Ecology | Info fidelity \(I_x\) | Maintain clarity | Disinformation storms | Atmospheric physics |
| Incentive Inversion | Corruption rate \(C\) | Adaptive stability | Chaos / stagnation | Thermodynamic metastability |

---

### End of System Logic Architecture

---

# **Dosadi Temporal Simulation Systems v1**

---

## **1. Purpose and Philosophy**

The Temporal System is the underlying scheduler of Dosadi — the simulation’s *pulse* that determines when and how processes occur.  
Every cycle is both a **world event** (physical and social processes) and a **perceptual event** (what information is observed, remembered, or decayed).

**Core Principle:**  
> Time is not merely passage — it is the rate at which entropy, information, and legitimacy evolve.

---

## **2. Simulation Granularity**

### **2.1 Time Units**
| Level | Duration | Used For | Description |
|--------|-----------|-----------|-------------|
| **Tick** | 0.6 seconds | Continuous simulation | Atomic step: metabolic change, hydration loss, suit function |
| **Turn** | 100 ticks (≈ 1 minute) | Agent actions | Decision/action resolution interval |
| **Cycle** | 144,000 ticks (≈ 1 day) | Ward-level economic and environmental updates |
| **Epoch** | 1 week | Governance and faction-level recalculations |
| **Era** | 1 month or major event | Structural change, rebellion, or crisis |

Each tier encapsulates the next:  
Ticks feed Turns → Turns feed Cycles → Cycles feed Epochs → Epochs feed Eras.

---

## **3. Event Scheduling and Update Order**

Each time step executes in a consistent top-down cascade:

1. **The Well / King Phase** – extraction, mandate generation.  
2. **Ward Governance Phase** – lord interpretation, enforcement, corruption.  
3. **Factional Operations Phase** – guild and collective execution, production, rumor creation.  
4. **Agent Activity Phase** – drives, health, hydration, fatigue, social interactions.  
5. **Environmental Update Phase** – decay, reclamation, pollution.  
6. **Rumor and Information Phase** – verification, propagation, decay.  
7. **Reflection / Summary Phase** – record metrics, trigger major events, advance the clock.

---

## **4. Decay, Cooldown, and Renewal**

Every system has time-dependent decay and renewal constants.  
The following table uses **Typical Decay Rate (per cycle)** to describe fractional loss per simulated day.

| Domain | Decay Variable | Typical Decay Rate (per cycle) | Notes |
|---------|----------------|--------------------------------|-------|
| **Water Storage** | Reservoir loss rate | 0.001–0.01 | Depends on engineering quality |
| **Rumor Credibility** | Credibility decay | 0.05–0.15 | Weakens unless refreshed |
| **Legitimacy** | Trust decay | 0.02–0.10 | Falls if not reinforced by results or fear |
| **Suit Integrity** | Wear rate | 0.005–0.02 | Restored via maintenance |
| **Agent Energy** | Fatigue recovery | -0.1 to -0.3 | Negative = recovery via rest |
| **Production Output** | Efficiency decay | 0.01–0.05 | Must be renewed by resource input |
| **Population Morale** | Stability loss | 0.01–0.08 | Drops in famine or unrest |

Decay ensures that **inactivity equals regression** — an idle faction or agent loses advantage over time.

---

## **5. Asynchronous Systems and Time Dilation**

The simulation allows different wards or factions to operate at different speeds for performance or narrative focus.

- **Foreground Simulation:** Active wards run full fidelity (tick-level).  
- **Background Simulation:** Calm wards compress time to epoch-level approximations.  
- **Time Dilation Coefficient:** Adjusts fidelity, e.g., 1.0 = full speed, 0.1 = 10× compression.

---

## **6. Temporal Dependencies and Causality Chains**

Events follow causal links that define both *direct* and *delayed* consequences.

- Immediate: combat → injury → reclamation.  
- Delayed: corruption → rebellion → death → resource surplus.

Causality can span days to months but operates within a dependency graph.

---

## **7. Temporal Feedback Loops**

| Loop Type | Example | Behavior |
|------------|----------|-----------|
| **Economic** | Overproduction → price collapse → famine → recovery | Damped oscillation |
| **Social** | Rumor surge → panic → suppression → apathy | Chaotic loop |
| **Environmental** | Water scarcity → reclamation → overpopulation → scarcity | Self-reinforcing |
| **Political** | High legitimacy → complacency → corruption → coup → renewal | Cyclical renewal |

Each loop has a unique time constant, governing how quickly stability returns.

---

## **8. Simulation Tick Implementation Concepts**

### **Pseudocode Example**
```python
for tick in world_time:
    time_progression = delta_t * tick_rate  # Δt = 0.6s base unit
    well.extract_water()
    king.issue_mandates()
    for ward in wards:
        ward.execute_governance_cycle()
        for faction in ward.factions:
            faction.update_legitimacy()
            faction.perform_production()
            faction.handle_rumors()
        for agent in ward.agents:
            agent.perform_drive()
            agent.update_health()
    environment.update_conditions()
    rumor_network.propagate()
    log_state()
```

---

## **9. Temporal Metrics**

| Metric | Description |
|---------|-------------|
| **Δt (Tick Rate)** | Base time step (0.6s) |
| **System Load (%)** | Entities processed per cycle |
| **Event Queue Length** | Pending events before overflow |
| **Entropy Index** | Overall disorder level |
| **Time Dilation Map** | Ward update fidelity |
| **Stability Index** | Combined legitimacy × resource × entropy measure |

---

## **10. Future Hooks**

- **Sleep/Awake Cycle Optimization** — RL agents learn predictive rest timing.  
- **Historical Time Compression** — fast-forward peaceful eras.  
- **Localized Time Distortion** — mystic or tech events warp perceived time.  
- **Planetary Cycles** — seasonal entropy and heat variations.  
- **Narrative Anchors** — milestone events tied to specific epochs.

---

### **End of Temporal Simulation Systems v1**



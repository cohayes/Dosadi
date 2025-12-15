---
title: Cadence_Contract
doc_id: D-RUNTIME-0230
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-15
depends_on:
  - D-RUNTIME-0001   # Simulation_Timebase (ticks/minute/hour/day)
  - D-AGENT-0020     # Agent model (states, goals, memory)
---

# Cadence Contract

A one-page contract describing *what runs when* for agents and world subsystems, with explicit rules for **Awake** vs **Ambient** agent fidelity. The goal is to preserve *crisp local causality* while keeping global runtime scalable.

## Principles

1. **Event-driven beats polling.** If a subsystem can be triggered by events (danger, injury, order, discovery), do that.
2. **Chronic systems integrate by elapsed time.** Avoid “chunky snapping” by storing `last_*_tick` and integrating `elapsed` on update.
3. **Stagger everything that is periodic.** No global “everyone updates on tick % N == 0” for large populations.
4. **Awake ≠ Ambient.** Awake agents run higher-frequency cognition and richer perception. Ambient agents run sparse timers + aggregated signals.
5. **Bound work per tick.** All schedules must degrade gracefully under load.

---

## Agent Fidelity Modes

### Awake Agents
Agents in the player’s interest set or in active zones:
- In-view / near-view of player focus
- In active conflict / high danger salience
- Performing high-stakes actions (combat, surgery, theft, arrest)
- In critical infrastructure zones (Well, ration office, suit depot)

### Ambient Agents
All other agents. Ambient agents still *progress*, but via coarse integration, event triggers, and aggregation.

---

## Update Triggers and Targets

> **Notation**
> - `tick` is the base simulation tick.
> - All periodic tasks use per-agent `next_*_tick` + jitter; never global modulo scans.

### 1) Action Resolution (Acute Causality)
**Trigger:** event-driven on action completion (`eta_tick`)  
**Runs for:** Awake + Ambient (if action is in progress)

- Apply immediate consequences: injuries, transfers, state changes
- Emit world events (sound/sight/smell, protocol violations, alarms)

**Budget note:** Never scan for “actions due”; schedule them in an `eta_tick -> list[Action]` wheel.

---

### 2) Movement / Queue / Local Mechanics
**Trigger:** timer-driven, but localized (only where relevant)

**Movement**
- Awake: every 10 ticks (default)
- Ambient: every 25–100 ticks (adaptive)

**Queue processing / facility service loops**
- Awake zones: every 50–200 ticks
- Ambient zones: every 200–600 ticks

**Adaptive rule:** If the zone has no active entities/events, downgrade cadence automatically.

---

### 3) Emergency Goal Reevaluation (Danger Override)
**Trigger:** **event-driven + cooldown**, not polling

- Enter emergency mode when danger salience crosses threshold (injury, weapon sighting, stampede, suit breach, alarm).
- While in emergency mode, allow reevaluation no more frequently than:

  - Awake: cooldown 10 ticks
  - Ambient: cooldown 50–200 ticks (or promote to Awake if nearby danger is high)

- Exit emergency mode when danger salience decays below threshold for a sustained window.

---

### 4) Physiology + Suit–Body–Environment
**Trigger:** timer-driven integration + immediate action costs

**Continuous model**
- Maintain “debts” (e.g., `heat_debt`, `hydration_debt`, `fatigue_debt`) as floats or fixed-point ints.
- Actions apply **acute** increments (labor, sprint, fight) immediately.
- Environment + suit quality applies **ambient** rate integrated on update.

**Integration cadence targets**
- Awake (active/exposed): every 100 ticks (1 minute) to 600 ticks (10 minutes), adaptive by exertion and exposure.
- Ambient: every 600–3000 ticks (10–50 minutes), integrating elapsed time in one shot.

**Rule:** Integration uses `elapsed = tick - last_physiology_tick` to avoid snapping.

---

### 5) Needs: Hunger / Thirst / Rest
**Trigger:** timer-driven integration + acute costs

- Same debt model as physiology; “needs” are a subset of physiological pressures.
- Target integration cadence:
  - Awake: 500–1500 ticks (5–15 minutes)
  - Ambient: 1000–6000 ticks (10–60 minutes)

**Wake-up rule:** If any need crosses a critical threshold, emit an internal event that may promote agent to Awake.

---

### 6) Memory Intake: Crumbs vs Episodes (Immediate)
**Trigger:** event-driven on perception candidate

Pipeline:
1. Spatial eligibility (range/LOS/zone)
2. Cheap salience score (O(1))
3. Branch:
   - below threshold → **Crumb** update (bounded counters/tags; decayable)
   - above threshold → **Episode** creation into STM (top-K via heap/buckets)

**Awake vs Ambient**
- Awake: lower episode threshold (richer narrative)
- Ambient: higher episode threshold (more compression into crumbs)

---

### 7) STM Maintenance (Boring Winner)
**Trigger:** timer-driven, staggered

- STM is maintained as top-K salience (min-heap or buckets). No O(K) scans on each insert.
- Maintenance pass may:
  - apply time-decay to STM salience
  - compact crumbs (optional)
  - export qualifying episodes to Daily buffer

**Cadence targets**
- Awake: 500–1500 ticks (5–15 minutes)
- Ambient: 1500–6000 ticks (15–60 minutes)

**Rule:** Avoid flush storms; use per-agent `next_stm_tick` with jitter.

---

### 8) Daily Consolidation → Beliefs (Sleep-Driven)
**Trigger:** on sleep cycle completion (preferred), else day boundary as fallback

- Convert Daily episodes (and crumb aggregates) into belief updates:
  - place beliefs, social beliefs, protocol trust, risk priors
- Promote crumbs into episodes if promotion thresholds met (count + time window + context)

**Awake vs Ambient**
- Same process; Awake agents simply accrue richer inputs.

---

### 9) Belief Decay (Lazy)
**Trigger:** lazy-on-access + optional weekly batch

- Store `belief.last_tick`; when a belief is read/updated, apply decay based on elapsed time.
- Optional: small weekly “maintenance batch” for beliefs that would otherwise never be touched.

**Target cadence**
- Lazy dominates; batch (if used): every ~1 week (approx. 1,008,000 ticks)

---

### 10) Chronic Disease / Aging
**Trigger:** sparse timers + milestones + lazy updates

**Disease progression**
- Default: day-scale (once per sleep cycle or once per day)
- Event triggers: exposure, injury, clinic intake → immediate evaluation

**Aging**
- Derived from `born_tick` and current time
- Apply effects at milestones (birthday, decade, etc.), not per-tick

---

## Scheduling Requirements (Implementation Contract)

1. **No global modulo loops over all agents.**
2. Periodic work uses:
   - `next_update_tick` per agent/subsystem
   - a timing wheel / buckets for due work
3. All periodic schedules must support:
   - jitter / staggering
   - Awake/Ambient cadence multipliers
   - adaptive slowdown under load

---

## Default Cadence Table

| Subsystem | Awake | Ambient | Trigger Type |
|---|---:|---:|---|
| Action completion | on eta | on eta | event-driven |
| Movement | 10 ticks | 25–100 ticks | timer (localized) |
| Decision loop (non-emergency) | 50–100 ticks | 200–600 ticks | timer (adaptive) |
| Emergency reevaluation | 10 tick cooldown | 50–200 tick cooldown | event + cooldown |
| Physiology integration | 100–600 ticks | 600–3000 ticks | timer + elapsed |
| Needs integration | 500–1500 ticks | 1000–6000 ticks | timer + elapsed |
| STM maintenance | 500–1500 ticks | 1500–6000 ticks | timer, staggered |
| Belief formation | on sleep | on sleep | sleep-driven |
| Belief decay | lazy | lazy | lazy (+ optional batch) |
| Disease progression | daily/sleep | daily/sleep | timer + events |
| Aging | milestones | milestones | lazy/milestone |

---

## Notes

- All numbers are tunable and should be validated via profiling (A/B runs with 1k, 10k, 100k agents).
- The system should expose knobs per scenario to tighten/loosen Awake/Ambient frequencies and thresholds.

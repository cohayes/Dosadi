# **Task Selection & Utility v1**

Minute-by-minute decision policy for agents to choose actions from the **Agent Action API v1** under the global **Tick/Minute** cadence.

> Timebase: evaluated on each **MinuteTick**.  
> Deterministic with seeded RNG; exploration via configurable softmax temperature.

---

## 0) Goals

1. **Coherent Drives → Actions**: map long-horizon *Drives* to short-horizon *Tasks/Verbs*.
2. **Feasibility First**: only consider actions whose preconditions can be satisfied with current stocks/access.
3. **Context Sensitivity**: incorporate environment stress, market risk, legitimacy, rumors, and relationships.
4. **Stability with Spice**: primarily greedy utility, but with controlled exploration and agenda persistence.
5. **Explainability**: utilities are decomposed into interpretable terms and logged.

---

## 1) Definitions

- **Drive Vector** `D ∈ R^K`: normalized weights for agent’s current investment priorities.  
  Suggested K (from earlier spec): Physiological(Apathy/Survival/Grow), Material(Hoard/Maintenance/Innovation),
  Social-Rep(Dominance/Subservience/Vengeance/Rep-Preservation/Legacy),
  Social-Rel(Conciliation/Paranoia/Destruction), Environmental(Reclamation/Order/Curiosity/Transcendence).

- **Candidate Action Set** `A_t`: subset of verbs feasible in the next 1–30 minutes (window configurable).

- **Utility Function** for action `a`:  
  `U(a) = Σ_i w_i · f_i(a)  -  c(a)  +  b_explore(a)`  
  where `f_i` are *feature returns* per drive, `w_i` are learned or rule-based drive-to-feature maps, `c(a)` is expected cost, and `b_explore` is a novelty bonus.

- **Agenda**: short FIFO plan (1–3 actions) that persists across minutes unless interrupted or re-scored as poor.

---

## 2) Pipeline Overview (per Minute per Agent)

1. **Sense**: read local context (env stress `S`, legitimacy `L(ward)`, market prices, recent threats, hunger/thirst/fatigue, relationship deltas, active cases).  
2. **Feasible Set Build**: enumerate verbs from API; filter by preconditions; estimate minimal plan if a one-step precondition is missing (e.g., move → trade → consume).  
3. **Utility Scoring**: compute `U(a)` using feature projections (§3) and costs (§4).  
4. **Selection**: choose `argmax U` with softmax exploration (§5).  
5. **Agenda Update**: append selected action (and required setup steps); drop old steps finished/invalid.  
6. **Emit**: create action envelopes to the scheduler.  
7. **Log**: store term breakdown for explainability and future learning.

---

## 3) Feature Returns `f_i(a)` (Drive → Action Projections)

Below are recommended mappings from *Drives* to action feature returns within a **1–10 minute horizon**. Scale each feature to `[0,1]` before weights.

### 3.1 Physiological
- **Apathy**: rewards inaction in safety: `f_apathy(Rest) = σ(1 - threat) · σ(Sta/ME - 0.6)`; penalize actions with high stamina burn.  
- **Survival**: `ConsumeRation`, `RelieveAtFacility`, `SeekClinic`, `RepairSuit` get large returns when `W,N,H,Seal` low.  
- **Grow**: `Labor` (if skill gain), `Craft` (if unlock progress), `Train` (if added later).

### 3.2 Material
- **Hoard**: `Trade/Buy/Sell` if profitable; `Escort/Guard` when high-value assets exposed; `SeizeAsset` if court-backed.  
- **Maintenance**: `RepairSuit`, `MaintainFacility` scaled by leakage/decay metrics.  
- **Innovation**: `Craft` with research tag; `InstallComponent` upgrades; novelty bonus.

### 3.3 Social – Reputation
- **Dominance**: `Guard/Patrol/SeizeAsset` (with legitimacy support), public `Commune` that signals strength.  
- **Subservience**: `RegisterContract`, `PayTax`, `Fulfill` workflows early.  
- **Vengeance**: `Ambush/Bounty pursuit/Fence evidence`; rumor broadcasting that harms target.  
- **Rep Preservation**: `RaiseDispute`, `Commune` for narrative repair, fulfill contracts before late.  
- **Legacy**: public works (`MaintainFacility` civic), high-quality `ProductionReported` visible.

### 3.4 Social – Relationships
- **Conciliation**: `Commune`, `Negotiate`, small gifts via `Trade`, shared escort.  
- **Paranoia**: `Scout`, `Hide`, `Observe`, `TokenContractCreate` (anonymous ops).  
- **Destruction**: `Ambush`, `SeizeAsset`, sabotage variants (later).

### 3.5 Environmental
- **Reclamation**: `ReclaimBiomass`, `MaintainFacility(reclaimers)`.  
- **Order**: `Guard/Patrol`, `WitnessContract`, report faults; favors lawful venues.  
- **Curiosity**: `Scout`, `Explore new venue` (later), `Observe` rare actors.  
- **Transcendence**: `UseNarcotic`, `Commune` at cult node; reduces sensitivity to negative stimuli temporarily.

---

## 4) Cost Model `c(a)`

All costs are converted to a **disutility** in `[0,1]` and subtracted from utility.

- **Time**: `c_time = norm(eta_min, 0, 30)` (cap window).  
- **Stamina/Nutrition/Water burn**: predicted deltas mapped with weights; harsher when reserves low.  
- **Risk**: `c_risk = ρ_env + ρ_sec + (1-L)` contextually; extra for illegal actions in lawful venues.  
- **Material Spend**: `c_mat = norm(credits + water_equiv, 0, budget)` where budget is drive-dependent.  
- **Opportunity Lock**: penalty if action blocks high-priority reactive needs (e.g., thirst).

Optional **expected value**: for trades/escorts, use `EV = P(success)·gain − (1−P)·loss`; integrate into `f_i` and costs.

---

## 5) Selection Rule & Exploration

- Compute `U(a)` for all `a ∈ A_t`.  
- **Softmax selection**: `P(a) = exp(U(a)/τ) / Σ exp(U/τ)` with `τ` temperature (lower=greedy).  
- **Novelty bonus** `b_explore(a) = κ · (1 - visit_rate[a])` decays as agent repeats the verb in recent horizon.  
- **Cooldowns**: verbs with external cooldowns (e.g., `UseNarcotic`) set `P(a)=0` until cleared.

Typical settings: `τ = 0.05–0.15` elites (focused), `0.2–0.35` lower wards (more exploratory); `κ = 0.05`.

---

## 6) Agenda Formation

If selected action requires setup (e.g., eat but no ration → buy → consume), create a **2–3 step agenda**:  
`[Acquire, Move, Execute]`. Agenda steps use **fast re-score** each minute; if cumulative `U` drops below a threshold due to context change (e.g., curfew), agenda is **aborted** or **replanned**.

- **Stickiness**: apply small inertia `+ζ` to currently in-progress agenda to avoid thrashing.  
- **Interruption**: CRITICAL security or physiological redline preempts immediately.

---

## 7) Personalization & Learning Hooks

- **Drive Weights Update**: slow EWMA from realized outcomes (e.g., survival near-misses increase Survival weight).  
- **Skill Influence**: as skills improve, expected returns for matching actions rise (e.g., crafting).  
- **Rumor Belief**: belief thresholds alter feasibility/risk; high belief in threat encourages `Hide/Guard`.  
- **Reputation Feedback**: agents valuing Dominance choose more public actions when audience is present.

Optional: bandit-style learning per action context `(state, verb)` updating a small Q-value used as an additive bias into `U(a)`.

---

## 8) Implementation Sketch

```python
def choose_actions(agent, minute_ctx):
    D = agent.drives  # normalized
    candidates = feasible_actions(agent, minute_ctx)

    scored = []
    for a in candidates:
        feats = compute_features(a, agent, minute_ctx)   # in [0,1]
        benefit = sum(w_i(D) * feats[i] for i in feats)  # drive-specific weights
        cost = compute_cost(a, agent, minute_ctx)        # [0,1]
        novelty = explore_bonus(agent, a)                # [0, ~0.1]
        U = benefit - cost + novelty
        scored.append((a, U))

    a_star = softmax_pick(scored, tau=agent.params.tau)
    agenda = build_agenda(agent, a_star, minute_ctx)     # may add setup steps
    return agenda
```

---

## 9) Default Drive→Feature Weights (Starter Table)

| Drive → Feature | Survival | Hoard | Maintenance | Innovation | Conciliation | Paranoia | Dominance | Vengeance | Reclamation | Order | Curiosity | Transcendence |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Rest/Consume/Clinic | 0.9 | 0.1 | 0.1 | 0.0 | 0.1 | 0.2 | 0.0 | 0.0 | 0.1 | 0.1 | 0.0 | 0.2 |
| Labor/Craft/Cook    | 0.2 | 0.6 | 0.3 | 0.5 | 0.2 | 0.1 | 0.2 | 0.1 | 0.1 | 0.1 | 0.2 | 0.0 |
| Trade/Buy/Sell      | 0.1 | 0.8 | 0.2 | 0.2 | 0.3 | 0.2 | 0.2 | 0.1 | 0.1 | 0.2 | 0.2 | 0.0 |
| Repair/Maintain     | 0.3 | 0.3 | 0.9 | 0.2 | 0.1 | 0.2 | 0.1 | 0.1 | 0.3 | 0.4 | 0.1 | 0.0 |
| Commune/Negotiate   | 0.2 | 0.2 | 0.2 | 0.2 | 0.9 | 0.1 | 0.3 | 0.2 | 0.1 | 0.2 | 0.2 | 0.1 |
| Guard/Seize/Escort  | 0.3 | 0.5 | 0.2 | 0.1 | 0.1 | 0.4 | 0.8 | 0.6 | 0.1 | 0.7 | 0.2 | 0.0 |
| Scout/Observe/Hide  | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 | 0.9 | 0.2 | 0.4 | 0.1 | 0.3 | 0.8 | 0.1 |
| Reclaim/Clinic      | 0.5 | 0.2 | 0.3 | 0.1 | 0.1 | 0.2 | 0.1 | 0.1 | 0.9 | 0.3 | 0.1 | 0.0 |
| Narcotics           | 0.1 | 0.0 | 0.0 | 0.0 | 0.1 | 0.1 | 0.0 | 0.1 | 0.0 | 0.0 | 0.1 | 0.9 |

*(Numbers are starting points; tune per playtests.)*

---

## 10) Explainability Log (per choice)

For each agent per minute, store:

```json
{
  "agent": "A17",
  "tick": 28800,
  "candidates": [{"verb":"Trade","U":0.41,"terms":{"benefit":0.63,"cost":0.27,"novelty":0.05}}],
  "selected": {"verb":"Trade","agenda":["MoveTo","Trade"]},
  "context": {"S":42,"L":0.61,"ρ_sec":0.18,"W":1.9,"Sta":66},
  "drives": {"Survival":0.22,"Hoard":0.36,"Conciliation":0.18,"Paranoia":0.10}
}
```

This enables post-hoc analysis and agent personality tuning.

---

### End of Task Selection & Utility v1

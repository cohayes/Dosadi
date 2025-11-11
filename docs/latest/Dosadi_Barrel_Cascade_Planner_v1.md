# **Barrel Cascade Planner v1 (Algorithm Spec)**

Daily planning algorithm for allocating Well draw to wards and vassals.  
Integrates with SVR v1, Event Bus v1, Scoring v1, and Tick Loop v1.

> Timebase: runs on **DayTick** (144k ticks). Emits `BarrelCascadeIssued` and seeds mandate contracts.

---

## 0) Objectives

1. **Stability** — prevent unrest by keeping wards above critical reserve.  
2. **Productivity** — route water where marginal output per liter is highest.  
3. **Legibility** — allocations must be explainable and auditable.  
4. **Control** — enable royal bias (political steering) without crashing stability.  
5. **Fairness over time** — rotation and minimum floors prevent starvation or dynastic lock‑ins.  

---

## 1) Inputs (Read‑Only)

From **SVR v1** / world state at DayTick:

- `reserve_w` — ward water stock (L).  
- `target_reserve` — policy buffer per ward (L) (can be tiered by ring).  
- `Spec_w ∈ [0,1]` — specialization score (rolling output signal).  
- `Loyal_w ∈ [0,1]` — loyalty to king (royal alignment).  
- `Risk_w ∈ [0,1]` — crisis intensity composite (env faults, security incidents).  
- `Need_w = norm(target_reserve - reserve_w; 0, target_reserve)` (Scoring v1).  
- `ProdMarginal_w` — liters → output conversion gradient (see §3).  
- `Reliab_w ∈ [0,1]` — reliability of ward governor faction (contract history).  
- `GovLegit_w ∈ [0,1]` — legitimacy of governor.  
- `RotationDebt_w ∈ [0,1]` — how long since last material allocation (fairness).  
- `LeakRate_w` — expected infra loss (fraction/day).  
- `SmuggleRisk_w ∈ [0,1]` — likelihood water exits intended recipients (intel).  
- `RoyalBias_w ∈ [-1,1]` — explicit policy knob for the “bowling” effect.  
- `Q_day` — total drawable liters from Well (policy/engineering cap).  
- `Tax_rate` — official skim on downstream transfers (0–0.2).

---

## 2) Hard Constraints

- **Conservation**: `sum(alloc_w) ≤ Q_day`.  
- **Safety Floor**: `alloc_w ≥ Floor_w` if `reserve_w < SafetyThreshold_w`.  
- **Max Throughput**: `alloc_w ≤ PipeCap_w` (logistics capacity).  
- **Bias Cap**: cumulative bias cannot reduce any ward below `MinRotationFloor` for more than `MaxStarveDays`.  
- **Leakage Adjustment**: expected delivered liters `eff_alloc_w = alloc_w * (1 - LeakRate_w)` must still satisfy floors.  

---

## 3) Productivity Model (Marginal Output per Liter)

For each ward, estimate the **marginal productivity** of an additional liter into its active pipelines today.

```
ProdMarginal_w = θ_spec * Spec_w + θ_rel * Reliab_w + θ_leg * GovLegit_w
                 + θ_chain * UpstreamSynergy_w - θ_risk * Risk_w
```
- `UpstreamSynergy_w` is computed from contracts that consume outputs of ward `w`.  
- Coefficients defaults: `θ_spec=0.4, θ_rel=0.25, θ_leg=0.15, θ_chain=0.15, θ_risk=0.2`.  
- Bound to `[0,1]`. Nonlinear option: apply `sqrt` or `log1p` to reduce runaway specialization.

---

## 4) Composite Allocation Score

Daily priority score before constraints:

```
NeedTerm   = aN * Need_w
ProdTerm   = aP * ProdMarginal_w
LoyalTerm  = aL * Loyal_w
RotateTerm = aR * RotationDebt_w
RiskTerm   = - aK * Risk_w
BiasTerm   = aB * RoyalBias_w
LeakTerm   = - aLeak * LeakRate_w
SmugTerm   = - aS * SmuggleRisk_w

Score_w = NeedTerm + ProdTerm + LoyalTerm + RotateTerm + RiskTerm + BiasTerm + LeakTerm + SmugTerm
```

**Defaults**: `aN=0.35, aP=0.25, aL=0.15, aR=0.10, aK=0.10, aB=0.08, aLeak=0.04, aS=0.03`.  
Clamp `Score_w` to `[0,1]` after affine rescale across wards each day (rank‑preserving).

---

## 5) Allocation Procedure

1. **Pre‑Floor Pass**  
   - Compute `Floor_w = max(0, SafetyThreshold_w - reserve_w)` bounded by `PipeCap_w`.  
   - Allocate floors to all `w` with `reserve_w < SafetyThreshold_w`. Subtract from `Q_day`.

2. **Scoring Pass**  
   - Compute `Score_w` for all wards (above).  
   - Compute soft shares:  
     `share_w = Score_w^γ / Σ Score^γ` with `γ ∈ [0.8, 2.0]` (γ>1 sharpens winners).

3. **Capacity Pass**  
   - Proposed `alloc_w = min(share_w * Q_remain, PipeCap_w)`.

4. **Leakage Correction**  
   - If `eff_alloc_w = alloc_w * (1 - LeakRate_w)` drops any ward below safety, top it up from remaining pool by taking proportionally from high‑Score wards (without violating their safety).

5. **Rotation & Fairness**  
   - Update `RotationDebt_w` (↓ for recipients; ↑ for others).  
   - Enforce `MinRotationFloor` for wards that exceed `MaxStarveDays`. This is a *small* guaranteed share (e.g., 0.5–2% of `Q_day`).

6. **Bias Budgeting**  
   - Cap the effect of `RoyalBias_w` by a daily **bias budget** `B_max` so political steering cannot crash safety.  
   - Implementation: recompute `Score_w` with `BiasTerm=0`, then add `BiasTerm` contributions and renormalize within `±B_max` liters moved from neutral plan.

7. **Mandate Seeding**  
   - For each recipient ward, generate downstream **mandate contracts** coherent with its specialization signals (e.g., if `Spec_w` high in suit repair, create maintenance mandates first).  
   - Publish civic notices; create tokenized black‑market proxies where appropriate.

8. **Emission**  
   - Emit `BarrelCascadeIssued { draw_L, targets, policy_bias, tax_rate }` (PUBLIC).  
   - Post `ContractActivated` for mandates.  
   - Record `CreditRateUpdated` if expected pricing shifts > ε.

---

## 6) Anti‑Gaming & Oversight

- **Reliability Dampener**: if a ward’s `Reliab_w` rises while **inspection rate** is low, apply skepticism factor until audits catch up.  
- **Leakage Audits**: randomize checks; if measured loss ≫ expected, raise `Corruption` and `SmuggleRisk`.  
- **Hoarding Detector**: if `reserve_w` climbs steadily while deliveries outpace consumption and contracts stall, trigger:  
  - `ContractDisputed` by royal clerks for nonperformance, or  
  - shift future allocations toward wards that convert liters to outputs.  
- **Crisis Guardrail**: if `Risk_w` > threshold, ensure minimal allocation to stabilize (security, clinics).

---

## 7) Parameterization (Policy Knobs)

```yaml
cascade:
  Q_day: 100000.0        # liters
  safety_threshold_by_ring:
    inner:  8000
    middle: 5000
    outer:  2500
  min_rotation_floor_pct: 0.005
  max_starve_days: 6
  gamma_share: 1.2
  bias_daily_budget_L: 4000
  epsilon_price_shift: 0.02
  pipecap_by_ward: {}    # liters/day
```

---

## 8) Worked Example (Small)

Wards A..E. `Q_day=10,000 L`. After floors, `Q_remain=7,000 L`. Scores → shares (`γ=1.2`).

| Ward | Score | Share | Cap | Alloc | Eff(−leak) |
|---|---:|---:|---:|---:|---:|
| A | 0.82 | 0.29 | 2500 | 2500 | 2400 |
| B | 0.74 | 0.23 | 3000 | 3000 | 2910 |
| C | 0.63 | 0.19 | 2000 | 1500 | 1470 |
| D | 0.41 | 0.12 | 3000 | 1000 |  950 |
| E | 0.33 | 0.09 | 1500 | 1000 |  950 |

Bias budget shifts +500 L from C→B (political favor), staying within `B_max`. Emit events and seed mandates that reflect A (maintenance), B (suit fabrication), etc.

---

## 9) Pseudocode

```python
def plan_cascade(world):
    Q = world.cascade.Q_day
    floors = {}
    for w in wards:
        floor = max(0, safety_threshold(w) - reserve(w))
        floors[w] = min(floor, pipecap(w))
    alloc = floors.copy()
    Q -= sum(floors.values())

    scores = {w: score_w(world, w) for w in wards}
    shares = softmax_pow(scores, gamma=cfg.gamma_share)
    for w in wards:
        if Q <= 0: break
        extra = min(Q * shares[w], pipecap(w) - alloc[w])
        alloc[w] += extra
    # Leakage correction
    for w in wards:
        eff = alloc[w] * (1 - leak(w))
        if reserve(w) + eff < safety_threshold(w):
            need = safety_threshold(w) - (reserve(w) + eff)
            donors = sorted(wards, key=lambda x: scores[x], reverse=True)
            for d in donors:
                if d == w: continue
                give = min(need, alloc[d] - floors[d])
                alloc[d] -= give
                alloc[w] += give
                need -= give
                if need <= 0: break
    # Bias budget
    neutral = alloc.copy()
    bias_move = budgeted_bias(neutral, scores, royal_bias, B_max=cfg.bias_daily_budget_L)
    alloc = combine(neutral, bias_move)

    seed_mandates(world, alloc)
    emit_barrel(world, alloc)
    return alloc
```

---

## 10) Emitted Data & Audit Trail

- `BarrelCascadeIssued`: includes `draw_L`, `targets`, `policy_bias` map, `tax_rate`.  
- **Royal Ledger**: store inputs, scores, floors, caps, final alloc, and reasons (top 3 contributing terms) for explainability.  
- **Civic Record** (public): ward‑level totals and rationale categories (safety/productivity/rotation).  
- **Black‑Market Mirror** (restricted): expected tokenized offers seeded from mandates.

---

## 11) Integration Touchpoints

- Consumes **Scoring v1 §8** scores (or its components) and **SVR** variables.  
- Emits events consumed by Law (contracts), Economy (prices), Rumor (public narratives), Governance (legitimacy).  
- Feeds back `RotationDebt_w` and updates specialization via `ProductionReported` downstream.

---

### End of Barrel Cascade Planner v1

---
title: Dosadi_Agent_Scoring_and_Update_Equations
doc_id: D-AGENT-0006
version: 1.0.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-AGENT-0001
---
# **Scoring & Update Equations v1 (Math Glue)**

This spec defines the minimal deterministic math that ties systems together.  
Timebase: **tick = 0.6 s**, **100 ticks = 1 minute**, variables reference the **SVR v1** keys.

---

## 0) Notation

- For any metric `x` with exponential decay: `x ← x * exp(-λ · Δmin)` where `Δmin` is minutes since last update.  
- Normalization: `norm(z; z_min, z_max) = clamp((z - z_min)/(z_max - z_min), 0, 1)`.  
- EWMA: `ewma(x; α) = α·x_new + (1-α)·x_old`.

---

## 1) Physiology (per Agent per Minute)

Let activity level `a ∈ {REST=0, LIGHT=1, MOD=2, HEAVY=3, EXTREME=4}` with workload multipliers `κ_a = {0.5, 1.0, 1.5, 2.25, 3.25}`.  
Environmental stress `S = env.S ∈ [0,100]`. Suit seal `σ = suit.Seal ∈ [0,1]`.

### 1.1 Hydration `body.W` (L)
Water loss per minute:
```
loss_W = base_W * κ_a * (1 + βS * S/100) * (1 - σ_eff)
σ_eff  = clamp(σ * suit.I, 0, 1)
base_W = 0.045  # L/min at LIGHT work in nominal conditions (~2.7 L/60min)
```
Update: `W ← max(0, W + intake_W - loss_W)`.

Dehydration penalty trigger: if `W < 1.0`, apply health/stamina penalties (see §1.4).

### 1.2 Nutrition `body.N` (kcal)
Burn per minute:
```
burn_N = base_N * κ_a * (1 + γS * S/100)
base_N = 2.0   # kcal/min at LIGHT work (~120 kcal/hr baseline)
```
Update: `N ← max(0, N + intake_kcal - burn_N)`.

### 1.3 Stamina `body.Sta` and Mental Energy `body.ME`
```
Sta ← clamp( Sta + r_rest_sta(a) - r_fatigue_sta(a,S) - r_dehyd_sta(W) , 0, 100)
ME  ← clamp( ME  + r_rest_me(a)  - r_focus_me(a)     - r_stress_me(S)  , 0, 100)
```
Suggested components (per minute):
- `r_rest_sta(a) = 0.6  if a=REST else 0.0`
- `r_fatigue_sta(a,S) = (0.4*κ_a) * (1 + 0.6*S/100)`
- `r_dehyd_sta(W) = 0.4 * norm(1.0 - W; 0, 1.0)`
- `r_rest_me(a) = 0.5 if a∈{REST,LIGHT} else 0.0`
- `r_focus_me(a) = 0.25*κ_a`  
- `r_stress_me(S) = 0.2 * S/100`

### 1.4 Health `body.H`
Health change per minute from physiology:
```
ΔH_phys = - φ_dehyd * norm(1.0 - W; 0, 1.0) 
          - φ_starve * norm(500 - N; 0, 500) 
          - φ_exhaust * norm(20 - Sta; 0, 20)
H ← clamp(H + heal_passive - ΔH_phys, 0, 100)
heal_passive = 0.05 if (Sta>70 and ME>70 and W>=2.0 and N>=1500) else 0.0
```
Recommended `φ_dehyd=0.4, φ_starve=0.2, φ_exhaust=0.2` (hp/min).

---

## 2) Suit Decay & Exposure

Let dust/chem factors from events be `D ∈ [0,1]`, `Chem ∈ [0,1]`.

```
# Integrity (structural wear)
λ_I = λ_I0 * (1 + a_I*S/100) * (1 + b_I*D)
I ← clamp( I * exp(-λ_I · Δmin) + repair_I, 0, 1 )

# Seal (microleaks)
λ_Seal = λ_S0 * (1 + a_S*S/100) * (1 + b_S*D + c_S*Chem)
Seal ← clamp( Seal * exp(-λ_Seal · Δmin) + repair_Seal, 0, 1 )

# Exposure score (drives health loss in extreme)
Exp ← 100 * (1 - σ_eff) * (S/100)
```
Defaults: `λ_I0=0.002/min`, `λ_S0=0.003/min`, `a_*≈0.5`, `b_*≈0.7`, `c_S≈0.8`.

---

## 3) Governance: Legitimacy `gov.L` (per Faction Leader, per Minute)

Inputs (minute rollups):
- `on_time_ratio ∈ [0,1]` of mandate-linked contracts delivered this day so far.
- `crisis_intensity ∈ [0,1]` from env faults/riots/security breaches.
- `bias_flag ∈ {0,1}` if recent rulings are inconsistent vs similar cases.
- `E_norm = norm(law.E; 0, E_max)` with `E_max` a policy cap (e.g., 3000 ticks ≈ 30 min).

Update:
```
ΔL = + α_mandate*on_time_ratio
     + α_rulings*law.AC
     - α_crisis*crisis_intensity
     - α_bias*bias_flag
     - α_latency*E_norm

L ← clamp( L*exp(-λ_L*Δmin) + ΔL, 0, 1 )
```
Defaults: `α_mandate=0.02, α_rulings=0.01, α_crisis=0.03, α_bias=0.02, α_latency=0.015, λ_L=0.001/min`.

**Effect hooks:** Higher `L` → lower price premiums (§5), higher compliance, lower unrest triggers.

---

## 4) Economic Reliability `econ.R` (per Faction)

After every contract resolution:
```
outcome_score = 1.0 if FULFILLED on-time
              = 0.7 if FULFILLED late
              = 0.3 if SETTLED (restorative)
              = 0.0 if BREACHED
R ← ewma(outcome_score; α_R),  α_R = 0.2
```
Aging (if no activity in 24h): `R ← 0.95*R + 0.05*R_prior_mean` (regression to mean).

---

## 5) Contract Risk Pricing & Collateral

Let counterparty metrics be `C` (corruption), `R` (reliability), context `L` (legitimacy), enforcement `E_norm`, environmental risk `ρ_env = S/100`, security risk `ρ_sec` from recent violence (0–1). Collateralization factor `χ ∈ [0,1]` (1 = fully collateralized via token/escrow).

**Price premium (credits):**
```
Prem = wC*C + wR*(1-R) + wE*E_norm + wL*(1-L) + wEnv*ρ_env + wSec*ρ_sec - wCol*χ
Prem ← max(0, Prem)
```
**Collateral requirement (asset units):**
```
Col = base_col * (1-R) * (1-L) * (1 - χ_bonus)
χ_bonus = 0.5 if tokenized_escrow else 0.0
```
Defaults: `wC=3, wR=4, wE=2, wL=2, wEnv=1.5, wSec=2.5, wCol=3; base_col = 100 (credits or equiv)`.

---

## 6) Rumor Credibility & Belief Update (Per Agent)

Each PUBLIC event or witness yields an observation `(cred, sal)`.  
Belief `B ∈ [0,1]` about proposition `p` updated minute-wise:

### 6.1 Credibility refresh
Exponential decay: `cred ← cred * exp(-λ_cred*Δmin)`, with `λ_cred=0.03/min` (SVR).

### 6.2 Belief update (logit add)
```
logit(B) = ln(B/(1-B))
Δ = k_cred*(cred - 0.5) + k_sal*(sal - 0.5) + k_src*src_bias
B ← σ( logit(B) + Δ )
```
- `src_bias` encodes agent’s prior alignment toward source faction (−1..+1 scaled).  
- `σ` is logistic. Defaults: `k_cred=1.2, k_sal=0.8, k_src=0.6`.

### 6.3 Action thresholds
- Act-as-true if `B ≥ 0.8`.  
- Treat-as-possible if `0.5 ≤ B < 0.8`.  
- Disregard if `B < 0.5`.

High-salience, repeated consistent observations increment **meme strength**:  
`M ← M + η * (sal · cred) · (1 - M)` with small `η = 0.05/min`, slow decay per SVR.

---

## 7) Reputation & Fear

When PUBLIC outcomes occur:

```
rep_audience ← rep_audience + δ_rep
fear_index   ← fear_index + δ_fear
```
Examples (recommended deltas):
- `ContractFulfilled`: `δ_rep=+0.02` for counterparties & observers (attenuate by distance); `δ_fear=0`.
- `ArbiterRulingIssued: RETRIBUTIVE`: if perceived as fair → `δ_rep=+0.01`, `δ_fear=+0.03`;  
  if arbitrary (bias_flag=1) → `δ_rep=-0.03`, `δ_fear=+0.02`.
- `EscortAmbushed` by faction X: observers assign `δ_rep=-0.04` to X with civilians, `δ_fear=+0.04` in lower wards.

Decay per SVR: `rep` λ=0.005/min, `fear` λ≈0.01/min.

---

## 8) Barrel Cascade Targeting Score (Planner Hint)

For ward `w`:
```
Need_w   = norm(target_reserve - reserve_w; 0, target_reserve)
Spec_w   = cascade.S_w                         # specialization 0–1
Loyal_w  = loyalty_to_king_w ∈ [0,1]
Risk_w   = norm(crisis_intensity_w; 0,1)

Score_w = aN*Need_w + aS*Spec_w + aL*Loyal_w - aR*Risk_w + aBal*rotation_bonus
```
Defaults: `aN=0.35, aS=0.25, aL=0.2, aR=0.15, aBal=0.05`.

Selected targets are the top‑K wards by `Score_w`, subject to diversity/rotation constraints.

---

## 9) Update Ordering (per Minute, preview for Tick Loop)

1) **Environment & Infrastructure** updates (`env.S`, faults, maintenance).  
2) **Physiology** (`W,N,Sta,ME,H`).  
3) **Suit** decay/repair.  
4) **Contracts** state transitions; **Reliability** updates.  
5) **Governance** (`L`) & taxes.  
6) **Rumor/Perception** updates (belief & memes).  
7) **Reputation/Fear** adjustments.  
8) **Markets** (price/credit updates via risk pricing).

(Deterministic ordering prevents feedback oscillations.)

---

## 10) Coefficient Table (Defaults)

| Symbol | Meaning | Default |
|---|---|---|
| `βS` | Hydration stress factor | 0.6 |
| `γS` | Calorie stress factor | 0.3 |
| `φ_dehyd` | Health dmg from dehydration (hp/min) | 0.4 |
| `φ_starve` | Health dmg from low nutrition | 0.2 |
| `φ_exhaust` | Health dmg from low stamina | 0.2 |
| `λ_I0` | Suit integrity base decay | 0.002/min |
| `λ_S0` | Seal base decay | 0.003/min |
| `α_mandate` | Legitimacy gain from on-time mandates | 0.02/min |
| `α_rulings` | Legitimacy gain from consistency | 0.01/min |
| `α_crisis` | Legitimacy loss per crisis intensity | 0.03/min |
| `α_bias` | Legitimacy loss on biased ruling | 0.02/min |
| `α_latency` | Legitimacy loss from enforcement latency | 0.015/min |
| `wC,wR,wE,wL,wEnv,wSec,wCol` | Risk weights | 3,4,2,2,1.5,2.5,3 |
| `k_cred,k_sal,k_src` | Belief coefficients | 1.2, 0.8, 0.6 |
| `η` | Meme consolidation rate | 0.05/min |

---

## 11) Pseudocode Snippets

### 11.1 Per‑Minute Agent Update
```python
def update_agent_minute(a):
    S = env.S[a.ward]
    a.W  = max(0, a.W + a.intake_W - loss_W(a.activity, S, a.suit))
    a.N  = max(0, a.N + a.intake_kcal - burn_N(a.activity, S))
    a.Sta = clamp(a.Sta + rest_sta(a.activity) - fatigue_sta(a.activity, S) - dehyd_pen(a.W), 0, 100)
    a.ME  = clamp(a.ME  + rest_me(a.activity)  - focus_me(a.activity)      - stress_me(S),  0, 100)
    a.H   = clamp(a.H + heal_passive(a) - health_penalties(a), 0, 100)
    a.suit.I, a.suit.Seal = decay_and_repair(a.suit, S, dust(a.ward), chem(a.ward))
```

### 11.2 Legitimacy & Pricing
```python
def update_legitimacy(f):
    L = f.L * exp(-λ_L*Δmin)         + α_mandate*on_time_ratio(f) + α_rulings*law.AC         - α_crisis*crisis_intensity(f.ward) - α_bias*bias_flag(f)         - α_latency*norm(law.E, 0, E_max)
    f.L = clamp(L, 0, 1)

def price_premium(counterparty, context):
    return max(0, wC*C(counterparty) + wR*(1-R(counterparty)) + wE*norm(E(context),0,E_max)
                   + wL*(1-L(context)) + wEnv*S(context)/100 + wSec*security_risk(context) - wCol*collateralization(counterparty))
```

---

### End of Scoring & Update Equations v1

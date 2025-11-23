---
title: Security_Loop
doc_id: D-INFO-0012
version: 1.0.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-INFO-0001
---
# **Security Loop v1**

Risk → Incidents → Response → Outcomes → Feedback.  
Integrates with **Worldgen v1**, **Agent Action API v1**, **Task Selection & Utility v1**, **Contracts/Case SM v1**, **Market Microstructure v1**, **Rumor & Perception v1**, **Tick Loop**.

> Cadence: risk updates **per MinuteTick**; incident resolution can span minutes to hours; legitimacy effects aggregate daily.

---

## 0) Goals

1. **Local & Route Safety** quantified as continuous risks.  
2. **Eventful but Predictable**: spikes cause visible incidents; quiet areas stay mostly calm.  
3. **Actionable Hooks**: maintenance, patrols, escorts, audits, and rulings push risk down; hoarding, shortages, and propaganda push risk up.  
4. **Explainable Feedback**: incidents alter reputation, prices, and legitimacy with audited reasons.

---

## 1) Risk Decomposition

For each ward `w` and route `r` keep risk vectors (0–1):

```
ρ_env(w)   # environment (heat, dust, power faults)
ρ_crime(w) # petty theft, mugging, sabotage
ρ_mil(w)   # factional conflict escalation (militia clashes)
ρ_reb(w)   # rebellion likelihood (political uprisings)
ρ_health(w)# epidemic/clinic overload
```

**Composite ward risk**: `Risk_w = 1 - Π (1 - θ_i * ρ_i)` with weights `θ_i`.  
**Route ambush risk**: `AmbushProb(r) = σ( a0 + a1*ρ_crime(src) + a2*ρ_crime(dst) + a3*CheckpointLeniency(r) + a4*SmuggleUse(r) )`.

---

## 2) Minute Risk Update

Update each component with pushes/pulls:

### Downward (stabilizers)
- **Patrol/Guard** minutes (security actions) → `ρ_crime↓, ρ_mil↓` (local radius).  
- **Escort success** on route `r` → `AmbushProb(r)↓`.  
- **MaintenanceCompleted** on critical infra → `ρ_env↓`, `ρ_reb↓`.  
- **ArbiterRulingIssued(RESTORATIVE)** widely respected → `ρ_mil↓, ρ_reb↓`.  
- **Clinic capacity** adequate → `ρ_health↓`.

### Upward (stressors)
- **Shortages** (`Need_w` high), **price spikes**, **late/breached contracts** → `ρ_reb↑, ρ_crime↑`.  
- **Ambush/Seizure** success → local `ρ_crime↑` and route ambush ↑.  
- **Propaganda/Memes** anti‑lord (PUBLIC high‑salience) → `ρ_reb↑`.  
- **Power/water faults** unresolved → `ρ_env↑` and bleed into `ρ_reb↑`.  
- **Epidemic** triggers if `clinic load > cap` for extended time → `ρ_health↑`.

All deltas are small per minute; clamp to [0,1]; decay toward baseline with `λ_decay`.

---

## 3) Incident Generator (Stochastic)

At each **MinuteTick**, sample Poisson‑like arrivals from risks:

```
λ_theft(w)   = k_t * ρ_crime(w)
λ_riot(w)    = k_r * ρ_reb(w)
λ_clash(w)   = k_c * ρ_mil(w)
λ_sabotage(w)= k_s * ρ_crime(w) * (1 - GovLegit_w)
λ_ambush(r)  = k_a * AmbushProb(r)
λ_outbreak(w)= k_h * ρ_health(w)
```

For each channel, draw `n ~ Poisson(λ)` or Bernoulli with `p=1-exp(-λ)`; enqueue incidents with severity sampled from risk and stocks at stake.

**Incident types**
- `PETTY_THEFT`, `FACILITY_SABOTAGE`, `MARKET_BRAWL`, `PROTEST`, `RIOT`, `MILITIA_CLASH`, `AMBUSH`, `BANDIT_RAID`, `CURFEW_VIOLATION`, `OUTBREAK`, `CHECKPOINT_BRIBE_STING`.

Emitted as `SecurityIncidentCreated {type, ward/route, severity, actors?}` (HIGH).

---

## 4) Response Policy

When an incident is created, choose response based on **venue**, **legitimacy**, and **resources**:

- **Auto‑Deploy**: if severity ≥ threshold and guards available → `MilitiaDeployed` with force level.  
- **Bounty**: if attackers escaped with assets or unidentified → `BountyPosted`.  
- **Arbiter Case**: for sabotage, riot leaders, or repeated theft → open `Case` with fast hearing for legitimacy.  
- **Curfew**: if riot probability persists → issue temporary curfew (`MilitiaDeployed` with checkpoints).

**Escalation ladder**
1. **Presence** (patrol/guard)  
2. **Detain & Fine** (restorative)  
3. **Seize Assets** (retributive for severe/organized)  
4. **Curfew**  
5. **Martial Response** (rare; heavy legitimacy risk if misused)

---

## 5) Resolution Dynamics

Each response produces outcomes with probabilities:

- **Deterrence**: local risk `ρ_crime` reduced by `Δ_deterrence` for `T_deterrence` minutes if response succeeded.  
- **Blowback**: harsh actions when `GovLegit_w` low increase `ρ_reb` and reduce legitimacy.  
- **Collateral**: casualties → reclamation flow; rumors spawn with high salience.

**Outcome events**
- `IncidentResolved {success, arrests, losses_L, injuries, rumors_emitted}`.  
- Update reliability for security factions (contract fulfillment).

---

## 6) Legitimacy Feedback (Daily Aggregation)

On **DayTick**, compute legitimacy delta per ward:

```
ΔL = + α_safe * (IncidentsPrevented / ExpectedIncidents) 
     + α_clear * (ClearRate) 
     - α_harsh * (HarshResponses / Responses) * (1 - PublicSupport)
     - α_fail  * (UnresolvedMajorIncidents)
```

- **Prevented** estimated from risk drop vs baseline.  
- **ClearRate** = resolved with restorative outcomes / total.  
- **PublicSupport** from rumor sentiments and price stability.

Clamp `GovLegit_w ← clamp(GovLegit_w + ΔL, 0, 1)` and emit `LegitimacyRecalculated` if |ΔL|>ε.

---

## 7) Market & Rumor Integration

- **Market**: widen spreads and add surcharges where `ρ_crime` or `AmbushProb` high; resolved incidents narrow them (see Market v1).  
- **Rumor**: each incident spawns PUBLIC rumors; credibility depends on evidence (cams, witnesses).  
- **Perception**: agents adjust Paranoia drive when local incidents surge; choose `Hide/Guard/Escort` more often.

---

## 8) Policy Knobs

```yaml
security:
  θ_env: 0.20
  θ_crime: 0.35
  θ_mil: 0.25
  θ_reb: 0.25
  θ_health: 0.15

  decay_per_min: 0.005

  k_t: 0.6   # theft arrival
  k_s: 0.3   # sabotage
  k_r: 0.2   # riots
  k_c: 0.15  # militia clashes
  k_a: 0.4   # ambush
  k_h: 0.1   # health

  deterrence_drop: 0.08
  deterrence_minutes: 120
  blowback_gain: 0.06

  curfew_threshold: 0.65
  martial_threshold: 0.85

  bounty_default: 400
  response_latency_target_min: 10
  legitimacy_eps: 0.01
```

---

## 9) Pseudocode

```python
def minute_security_update(world):
    for w in world.wards:
        pull = decay_to_baseline(w)
        push = sum_pushes_from_events(w)
        w.ρ_env = clamp(w.ρ_env + pull.env + push.env, 0, 1)
        w.ρ_crime = clamp(w.ρ_crime + pull.crime + push.crime, 0, 1)
        w.ρ_mil = clamp(w.ρ_mil + pull.mil + push.mil, 0, 1)
        w.ρ_reb = clamp(w.ρ_reb + pull.reb + push.reb, 0, 1)
        w.ρ_health = clamp(w.ρ_health + pull.health + push.health, 0, 1)

    for r in world.routes:
        if bernoulli(k_a * ambush_prob(r)):
            create_incident("AMBUSH", r)

def respond_to_incident(inc):
    policy = choose_response(inc)
    outcome = simulate_resolution(inc, policy)
    apply_feedback(inc, policy, outcome)
```

---

## 10) Explainability & Audit

For each incident keep:
- **Why here?** top contributing risks with weights.  
- **Why that response?** threshold logic & resource availability.  
- **Outcomes** with evidence references; rumor emissions linked.  
- **Feedback** applied to risk, legitimacy, prices.

---

### End of Security Loop v1

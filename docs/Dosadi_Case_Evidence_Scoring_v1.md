# **Case Evidence Scoring v1**

Credibility/salience model for evidence used by the **Arbiters’ Guild** and downstream systems (rumor, legitimacy, reliability). Integrates with **Contract & Case State Machines v1**, **Scoring v1**, and **Event Bus v1**.

> Timebase: evidence values update on **MinuteTick**; decay/aging per SVR.  
> Scope: computes **cred ∈ [0,1]**, **sal ∈ [0,1]**, and **weight ∈ [0,1]** per evidence and aggregates to case‑level scores.

---

## 0) Evidence Types & Base Priors

```
LEDGER     (official reservoirs/credits ledgers, double-entry)      base_cred 0.90  base_sal 0.60
SENSOR     (facility monitors, gate logs, cams, IoT)                 base_cred 0.80  base_sal 0.70
VIDEO      (portable recordings, bodycams)                           base_cred 0.75  base_sal 0.80
WITNESS    (human statement; signed by witness)                      base_cred 0.60  base_sal 0.50
MEDICAL    (clinic reports, autopsies)                               base_cred 0.85  base_sal 0.70
TOKEN      (escrow proofs, cryptographic receipts)                   base_cred 0.88  base_sal 0.55
INTEL      (informant reports; graded sources)                       base_cred 0.55  base_sal 0.60
ANALYSIS   (arbiter/forensic syntheses; derived)                     base_cred 0.70  base_sal 0.65
```

Priors are policy-configurable and venue-adjusted (see §7).

---

## 1) Adjustments per Evidence

For a piece `e` with priors `(c0, s0)` compute modifiers in `[−1, +1]` then clamp final scores to `[0,1]`.

**a) Source Reliability (`Δsrc`)**  
- `Δsrc = + (rep_src - 0.5) * α_src` for witnesses/submitters.  
- For SENSOR/LEDGER, use operator’s reliability and device trust score.

**b) Chain of Custody (`Δcoc`)**  
- Full cryptographic chain → `+α_coc`.  
- Missing hops → `−k * missing_fraction`.  
- Tamper flags → set `tampered=True`, hard cap `cred ≤ τ_tamper`.

**c) Temporal Proximity (`Δtime`)**  
- `Δtime = +α_time * exp(−λ_time * Δmin)` if immediate; decays with delay.

**d) Corroboration (`Δcorr`)**  
- Let `M` corroborating items with positive agreement; `N` total.  
- `Δcorr = α_corr * (M/N)^γcorr` with diminishing returns.

**e) Venue Integrity (`Δvenue`)**  
- Civic center adds `+α_venue`; black‑market node `−α_venue_bm` unless token proof present.

**f) Bias Correction (`Δbias`)**  
- If witness has alignment toward a litigant, subtract `α_bias * |alignment| * sign(favorable)`.

**g) Visibility & Public Interest (`Δvis`)** *(affects salience more than credibility)*  
- Public, high‑audience events add salience: `sal += β_vis * audience_norm`.

**Final per‑evidence**  
```
cred_e = clamp(c0 + Δsrc + Δcoc + Δtime + Δcorr + Δvenue + Δbias, 0, 1)
sal_e  = clamp(s0 + Δvis + 0.5*max(0, Δcorr), 0, 1)
weight_e = cred_e * (0.5 + 0.5*sal_e)   # prefer credible & salient
```

---

## 2) Aging & Decay

Per minute:
```
cred_e  ← cred_e * exp(−λ_cred * Δmin)       # λ_cred default 0.002/min
sal_e   ← sal_e  * exp(−λ_sal  * Δmin)       # λ_sal  default 0.001/min
weight_e← weight_e* exp(−λ_w    * Δmin)      # λ_w    default 0.001/min
```
Reset small boosts on re‑verifications (e.g., re-signed attestations) capped by priors.

---

## 3) Aggregation to Case Scores

For case `K`, split evidence by **supports** vs **refutes** proposition `P` (determined at intake).

```
S = Σ weight_e over supports
R = Σ weight_e over refutes
T = S + R + ε
case_strength = S / T                     # ∈ [0,1], favoring supports
case_confidence = (S + R) / (S + R + κ)   # more total weight → more confidence
```

**Decision thresholds (policy)**  
- Proceed to **HEARING** if `case_confidence ≥ θ_conf_min`.  
- **RULING-eligible** if `case_strength ≥ θ_strength` and `case_confidence ≥ θ_conf_rule`.

Emit `CaseScoresUpdated {case_id, strength, confidence}` on changes crossing thresholds.

---

## 4) Conflict & Inconsistency Handling

- If two high-cred items **contradict**, both get a penalty:  
  `cred ← cred * (1 − δ_conflict)` and create an `EVIDENCE_CONFLICT` flag.  
- If VIDEO/SENSOR disagree with WITNESS and their device trust ≥ τ_device, prefer device and damp witness by `δ_device_overrides`.

---

## 5) Tamper & Fraud Signals

Set `tampered=True` if any of:
- Hash mismatch or chain break on LEDGER/SENSOR/VIDEO.  
- Witness recantation with corroboration elsewhere.  
- Statistical anomalies (ledger totals fail conservation).

Tampered evidence is retained but capped and highlighted in Arbiter UI; repeated submitters lose **source reliability**.

---

## 6) Integration with Rumor & Legitimacy

- PUBLIC evidence with `sal_e ≥ θ_rumor_sal` emits `RumorEmitted` with `(cred=cred_e, sal=sal_e)`.  
- High‑cred public rulings boost **Legitimacy** more; biased or low‑cred rulings reduce it (Scoring v1 §3).

---

## 7) Venue & Type Modifiers (Policy Knobs)

```yaml
evidence:
  base_priors:
    LEDGER:  {cred: 0.90, sal: 0.60}
    SENSOR:  {cred: 0.80, sal: 0.70}
    VIDEO:   {cred: 0.75, sal: 0.80}
    WITNESS: {cred: 0.60, sal: 0.50}
    MEDICAL: {cred: 0.85, sal: 0.70}
    TOKEN:   {cred: 0.88, sal: 0.55}
    INTEL:   {cred: 0.55, sal: 0.60}
    ANALYSIS:{cred: 0.70, sal: 0.65}
  α_src: 0.30
  α_coc: 0.20
  λ_time: 0.02
  α_time: 0.15
  α_corr: 0.25
  γcorr: 0.6
  α_venue: 0.10
  α_venue_bm: 0.08
  α_bias: 0.20
  β_vis: 0.25
  τ_tamper: 0.35
  λ_cred: 0.002
  λ_sal: 0.001
  λ_w:   0.001
  θ_conf_min: 0.35
  θ_conf_rule: 0.55
  θ_strength: 0.60
  θ_rumor_sal: 0.70
  δ_conflict: 0.15
  δ_device_overrides: 0.25
```

---

## 8) Pseudocode

```python
def score_evidence(e, ctx):
    c, s = prior(e.type)
    c += α_src * (source_reliability(e) - 0.5)
    c += chain_bonus(e.coc)
    c += α_time * math.exp(-λ_time * minutes_since(e.event_min))
    c += α_corr * corroboration_power(e, ctx)
    c += venue_adjust(e.venue, e.type)
    c -= α_bias * bias_alignment(e) * favorability(e)

    c = clamp(c, 0, 1)
    s = clamp(s + β_vis * audience_norm(e) + 0.5*max(0, α_corr * corroboration_power(e, ctx)), 0, 1)

    if tamper_detected(e):
        c = min(c, τ_tamper)
        e.flags.add("TAMPER")

    w = c * (0.5 + 0.5*s)
    return c, s, w

def aggregate_case(K):
    S, R = 0.0, 0.0
    for e in K.evidence:
        c,s,w = score_evidence(e, K.ctx)
        if e.supports: S += w
        else:          R += w
    strength = S / max(S+R, 1e-6)
    confidence = (S+R) / (S+R + κ)
    emit_if_thresholds_change(K.id, strength, confidence)
    return strength, confidence
```

---

## 9) Explainability

For each evidence item store a breakdown documenting contributions of each modifier (`Δsrc, Δcoc, Δtime, Δcorr, Δvenue, Δbias, Δvis`) and the final trio `(cred, sal, weight)`. Provide a case‑level summary with top contributing evidence for/against.

---

### End of Case Evidence Scoring v1

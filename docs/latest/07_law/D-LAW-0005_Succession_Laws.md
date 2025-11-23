---
title: Succession_Laws
doc_id: D-LAW-0005
version: 1.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-11
parent: D-LAW-0001
---
# **Succession Laws v1.1 (Legitimacy, Claims, and Transfer of Power)**

**Purpose.** Define how leadership of factions (from King to ward lords to guilds and militias) transfers hands in Dosadi; how *legitimacy* is assessed; how claims are made, contested, and resolved; and how outcomes propagate across Law, Security, Economy, and Rumor systems.

Integrates with **Factional & Governance v1**, **Law & Contract Systems v1** (Arbiters & Contracts), **Rumor Credibility v1.1**, **Barrel Cascade v1.1**, **Security/Escort v1**, **Clinics v1**, **Work–Rest v1**, **Credits & FX v1**, and the **Tick Loop**.

> Timebase: claim windows can be measured in **days**; legitimacy updates **hourly**; emergency succession can finalize within **minutes** after death/coup.\n
---
## 0) Core Definitions

- **Office**: a leadership seat in a faction. `{office_id, faction_id, title, rank, scope, term: LIFE|FIXED|AT_WILL}`
- **Incumbent**: `{agent_id, start_date, mandate_doc, legitimacy}`
- **Legitimacy**: *probability-weighted obedience* to the office holder’s orders by the relevant audience (staff, vassals, public). Computed from:
  - **Performance** (delivery on mandates: cascade coverage, security, clinics, labor output)
  - **Meme Polarity** (net positive/negative narratives about competence/corruption)
  - **Lawfulness** (contract compliance, audits passed, Arbiter decrees)
  - **Force Posture** (ability to enforce, coalition size/equipment)
  - **Continuity** (recognized line of succession, heir tokens, oaths kept)
- **Claimant**: an agent (or council) asserting right to the office. Claims types: `HEREDITARY | APPOINTIVE | ELECTIVE | COUP | RECEIVERSHIP (arbiter)`
- **Heir Token**: signed artifact proving designated succession (seal + ledger hash); redeemable at Arbiter for recognition.
- **Oath Contract**: tokenized contract binding vassals/units to an office holder/claimant (with penalties for breach).
- **Receivership**: temporary technocratic control imposed by Arbiters over a failing faction (fraud, collapse).\n
---
## 1) Sources of Legitimacy (Computation)

Let the relevant audience for office *O* be set **A** (vassals, employees, public in ward W). Legitimacy ∈ [0,1]:
```
Legit_O = clamp( w_perf*Perf + w_meme*Meme + w_law*Law + w_force*Force + w_cont*Continuity )
```
- **Perf**: normalized KPI basket: `CascadeCoverage↑, DeliveryVariance↓, ClinicMortalityAdj↓, SecurityIncidentsAdj↓, WorkViolations↓`.
- **Meme**: meme index polarity for claims about competence/corruption (weighted by reach & credibility).
- **Law**: contract fulfillment rate, tax compliance, audit pass rate; Arbiter decrees (uphold/retract/sanction).
- **Force**: effective ready strength (quality×quantity×logistics); QRF times, escort success rate.
- **Continuity**: presence of heir token, clear bylaws, vassal oaths up-to-date, succession rehearsals.

**Thresholds:**
- `T_govern` (e.g., 0.60): below this, orders often fail; corruption rises.
- `T_contest` (e.g., 0.55): claimants may legally file contest.
- `T_coup` (e.g., 0.45): power vacuum dynamics activate (see §6).
Legitimacy updates hourly; spikes from scandals, audits, or victories can move it rapidly.\n
---
## 2) Succession Archetypes & Default Rules

### A) **King (Well Sovereign)**
- **Rule**: Hereditary with **Designated Heir Token**; failing that, **Great Vassal Council** elects from dukes.
- **Veto**: Arbiter may block a patently invalid heir (forgery) but not policy disagreements.
- **Crisis**: If king falls < `T_govern` while cascade collapses, Council may invoke **Regency** (Receivership of Well ops).

### B) **Feudal Lords (Dukes, Ward Lords)**
- **Rule**: Hereditary or Appointive by superior (king/duke) + Oath Contracts.
- **Contest**: Eligible challengers (bloodline, appointed deputy, or vassal coalition) can file **Claim of Competence** if Incumbent < `T_contest`.
- **Hearing**: Arbiter convenes *Legitimacy Hearing* with KPIs + meme evidence + oath counts.

### C) **Mercenary / Military Companies**
- **Rule**: **Elective by Force**—leader is officer with greatest *effective combat power* and contract book.
- **Audit**: Must publish readiness ledger; fraud → Arbiter receivership; mutiny if payroll defaults.

### D) **Industrial Guilds**
- **Rule**: **Competence College**—masters vote; weight = proven output + apprenticeship lineage.
- **Continuity**: Deputy Master acts if leader dies; election within N days.

### E) **Civic Commonwealths / Councils**
- **Rule**: **Elective** among civic service heads; legitimacy weighted by service uptime (food/med/rec/finance/comms).

### F) **Mystic Cults**
- **Rule**: **Doctrine-bound** (trial/vision/council). Arbiter intervenes only on criminal claims or mass-harm risk.

### G) **Bureaucratic Networks (Arbiters, Clerks)**
- **Rule**: **Seniority & Merit** hybrid; panels appoint; recusal to avoid conflicts.

### H) **Criminal / Smuggling Syndicates** (optional)
- **Rule**: **Power Auction**—stock of favors, routes, and crews; tokens via black boards ensure anonymous transfers.\n
---
## 3) Claim Lifecycle

1) **Trigger**: vacancy (death, abdication, deposition), or legitimacy below `T_contest` (or scandal event).
2) **Notice Window**: `N_notice` hours to register intent; submit claim type + evidence (heir token, oaths, KPIs).
3) **Cooling-Off**: `N_cool` hours for mediation; duels/proxy conflicts prohibited in inner/middle wards.
4) **Hearing**:
   - **Evidence Docket**: KPIs (past 30 days), meme index, audits, oaths tally, force posture.
   - **Public Arguments**: optional broadcast (improves Meme transparency; backfires if weak).
   - **Arbiter Findings**: *Recognize*, *Reject*, or *Order Runoff* (e.g., council vote, trial-by-task).
5) **Decision & Oaths**: winner posts **Succession Contract**; vassals renew oaths (with exit clauses).

Timers and ward-tier policies modulate each phase (outer wards may skip cooling-off).\n
---
## 4) Edge Cases & Special Processes

- **Regency**: minor heir → Regent (appointed per bylaw or Arbiter) limited to operational mandates.
- **Dual Claims**: if two claimants exceed `T_govern` with different audiences, Arbiter may split scope or order **Power Trial**.
- **Power Trial** (bounded contest): convoy protection, clinic stabilization, or production mandate; winner by KPI target.
- **Receivership**: for fraud/collapse: Arbiter installs caretaker; auctions contracts; schedules new succession within `N_days`.
- **Coup**: if Incumbent < `T_coup` and challenger’s force × legitimacy > threshold, **Coup Attempt** event proceeds (Security Loop handles kinetics); Arbiter later validates or sanctions.\n
---
## 5) Contracts, Tokens, and Oaths

- **Heir Token**: `issuer_sign + heir_sign + hash(mandate_doc)`; revocable only by new token or Arbiter decree.
- **Succession Contract**: lists obligations (`cascade coverage, clinics, security, tax`) → becomes **performance bond**.
- **Oath Contracts**: vassals pledge obedience conditional on incumbent legitimacy ≥ `T_govern` and payroll solvency.
- **Black-board Tokens** (illegal): used by syndicates; Arbiter may invalidate upon exposure; still powerful in outer wards.\n
---
## 6) Legitimacy Dynamics & Rumors

- Meme engine updates **hourly**; **public boards** in transparent wards accelerate stabilization.
- **Positive shocks**: ambush repelled, mandate exceeded, clinic mortality drop → legitimacy +ε.
- **Negative shocks**: cascade theft case, hygiene scandal, tax fraud → legitimacy −ε.
- **Counterspeech**: publish evidence bundles; Arbiter decrees apply large credibility weights (can flip polarity).
- **Decay**: absent performance, legitimacy drifts toward priors; rumor suppression in opaque wards increases volatility.\n
---
## 7) Enforcement & Violence Bounds

- Inner wards: strict ROE; hearings mandatory; coups rare and punished.
- Middle: mixed; hearings common but time‑boxed; limited show‑of‑force allowed.
- Outer: pragmatic; Arbiter presence thin; receivership and power trials replace lengthy hearings; violence more decisive.\n
---
## 8) Policy Knobs (defaults)

```yaml
succession:
  T_govern: 0.60
  T_contest: 0.55
  T_coup: 0.45
  windows:
    notice_hours: 24
    cool_hours: 12
    runoff_hours: 8
  weights:
    performance: 0.30
    meme: 0.25
    law: 0.20
    force: 0.15
    continuity: 0.10
  receivership_triggers:
    audit_fraud: true
    liquidity_crisis_days: 7
    clinic_mortality_spike: true
  power_trial_menu:
    - "Escort a cascade lane with ≤2% loss"
    - "Reduce clinic LWBS by 50% in 48h"
    - "Meet a production quota with ≤1% variance"
```

Knobs are ward‑tiered; inner wards tend toward longer windows and heavier law weights.\n
---
## 9) Event & Function Surface (for Codex)

**Functions**
- `open_succession(office_id, trigger)` → initializes timers; posts notice.
- `register_claim(office_id, agent_id, claim_type, evidence)` → validates token/oaths; enters docket.
- `run_hearing(office_id)` → aggregates KPIs/memes/audits; returns finding.
- `order_power_trial(office_id, trial_type)` → spins scenario and KPI targets.
- `finalize_succession(office_id, winner_id)` → issues decree, rotates oaths/payroll/keys.
- `enter_receivership(faction_id, cause)` → installs caretaker; sets auction.
- `update_legitimacy(office_id)` → recompute hourly via weights.

**Events**
- `SuccessionOpened`, `ClaimRegistered`, `HearingStarted`, `ArbiterDecree`, `PowerTrialOrdered`, `PowerTrialCompleted`, `SuccessionFinalized`, `ReceivershipStarted`, `LegitimacyUpdated`.\n
---
## 10) Pseudocode (Legitimacy & Hearing)

```python
def update_legitimacy(office, kpis, meme, law, force, continuity, w):
    L = clamp(
        w["performance"]*kpis.score +
        w["meme"]*meme.polarity +
        w["law"]*law.compliance +
        w["force"]*force.effective +
        w["continuity"]*continuity.score
    )
    emit("LegitimacyUpdated", {"office": office.id, "legitimacy": L})
    return L

def run_hearing(office, claims):
    evidence = gather(office, claims)
    L = update_legitimacy(office, **evidence.weights)
    if valid_heir_token(evidence): return DECREE.RECOGNIZE
    if L < policy.T_contest and better_claimant_exists(evidence):
        return DECREE.RUNOFF_OR_TRIAL
    return DECREE.RETAIN
```

---
## 11) Typical Scenarios

- **Clean Heir Transfer**: king dies; heir token verified; vassal oaths renewed; Cascade steady → legitimacy stable.
- **Competence Challenge**: ward lord misses mandates; meme turns negative; deputy files claim; *Power Trial*: escort lane ≤2% loss → deputy wins.
- **Receivership**: guild caught in meter fraud; Arbiter seizes; caretaker runs auctions; election in 5 days.
- **Outer Ward Coup**: incumbent < `T_coup`; rival with superior force takes throne; Arbiter later sanctions but accepts de facto control.\n
---
## 12) Dashboards & Explainability

- **Office Card**: legitimacy trend, KPI deltas, meme polarity, oath counts, force posture.
- **Docket Viewer**: claims, evidence bundles, hearing schedule, decrees.
- **Power Trial Board**: live KPIs vs target; public wagers/rumor spikes (optional future).\n
---
## 13) Test Checklist (Day‑0+)

- Heir token + sufficient continuity → auto‑recognition unless fraud flagged.
- When Incumbent < `T_contest`, valid challenger opens hearing; decision within policy windows.
- Meme shocks (audit scandal) move legitimacy by ≥ ε and can flip outcome when near threshold.
- Power Trial outcomes switch leadership when KPI targets met; oaths rotate; contracts and keys transfer.

---
### End of Succession Laws v1.1

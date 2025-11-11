---
title: Dosadi_Rumor_Credibility_Propagation
doc_id: D-INFO-0002
version: 1.1.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-INFO-0001
---
# **Rumor Credibility Propagation v1.1 (Perception, Memes, Evidence, and Defamation)**

**Purpose:** Model how observations become beliefs, beliefs become rumors, rumors become *memes*, and information flows reshape behavior, prices, legitimacy, and conflict. Adds evidence weighting, faction “knowledge banks,” Arbiter defamation checks, and counterspeech dynamics.

Integrates with **Perception & Memory v1**, **Factional & Governance v1**, **Law & Contract Systems v1** (Arbiters), **Security/Escort v1**, **Barrel Cascade v1.1**, **Credits & FX v1**, **Clinics v1**, **Work–Rest v1**, and the **Tick Loop**.

> Timebase: memory updates **per Minute**; rumor exchanges **per Interaction**; credibility recomputation **per 5 Minutes**; public meme indices **hourly**.
---
## 0) Concepts & State
- **Observation**: `{who, what, where, when, modality: SIGHT|SOUND|TEXT|SENSOR, salience, evidence_bundle?}`
- **Claim** (normalized proposition): text key + typed slots, e.g., `"duke_X diverted 2000 L"`, `"clinic_Y LWBS spike"`.
- **Belief** (per agent): `{claim_id, cred ∈ [0,1], confidence, last_update, source_map{faction/person→weight}}`.
- **Rumor** (message): `{claim_id, stance: SUPPORT|REFUTE|UNSURE, payload: summary+evidence_refs, channel, privacy}`.
- **Meme** (public narrative): aggregation of many rumors to a stable story kernel; `{claim_id, meme_score, polarity}`.
- **Faction Knowledge Bank**: per‑faction curated set of vetted claims with provenance; ranks by utility to faction goals.
- **Evidence Bundle**: pointers to `SENSOR`, `VIDEO`, `LEDGER`, `WITNESS`, `ARBITER_DECREE`.
- **Defamation Case**: Arbiter process for contested claims harming reputation.
---
## 1) Credibility Model (per Agent per Claim)
`cred = clamp( w_obs*Obs + w_src*Src + w_net*Net + w_ev*Ev − w_bias*Contradiction − w_opp*Opposition )`
- **Obs**: firsthand observation confidence (modality quality × conditions × memory freshness).  
- **Src**: trust in sender (relationship, reputation, role proximity).  
- **Net**: network reinforcement (trusted alters repeating the claim; discounts duplicates).  
- **Ev**: evidence quality (bundle type weights; cross‑verifiable hashes ↑, anonymous hearsay ↓).  
- **Contradiction**: strength of disconfirming experiences or refutations with evidence.  
- **Opposition**: the claim hurts an allied faction or conflicts with strong priors; scaled by **partisanship**.
**Belief vs Propagation**: 
- **Belief Thresholds**: `T_believe`, `T_doubt`, `T_reject`.  
- **Share Thresholds**: `T_share_public ≥ T_believe`, `T_share_private ≤ T_believe`.  
- Agents can *believe but not share* (fear, secrecy) or *share without belief* (strategic behavior), but the latter is disabled until propaganda rules are added explicitly.
---
## 2) Memory & Decay
- **Observation decay**: exponential with half‑life by salience; rehearsed claims reset decay.  
- **Rumor decay**: network‑dependent; isolated claims fade faster.  
- **Meme stabilization**: once `meme_score` > `M_stable` with diverse sources and low contradiction, it becomes **decay‑resistant**; retractions require strong evidence or Arbiter decree.
---
## 3) Channels & Privacy
- **Direct** (whisper, encrypted token): high trust, low reach, slow.  
- **Faction Forums** (in‑house briefings): moderate trust, scoped reach; can mark *internal only*.  
- **Public Nodes** (markets, civic boards): large reach; higher Arbiter scrutiny; creates strong meme pulses.  
- **Black‑Market Boards**: anonymous; low trust; high rumor volatility; token‑contract payments for tips.
Channel choice affects `Src` and `Opposition` weights and legal risk.
---
## 4) Evidence Bundles (weights example)
```yaml
evidence_weights:
  SENSOR: 0.35   # meter/GPS hash matches, clock sync
  VIDEO:  0.30   # clear POV, chain-of-custody present
  LEDGER: 0.25   # official records, receipts
  WITNESS:0.15   # named > anonymous
  ARBITER_DECREE: 0.40  # overrides others; can flip polarity
  ANON_HEARSAY: 0.05
  PUBLIC_DASH: 0.20  # published clinic/cascade boards
```
Evidence correctness uses cross‑checks (hash, time, route, issuer keys). Conflicts spawn **cases**.
---
## 5) Propagation Mechanics
At an **interaction** between sender `S` and receiver `R`:
1) **Eligibility**: `S.cred(claim) ≥ T_share_private` and `channel_policy_ok`.  
2) **Message Build**: include stance & compact evidence set; `S` can omit sources (privacy loss → lower weight).  
3) **Reception Update**: `R` recomputes `cred` with its own weights; stores/updates Belief.  
4) **Downstream Decisions**: `R` may share (public/private), act (buy/sell/avoid), or open a **Defamation** case if harmed.
**Anti‑spam**: channel rate limits per agent/faction; duplicate suppression; credibility damping for high‑volume spammers.
---
## 6) Faction Knowledge Banks
- **Curate**: ingest claims with evidence; rank by *actionability* and *alignment*.  
- **Access Control**: rank‑gated; leaks create reputational penalties and legal risk.  
- **Publication**: some vetted claims become **public advisories** (safety warnings, fraud alerts) raising meme score quickly.
---
## 7) Defamation & Arbiters
- **Trigger**: if a claim reduces `Reputation` beyond threshold or involves criminal allegation without sufficient evidence.  
- **Process**: `CaseOpened` → evidence submission → Arbiter hearing → `ARBITER_DECREE` (UPHOLD | RETRACT | SANCTION).  
- **Outcomes**: decrees push large positive/negative weights into `Ev`; can impose fines, forced retractions, or apology broadcasts.  
- **Strategic Silence**: failing to contest damaging memes may allow stabilization against the target.
---
## 8) Memes (Public Narrative Index)
- For each claim, compute `meme_score = Σ (audience_weight × cred × reach × recency) − contradiction_penalty`.
- Track **polarity** (supports vs refutes).  
- Publish **Meme Board** hourly in wards with transparency norms; outer wards may suppress boards (rumor variance ↑).
---
## 9) Behavior Hooks
- **Market**: price spreads widen with negative memes about cascade delivery; clinics with “dirty” memes see LWBS↑.  
- **Security**: ambush probability ↑ when memes of weak escorts trend; escorts reputation adjusts contract rates.  
- **Legitimacy**: lords’ legitimacy shifts with meme polarity about competence/corruption; affects rebellion risk.  
- **Work–Rest**: collapse rumors increase safety buffers; productivity dips but incidents fall.
---
## 10) Policy Knobs (defaults)
```yaml
rumor:
  T_believe: 0.6
  T_doubt: 0.4
  T_reject: 0.2
  T_share_public: 0.7
  T_share_private: 0.5
  w:
    obs: 0.35
    src: 0.20
    net: 0.15
    ev:  0.30
    bias: 0.20    # subtractive
    opp:  0.10    # subtractive
  decay_half_minutes:
    observation: 240
    rumor: 360
    meme: 1440
  spam_limit_per_hour: 6
  duplicate_supp_window_min: 30
  defamation_threshold: 0.15   # Δ reputation in short window
  arbiter_override_weight: 0.9
```
---
## 11) Event & Function Surface (for Codex)
**Functions**
- `record_observation(agent_id, claim, evidence)` → adds/updates Belief with Obs weight.  
- `compose_rumor(agent_id, claim, stance, channel, evidence_refs)` → returns rumor packet if eligible.  
- `transmit_rumor(sender_id, receiver_id|channel)` → updates receiver Belief; handles rate limits.  
- `update_meme_index(ward_id)` → aggregates rumor streams → meme_score & polarity; publishes boards.  
- `open_defamation_case(target, claim_id)` → Arbiter process; later `ARBITER_DECREE`.  
- `publish_advisory(faction_id, claim_id, evidence)` → vetted public note (big Ev bump).
**Events**
- `ObservationLogged`, `BeliefUpdated`, `RumorTransmitted`, `MemeIndexUpdated`, `DefamationCaseOpened`, `ArbiterDecree`, `AdvisoryPublished`.
---
## 12) Pseudocode (Credibility & Sharing)
```python
def update_cred(agent, claim, inputs):
    Obs = obs_score(agent, claim)
    Src = source_trust(agent, inputs.sender)
    Net = net_reinforcement(agent, claim)
    Ev  = evidence_quality(inputs.evidence)
    Contr = contradiction_strength(agent, claim)
    Opp = opposition_penalty(agent, claim)
    cred = clamp(w.obs*Obs + w.src*Src + w.net*Net + w.ev*Ev - w.bias*Contr - w.opp*Opp)
    return cred

def maybe_share(agent, claim, ch):
    cred = agent.belief[claim].cred
    if ch == "PUBLIC" and cred >= T_share_public: return build_packet(...)
    if ch == "PRIVATE" and cred >= T_share_private: return build_packet(...)
    return None
```
---
## 13) Explainability & Dashboards
- **Per‑agent rationale**: spider chart of Obs/Src/Net/Ev versus Bias/Opp; last evidence seen.  
- **Claim timeline**: meme score trajectory with source mix; Arbiter decrees highlighted.  
- **Leak tracker**: which faction knowledge items escaped; sanctions if recurrent.
---
## 14) Test Checklist (Day‑0+)
- Evidence‑rich claims cross `T_believe` faster than hearsay; Arbiter decrees flip polarity reliably.  
- Spam throttles cap per‑agent transmissions; duplicates within window are suppressed.  
- Negative escort memes increase ambush attempts; clinic “dirty” memes push LWBS up unless hygiene improved.  
- Publishing a vetted advisory propagates faster and with higher final meme_score than ordinary rumors.
---
### End of Rumor Credibility Propagation v1.1

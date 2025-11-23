---
title: Smuggling_Loop
doc_id: D-INFO-0011
version: 1.0.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-INFO-0001
---
# **Smuggling Loop v1 (Routes, Safehouses, Detection, Seizure, and Distortions)**

**Purpose:** Model cross‑ward illicit movement of water, credits, narcotics, weapons, and information—how smugglers operate, how authorities detect and interdict, and how this loop feeds prices, FX, legitimacy, and rumors.

Integrates with **Security Loop v1**, **Market v1**, **Credits & FX v1**, **Rumor & Perception v1**, **Law & Contract Systems v1**, **Labor v1**, **Maintenance v1**, and **Tick Loop**.

> Cadence: route risk & patrol intensity update **per Minute**; price/FX impacts and legitimacy aggregate **per Day**.

---

## 0) Actors & Assets

- **Smuggler Factions**: cells with `operators`, `scouts`, `forgers`, `fixers`. Reputation keys access to **black‑nodes**.

- **Cargo**: `water_L`, `credits (physical chits)`, `narcotics`, `weapons`, `high‑value components`, `intel`.

- **Vehicles & Gear**: low‑sig trucks, suit mods (thermal baffles), jammer/decoy kits, forged tokens/passes.

- **Safehouses**: route nodes with stash capacity, jammer fields, exit tunnels; owned by smugglers or corrupt locals.

- **Black‑Nodes**: escrow markets using token‑based contracts and proxies for creator anonymity.

---

## 1) Job & Planning Surface

- **Token‑Escrow Contracts** (at black‑nodes):

  - `pickup`, `drop`, `window_min`, `route_hint`, `bonus_hazard`, `penalty_seizure`.

- **Planning**: select path (gate vs wild), safehouses, and deception plan (decoys, split‑loads, forged docs).

- **Crew Assignment**: driver + escort + scout + fixer; suits/tools checked against risk profile.

Events: `SmuggleContractOpened`, `SmugglePlanCommitted`, `CrewAssembled`.

---

## 2) Route Types & Detection Model

**2.1 Gate Routes**

- Pros: fast, predictable; Cons: checkpoints, scanners, clerks. 

- **Detection probability** per checkpoint:

  - `P_det_gate = base * (cargo_heat) * (alert_level) * (1 - bribery_effect) * (1 - forged_pass_quality)`

**2.2 Wild Routes (walls, drains, tunnels)**

- Pros: bypasses most checks; Cons: slow, terrain risk, higher chance of ambush.

- **Detection probability** via patrols/sensors:

  - `P_det_wild = base * patrol_density * sensor_quality * route_exposure`

**2.3 Mixed**: split cargo with decoy vs main load; escorts influence outcomes.

Events: `CheckpointScan`, `PatrolSweep`, `SensorPing`.

---

## 3) Execution Tick (Minute)

For an active run:

1) **Scout Sweep** → update risk nowcast; if hot, reroute or delay.

2) **Transit Step** → progress along edge; time cost accumulates.

3) **Encounter Roll** (ordered): sensor → checkpoint → patrol → ambush.

4) **Response** — choices: bribe/forged doc, flee, fight, dump cargo, or surrender.

5) **Log** evidence: scans, bribes, shots fired → feed **Rumor/Evidence**.

Events: `SmuggleTransitTick`, `Encounter`, `BribeOffered/Accepted`, `Skirmish`, `CargoDumped`.

---

## 4) Outcomes

- **Success**: `SmuggleCompleted{cargo, value, route, safehouses_used}`; prices locally **fall** if water/food arrives; narcotics/arms **raise** crime pressure.

- **Partial**: some cargo seized/dumped; rumors spike; FX discount may widen on issuer embarrassment.

- **Seizure**: `SmuggleSeized{by: guard|rival|bandit, evidence}`, legal case opens; seized cargo re‑enters via **official auction** or **quiet diversion** (corruption).

- **Loss to Bandits**: fuels black economy; future patrol/policy change.

---

## 5) Price, FX, and Legitimacy Effects

- **Commodity Arrivals** (water/food) → ward `P_ref` ↓; spreads narrow short‑term.

- **Credit Chit Flow** between issuers → triangular FX distortions; more chits of a weak issuer outside home widens its discount.

- **High‑profile Seizure** → legitimacy `+` for enforcers (if evidence public and clean); `−` if framed as extortion/bribe.

- **Persistent Smuggling Corridors** → undercut official prices, starve tax intake; kings may shift cascade lanes or raise audits.

---

## 6) Evidence & Law Hooks

- Evidence generated along the run: `SENSOR` (scan logs), `LEDGER` (escrow), `WITNESS`, `VIDEO`, `TOKEN` (escrow proof).

- Opens **Cases**: seizure legitimacy, wrongful arrest, breach of escrow, murder, stolen cargo auctions.

- Arbiters can subpoena black‑node escrow (hash‑locked) with multi‑party reveal timers.

Events: `CaseOpened` (auto), `EvidenceSubmitted`, `ArbiterRulingIssued`.

---

## 7) Reputation & Reliability

- **Smuggler Reliability**: % successful runs, on‑time, collateral losses.

- **Checkpoint/Patrol Reliability**: clean seizures vs planted evidence/extortion.

- **Safehouse Reliability**: stash integrity and opsec; compromised houses get retired.

- Reputation changes pricing of future contracts and bribe tables.

---

## 8) Bribe Table (Conceptual)

```
bribe_required = base * cargo_value * alert_level * (1 - corruptibility)
accept_prob   = f(corruptibility, bribe_multiple, witness_risk)
```

- **Witness Risk**: higher in clean inner wards; lower at black‑nodes; video increases prosecution risk → higher bribe ask.

- **Arbiter Sting** operations periodically reduce corruptibility where scandals erupt.

---

## 9) Patrol & Policy Response

- On seizure clusters: increase patrol density, sensor upgrades, randomize checkpoint patterns.

- On famine signals: temporary **amnesty windows** for water/food smuggling (convert to official corridors).

- On narcotics/arms surge: curfews, searches, and targeted raids; risk of backlash & legitimacy drop if abusive.

Events: `PatrolPolicyUpdated`, `AmnestyWindowOpened/Closed`, `CurfewDeclared/Lifted`.

---

## 10) Policy Knobs

```yaml
smuggling:
  gate_base_det: 0.18
  wild_base_det: 0.08
  bribery_effect_max: 0.6
  forged_pass_quality_max: 0.5
  patrol_density: { inner: 0.6, middle: 0.4, outer: 0.25 }
  sensor_quality: { inner: 0.7, middle: 0.5, outer: 0.35 }
  ambush_prob_add: 0.10
  safehouse_max_per_route: 3
  escrow_fee_pct: 0.03
  evidence_leak_prob: 0.15
```

---

## 11) Event & Function Surface (for Codex)

**Functions**

- `open_smuggle_contract(spec)` → `SmuggleContractOpened`

- `plan_smuggle(contract_id, plan)` → `SmugglePlanCommitted`

- `start_smuggle(run_id)` → `CrewAssembled`

- `minute_smuggle_tick(run_id)` → `SmuggleTransitTick|Encounter|...`

- `resolve_encounter(run_id, action)` → `BribeAccepted|Skirmish|CargoDumped|Seized`

- `close_smuggle(run_id, outcome)` → `SmuggleCompleted|SmuggleSeized`

- `update_patrol_policy(ward, patch)` → `PatrolPolicyUpdated`

- `open_amnesty_window(ward, goods, window_min)` → `AmnestyWindowOpened`

**Events**

- `SmuggleContractOpened`, `SmugglePlanCommitted`, `CrewAssembled`, `SmuggleTransitTick`,

  `Encounter`, `BribeOffered/Accepted`, `Skirmish`, `CargoDumped`, `SmuggleCompleted`, `SmuggleSeized`,

  `PatrolPolicyUpdated`, `AmnestyWindowOpened/Closed`, `CurfewDeclared/Lifted`.

---

## 12) Typical Scenarios

- **Water Relief Run to W21**: success lowers prices & hoarding; if seized with video, legitimacy for guards +ε; if extortion rumor leaks, −ε.

- **Narcotics Surge**: short‑term calm (addiction), long‑term crime/clinic load ↑; Arbiter stings target corrupt checkpoints.

- **Weapons Pipeline**: raises ambush lethality; king shifts cascade, increases escort bounties, and opens amnesty for food/water only.

---

## 13) Explainability

- For each `run_id`, keep: route, safehouses, cargo manifest, encounter log, bribes, losses, time, evidence links.

- Counterfactuals: “If forged pass quality +0.2, detection −30% at Gate‑3; ETA −12 min; expected P&L +18%.”

---

### End of Smuggling Loop v1

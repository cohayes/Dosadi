# **Dosadi Agent Action API v1**

A unified verb set for agents and systems to change world state via the event bus.  
Each action defines **preconditions**, **costs**, **effects**, **emitted events**, and **failure modes**.  
Timebase: **tick = 0.6 s**, **100 ticks = 1 minute**. RNG must use per‑system streams (see Tick Loop v1).

---

## 0) Action Envelope (Standard)

```json
{
  "action_id": "string",
  "actor": "AgentID|FactionID",
  "verb": "StringEnum",
  "start_tick": 0,
  "eta_ticks": 0,
  "target": { "agent":"AgentID|null", "faction":"FactionID|null", "ward":"WardID|null", "place":"FacilityID|null", "asset":"ID|null" },
  "params": { "k": "v" },
  "preconditions_checked": true,
  "status": "QUEUED|RUNNING|SUCCESS|FAIL|CANCELLED|INTERRUPTED",
  "outcome": { "effects": {}, "events": ["EventID"], "notes": "string" }
}
```
**Engine rules**
- Preconditions are *pure* checks against current state; if false, action never starts.
- Costs are debited atomically at start (or at milestone for long actions).
- Effects occur atomically at completion; events emitted then.
- Actions can be **interrupted** by security/combat or facility outages; partial costs may remain.
- All state changes are also reflected via **events** for subscribers.

---

## 1) Taxonomy of Verbs

1. **Survival & Physiology**: `Rest`, `ConsumeRation`, `UseNarcotic`, `RelieveAtFacility`.  
2. **Perception & Movement**: `Observe`, `Scout`, `MoveTo`, `Tail`.  
3. **Social & Lawful**: `Commune`, `Negotiate`, `RegisterContract`, `WitnessContract`, `PayTax`, `RaiseDispute`.  
4. **Economic & Production**: `Labor`, `Craft`, `CookRations`, `Trade`, `Buy`, `Sell`.  
5. **Maintenance & Infrastructure**: `RepairSuit`, `MaintainFacility`, `InstallComponent`.  
6. **Security & Combat**: `Escort`, `Guard`, `Patrol`, `SeizeAsset`, `Ambush`, `Flee`.  
7. **Black‑Market & Covert**: `Smuggle`, `FenceGoods`, `TokenContractCreate`, `TokenEscrowSettle`, `Hide`.  
8. **Reclamation & Health**: `ReclaimBiomass`, `SeekClinic`, `TreatInjury`.

Each verb below: signature, preconditions, costs, effects, events, failure modes.

---

## 2) Survival & Physiology

### 2.1 `Rest(duration_min)`
- **Pre:** actor safe (`no active combat`), facility `SAFEHOUSE|BUNK|HOME` access OR low-risk public space.
- **Cost:** blocks actor for `duration_min * 100` ticks.
- **Effect:** Apply Scoring v1 §1 recovery for each minute; no asset change.
- **Events:** none (LOW priority optional `RestTick` for traces).
- **Fail:** interrupted by `MilitiaDeployed` curfew or `EscortAmbushed` nearby → `INTERRUPTED`.

### 2.2 `ConsumeRation(item_id)`
- **Pre:** item in inventory and not spoiled; not currently `VOMITING`.
- **Cost:** consume item; time 30 ticks.
- **Effect:** `intake_kcal`, `intake_W` set per item; small `Comf` uptick.
- **Events:** `ProductionReported` (for kitchens if tracked per-faction) optional.
- **Fail:** item invalid → `FAIL` (no cost).

### 2.3 `UseNarcotic(item_id, dose)`
- **Pre:** item available; actor not under incompatible drug.
- **Cost:** consume charges; 20–60 ticks.
- **Effect:** temporary modifiers (pain dampening, bias shift, salience boost) with crash timer.
- **Events:** `RumorEmitted` (PUBLIC) if taken in view at civic centers.
- **Fail:** overdose risk (RNG + tolerance) → health damage, possible `SeekClinic` auto‑enqueue.

### 2.4 `RelieveAtFacility(facility_id)`
- **Pre:** facility access; path exists.
- **Cost:** 20–80 ticks; nominal fee in credits.
- **Effect:** empty `Blad/Bow`; update facility reclaim feed.
- **Events:** facility `ProductionReported` (greywater/biomass).
- **Fail:** facility offline → refund, `FAIL`.

---

## 3) Perception & Movement

### 3.1 `Observe(target, duration_min)`
- **Pre:** LOS or same venue; not blinded by `DustIngress` threshold.
- **Cost:** actor occupied; 1–15 minutes typical.
- **Effect:** create **witness stub** → minute rollup to `RumorEmitted` with source credibility.
- **Events:** none immediate.
- **Fail:** target leaves; partial observation yields lower `cred/sal`.

### 3.2 `Scout(ward_or_route)`
- **Pre:** route exists; risk budget nonnegative.
- **Cost:** travel time by distance + checkpoints; stamina burn.
- **Effect:** discover hazards (ambush chance, dust pockets), update ward `infra` hints.
- **Events:** `RumorEmitted` (findings), `MaintenanceTaskQueued` if fault spotted.
- **Fail:** ambush → branch to Security.

### 3.3 `MoveTo(place)`
- **Pre:** path; passes access checks.
- **Cost:** time by distance & suit; stamina burn.
- **Effect:** new location.
- **Events:** none unless crossing restricted gates (may emit `RumorEmitted` if witnessed).
- **Fail:** blocked gate → `FAIL`.

---

## 4) Social & Lawful

### 4.1 `Commune(audience, topic, duration_min)`
- **Pre:** presence with audience; social hostility below threshold.
- **Cost:** time; small hydration/energy use.
- **Effect:** relationship deltas; possible rumor propagation to audience memory.
- **Events:** `RumorEmitted` if new intel shared; low salience by default.
- **Fail:** audience refuses → mild reputation down.

### 4.2 `Negotiate(counterparty, proposal)`
- **Pre:** minimal trust or collateral; venue supports deals (civic hall or black‑market node).
- **Cost:** time; optional escrow lock.
- **Effect:** draft contract object (not yet active).
- **Events:** none.
- **Fail:** no acceptable terms → `FAIL`.

### 4.3 `RegisterContract(contract_id)`
- **Pre:** proposal exists; required **witnesses** present OR **token** prepared (see 7.2).
- **Cost:** clerk fee; time 30–120 ticks.
- **Effect:** contract status → `ACTIVE`.
- **Events:** `ContractActivated` (PUBLIC).
- **Fail:** missing witness or invalid token → `FAIL`.

### 4.4 `WitnessContract(contract_id)`
- **Pre:** agent is registered observer; free of conflicts (or bribe risk model allows).
- **Cost:** time; minor reputation impact if corrupt.
- **Effect:** adds witness signature; boosts enforceability.
- **Events:** none.
- **Fail:** conflict uncovered later → Arbiter may apply penalties.

### 4.5 `PayTax(issuer, amount)`
- **Pre:** official transfer; has credits.
- **Cost:** credits debited.
- **Effect:** updates royal/ward coffers.
- **Events:** included in `BarrelDelivered` payload or separate `CreditRateUpdated` on shifts.
- **Fail:** insufficient funds → `FAIL` + risk flag.

### 4.6 `RaiseDispute(contract_id, reason)`
- **Pre:** contract exists and within dispute window.
- **Cost:** filing fee; time 20–60 ticks.
- **Effect:** create `ArbiterCase`.
- **Events:** `ContractDisputed` (PUBLIC).
- **Fail:** out of window → `FAIL`.

---

## 5) Economic & Production

### 5.1 `Labor(job_id)`
- **Pre:** facility online; actor has skills/affinities/tools.
- **Cost:** minute blocks; stamina and nutrition burn; suit wear if harsh env.
- **Effect:** produce output units into faction stock; raises specialization metric.
- **Events:** `ProductionReported` (PUBLIC/NORMAL).
- **Fail:** brownout or condensation failure → partial output.

### 5.2 `Craft(recipe, qty)`
- **Pre:** materials present; workshop access.
- **Cost:** consumes reagents; time per unit; risk of scrap on failure (skill‑based).
- **Effect:** items added to stock; potential tech progress for innovation paths.
- **Events:** `ProductionReported`.
- **Fail:** lack of reagents or tool break → `FAIL` or partial.

### 5.3 `CookRations(batch)`
- **Pre:** kitchen access; water/fuel available.
- **Cost:** consumes water/biomass; time.
- **Effect:** create ration items with shelf timers.
- **Events:** `ProductionReported`.
- **Fail:** fuel outage → partial.

### 5.4 `Trade(counterparty, give, get)`
- **Pre:** both stocks available; price within tolerance or via negotiation.
- **Cost:** fees; time.
- **Effect:** atomic transfer ledger entries.
- **Events:** PUBLIC if civic venue; RESTRICTED if black‑market node.
- **Fail:** counterparty defaults → auto `RaiseDispute` option.

### 5.5 `Buy` / `Sell`
- Thin wrappers around `Trade` for market kiosks.

---

## 6) Maintenance & Infrastructure

### 6.1 `RepairSuit(parts)`
- **Pre:** parts/tools; workshop access (or field kit with penalty).
- **Cost:** materials; time; credits to technician if outsourced.
- **Effect:** increase `suit.I`, `suit.Seal`, `suit.Comf`.
- **Events:** `ProductionReported` for the guild; optional `RumorEmitted` if flashy result.
- **Fail:** wrong parts → `FAIL`; field repair lower cap.

### 6.2 `MaintainFacility(subsystem)`
- **Pre:** authorization or contract; parts on hand.
- **Cost:** time; materials.
- **Effect:** `infra.M += ΔM`; clear fault flags; reduce env stress.
- **Events:** `MaintenanceCompleted` (WARD scope).
- **Fail:** misdiagnosis → small `ΔM` only.

### 6.3 `InstallComponent(facility, component)`
- **Pre:** component available; downtime window.
- **Cost:** consumes component; time; coordination lock.
- **Effect:** upgrade facility efficiency; adjust leakage / energy draw.
- **Events:** `ProductionReported` (installations ledger).
- **Fail:** install error → revert; materials at risk (RNG).

---

## 7) Security & Combat

### 7.1 `Escort(route, cargo)`
- **Pre:** route intelligence exists; guards assigned; contract optional.
- **Cost:** travel time; wages; fatigue; ammunition reserve (if combat occurs).
- **Effect:** move assets between reservoirs; increase safety for traders on route.
- **Events:** `MilitiaDeployed` (start), `BarrelDelivered` on success, `EscortAmbushed` on attack.
- **Fail:** ambush → branch to combat resolution; losses emit `AssetSeized` by attackers.

### 7.2 `Guard(place)` / `Patrol(area)`
- **Pre:** jurisdiction; pay in place.
- **Cost:** time; stamina; ammo if skirmish.
- **Effect:** reduce security risk metric in area; deter small thefts.
- **Events:** `MilitiaDeployed`.
- **Fail:** overwhelming attack → emit `EscortAmbushed`/combat chain.

### 7.3 `SeizeAsset(target, asset, amount)`
- **Pre:** authority (warrant/edict) **or** black‑market order; numerical advantage.
- **Cost:** time; enforcement risk to reputation if arbitrary.
- **Effect:** atomic transfer; morale impact on target ward.
- **Events:** `AssetSeized` (PUBLIC), possible `ContractDisputed`.
- **Fail:** resistance → combat; legitimacy loss if unjustified.

### 7.4 `Ambush(convoy)`
- **Pre:** route and timing known; concealment point.
- **Cost:** setup time; ammo; risk of casualties.
- **Effect:** on success, water/material capture; reputational fear increase; casualties → reclaimer flow.
- **Events:** `EscortAmbushed`, then `AssetSeized`; rumor high‑salience.
- **Fail:** convoy stronger than expected → losses; bounty may be posted.

### 7.5 `Flee(direction)`
- **Pre:** engagement active.
- **Cost:** stamina spike; route risk.
- **Effect:** break contact; potential asset drop.
- **Events:** none (implicit in combat logs).
- **Fail:** pinned → damage taken.

---

## 8) Black‑Market & Covert

### 8.1 `Smuggle(goods, route)`
- **Pre:** clandestine route; bribe budget positive.
- **Cost:** time; bribes (credits); risk of seizure.
- **Effect:** move goods without PUBLIC events; RESTRICTED logs only.
- **Events:** if detected, `AssetSeized` PUBLIC; otherwise `TokenEscrowSettled` on completion.
- **Fail:** detection → seizure + bounty.

### 8.2 `FenceGoods(items)`
- **Pre:** illicit items in stock; fence contact.
- **Cost:** fee; reputation with law‑abiding factions down.
- **Effect:** convert to credits/tokens at discount.
- **Events:** RESTRICTED trade logs; rumor if sting operation.

### 8.3 `TokenContractCreate(terms)`
- **Pre:** black‑market node; escrow proxy.
- **Cost:** token mint fee.
- **Effect:** creates tokenized contract (anonymized issuer).
- **Events:** none (RESTRICTED registration).

### 8.4 `TokenEscrowSettle(token_id)`
- **Pre:** proof of completion submitted.
- **Cost:** escrow fee.
- **Effect:** transfer via proxy; clears obligation.
- **Events:** `TokenEscrowSettled` (RESTRICTED).

### 8.5 `Hide(duration_min)`
- **Pre:** cover location; no active tail.
- **Cost:** time; small morale drain.
- **Effect:** reduce detection chance; decay recent PUBLIC visibility.
- **Events:** none.
- **Fail:** discovered → guards notified.

---

## 9) Reclamation & Health

### 9.1 `ReclaimBiomass(source)`
- **Pre:** facility access; transport present.
- **Cost:** time; energy.
- **Effect:** produce water/biomass outputs; tax hooks to king/lord.
- **Events:** `ProductionReported` + ledger to taxes.
- **Fail:** contaminated source → lower yield.

### 9.2 `SeekClinic()`
- **Pre:** clinic access; fees.
- **Cost:** credits; time.
- **Effect:** heal `H`, treat `chronic` flags; narcotic withdrawal handling.
- **Events:** none PUBLIC by default; may create rumor if celebrity patient.

### 9.3 `TreatInjury(target)`
- **Pre:** medkit; skill threshold.
- **Cost:** consumables; time.
- **Effect:** stabilize target; reduce bleed; set clinic referral.
- **Events:** none.

---

## 10) Observation & Rumor Hooks

- Any PUBLIC action within visibility becomes a **witness stub**; minute rollup calculates `(cred, sal)` and emits `RumorEmitted` if above thresholds.  
- Black‑market actions are RESTRICTED; only leak via detection or informants (separate actions).  
- `Observe`, `Scout`, and `Commune` can *intentionally* emit rumors by setting `params.intent="broadcast"`.

---

## 11) Failure, Retry, Interrupts

- **FAIL**: preconditions false, or facility down → no effects; partial costs refunded where sensible.  
- **INTERRUPTED**: combat/fault occurs mid‑action → partial progress; may resume with `resume=true`.  
- **CANCELLED**: actor/user aborts; costs sunk; no effects.  
- Automatic **retry** allowed for `Maintenance` and `Labor` if outage resolves within retry window.

---

## 12) Minimal Effects Table (Common Fields)

| Effect | Field | Type | Notes |
|---|---|---|---|
| Stock delta | `stocks.water_L/materials/credits` | ±float | Atomic ledger |
| Physiology | `ΔW, ΔN, ΔSta, ΔME, ΔH` | float | Per Scoring v1 |
| Suit | `ΔI, ΔSeal, ΔComf` | float | Repairs/wear |
| Reputation | `rep.R[audience] += δ` | float | Audience‑weighted |
| Reliability | `econ.R` | ewma | Contract outcomes |
| Legitimacy | `gov.L` | float | Via rulings & crises |
| Risk | `ρ_env, ρ_sec` | float | Area modifiers |

---

## 13) Example Action JSON

```json
{
  "action_id": "act_0001",
  "actor": "agent_A17",
  "verb": "Escort",
  "start_tick": 28800,
  "eta_ticks": 3600,
  "target": { "route":"ward05->ward11", "asset":"barrel_93" },
  "params": { "guards": 6, "contract_id":"c_201", "insurance":"token:tkn_77" },
  "status": "RUNNING"
}
```

---

### End of Agent Action API v1

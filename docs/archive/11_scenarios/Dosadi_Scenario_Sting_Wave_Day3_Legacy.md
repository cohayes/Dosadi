---
title: Dosadi_Scenario_Sting_Wave_Day3
doc_id: D-SCEN-0002
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-13
parent: 
---
# **Scenario Playbook: Sting Wave — Day‑3 v1**

**Version:** v1 — 2025‑11‑13  
**Purpose.** Orchestrate a multi‑system “sting wave” that exercises Black‑Market listings, dark escrow, smuggler routing, checkpoints, crackdowns, FX/rumor ripples, audits, and reserve checks—producing rich telemetry for dashboards and downstream policy tuning.

Integrates with **Black‑Market Networks v1**, **Logistics Corridors & Safehouses v1**, **Telemetry & Audit v1**, **Identity/Licensing & Permits v1**, **Escort & Security v1**, **Law & Contract Systems v1**, **Credits & FX v1.1**, **Financial Ledgers & Taxation v1**, **Clinics & Health v1.1**, **Rumor v1.1**, **Production & Fabrication v1**, and the **Tick Loop** (0.6 s/tick).

> Run length: **1 sim day** (144,000 ticks). Key events clustered in hours 02–08 and 14–20.

---
## 0) Initial Conditions (Day‑3 Boot)

- **FX & Liquidity**
  - WaterBasis mid set from prior day close; issuer spreads: `king 0.5%`, `dukeA 1.2%`, `ward12 2.1%`.
  - Reserve ratios: `king 0.62`, `dukeA 0.31`, `ward12 0.26` (near floor).
- **Corridors**
  - Lane `L‑M12‑OUTER‑03`: rumor_heat `0.35`, patrol_level `0.3`, checkpoint `False`.
  - Lane `L‑M07‑MIDDLE‑11`: rumor_heat `0.12`, patrol_level `0.6`, checkpoint `True`.
  - Two **Safehouse_DARK** along OUTER chain: `SH‑D‑Stonecut`, `SH‑D‑RedVane` (Class D).
- **Nodes (Black‑Market)**
  - `N‑BackAlley‑W12` (hush `0.7`, audit_heat `0.15`), `N‑RepairDen‑W07` (hush `0.5`, audit_heat `0.22`).
- **Actors**
  - **Broker** `B‑Whisper`: rep `{reliability:0.72, discretion:0.81}`; cut `5%`.
  - **Crew** `Op‑GreyJackal`: stealth `0.68`, escort `mid`, cold_chain `no`.
  - **Fence** `F‑CopperLoom`: haircut `16%`; convert to `dukeA` credits.
  - **Arbiter Panel** `AP‑North`: sting budget `3` decoys; crackdown wave size `2`.
- **Permits/ROE**
  - INNER lanes: telemetry required; heavy weapons ban enforced.
  - OUTER lanes: spot checks only; smuggler lanes uninspected but high ambush variance.
- **Policy Tuning (overrides)**
  - `black_market.sting_injection_rate = 0.08` (for this scenario window).
  - `logistics.escort_mismatch_penalty = 0.18` (heightened risk perception).
  - `telemetry_audit.min_evidence_for_decree.WITNESS = 2` (harder to convict on hearsay).

---
## 1) Scenario Phases & Timeline

**Phase A — Anonymous Listing** *(Hour 02)*  
- Post `SELL: forged_permits (carry: HEAVY_WEAPON), qty 12`, reserve `= 40 L` each, tokenized via **Black‑Board Escrow**.
- Events: `ListingPosted`, mirrored to two nodes.

**Phase B — Broker Match & Routing** *(Hour 03)*  
- `B‑Whisper` matches buyer, plans **SMUGGLER/OUTER** route using `L‑M12‑OUTER‑03`.  
- Books **Safehouse_DARK** slots at `SH‑D‑Stonecut` & `SH‑D‑RedVane`.
- Events: `DarkRoutePlanned`, `StagingBooked`.

**Phase C — Escrow & Handoff #1** *(Hour 04)*  
- Buyer funds escrow (dukeA credits) → `escrow_id`.  
- Handoff ritual at `N‑BackAlley‑W12`: pass‑phrase, seal‑tree fragment check.  
- Events: `OrderPlaced`, `HandoffCompleted` (privacy: faction‑sealed custody).

**Phase D — Sting Injection** *(Hour 05)*  
- `AP‑North.inject_sting()` posts decoy `BUY: meds_high` & `SELL: forged_permits` near `N‑RepairDen‑W07`.  
- Telemetry trap tokens embedded; patrols staged on `L‑M07‑MIDDLE‑11`.
- Events: `StingInjected` ×2.

**Phase E — Movement & Encounter** *(Hours 05–06)*  
- `dispatch_convoy(Op‑GreyJackal)` with forged permits (cargo value high).  
- On `L‑M12‑OUTER‑03`: roll `AmbushAttempted` (value‑elastic risk).  
- **Branch**: If ambush success → partial loss, injuries → `Clinics` surge; else proceed.

**Phase F — Meetup with Decoy** *(Hour 06)*  
- Crew attempts second sale to decoy buyer; inspection probability high on MIDDLE lane checkpoint.  
- Trap springs: `InspectionOccurred` → `CrackdownExecuted` at `N‑RepairDen‑W07` (closures 8–36 h).  
- Seizures: forged permits, partial liters, weapons.

**Phase G — Audit & Decrees** *(Hour 07–08)*  
- `AuditOpened` for `Op‑GreyJackal` & `B‑Whisper`; `verify_bundle()` against sting tokens.  
- Decrees: revoke carry licenses for caught agents; fines; blacklist on black boards.  
- Events: `ArbiterDecree`, `Revoked`, `FineIssued`.

**Phase H — FX & Reserves Feedback** *(Hour 14)*  
- Surge in `dukeA` credit redemptions by seized‑party creditors → temporary **reserve dip** to `0.27`.  
- `ReserveBreach` check for **ward12** issuer after rumor spike on closures and seizures.  
- Spreads widen `dukeA +40 bps`, `ward12 +90 bps`.  
- Events: `ReserveBreach?`, `FXMarked`.

**Phase I — Rumor & Migration** *(Hours 16–20)*  
- `RumorHeatUpdated`: OUTER lane heat +0.2; targeted node volume migrates to adjacent ward.  
- Listings shift from forged permits → **data_wipes** and **intel** (lower physical risk).  
- Node `N‑RepairDen‑W07` reopens later per closure timer; rep score down.

---
## 2) KPIs & Success Criteria

- `BustRate ↑` in targeted classes without catastrophic spillover to clinics.  
- `Reserve Ratio` stays ≥ min for king & major issuers; local issuers may wobble but avoid persistent breach.  
- `AvgRiskPremium` rises for forged permits during crackdown window, normalizes within 48 h.  
- Rumor heat peaks then decays at policy slope; lane volume migrates but total corridor throughput ≥ 80% baseline.

---
## 3) Instruments & Anchoring

- **Custody**: faction‑sealed during dark handoffs; unsealed under decree.  
- **Boards**: anchors for `StingInjected`, `CrackdownExecuted`, `ArbiterDecree`, `TaxSettled`, `FXMarked`, `ReserveBreach`.  
- **Ledgers**: seizures posted as `Fines_Penalties` and inventory adjustments in liters.

---
## 4) Orchestration API (for Codex)

```python
def run_sting_wave_day3(seed=1337):
    set_policy_overrides({...})
    seed_rng(seed)
    boot_day3_state()

    # Phase A
    list_id = post_listing(node_id="N-BackAlley-W12",
                           listing=SELL("forged_permits", qty=12, reserve_L=40, escrow=True))
    # Phase B
    route = route_dark(list_id)              # smuggler/outer + Safehouse_DARK
    # Phase C
    escrow_id = place_order(list_id, offer_L=480, escrow=True)
    perform_handoff(order_id=escrow_id, node_id="N-BackAlley-W12")

    # Phase D
    for proto in [{"commodity":"meds_high","type":"BUY"},
                  {"commodity":"forged_permits","type":"SELL"}]:
        inject_sting(node_id="N-RepairDen-W07", listing_proto=proto)

    # Phase E
    convoy_id = dispatch_convoy(op_id="Op-GreyJackal", route=route)
    while moving(convoy_id):
        tick_movement(convoy_id)

    # Phase F
    outcome = perform_handoff(order_id=escrow_id, node_id="N-RepairDen-W07")  # decoy target
    if outcome != "ok":
        # bail/ambush branch handling
        pass

    # Phase G
    case = open_audit(entity_id="Op-GreyJackal", scope="forged_permits_wave")
    decree = arbitrate(case)

    # Phase H
    mark_to_waterbasis(issuer="dukeA")
    reserve_check(issuer="ward12")

    # Phase I
    update_rumor_heat(lane_id="L-M12-OUTER-03", event="CrackdownExecuted")
    migrate_listings_from("N-RepairDen-W07")
```

---
## 5) Dashboards to Watch

- **Dark Board**: forged‑permit prices, fill rates, escrow outstanding, node closures.  
- **Corridor Map**: lane heat, incident pins, patrol coverage.  
- **FX & Reserves**: issuer spreads, reserve ratios, redemptions queue.  
- **Arbiter Panel**: open audits, decrees, penalties.  
- **Clinics**: episodes tagged to ambush/inspection incidents.  
- **Compliance**: seizures, fines, settlement timeliness.

---
## 6) Parameter Sweeps (optional)

- `sting_injection_rate ∈ {0.0, 0.03, 0.08, 0.15}`  
- `escort_mismatch_penalty ∈ {0.06, 0.12, 0.18}`  
- `node_closure_duration_hours ∈ [4..72]`  
- `forged_detection_multiplier_inner ∈ {1.0, 2.0, 3.0}`  
- Record effects on `BustRate`, `AvgRiskPremium`, `CorridorThroughput`, `ReserveBreach` probability.

---
## 7) Test Checklist (Day‑0+)

- Decoy listings trigger inspections and at least one crackdown; custody & tokens verify cleanly.  
- Escrow releases or is confiscated per decree; ledgers reflect fines and seizures in liters.  
- Lane rumor heat spikes and decays; listings migrate; prices reflect risk premiums.  
- FX spreads widen for affected issuers and relax after closures lift; reserve floor never breached persistently.  
- Clinics see plausible incident‑linked load; no runaway epidemics from this scenario alone.

---
### End of Scenario Playbook: Sting Wave — Day‑3 v1

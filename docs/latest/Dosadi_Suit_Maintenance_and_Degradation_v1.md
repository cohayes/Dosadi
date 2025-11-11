# **Suit Maintenance & Degradation v1**

**Purpose:** Operationalize how environmental exposure, usage, and damage degrade suits over time — and how inspection, servicing, and parts logistics restore performance. Anchors to **Suit–Body–Environment v1**, **Maintenance Fault Loop v1**, **Labor v1**, **Market v1**, **Credits & FX v1**, **Rumor & Perception v1**.

> Cadence: wear accumulation **per Minute**; diagnostics/alerts **on threshold**; service tasks batched **per Hour**; KPIs aggregated **per Day**.

---

## 0) Suit Parts Taxonomy (replaceables & subsystems)

- **Sealing System**: face gasket, limb cuffs, zipper tracks, valve O‑rings, patch membranes.  

- **Filtration & Air Handling**: particulate filters, biofilters, blower, check valves, CO₂ scrub cartridge.  

- **Thermal Loop**: heat spreader fabric, coolant microtubes, pump, thermal electric (TEC) plates, radiator fins.  

- **Power & Control**: battery pack, DC bus, fuses, control board, temp/humidity/pressure sensors.  

- **Reservoir & Hygiene**: moisture trap, urine diverter cartridge, fecal capture liner, biocide sachets.  

- **Armor Layers**: blunt pad, slash weave, pierce plates; trauma gel packets.  

- **Softgoods & Fit**: inner liner, harness straps, boot cuffs, glove rings.

Each part has: `SKU`, `tier` (LOW/MID/HIGH/ELITE), `MTBF_hours`, `WearCoeffs`, `ServiceType`, `Skills`, `SwapTime_min`, `Weight_kg`, `Cost{credits, water_L}`.

---

## 1) Wear & Degradation Model

Per minute, each subsystem accrues fractional wear from **environment**, **workload**, and **age**:

```
Δwear_part = base_rate
           + k_dust * Dust
           + k_heat * max(0, T_skin - 34)
           + k_cold * max(0, 28 - T_skin)
           + k_motion * ActivityIndex
           + k_bio * BiofilmIndex
           + k_leak * (1 - Seal)                # feedback loop
```

- **Stochastic spikes**: impacts/abrasion add discrete damage to `Integrity`; punctures cause **Seal** drop.  

- **Filter Load** grows with `Dust` & `RespFlow`; increases blower power draw and reduces moisture recovery.

**Performance decay curves** (piecewise):

- `FilterEff(wear)` ~ gently sloped until 0.6, then steep drop; `SuitFilterWarning` at 0.7, `Critical` at 0.9.

- `SealTightness(wear)` ~ linear; excursions >0.2 leak increase trigger `SuitSealWarning`.

- `CoolingCapacity(wear)` ~ flat until pump/TEC thresholds; failure when either crosses `MTBF_shock`.

---

## 2) Diagnostics & Alert Thresholds

- **Soft Alerts** (advisory): filter ΔP rising; seal creep; battery cycle count high; sensor drift.  

- **Hard Alerts** (actionable): `SuitBreach`, pump stall, TEC overtemp, CO₂ scrub near spent, reservoir biofilm high, fecal liner full.  

- **Critical** (immediate): explosive decompression, battery thermal runaway, sensor suite offline.

Events: `SuitFilterWarning`, `SuitSealWarning`, `SuitPumpAnomaly`, `SuitCO2NearSpent`, `SuitBiofilmHigh`, `SuitBreach`, `SuitCritical`.

---

## 3) Maintenance Tasks (standard operating procedures)

**Inspection (Quick)** — visual + sensor check, wipe dust, read diagnostics. `5–10 min`, `no parts`.  

**Filter Service** — swap particulate/biofilter, blower intake wipe. `10–20 min`, parts: filters.  

**Seal Service** — replace cuffs/O‑rings, lube zips, patch microtears. `20–40 min`, parts: seals/patches.  

**Thermal Loop Flush** — purge coolant, check pump/TEC, re‑prime. `30–60 min`, parts: coolant, seals.  

**Sensor Calibrate** — temp/RH/pressure; update offsets. `15–30 min`, parts: none.  

**Reservoir Hygiene** — drain, scrub, biocide re‑dose; replace liners. `20–40 min`, parts: biocide, liners.  

**Armor Refit** — swap plates/pads; gel packet recharge. `20–45 min`.  

**Battery Swap** — replace pack; run self‑test. `10–15 min`.

Each task mapped to: `Skills`, `FacilityGrade` (LOW/MID/HIGH), `WaterUse_L` (cleaning), `WasteStreams` (filters, greywater).

---

## 4) Service Scheduling (policies)

**Strategies:**

- **Run‑to‑Alert** (outer wards): act on hard warnings only; cheapest, risky.  

- **Interval‑Based** (middle): fixed hours/ticks; predictable queues.  

- **Condition‑Based** (inner/elite): trigger on trend (ΔP, ΔT, vibration, drift).  

- **Mission‑Prep**: forced inspection before high‑risk jobs (escort/raid/long haul).

**Planner objective:** minimize expected failure cost = parts + labor + downtime + risk externalities (heat stress, leaks, bad PR).

---

## 5) KPIs & Ledgers

- `Uptime%`, `MeanTimeBetweenAlerts`, `MeanTimeToService`, `LeakRate_avg`, `FilterHours`, `BiofilmIndex`, `CoolingMargin`, `BatterySOH`.  

- `ServiceCost{credits, water_L}`, `WasteRecovered_L` (from hygiene), `FailureIncidents` (#), `ReputationImpact` (for service guilds).  

- Daily **maintenance ledger** lines with evidence `LEDGER`, `SENSOR`, `VIDEO` for audits & rumors.

---

## 6) Parts Supply & Economics

- **Catalog tiers** align with caste: LOW (cheap, short MTBF), MID, HIGH, ELITE (long MTBF, better coefficients).  

- **Counterfeit risk** (black market): cheaper but higher variance MTBF and hidden failure modes.  

- **Water cost** for cleaning & test benches; facilities with high water recovery (sealed interiors) have cost edge.  

- **Credits & FX**: issuer discount/strength shifts parts pricing; elite parts often priced in king‑credits.  

- **Scrap & Reclaim**: used filters/liners → reclaim mass + water; biohazard handling governs net recovery.

---

## 7) Black‑Market Mods

- **Thermal Overclock**: boost `ActiveCooling` by +25–50% at cost of battery & pump wear; higher failure risk.  

- **Stealth Baffle Kit**: reduce IR signature (−Radiant coupling) but lower heat rejection capacity.  

- **Armor Swap**: heavier plates (pierce↑) increase metabolic cost and fatigue.  

- **Respirator Bypass**: lower breathing work at cost of moisture recovery; extreme dehydration risk if abused.  

- **Sensor Forgers**: lie to diagnostics (conceal wear); heavy sanctions if discovered.

Rumor hooks: visible modded suits spark **fear/respect** memes; failures become cautionary tales.

---

## 8) Integration with Maintenance Fault Loop v1

- Threshold crossings emit `FaultDetected` with `component`, `severity`, `symptoms`.  

- `MaintenanceTaskQueued` includes `parts`, `skills`, `ETA`, `FacilityGrade`.  

- Completion updates suit state, resets wear counters, logs `MaintenanceCompleted` with evidence links.  

- Missed maintenance → raises `RiskIndices` in Security & Clinics; propagates to **Legitimacy** if widespread.

---

## 9) Policy Knobs

```yaml
suit_maint:
  wear_base_per_min: 0.0001
  k_dust: 0.0004
  k_heat: 0.0003
  k_cold: 0.0003
  k_motion: 0.0002
  k_bio: 0.0005
  k_leak: 0.0006
  filter_warn: 0.70
  filter_crit: 0.90
  seal_warn_leak: 0.20
  pump_alert_vibe: 0.75
  biofilm_warn: 0.65
  hygiene_water_L: { quick: 0.3, full: 1.5 }
  counterfeit_mtbf_mult: 0.6
  overclock_fail_mult: 1.8
```

---

## 10) Event & Function Surface (for Codex)

**Functions**

- `minute_suit_wear(agent_id, env, workload)` → updates part wear, filter load, biofilm; returns alerts.  

- `run_diagnostics(agent_id)` → collates sensor drift, ΔP, temps; returns health summary.  

- `queue_suit_service(agent_id, task_spec)` → `MaintenanceTaskQueued` (maps to facility & parts).  

- `complete_suit_service(agent_id, task_id, used_parts)` → `MaintenanceCompleted`; resets wear.  

- `apply_mod(agent_id, mod_spec)` → adjust coefficients, add hidden risks if black‑market.  

- `audit_suit(agent_id)` → evidence bundle for law/rumor; detects forged sensors.

**Events**

- `SuitFilterWarning`, `SuitSealWarning`, `SuitPumpAnomaly`, `SuitBiofilmHigh`, `SuitCO2NearSpent`, `SuitBreach`, `MaintenanceTaskQueued`, `MaintenanceCompleted`.

---

## 11) Pseudocode (Minute Wear Loop)

```python
def minute_suit_wear(suit, env, workload):
    A = activity_index(workload, suit.fit)
    for part in suit.parts:
        d = wear_base + k_dust*env.dust + k_heat*max(0, suit.T_skin-34)                     + k_cold*max(0, 28-suit.T_skin) + k_motion*A                     + k_bio*suit.biofilm + k_leak*(1-suit.seal)
        part.wear = clamp(part.wear + d)
        if part.kind == "filter":
            suit.filter_load = clamp(suit.filter_load + d*alpha_filter)
            if suit.filter_load > filter_warn: emit("SuitFilterWarning", {...})
        if part.kind == "seal" and (1 - suit.seal) > seal_warn_leak:
            emit("SuitSealWarning", {...})
    # stochastic impacts
    if random_event("impact"): suit.integrity -= Δ; suit.seal -= Δ_seal; emit("SuitBreach", {...})
    return summary(suit)
```

---

## 12) Explainability & Dashboards

- **Maintenance dashboard**: per‑suit health, alerts, recommended tasks, parts ETA, downtime forecast.  

- **Water ledger hook**: service hygiene shows water used/recovered; supports audits and Credits & FX cost tracing.  

- **Counterfactuals**: “If filter serviced 6 hrs earlier, blower power −12%, heat strain events −1.”

---

## 13) Test Checklist (Day‑0+)

- Dusty OUTSIDE run raises filter load to warning in ≤ 3 hours (policy‑tunable).  

- Seal creep under heavy motion emits warning before reaching large hydration losses.  

- Thermal overclock raises failure probability and reduces battery life measurably.  

- Completing `Filter Service` resets load and narrows heat/resp strain in **Suit–Body–Environment** metrics within 30–60 min.

---

### End of Suit Maintenance & Degradation v1

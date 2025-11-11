# **Suit–Body–Environment v1 (Thermal & Fluid Core)**

**Purpose:** Couple ambient conditions, suit performance, and human physiology into a single loop that governs survival, fatigue, and water accounting. This is *the* substrate behind all agent actions.

Integrates with **Agents v1 (Body/Suit/Drives)**, **Environment Dynamics v1**, **Maintenance Fault Loop v1**, **Clinics v1**, **Rations v1**, **Credits & FX v1** (via water costs), **Labor v1** (fatigue gates), **Rumor & Perception v1** (visible distress & failures), and the **Tick Loop**.

> Timebase: `Tick = 0.6 s`, `Minute = 100 ticks`.  
> Simulation cadence: thermal & fluid microlayer runs **each Minute**; aggregation to status effects runs **per 5 Minutes**.

---

## 0) State Variables (per Agent)

**Body (physiology)**

- `T_core` (°C) — target 37.0; safe band 36.1–37.8; danger bands below/above.  

- `T_skin` (°C) — interface to suit/air; drives comfort/perceived exposure.  

- `Hydration_L` — free water pool; depletes via resp/persp/excreta; gains via intake/reclaim.  

- `Glycogen_kJ`, `Fat_kJ` — metabolic fuel stores (coarse); energy availability gates work.  

- `Stamina` (0–1) — short‑term physical capacity; recovers with rest/sugar; drains with work/heat.  

- `MentalEnergy` (0–1) — cognitive capacity; drains with decision load/sleep debt.  

- `Bladder_L`, `Bowel_kg` — excreta buffers (comfort & urgency signals).  

- `InjuryFlags` — bleeding, burns, infection (modulate heat/fluid loss and clinic needs).  

- `Acclimatization` (0–1 HOT, 0–1 COLD) — shifts sweat onset/shiver thresholds.

**Suit (equipment)**

- `Seal` (0–1) — vapor tightness; leaks rise with motion & damage.  

- `Integrity` (0–1) — structural health; governs armor & thermal pathways.  

- `Insulation` (clo) — thermal resistance baseline (model grade + layering).  

- `ActiveCooling_W` — Peltier/liquid loops; draws power; caps heat rejection.  

- `ActiveHeating_W` — resistive panels; draws power; caps warmth.  

- `MoistureRecovery` — efficiency by stream: `resp`, `persp`, `urine`, `feces` (e.g., 0.999 / 0.98 / 0.995 / 0.98 high‑tier).  

- `Reservoir_L` — onboard reclaimed water buffer (feeds drink line/cooking).  

- `FilterLoad` (0–1) — dust/bioload; raises breathing work, lowers recovery.  

- `Fit` (−2 … +2) — mismatch of suit size/ergonomics; affects fatigue & injury risk.  

- `Armor` (blunt/slash/pierce) — maps to injury probability if attacked.

**Environment (cell/venue)**

- `T_air` (°C), `RH` (%), `Radiant` (W/m²), `Wind` (m/s), `Dust` (mg/m³), `O2` (%), `CO2` (ppm).  

- `ExposureClass` — OUTSIDE | LEAKY_INTERIOR | SEALED_INTERIOR.  

- `Workload` — metabolic class: REST, LIGHT, MODERATE, HEAVY, EXTREME (from Labor v1).  

- `Hazards` — chemical/radiation/electrical; map to suit defense vs risk of injury.

---

## 1) Thermal Model (conceptual, stable & cheap)

### 1.1 Heat Balance

Net core heat per minute:

```
Q_gen   = M(WL, acclim)             # metabolic heat from workload
Q_xfer  = k_body * (T_core - T_skin) # core→skin conduction
Q_suit  = f_insul(Insulation, Wind) * (T_skin - T_suit_air)
Q_active= clamp(ActiveCooling_W - ActiveHeating_W, -H_cap, +C_cap)
ΔT_core = (Q_gen - Q_xfer - sweat_cooling) / C_body
ΔT_skin = (Q_xfer - Q_suit + env_radiant) / C_skin
```

- `M(WL)` typical (kJ/min): REST 4, LIGHT 6, MOD 10, HEAVY 16, EXTREME 24 (policy‑tunable).  

- `sweat_cooling = evap_rate * L_vap * efficiency` (evap_rate gates by `RH`, airflow, suit recovery).  

- `env_radiant` from `Radiant` and albedo; mitigated by suit coatings.

### 1.2 Thresholds → Status

- **Heat strain index** combines `T_core`, sweat rate, stamina drain.  

- **Cold strain index** combines `T_core`, shiver onset, dexterity loss.  

- Convert to effects (per 5‑min aggregation):

  - `Stamina` drain multiplier, `ErrorRate` (dex/cog), `InjuryRisk` bump, clinic flags if severe.

---

## 2) Fluid Model (water accounting)

Per minute flows (liters):

```
resp_L  = f_breath(T_air, RH, workload)         # humidification loss
persp_L = f_sweat(T_core, WL, acclim, RH)       # thermoreg sweat
urine_L = f_homeostasis(Hydration, intake)      # wastes + balance
feces_L = f_digest(meal_quality) * water_frac
```

Suit recoveries:

```
resp_rec  = resp_L  * MoistureRecovery.resp
persp_rec = persp_L * MoistureRecovery.persp * (Seal)
urine_rec = urine_L * MoistureRecovery.urine
feces_rec = feces_L * MoistureRecovery.feces
Hydration_L += (intake + resp_rec + persp_rec + urine_rec + feces_rec - (resp_L + persp_L + urine_L + feces_L))
Reservoir_L += (resp_rec + persp_rec + urine_rec + feces_rec) - (dispensed_to_drink_or_cook)
```

**Quality gates:** Low `FilterLoad` and good hygiene → usable reclaimed water; dirty states route to `greywater` (needs facility reclamation).

---

## 3) Comfort, Exposure, and Perceived Danger

- `Comfort` ∝ −|T_skin − 32°C| − chafing(Fit) − biofilm(FilterLoad).  

- `Exposure` ∝ leakiness(Seal, Integrity) × (OUTSIDE penalty vs SEALED_INTERIOR).  

- `PerceivedDanger` from `Armor` vs observed threats; raises **Fear** sensation, drains `MentalEnergy`.

Effects:

- Low `Comfort` increases **fatigue** rate and narcotic temptation.  

- High `Exposure` amplifies **hydration** drain (microleaks) and stress.  

- High `PerceivedDanger` boosts vigilance but harms fine tasks; feeds Rumor if others observe panic.

---

## 4) Fit & Motion Penalties

- `Fit` mismatch adds metabolic cost: `M' = M * (1 + 0.05 * |Fit|)` and raises **chafe injury** chance.  

- Sprinting/struggles spike `Q_gen` and perspiration; poor sealing under motion → microleak multiplier.

---

## 5) Failure Modes & Maintenance Hooks

**Soft fails (degrade):**

- Filter saturation → ↑ breathing work, ↓ resp recovery; emits `SuitFilterWarning`.

- Seal creep (gasket fatigue) → ↑ leak factor; emits `SuitSealWarning`.

**Hard fails:**

- Puncture/tear → instant `Seal` drop; `Integrity` −Δ; emits `SuitBreach` with location & leak rate.  

- Pump/TEC failure → lose `ActiveCooling/Heating`; triggers thermal runaway risk.

**Maintenance:**

- Tasks: replace filters/gaskets, patch fabric, flush biofilm, recalibrate sensors.  

- KPIs: `MTBF`, `LeakRate`, `FilterHours`, `BiofilmIndex`.  

- Tie to **Maintenance Fault Loop v1** (`MaintenanceTaskQueued/Completed`).

---

## 6) Intake & Rations Links

- **Intake targets** per Environment & Workload: baseline 2.5–3.7 L/day (rest), up to 6–10+ L/day in hot heavy work.  

- `Rations v1` provides: `HydrationGain`, `ElectrolyteBalance`, `MealThermicEffect` (small heat).  

- Dehydration staging (approx):  

  - −2% body water → thirst, stamina −10%.  

  - −4% → heat tolerance collapse, cognition −15%, clinic flag.  

  - −6–8% → collapse risk; mandatory **evac** event.

---

## 7) Narcotics & Modulators

- `Analgesic` raises pain threshold → risk of overexertion (hidden strain).  

- `Sedative` lowers `Q_gen` but slows reaction; increases cold risk.  

- `Stimulant` raises `Q_gen` and sweat; masks fatigue temporarily; bigger crash later.  

- All adjust **sensations** (Pain/Thirst/Fatigue) but not raw physics; deception requires explicit rules later.

---

## 8) Status Effects (5‑Minute Aggregation)

- **Heat Stress**: tiers I–IV → stamina drain, error rate, clinic referral thresholds.  

- **Cold Stress**: dexterity loss, shiver energy cost, frost injury risk.  

- **Dehydration**: −Stamina cap, −MentalEnergy, dizzy events, clinic flags.  

- **Comfort Debt**: persistent low comfort → morale hit, drive shifts (Apathy ↑, Maintenance/Hoard ↑).

Events: `ThermalStrainUpdated`, `HydrationStatusUpdated`, `ComfortDebtUpdated`.

---

## 9) Environment Cells & Venues

- OUTSIDE: high `Dust`, low `RH`, high thermal swing; wind gusts; visibility penalties.  

- LEAKY_INTERIOR: modest `RH`, partial shielding; variable ventilation.  

- SEALED_INTERIOR: controlled `T_air/RH/O2`; best for recovery & cooking; high social density.

Transitions between cells trigger transient spikes (door cycling, suit equalization).

---

## 10) Policy Knobs (defaults)

```yaml
thermal_fluid:
  metabolic_kJ_per_min: { REST: 4, LIGHT: 6, MODERATE: 10, HEAVY: 16, EXTREME: 24 }
  sweat_evap_efficiency: 0.7
  sweat_onset_core: 37.0       # °C (shift by HOT acclim)
  shiver_onset_core: 36.5      # °C (shift by COLD acclim)
  suit_microleak_motion_mult: 1.25
  filter_load_penalty_per_min: 0.001
  reservoir_min_drink_L: 0.2
  comfort_chafe_coeff: 0.08
  danger_armor_map: { blunt: 0.7, slash: 0.6, pierce: 0.5 }
  dehydration_stages: [0.02, 0.04, 0.06]
```

---

## 11) Event & Function Surface (for Codex)

**Functions**

- `minute_thermal_fluid(agent_id, env_cell)` → updates temps & flows; returns deltas.  

- `aggregate_status(agent_id)` → computes status effects and clinic flags.  

- `apply_suit_damage(agent_id, kind, severity)` → Seal/Integrity drop; may emit `SuitBreach`.  

- `perform_maintenance(agent_id, task)` → resets filter/seal/biofilm; consumes parts/time.  

- `drink(agent_id, source)` / `dispense_from_reservoir(agent_id, L)` → water accounting.

**Events**

- `SuitFilterWarning`, `SuitSealWarning`, `SuitBreach`, `ThermalStrainUpdated`, `HydrationStatusUpdated`, `ComfortDebtUpdated`.

---

## 12) Pseudocode (Minute Loop)

```python
def minute_thermal_fluid(agent, env):
    M = metabolic(env.workload, agent.suit.fit)
    resp_L, persp_L = resp_persp(env, agent, M)
    rec = recover_streams(agent.suit, resp_L, persp_L, agent.bladder, agent.bowel)
    Q = heat_balance(agent, env, M, rec["evap_cooling"])
    update_core_skin(agent, Q)
    apply_microleaks(agent.suit, env)
    update_hydration(agent, intake=agent.intake_min, losses=(resp_L+persp_L)+excreta_L, rec=rec["total"])
    accumulate_comfort_exposure(agent, env)
    emit_events_if_thresholds(agent)
    return deltas(agent)
```

---

## 13) Explainability

- Per agent **thermal ledger**: sources of heat (metabolic, radiant), sinks (sweat, active cooling), net ΔT.  

- **Water ledger**: intake vs losses vs recovered by stream; provenance of reclaimed liters (resp/persp/urine/feces).  

- **Counterfactuals**: “If `Seal +0.1`, hydration savings +0.6 L/day; if `Insulation +0.5 clo`, heat‑strain time‑to‑tier‑III +18 min.”

---

### End of Suit–Body–Environment v1

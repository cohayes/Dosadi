# **Escort & Combat v1 (Convoys, Ambushes, Damage, and Aftermath)**

**Purpose:** Specify how armed protection interacts with smuggling/official convoys, how engagements start and resolve, how suits and bodies take damage, and how outcomes ripple into Security/Market/Clinics/Law.

Integrates with **Smuggling Loop v1**, **Barrel Cascade v1**, **Security Loop v1**, **Suit–Body–Environment v1**, **Suit Maintenance v1**, **Clinic Protocols v1**, **Law & Contract Systems v1**, **Credits & FX v1**, **Rumor & Perception v1**, and the **Tick Loop**.

> Cadence: patrol/overwatch checks **per Minute** along routes; combat ticks **per 3 Seconds** (5 ticks/minute); resolution + logging **end of engagement**.

---

## 0) Actors & Roles

- **Convoy Core:** `{lead, cargo, tail}` vehicles with drivers.

- **Escort Team:** `close_security` (vehicle gunners), `overwatch` (elevated or drone), `QRF` (quick‑reaction reserve), `medic`, `clerk` (evidence).

- **Adversaries:** `bandits`, `rivals`, `rogue guards`, `wildlife?/hazards` (optional future).

- **C2 (Command & Control):** local ward ops; can broadcast **Rules of Engagement (ROE)** and authorize escalations.

---

## 1) Route Security Pre‑Run

- **Threat Model:** from Security Loop risk map: `ambush_hotspots`, `patrol_density`, `sensor_coverage`, `recent_incidents`.

- **Loadout Plan:** armor tier, weapons table (lethal / less‑lethal), jammer/decoys, med kit, spares, camera kit.

- **Formation:** vehicle spacing, overwatch posts, scout pathfinder choice, safehouse handoffs.

- **ROE Template:** `SHOW | CHALLENGE | DISABLE (less‑lethal) | DISABLE (lethal) | PURSUE | BREAK_CONTACT` with legal/evidence notes.

Events: `EscortPlanned`, `ROEPosted`.

---

## 2) Detection → Ambush Initiation

Per **Minute** while transiting a route segment:

1) **Recon Check:** overwatch/scouts contest attacker setup: `P_spot = f(sensor, vantage, daylight, dust, discipline)`.

2) If failed and attackers decide to strike: **Ambush Go/No‑Go** based on force ratio, morale, weather, target value, and rumor heat.

3) **Ambush Geometry:** L‑shape, linear, V‑shape, block‑and‑ram; generates initial positions, ranges, and cover.

Events: `AmbushDetected|AmbushSprung`.

---

## 3) Combat Tick (every 3 s)

### 3.1 Sequence

- **Initiative:** ambushers get first volley; afterwards per‑unit initiative with jitter from training/morale/fatigue.

- **Action Budget:** per tick, each unit selects **1 action** and **1 micro‑move**: `shoot / suppress / maneuver / aid / repair / comms / smoke / jamming / surrender`.

- **Suppression:** incoming fire raises **suppression** on targets → accuracy ↓, movement risk ↑; discipline + armor + cover mitigate.

### 3.2 Accuracy & Damage (simplified, tiered)

- `HitProb = aim(base) × range_decay × motion_penalty × suppression_penalty × cover_mod × optics_bonus × training`

- **Weapons Classes:** `blunt (baton/ram)`, `slash (blades)`, `pierce (projectiles)`, `chem`, `elec`.

- **Suit vs Weapon Mapping:**

  - **Blunt:** compare to `Armor.blunt` → `bruise/fracture` risk, `Integrity` loss.

  - **Slash:** vs `Armor.slash` → `cut/laceration`, `Seal` loss proportional; bleed.

  - **Pierce:** vs `Armor.pierce` → `penetration` → `Seal` drop, possible core injury; bleed.

  - **Chem/Elec:** vs `Suit_chem/electric` → burns, sensor/pump outages.

- **Body Injury Table (probabilistic tiers):**

  - Minor: bruise, superficial lac, light burn.  

  - Moderate: deep lac (suturable), non‑displaced fracture, inhalation irritation.  

  - Severe: penetrating trauma, compound fracture, major burn, shock.

- **Suit Damage Effects:** `Seal↓`, `Integrity↓`, `Cooling/Heating offline?`, `FilterLoad↑`; may trigger **SuitBreach**.

### 3.3 Morale

- Per side `Morale` (0–1) shifts with casualties, leadership, ammo, fatigue, surprise; drives `break_contact` or `surrender`.

Events: `ShotFired`, `UnitSuppressed`, `SuitBreach`, `AgentInjured`, `MoraleShift`.

---

## 4) Non‑Lethal & De‑Escalation

- **Less‑Lethal Tools:** tear agents (consider suit chem defense), shock batons, beanbag/foam, dazzlers, spike strips.

- **Disable Vehicle:** tire shots, EMP pulse (optional), blocking maneuvers.  

- **De‑Escalation Script:** loudhail → warning shot → disable tires → targeted arrest; required for high‑legitimacy zones.

- **Evidence Mode:** bodycams + clerk logs required to justify force; failure → legal exposure & legitimacy cost.

Events: `LessLethalUsed`, `SuspectDetained`, `EvidenceCaptured`.

---

## 5) Micro‑Repairs & Med Aid (During Fight)

- **Field Patch (Seal):** apply quick patch; recovers `Seal` up to threshold; risk under fire.

- **Heat Rescue:** deploy portable TEC or move casualty to sealed cabin; prevents heat stroke.

- **TCCC Bundle:** bleeding control, airway, chest seal; hands off to clinic post‑fight.

Events: `FieldPatchApplied`, `CasualtyStabilized`.

---

## 6) Resolution & Aftermath

- **Outcomes:** `AMBUSH_REPELLED | CARGO_ESCAPED | CARGO_SEIZED | MUTUAL_BREAK | PURSUIT`.

- **Salvage/Loot:** seized items logged; route rumor spikes; market reacts (local P_ref moves).  

- **Legal:** `CaseOpened` for use‑of‑force, seizure legitimacy, wrongful death.  

- **Clinic:** casualties queued by **ESI**; water/med consumption logged.  

- **Maintenance:** damaged suits/vehicles queue tasks; costs and downtime recorded.

Events: `EngagementEnded`, `CargoStatus`, `CaseOpened`, `MaintenanceTaskQueued`.

---

## 7) Convoy & Escort Economics

- **Contract Types:** `escort_fixed_fee`, `escort_success_fee`, `per‑km`, `per‑risk` multipliers; king‑subsidy for cascade lanes.

- **Cost Drivers:** escort size, armor tier, ammo/meds spend, expected downtime, legal risk premium, FX of paying issuer.

- **Optimality:** diminishing returns after coverage threshold; overwatch intel can substitute for guns.

---

## 8) Evidence, Rumors, Legitimacy

- **Evidence Bundle:** GPS path, cam feeds, fired‑rounds count, body telemetry, seized cargo manifest, witness statements.  

- **Rumors:** heroic defense (legitimacy +ε), extortion/abuse (−ε), botched op (−ε), or scandal (bribes, planted evidence).  

- **Transparency Windows:** public release in high‑legitimacy wards narrows rumor spread and price shock.

Events: `EvidenceSubmitted`, `PublicReleasePosted`, `RumorBurst`.

---

## 9) Policy Knobs (defaults)

```yaml
escort_combat:
  combat_tick_sec: 3
  recon_base_spot: 0.35
  cover_effect: { open: 0.6, light: 0.75, hard: 0.9 }
  suppression_coeff: 0.25
  training_mod: { militia: 0.9, merc: 1.05, guard: 1.1, bandit: 0.85 }
  morale_break_at: 0.25
  damage_map:
    blunt:  { bruise: 0.6, fracture: 0.1, seal_drop: 0.05 }
    slash:  { lac_minor: 0.5, lac_deep: 0.25, seal_drop: 0.2 }
    pierce: { superficial: 0.3, penetrating: 0.25, seal_drop: 0.35, integrity_drop: 0.15 }
    chem:   { irritation: 0.4, burn: 0.2, sensor_fail: 0.1 }
    elec:   { stun: 0.5, pump_fail: 0.15 }
  less_lethal_bias_inner: 0.6
  evidence_required_inner: true
  qrf_response_min: { inner: 8, middle: 15, outer: 30 }
  pursuit_risk_mult: 1.3
```

---

## 10) Event & Function Surface (for Codex)

**Functions**

- `plan_escort(route_id, formation, roe)` → `EscortPlanned`, `ROEPosted`

- `minute_security_tick(convoy_id)` → recon checks and ambush tests; maybe `AmbushDetected|AmbushSprung`

- `start_engagement(convoy_id, attackers)` → init geometry, sides, ROE

- `combat_tick(engagement_id)` → resolves a 3‑second step; emits shots, injuries, morale shifts

- `apply_field_patch(agent_id, part)` → `FieldPatchApplied`

- `end_engagement(engagement_id)` → `EngagementEnded`, `CargoStatus`, legal/clinic/maintenance hooks

- `post_evidence(engagement_id, bundle)` → `EvidenceSubmitted|PublicReleasePosted`

**Events**

- `EscortPlanned`, `ROEPosted`, `AmbushDetected`, `AmbushSprung`, `ShotFired`, `UnitSuppressed`, `SuitBreach`, `AgentInjured`, `MoraleShift`, `LessLethalUsed`, `SuspectDetained`, `FieldPatchApplied`, `CasualtyStabilized`, `EngagementEnded`, `CargoStatus`, `EvidenceSubmitted`, `PublicReleasePosted`, `RumorBurst`.

---

## 11) Pseudocode (Combat Core)

```python
def combat_tick(state):
    # initiative
    units = sort_by_initiative(state.units)
    for u in units:
        if u.suppressed: action = choose(["suppress","cover","smoke","retreat"], u.brain)
        else: action = choose_best(u, state)  # shoot / maneuver / aid ...
        outcome = resolve_action(u, action, state)
        apply(outcome, state)
    # morale & end checks
    for side in state.sides:
        side.morale = update_morale(side)
        if side.morale < morale_break_at: side.break_contact = True
    if cargo_escaped_or_seized(state) or both_broken(state):
        finalize_outcome(state)
```

---

## 12) Test Checklist (Day‑0+)

- Overwatch present reduces ambush surprise probability by ≥ X%; early `AmbushDetected` flips initiative.

- Slash/pierce produce `Seal` loss rates consistent with armor tiers; Clinic ESI mix shifts with weapon type.

- Less‑lethal use higher in inner wards; evidence absence causes legitimacy penalty.

- QRF arrival within policy mins changes `CARGO_SEIZED` → `AMBUSH_REPELLED` in ≥ Y% of trials.

- Field patches reduce hydration losses measurably; maintenance queue fills after heavy fights.

---

### End of Escort & Combat v1

---
title: Response_Cadences_and_Alert_Levels
doc_id: D-MIL-0003
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-22
depends_on:
  - D-RUNTIME-0001        # Simulation_Timebase
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-IND-0002            # Industry_Suitability_and_Evolution
  - D-ECON-0001           # Logistics_Corridors_and_Safehouses
---

# 09_military · Response Cadences and Alert Levels (D-MIL-0003)

## 1. Purpose

This document defines how **force response unfolds over time** on Dosadi, using
the global Simulation Timebase (D-RUNTIME-0001) and the ward schema
(D-WORLD-0002).

It specifies:

- A small set of **alert levels** at ward and regime scale.
- The **event categories** that push wards up or down those levels.
- The **response cadences** for different force types (D-MIL-0001).
- How **ward attributes** (e.g. `garrison_presence`, `corridor_centrality`)
  modulate response time and intensity.

This is a **logic & structure** document intended to be implementable in code.

---

## 2. Timebase & Scope

### 2.1 Timebase recap

From D-RUNTIME-0001:

- Simulation ticks at a fixed rate (e.g. **1.67 ticks per second** ≈ 100 ticks/min).
- Higher-level cadences (seconds, minutes, hours) are derived from ticks.

This document uses the following non-normative mapping for convenience:

```text
1 tick   ≈ 0.6 seconds
10 ticks ≈ 6 seconds
50 ticks ≈ 30 seconds
100 ticks ≈ 1 minute
300 ticks ≈ 3 minutes
600 ticks ≈ 6 minutes
```

Implementation MAY adjust real-world timing as long as **relative relationships**
between force types and alert levels are preserved.

### 2.2 Scope of alert logic

Alert logic is defined at two overlapping levels:

- **Ward-level alert** `alert_level(w)`  
  - Local state for a particular ward.
  - Driven by incidents inside that ward (and sometimes in neighbors).

- **Regime/global alert** `alert_level_global`  
  - Represents overall tension (city-wide unrest, coups, external threats).
  - Acts as a **multiplier** on local responses (faster, harsher, or more cautious).

Most gameplay and agent behavior will respond primarily to **ward-level alert**,
with global alert acting as a background modifier.

---

## 3. Alert Levels

We define four main alert levels, plus an optional fifth for catastrophic scenarios.

```yaml
ALERT_0_CALM:
  label: "Calm"
  description: "Routine patrols, low visible tension."
ALERT_1_TENSE:
  label: "Tense"
  description: "Increased checks, mild curfews, visible readiness."
ALERT_2_LOCKDOWN:
  label: "Lockdown"
  description: "Movement restricted, checkpoints hardened, raids more common."
ALERT_3_CRACKDOWN:
  label: "Crackdown"
  description: "Brutal enforcement, exo deployment, mass detentions."
ALERT_4_WARFOOTING:
  label: "War Footing"   # optional, scenario-specific
  description: "Sustained military operations; normal civic life largely suspended."
```

Implementation MAY omit `ALERT_4_WARFOOTING` for smaller scenarios.

Each level has **typical behaviors** and **available force types**, keyed to
D-MIL-0001.

### 3.1 Force availability by alert level (conceptual)

This table is indicative, not exhaustive:

| Force Type            | Calm | Tense | Lockdown | Crackdown | War Footing |
|-----------------------|:----:|:----:|:--------:|:---------:|:-----------:|
| Street Enforcers      |  ✔   |  ✔   |    ✔     |    ✔      |     ✔✔      |
| Corridor Troops       |  (low) | ✔  |    ✔     |    ✔✔     |     ✔✔      |
| Garrison Units        |  (reserve) | (visible) | ✔ | ✔✔ | ✔✔ |
| Exo-Suit Cadres       |   –  | (rare) | (targeted) | ✔ | ✔✔ |
| Rapid-Response Teams  |  (limited) | ✔ | ✔✔ | ✔✔ | ✔✔ |
| Clandestine Cells     |  ✔   |  ✔   |    ✔     |    ✔      |     ✔      |

- `(low)` or `(reserve)` indicates availability in principle but low visible use.
- `✔✔` indicates **maximum deployment** (subject to local capacity).

---

## 4. Incident Categories & Escalation Pressure

Alert levels are driven by **incidents**. For each ward `w`, the simulation
tracks an **escalation pressure** value `P(w)`.

### 4.1 Incident categories

Non-exhaustive list of incident categories (each is a typed event with a weight):

```yaml
INCIDENT_MINOR_DISORDER:
  description: "Small brawls, shouted arguments, minor vandalism."
  base_weight: 1

INCIDENT_STRUCTURAL_DAMAGE:
  description: "Visible damage to corridors, rails, or key equipment without casualties."
  base_weight: 2

INCIDENT_ECONOMIC_SABOTAGE:
  description: "Sabotage of pumps, grids, vats, or key industrial nodes."
  base_weight: 3

INCIDENT_ATTACK_ON_FORCES:
  description: "Attack on patrols, checkpoints, or barracks; casualties likely."
  base_weight: 4

INCIDENT_MASS_GATHERING:
  description: "Large unauthorized gathering, protest, or religious/union assembly."
  base_weight: 2

INCIDENT_RIOT:
  description: "Sustained, spreading disorder; multiple concurrent minor incidents."
  base_weight: 4

INCIDENT_EXO_OR_HEAVY_WEAPON_USE:
  description: "Use of exo-suits or heavy weapons by non-authorized actors."
  base_weight: 5

INCIDENT_COUP_SIGNAL:
  description: "Coordinated attacks on signal hubs, armories, or leadership."
  base_weight: 6
```

Each incident can be modified by **context** (ward attributes, target type,
global alert). For example:

- Attacking an armory in a core ward is worse than a minor brawl in a slum.
- Sabotage of WATER_ATMOSPHERE infra is weighted more heavily than a small
  factory fire in some scenarios.

### 4.2 Escalation pressure update

At each incident in ward `w` at time `t`:

```text
P(w) += incident_weight(incident, w, t)
```

Where:

```text
incident_weight = base_weight
                * target_importance_factor
                * regime_paranoia_factor
                * (1 + global_alert_modifier)
```

- `target_importance_factor` may depend on:
  - Hit industries (e.g. WATER_ATMOSPHERE, INFO_ADMIN).
  - Hit infrastructure (armory, exobay, signal hub).
- `regime_paranoia_factor` is a scenario parameter.
- `global_alert_modifier` grows as `alert_level_global` rises.

### 4.3 Natural decay of pressure

Over time, in the absence of new incidents, pressure relaxes:

```text
P(w) = max(0, P(w) - decay_rate(w) * Δt)
```

- `decay_rate(w)` MAY depend on:
  - `garrison_presence(w)` (higher → faster decay; more troops reassure/terrify).
  - `fear_index(w)` (higher fear → incidents have longer shadow; slower decay).
  - `INFO_ADMIN` industry weight (more admin → better narrative control).

This creates a **memory window**: a burst of trouble raises P(w), and if not
repeated, it fades out.

---

## 5. Mapping Pressure to Alert Levels

Each ward maps `P(w)` to an `alert_level(w)` via thresholds. Example:

```yaml
thresholds:
  ALERT_0_CALM:      P < 2
  ALERT_1_TENSE:     2 ≤ P < 5
  ALERT_2_LOCKDOWN:  5 ≤ P < 10
  ALERT_3_CRACKDOWN: 10 ≤ P < 18
  ALERT_4_WARFOOTING: P ≥ 18   # optional/high-tension scenarios
```

Thresholds MAY vary by ward or scenario. For example:

- Wards with high `loyalty_to_regime` and high `fear_index` may have **lower
  thresholds** (regime eager to clamp down).
- Wards with low `garrison_presence` or heavy industry may have **higher
  thresholds** (crackdown is expensive or risky).

### 5.1 Hysteresis (preventing oscillation)

To avoid wild up/down swings, you can use **hysteresis**:

- Use slightly lower thresholds to **de-escalate** than to escalate.

Example for a given ward `w`:

```yaml
escalate_thresholds:
  CALM→TENSE:  P_escalate ≥ 2
  TENSE→LOCKDOWN: P_escalate ≥ 5
  LOCKDOWN→CRACKDOWN: P_escalate ≥ 10

deescalate_thresholds:
  TENSE→CALM: P_deescalate ≤ 1
  LOCKDOWN→TENSE: P_deescalate ≤ 4
  CRACKDOWN→LOCKDOWN: P_deescalate ≤ 8
```

This means once a ward is in LOCKDOWN, it must **cool down further** than it
took to get there before dropping a level.

---

## 6. Response Cadence by Force Type

Each force type (D-MIL-0001) has a **baseline response time** that is then
scaled by ward attributes and alert level.

We define a conceptual response time function:

```text
response_time_ticks(force_type, source_ward, target_ward) ≈
    base_deploy_ticks(force_type, alert_level(source_ward), alert_level_global)
  + travel_ticks(source_ward, target_ward)
```

### 6.1 Base deploy times (indicative)

Assuming **ALERT_0_CALM** and sufficient capacity in `source_ward`:

```yaml
base_deploy_ticks:
  mil_street_enforcers: 20    # ~12 seconds (already on the street)
  mil_corridor_troops: 60     # ~36 seconds
  mil_garrison_units: 200     # ~2 minutes
  mil_exo_cadres: 400         # ~4 minutes (suit-up & checks)
  mil_rapid_response: 80      # ~48 seconds
  mil_clandestine_cells:  variable / scenario-scripted
```

Alert levels **modify** these baselines via a multiplier:

```yaml
alert_multiplier:
  ALERT_0_CALM:      1.5
  ALERT_1_TENSE:     1.0
  ALERT_2_LOCKDOWN:  0.7
  ALERT_3_CRACKDOWN: 0.5
  ALERT_4_WARFOOTING: 0.4
```

So under CRACKDOWN, exo-cadres in a prepared ward might deploy in `400 * 0.5 = 200`
ticks (~2 minutes) rather than 4 minutes.

### 6.2 Travel time along corridors

Travel time is approximated by the **shortest path** along the corridor graph
with a per-edge cost:

```text
travel_ticks(s, w) ≈ path_length_edges(s, w) * edge_travel_cost(s, w)
```

Where `edge_travel_cost` is modified by:

- `corridor_control` (more checkpoints, more barbed routes).
- `structural_capacity` (for heavy or exo forces).
- `alert_level` (higher levels may grant priority of passage).

A simple formulation:

```text
edge_travel_cost ≈ base_edge_ticks
                 / (1 + mobility_bonus(s))
```

`mobility_bonus(s)` increases with:

- `mil_motor_pools` presence in source.
- `ENERGY_MOTION` industry weight.
- `garrison_presence` and `loyalty_to_regime` (troops face less passive resistance).

### 6.3 Local vs imported response

If `target_ward == source_ward`, travel time may be negligible or minimal.

- Street enforcers and local barracks respond quickly **inside** their own ward.
- For larger responses, the simulation may choose a **staging ward** `s` with
  higher capacity, then compute travel to `w`.

Selection of `source_ward` is a policy question; simplest implementation:

- Use the **closest ward** with capacity for the required force type, weighted
  by `garrison_presence` and `military_weight` for that type.

---

## 7. Coupling to Ward Attributes

Ward attributes (D-WORLD-0002) influence both **how quickly** response arrives
and **how harsh** it is.

### 7.1 Factors that speed up response

Response is faster when:

- `garrison_presence(w)` is high.
- `corridor_centrality(w)` is high and corridors are controlled.
- `loyalty_to_regime(w)` is high.
- `fear_index(w)` is high (population self-polices, reports trouble quickly).
- `INFO_ADMIN` and `ENERGY_MOTION` weights are high (signal hubs + power).

Implementation can treat these as a **response speed factor**:

```text
response_speed_factor(w) ≈
    a1 * garrison_presence(w)
  + a2 * corridor_centrality(w)
  + a3 * loyalty_to_regime(w)
  + a4 * info_admin_weight(w)
```

And then:

```text
effective_response_time = raw_response_time / (1 + response_speed_factor(w))
```

### 7.2 Factors that slow or blunt response

Response is slower or more hesitant when:

- `toxicity_ruin(w)` is very high (dangerous to move in force).
- `ventilation_regime = open` with high `pollution_sink_index` and low suit coverage.
- `black_market_intensity(w)` is high and regime is partially captured or hesitant.
- `unrest_index(w)` is already high (fear of mutiny or overextension).
- `dist_to_well` and `elevation` together make logistics expensive.

These can add a **drag factor**:

```text
drag_factor(w) ≈
    b1 * toxicity_ruin(w)
  + b2 * black_market_intensity(w)
  + b3 * shortage_index(w)
```

Which can be applied as:

```text
effective_response_time = effective_response_time * (1 + drag_factor(w))
```

---

## 8. De-escalation Actions

De-escalation is not only passive (decay of P(w)) but can be **actively pursued**:

Examples:

- **Curfew + soft patrols**:
  - Deploy street enforcers and corridor troops without overt violence.
  - Gradually reduce `P(w)` if no new incidents occur for a window.

- **Concessions** (economic/food/water):
  - Temporarily boost `food_buffer(w)` and/or `water_quota(w)`.
  - Reduce `unrest_index(w)` and speed up decay of P(w).

- **Targeted repression**:
  - Arrest or remove key agents/factions (modeled elsewhere).
  - Reduce frequency/weight of incidents but increase `fear_index(w)`.

Mechanically, de-escalation actions can modify:

- `decay_rate(w)` for P(w).
- Thresholds for de-escalation between alert levels.
- Future base weights for incidents (e.g. protests are rarer or more explosive).

---

## 9. Implementation Sketch (Non-Normative)

A minimal loop for each ward `w` per tick or per small batch of ticks:

```text
1. Collect new incidents in ward w.
2. For each incident:
     P(w) += incident_weight(incident, w, t)
3. Apply natural decay:
     P(w) = max(0, P(w) - decay_rate(w) * Δt)
4. Determine new alert_level(w) using thresholds and hysteresis.
5. For any change in alert_level(w):
     - Optionally adjust patrol density, checkpoint behavior, curfew flags.
6. For any request to deploy forces to/from w:
     - Compute response_time based on force type, source ward, and attributes.
     - Schedule arrival events in future ticks.
```

Global alert level `alert_level_global` can be updated using a similar pressure
mechanism, but aggregating across wards (e.g. sum or weighted sum of unrest and
incidents).

---

## 10. Design Notes

- Alert levels give a **simple, legible state** that agents and UI can respond to,
  while still being driven by deeper simulation variables.
- Response times are intentionally **non-instant** and shape the strategic space:
  agents can exploit gaps, dead-ends, and slow-response zones.
- The same logic can support:
  - Routine low-tension life (CALM–TENSE).
  - Localized uprisings (LOCKDOWN–CRACKDOWN in a cluster of wards).
  - System-wide emergencies (WARFOOTING).

This document is expected to evolve as law, info_security, and rumor systems
become more concrete and start to feed additional incident types and modifiers
into the escalation logic.

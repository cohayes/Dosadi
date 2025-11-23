---
title: Operator_Alerts_and_Escalation_Prompts
doc_id: D-INFO-0015
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-WORLD-0003          # Ward_Evolution_and_Specialization_Dynamics
  - D-IND-0003            # Guild_Influence_and_Bargaining_Power
  - D-IND-0101            # Guild_Templates_and_Regional_Leagues
  - D-IND-0102            # Named_Guilds_and_Internal_Factions
  - D-IND-0103            # Guild_Charters_and_Obligations
  - D-IND-0104            # Guild_Strikes_Slowdowns_and_Sabotage_Plays
  - D-IND-0105            # Guild-Militia_Bargains_and_Side_Contracts
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-ECON-0004           # Black_Market_Networks
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-MIL-0002            # Garrison_Structure_and_Deployment_Zones
  - D-MIL-0003            # Response_Cadences_and_Alert_Levels
  - D-MIL-0102            # Officer_Doctrines_and_Patronage_Networks
  - D-MIL-0103            # Command_Rotations_and_Purge_Cycles
  - D-MIL-0104            # Checkpoint_and_Patrol_Behavior_Profiles
  - D-MIL-0105            # Garrison_Morale_and_Fracture_Risk
  - D-MIL-0106            # Field_Justice_and_In-Unit_Discipline
  - D-MIL-0107            # Special_Detachments_and_Commissar_Cadres
  - D-MIL-0108            # Counterintelligence_and_Infiltration_Risk
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0002           # Espionage_Branch
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-INFO-0009           # Counterintelligence_Tradecraft_and_Signatures
  - D-INFO-0014           # Security_Dashboards_and_Threat_Surfaces
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-RUNTIME-0001        # Simulation_Timebase
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 08_info_security · Operator Alerts and Escalation Prompts (D-INFO-0015)

## 1. Purpose

This document defines how **security dashboards** (D-INFO-0014) generate:

- **Operator alerts** – notifications that something requires attention.
- **Escalation prompts** – nudges toward taking specific classes of action.

It is concerned with:

- The logic that turns underlying indices and CI signatures into alerts.
- How different roles (dukes, Espionage, MIL, LAW, guild security) are:
  - warned,
  - misled,
  - or manipulated by their alert channels.
- How alerts feed into:
  - MIL response cadences (D-MIL-0003),
  - LAW and tribunal activation (D-LAW-*),
  - CI operations (D-MIL-0108, D-INFO-0009),
  - campaign-level triggers (future RUNTIME docs).

The goal is to provide a **semi-standardized alert vocabulary** and escalation
logic that the simulation and scenarios can hook into.

---

## 2. Alert Model

We define a generic alert object:

```yaml
SecurityAlert:
  id: string
  timestamp_tick: int
  source_system: "CI" | "MIL" | "LAW" | "WORLD" | "ECON" | "RUMOR"
  severity: "info" | "warning" | "critical"
  scope: "ward" | "node" | "threat_surface" | "global"
  target_roles:
    - "duke_house"
    - "espionage_analyst"
    - "mil_commander"
    - "law_officer"
    - "guild_security"
  summary_tag: string
  details_ref: string            # link to dashboard slice or report bundle
  suggested_responses:
    - "increase_ci_posture"
    - "raise_alert_level"
    - "initiate_purge_probe"
    - "open_negotiation_channel"
    - "monitor_only"
  confidence: float              # 0–1, from signature assessment
  political_spin: string         # optional narrative framing
```

Alerts are created from:

- `WardSecuritySummary` changes,
- `CIState` and CI signature assessments (D-INFO-0009, D-MIL-0108),
- LAW and sanction patterns (D-LAW-*),
- RUMOR volatility spikes.

---

## 3. Escalation Prompt Model

We define a more constrained **escalation prompt**:

```yaml
EscalationPrompt:
  id: string
  timestamp_tick: int
  ward_id: string
  threat_surface_id: string | null
  recommended_track: "military" | "legal" | "ci" | "political" | "propaganda" | "economic"
  urgency: "low" | "medium" | "high"
  rationale_tags:
    - "garrison_fracture_risk"
    - "guild_strike_risk"
    - "cartel_capture_risk"
    - "coup_vector"
    - "rebellion_vector"
  alternative_tracks:
    - "monitor_only"
    - "deescalate"
    - "backchannel_deal"
  expected_consequences_hint: string
```

Prompts are higher-level suggestions generated when:

- multiple alerts converge on a ward or threat surface,
- thresholds are crossed in key indices.

Scenarios and AI controllers can:

- accept prompts,
- reject them,
- or systematically bias toward/against certain tracks.

---

## 4. Alert Sources and Triggers

### 4.1 Dashboard-driven thresholds

From D-INFO-0014:

Examples of thresholds:

- `WardSecuritySummary.threat_level` moves to *high* or *critical*.
- `garrison_stability_index` drops below a given value.
- `infiltration_risk_index` exceeds a CI posture-adjusted limit.
- `black_market_intensity_index` spikes in a high-leverage ThreatSurface.

When such thresholds are crossed:

- An alert is generated with `source_system: "INFO"` or `"CI"`,
- scope = `"ward"` or `"threat_surface"`.

### 4.2 CI signature activations

From D-INFO-0009:

- High-confidence signatures:
  - Protected Corridor,
  - Phantom Losses,
  - Sudden Cleanliness,
  - Patronage Drift,
  - Rumor Echo Chambers,
  - Structural Justice Anomalies.

When confidence >= configured level:

- CI generates `SecurityAlert` with:
  - `source_system: "CI"`,
  - `severity`: warning/critical,
  - `suggested_responses` depending on signature type.

### 4.3 MIL, LAW, and WORLD incident triggers

- Repeated mutinies, desertions, or alignment switches (D-MIL-0105),
- Major field justice abuses or spectacular executions (D-MIL-0106),
- Large-scale sanctions or tribunals (D-LAW-*),
- WORLD shocks:
  - infrastructure failure,
  - environmental hazard events.

These trigger:

- cross-pillar alerts with multiple `target_roles`.

---

## 5. Role-Specific Alert Channels

### 5.1 Duke-house Channel

Receives:

- Highly filtered alerts:
  - `severity` = warning/critical only,
  - scope = ward/threat_surface/global.

Typical summary_tags:

- `"SPINE_GUILD_CAPTURE_RISK"`,
- `"COUP_VECTOR_IN_CORE"`,
- `"REBEL_ACTIVITY_IN_SHADOW"`.

Often accompanied by **political_spin**, e.g.:

- “Espionage Branch warns of [rival duke] influence in Ward 11.”

Duke responses feed:

- purge campaigns,
- pressure on MIL and LAW,
- high-level decrees altering CI posture.

---

### 5.2 Espionage Branch Analyst Channel

Receives:

- Most CI-related alerts, including medium severity,
- direct links to CI and infiltration panels (D-INFO-0014),
- alerts from LAW (unusual tribunal distributions) and RUMOR panels.

Analysts:

- triage alerts into:
  - ignore,
  - monitor,
  - open file,
  - recommend operation.

They also generate:

- structured EscalationPrompts for higher-level sign-off.

---

### 5.3 MIL Commander Channel

Receives:

- Ward-specific alerts on:
  - garrison fracture risk,
  - infiltration suspicion in subordinates,
  - imminent guild strikes or unrest.

- Limited CI detail:
  - often sanitized or vague.

Prompts:

- Often recommend:
  - raise alert level,
  - reassign units,
  - request or accept special detachments.

---

### 5.4 LAW and Tribunal Channel

Receives:

- Alerts on:
  - concentrated law opacity or bias,
  - high-profile MIL or guild cases.

Prompts:

- Recommend:
  - opening investigations,
  - convening tribunals,
  - issuing curfew or emergency decrees (D-LAW-0003).

---

### 5.5 Guild Security Channel

For major guilds and some bishops:

- They maintain **parallel dashboards** using:
  - partial official data,
  - their own spies,
  - rumor networks.

Alerts:

- about hostile CI and MIL focus on their wards or assets,
- about rival guild/cartel maneuvers.

Prompts:

- Suggest:
  - lying low,
  - pre-emptive strikes,
  - charter-based public complaints,
  - quiet bargains with MIL/LAW.

---

## 6. Escalation Tracks and Typical Prompts

### 6.1 Military Track

Prompts like:

- “Raise local alert to heightened.”
- “Deploy additional patrols to ThreatSurface X.”
- “Request special detachment from core.”

Risks:

- Overuse generates:
  - fatigue,
  - garrison morale collapse,
  - long-term fracture risk.

---

### 6.2 Legal Track

Prompts like:

- “Open investigation into Ward 09 tribunals.”
- “Convene Security Tribunal on suspected infiltrators.”
- “Issue targeted curfew orders.”

Risks:

- Overuse deepens law opacity,
- fuels narratives of regime injustice,
- may drive more actors into Shadow.

---

### 6.3 CI Track

Prompts like:

- “Elevate CI posture in Spine Ring 3.”
- “Launch integrity checks on Corridor Commanders 7 and 8.”
- “Set up sting on Rat Gate checkpoint.”

Risks:

- CI overreach can:
  - cause backlash,
  - trigger counter-infiltration by factions,
  - fragment info-security trust.

---

### 6.4 Political and Propaganda Track

Prompts like:

- “Launch narrative operation to blame unrest on Cartel X.”
- “Publicly announce investigation into corrupted officers in Ward 10.”
- “Celebrate loyal garrison in Ward 03 to reinforce doctrine.”

Risks:

- Mismatch between narrative and ground reality undermines credibility,
- can make future alerts less effective.

---

### 6.5 Economic Track

Prompts like:

- “Adjust ration flows to reduce pressure in Ward 12.”
- “Offer temporary tax relief to key guilds.”
- “Threaten contractual sanctions on guild charters.”

Risks:

- Can temporarily relieve tension,
- or be read as weakness, inviting further pressure.

---

## 7. Biases, Feedback, and Alert Fatigue

### 7.1 Political bias

Alerts and prompts are not neutral:

- thresholds can be tuned,
- severity labels can be inflated or downplayed.

Ducal factions, Espionage sub-factions, and guild infiltrators may:

- silence certain alerts,
- amplify others,
- generate fake alerts to justify desired actions.

### 7.2 Alert fatigue

If operators are:

- flooded with critical alerts,
- burned by false positives,

they may:

- start ignoring or downgrading subsequent alerts,
- prioritize short-term quiet over long-term risk.

Simulation hook:

- track per-role **alert_trust_index** that evolves based on outcomes.

---

## 8. Integration with Campaign and Runtime

Alerts and escalation prompts are key inputs for:

- **Campaign milestones**:
  - thresholds of unrest, purge intensity, or coup risk.

- **Scenario triggers**:
  - e.g., “Three ‘COUP_VECTOR’ alerts in core → coup attempt scenario unlock.”

- **AI policy learning**:
  - RL agents can be trained to decide:
    - which prompts to follow,
    - how aggressively to escalate,
    - balancing stability vs repression vs infiltration.

---

## 9. Implementation Sketch (Non-Normative)

1. **At each simulation macro-step**:

   - Recompute dashboards and indices (D-INFO-0014).
   - Check:
     - thresholds,
     - CI signature activations,
     - notable incident events.

2. **Generate SecurityAlert objects**:

   - Assign severity and target_roles by template rules.
   - Attach confidence and optional political_spin.

3. **Aggregate alerts into EscalationPrompts**:

   - Group by ward or ThreatSurface.
   - Evaluate:
     - persistence,
     - convergence of multiple signal types.

4. **Deliver alerts/prompts to role views**:

   - Apply role filters, delays, and political distortions.

5. **Allow operator / AI decisions**:

   - Accept, reject, or modify prompts.
   - Log decisions and outcomes for:
     - metrics,
     - RL training,
     - narrative retrospective.

---

## 10. Future Extensions

Potential follow-ups:

- `D-RUNTIME-0102_Campaign_Milestone_and_Crisis_Triggers`
  - Formalizing how alerts and indices combine into large-scale campaign
    state changes.

- Scenario templates:
  - “Alert Storm” — the regime drowns in signals and must choose which to
    believe,
  - “Silent Coup” — key alerts are suppressed, and dashboards whisper too late.

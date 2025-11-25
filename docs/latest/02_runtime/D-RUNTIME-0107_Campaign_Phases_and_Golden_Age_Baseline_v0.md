---
title: Campaign_Phases_and_Golden_Age_Baseline
doc_id: D-RUNTIME-0107
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-24
depends_on:
  - D-RUNTIME-0001  # Simulation_Timebase
  - D-RUNTIME-0103  # Scenario_Framing_and_Win_Loss_Conditions
  - D-RUNTIME-0105  # AI_Policy_Profiles
  - D-RUNTIME-0106  # Office_Precedent_and_Institutional_Memory
  - D-WORLD-0001    # World_Index / Ward_Schema
  - D-ECON-0001     # Ward_Resource_and_Water_Economy
  - D-IND-0001      # Industry_Index
  - D-AGENT-0001    # Agent_Core_Schema_v0
  - D-AGENT-0006    # Agent_Attributes_and_Skills_v0
---

# 02_runtime · Campaign Phases & Golden Age Baseline v0 (D-RUNTIME-0107)

## 1. Purpose & Scope

This document defines a **three-phase campaign model** for the Dosadi
simulation and formalizes the **Golden Age Baseline** as the primary
configuration target for early development and testing.

The goals are to:

- provide a shared language for long-horizon campaign evolution,
- describe what the world looks like when it is **not yet in crisis**,
- specify which mechanics are **enabled / disabled by phase**, and
- give scenario authors a clear way to declare:
  - "This scenario is Golden Age" vs
  - "This scenario takes place after the realization of limits" vs
  - "This scenario is deep in scarcity and corruption."

This is a **runtime framing** document: it does not introduce new low-level
mechanics, but instead coordinates how existing pillars (WORLD, AGENT, ECON,
IND, MIL, LAW, INFO) are used across long campaigns.

---

## 2. Phase Model Overview

We distinguish three high-level campaign phases:

1. **Phase 0 · Golden Age Baseline**  
   - The Well can supply **more than enough** water for current population and
     reasonable growth.  
   - Structural **corruption and unrest are near zero**; minor variance exists
     but does not dominate behavior.  
   - R&D focuses on **efficiency, safety, comfort**, not on coercive control.  
   - Narcotics exist but are **regulated and secondary** (medical and mild
     entertainment uses).

2. **Phase 1 · Realization of Limits**  
   - Analysts and upper-tier actors become aware that the Well is **finite**.  
   - Forecasts show that without changes, the system will enter crisis within
     a campaign-relevant horizon (decades).  
   - Rationing, discipline, and efficiency drives are introduced while
     attempting to preserve legitimacy and order.  
   - R&D begins to pivot toward **resource efficiency and early control tools**.  
   - Narcotics start being used more deliberately as **population management**
     (sedation in high-stress wards, etc.), but corruption is still limited.

3. **Phase 2 · Age of Scarcity and Corruption**  
   - Water and other critical resources are **seriously constrained**.  
   - Structural **corruption, cartelization, and black markets** become
     central to survival.  
   - Narcotics are a primary lever of both state and cartel control.  
   - R&D is bifurcated: efficiency vs coercion, with elite-only comfort tech.  
   - Open rebellion, coups, and regime fragmentation are possible and may be
     common at the edges.

The intent is that **Phase 0** defines a logically consistent, mostly-stable
world: the "ingredients" of Dosadi before we turn up the heat. Phases 1 and 2
are then layered on top by **changing parameters and toggles**, not by
rewriting the underlying machinery.

---

## 3. Phase 0 · Golden Age Baseline

### 3.1 Narrative description

- The Well is effectively **abundant** relative to population and industrial
  demand.  
- Wards differ in privilege and comfort, but **no ward is existentially
  starved** in normal operation.  
- The regime is **firm but broadly legitimate**; unrest is local and episodic,
  not structural.  
- Administrative, industrial, and military actors are assumed to behave
  **within legal and institutional norms**; serious corruption is rare and
  swiftly punished when found.  
- R&D is a crown- and guild-sponsored activity aimed at:
  - safer and more efficient suits and HVAC,
  - better condensers and reduced losses,
  - improved industrial yields and reliability.  
- Narcotics are present but modest in scope:
  - regulated drugs for medicine and mild recreation,
  - no mass dependency, and no narcotics-based power blocs yet.

The Golden Age is **not utopia**—there is hierarchy, inequality, and harsh
labor—but the system is **coherent, growth-oriented, and not yet in crisis**.

### 3.2 Systemic assumptions

Phase 0 scenarios SHOULD respect the following assumptions:

- **Well output**  
  - `well_output_per_tick ≥ total_expected_demand * (1 + safety_margin)`  
  - Safety margin recommended in v0: 10–25%.

- **Structural corruption**  
  - `corruption_base_rate ≈ 0` for core institutions (crown, dukes, audit,
    militia, key guilds).  
  - Individual bad actors may exist, but **systemic incentives do not reward
    corruption** strongly.

- **Unrest & fragmentation**  
  - `unrest_floor` and `fragmentation_floor` are low but nonzero (there is
    always some friction).  
  - No wards start at or near rebellion thresholds.

- **R&D**  
  - Focus tags skew toward `efficiency`, `safety`, `comfort`.  
  - Coercive tech tags (`surveillance`, `control_drugs`, etc.) are present but
    low-weight or dormant.

- **Narcotics & vice**  
  - Narcotics industry exists as a **regulated economic niche**, low volume.  
  - No narcotics-based cartel has structural influence in Phase 0 scenarios.

### 3.3 Phase 0 metrics & health bands

For Phase 0, it is useful to define **healthy bands** for the global metrics
used in dashboards:

- **Stress**: should oscillate within a low-moderate range, with occasional
  spikes during incidents, returning to baseline without dramatic interventions.
- **Fragmentation**: low; factions exist but do not seriously threaten the
  regime.  
- **Legitimacy**: high to very high for the crown and its primary institutions.
- **Unrest**: low; only localized events under extreme conditions.  
- **Repression**: low to moderate; high repression should be rare and notable.  
- **Infiltration / CI Risk**: low; espionage focuses more on external threats,
  efficiency, and early anomaly detection.

These bands are scenario-specific but should be **stable targets** for Phase 0
AI and office behavior.

### 3.4 Phase 0 AI & office behavior

Tier-3 actors in Phase 0 SHOULD:

- use **Golden Age AI_PolicyProfiles** emphasizing:
  - maintaining stability and legitimacy,
  - investing in infrastructure and efficiency,
  - resolving issues via soft levers (relief, reallocation, administrative
    fixes) before hard crackdowns;
- treat corruption and unrest as **rare anomalies**, not everyday tools;
- see R&D as a **public good** first, not a power hoard.

This does not outlaw ambition or politics, but **keeps them bounded** by a
shared understanding that the system is, for now, generous enough for everyone
to survive within the rules.

### 3.5 Scenario flags for Phase 0

Phase 0 scenarios SHOULD explicitly set:

```yaml
campaign_phase: 0

well_model:
  mode: "abundant"
  safety_margin: 0.15          # e.g. 15% above projected demand
  depletion_curve: "none"      # or very long horizon beyond scenario length

corruption:
  enabled: false               # systemic corruption model off
  base_rate: 0.0

unrest:
  structural_enabled: false    # no deep grievance engine yet
  random_incidents_enabled: true

r_and_d:
  focus_weights:
    efficiency: 0.6
    safety: 0.2
    comfort: 0.15
    control: 0.05

narcotics:
  control_mode: "regulated_low"
  cartel_pressure: "minimal"
```

The exact names of knobs may differ in implementation, but **the spirit is
that Phase 0 runs with generous, low-drama defaults**.

---

## 4. Phase 1 · Realization of Limits

### 4.1 Narrative description

Phase 1 begins when credible analysis shows that **The Well is finite** and
the current pattern of consumption is unsustainable within a politically
relevant timescale (decades).

Key features:

- The crown and key advisors accept that a **course correction** is required.  
- New institutions, decrees, or R&D programs are launched to:
  - reduce waste and leaks,
  - refine the barrel cadence system,
  - increase monitoring of consumption across wards and industries.
- Rationing begins gradually:
  - certain wards or sectors face **mild reductions** in allocations,
  - others are incentivized to conserve in exchange for future benefits.
- R&D intensifies around:
  - more efficient condensers,
  - improved suits and HVAC,
  - early forms of **surveillance and forecasting**.

Narcotics and propaganda may see early experiments as **stability tools**, but
they are not yet central to control.

### 4.2 Systemic assumptions

Compared to Phase 0:

- **Well output model** switches from "effectively infinite" to a **finite
  reservoir or diminishing-return curve**.  
- **Unrest model** activates structural components:
  - long-term inequality, perceived unfairness in rationing, and policy
    shocks now contribute to unrest.  
- **Corruption model** is still nominally off or minimal, but:
  - the **incentive landscape** changes; opportunities for skimming, insider
    deals, and illicit flows begin to appear at the edges.

Scenario flags might look like:

```yaml
campaign_phase: 1

well_model:
  mode: "finite"
  safety_margin: 0.05
  depletion_curve: "slow_exponential"

corruption:
  enabled: true
  base_rate: 0.01              # low but nonzero

unrest:
  structural_enabled: true
  random_incidents_enabled: true

r_and_d:
  focus_weights:
    efficiency: 0.5
    safety: 0.15
    comfort: 0.1
    control: 0.25              # control tools start to matter

narcotics:
  control_mode: "emergent_tool"
  cartel_pressure: "low"
```

### 4.3 Role in campaigns

Phase 1 is where the system is **still salvageable** in principle:

- A wise and disciplined regime could stabilize on a lower resource plateau.  
- A shortsighted one will lay the groundwork for Phase 2 catastrophe.

Campaigns that begin in Phase 1 should highlight **tensions in the ruling
class**: some actors push for technocratic reform, others for extraction and
suppression.

---

## 5. Phase 2 · Age of Scarcity and Corruption

### 5.1 Narrative description

Phase 2 is the full-flavor **Dosadi pressure cooker**:

- The Well’s effective output is insufficient for population and
  industrial appetite.  
- Structural corruption is widespread:  
  skimming, black markets, off-books deals, and cartel-enforced flows.  
- Narcotics are a core piece of social and political control:  
  both state and cartels use them to create dependency, compliance, and profit.  
- R&D has split into:
  - survival/efficiency tech for the system as a whole, and
  - elite/control tech for specific factions.

Major features:

- Persistent, structural **unrest** in some wards.  
- Meaningful probabilities of **rebellion, coups, and secession**.  
- Tier-3 actors must choose between:
  - trying to reform a failing system,
  - doubling down on extraction and control,
  - or cutting side deals with cartels and rivals.

### 5.2 Systemic assumptions

Scenario flags might look like:

```yaml
campaign_phase: 2

well_model:
  mode: "finite"
  safety_margin: -0.10         # structural shortfall
  depletion_curve: "late_stage"

corruption:
  enabled: true
  base_rate: 0.05-0.15         # significantly higher baseline

unrest:
  structural_enabled: true
  rebellion_enabled: true
  random_incidents_enabled: true

r_and_d:
  focus_weights:
    efficiency: 0.3
    safety: 0.1
    comfort: 0.1
    control: 0.5               # heavy emphasis on coercive tech

narcotics:
  control_mode: "central_axis"
  cartel_pressure: "high"
```

Phase 2 scenarios are where the **full depth of your agent learning,
precedent, rumor systems, and power stacks** come alive.

---

## 6. Implementation Hooks & Scenario Integration

To make these phases usable in code and YAML, scenarios SHOULD:

1. **Declare campaign_phase** explicitly (0, 1, or 2).  
2. Use campaign_phase to set **defaults** for:
   - Well model and safety margins,
   - corruption and unrest switches,
   - R&D focus weights,
   - narcotics/control assumptions.
3. Allow **scenario-specific overrides** where appropriate
   (e.g., a Phase 0 scenario could explore an isolated corruption incident
   without flipping the global corruption model to Phase 2).

Runtime components SHOULD:

- treat campaign_phase as a **high-level context variable**, not a single
  hard-coded behavior switch;
- derive **office templates, AI_PolicyProfiles, and event tables** from the
  current phase, so the same office can behave differently when ported from a
  Golden Age scenario into a Late Scarcity one.

---

## 7. Future Work

Future versions of this document may:

- define a **canonical timeline** (e.g. Golden Age ≈ first 100 years, Phase 1
  ≈ next 50–100, Phase 2 thereafter),  
- specify how **player-facing campaigns** can span multiple phases in one
  long run,  
- introduce **mid-phase transitions and shocks** (e.g. a disaster that forces
  an early jump from Phase 0 → Phase 2 in a region),  
- and attach **example scenarios** for each phase:
  - S-000X: Golden Age Stable City,
  - S-00YX: Early Rationing and Reform,
  - S-01ZX: Late Scarcity and Cartel Ascendancy.

For now, D-RUNTIME-0107 SHOULD be treated as the authoritative reference for
how to talk about campaign phases and how to configure a **Golden Age**
scenario as the baseline for system development.

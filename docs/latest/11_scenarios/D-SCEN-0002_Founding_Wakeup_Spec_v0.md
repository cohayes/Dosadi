---
title: Founding_Wakeup_Spec
doc_id: D-SCEN-0002
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-25
depends_on:
  - D-CAMPAIGN-0001   # Campaign_Phases
  - D-AGENT-0020      # Agent_Model_v0
  - D-AGENT-0023      # Agent_Goal_System_v0
  - D-AGENT-0024      # Agent_Decision_Loop_v0
  - D-MEMORY-0002     # Episode_Schema_and_Memory_Behavior_v0
  - D-MEMORY-0003     # Episode_Transmission_Channels_v0
  - D-WORLD-000X      # Worldgen_Basics (placeholder)
---

# 11_scenarios · Founding Wakeup Spec v0 (D-SCEN-0002)

## 1. Purpose

This document defines the **Founding Wakeup** scenario spec: the very first
campaign moment when the colonists wake up around the Well, step into their
basic suits, and begin self-organizing.

It is designed so that the **shape of the opening behavior** stays the same
across parameter changes:

1. Colonists wake up in sealed bunk pods.
2. They begin utilizing nearby resources and exploring unsealed facilities.
3. Proto-political bodies form to protect people and key assets.
4. Surveys of population and geography lead to task-forces acting on those
   body-level goals.

Only tunable parameters (population, supplies, world template) change pacing
and difficulty, not this qualitative arc.

This is a **scenario-level** spec (SCEN pillar). Underlying geography and
worldgen knobs live in WORLD documents and are referenced here via templates.

---

## 2. Scenario Identity

- **scenario_id**: `founding_wakeup`
- **label**: Founding Wakeup · Colonists Around the Well
- **campaign_phase**: Phase 0 · Golden Age Baseline
- **timeframe**:
  - start: tick 0
  - nominal end: first 60–90 days of colony operation (tunable)

This scenario SHOULD be playable in isolation (for early tests) and also serve
as the canonical **campaign starting state** for long-run simulations.

---

## 3. Tunable Starting Parameters

The following parameters MAY be tuned between runs without changing the
qualitative behavior curve.

### 3.1 Population

- `colonist_count`
  - default: 20_000
  - suggested range: 5_000 – 100_000

- `attribute_distribution`
  - per-attribute means and variances for STR, DEX, END, INT, WIL, CHA
    (see D-AGENT-0006).

- `personality_distribution`
  - proportions for:
    - high Control/Prediction/Order
    - high Ambition
    - high Communal
    - high Curiosity
    - high Bravery vs high Caution
  - remaining population clustered near middling values.

- `skill_profile_distribution`
  - fractions of colonists with baseline competencies:
    - `pct_technical`       # exo-bay, fabrication, power/thermal systems
    - `pct_medical`
    - `pct_logistics`
    - `pct_military`
    - `pct_administrative`
    - `pct_unskilled`

All colonists start with **tier: 1**. Higher tiers emerge through later
appointments and promotions.

### 3.2 Supplies

- `supply_profile`
  - `rations_person_days`
    - baseline days of food at minimal maintenance diet.
  - `water_buffer_days`
    - days of stored water (separate from live Well extraction).
  - `tools_technical_index`
    - quantity and diversity of heavy tools and precision equipment.
  - `tools_civil_index`
    - bunks, sanitation, basic medical and maintenance tools.
  - `spares_critical_index`
    - spare valves, pumps, filters, suit seals, etc.

- `supply_distribution`
  - how clustered vs dispersed crates are:
    - `depot_layout: "single_core" | "multi_clustered" | "ringed"`
  - labeling clarity:
    - `label_clarity: "pictogram_clear" | "mixed" | "cryptic_codes"`

### 3.3 Geography & Hazards (Worldgen Hooks)

These reference WORLD-level definitions (e.g. D-WORLD-000X). In this spec we
only name the hooks.

- `worldgen_template`
  - e.g. `"bowl_city_v1"` or `"shaft_city_v1"`.

- `well_core_radius`
  - radius around the Well where permanent sealed structures can exist.

- `bunk_ring_layout`
  - number and arrangement of sealed bunk pods in rings or clusters around the
    well_core.

- `outer_hazard_gradient`
  - mapping from distance / elevation to base environmental risk:
    - heat, dryness, radiation, particulates, etc.

- `terrain_complexity`
  - density of corridors, choke points, blind alleys, shafts.

The **key constraint** for this scenario:

> **Bunk pods are sealed; facilities and corridors outside the pods are
> unsealed and environmentally hostile without suits.**

This underpins the colonists’ need to use their basic suits when stepping out
of bunk pods.

---

## 4. Initial Agent State

### 4.1 Legal & Social Status

At tick 0:

- no nobility, no kings, no dukes;
- each agent has:
  - `legal_status: "colonist"`
  - `tier: 1`
  - no pre-existing office or seat in any political body.

There are no pre-scripted councils, guilds, cartels, or military chains of
command. These emerge from interaction.

### 4.2 Attributes, Personality, Skills

Each colonist is instantiated according to D-AGENT-0020 and D-AGENT-0006:

- **Attributes**
  - STR, DEX, END, INT, WIL, CHA sampled from `attribute_distribution`
    (centered on 10, with ~10% effects per step).

- **Personality Traits**
  - Ambition–Contentment, Bravery–Caution, Communal–Self-Serving,
    Curiosity–Routine, Trusting–Paranoid, Honesty–Deceitfulness,
    etc., per `personality_distribution`.

- **Skills**
  - a small number of non-zero skills assigned per
    `skill_profile_distribution`.

### 4.3 Goals (Initial Stack)

All colonists start with a **goal stack** biased toward:

- **Survival**
  - secure water access,
  - secure safe sleeping,
  - secure food intake.

- **Uncertainty Reduction**
  - orient within immediate surroundings,
  - identify immediate hazards and safe spots,
  - understand basic rules of the environment.

- **Affiliation / Communal Coherence (low intensity baseline)**
  - seek a stable local pod for mutual support.

- **Control / Prediction / Order**
  - strongly weighted only for a minority predisposed towards organizing and
    rule-making.

No colonist begins with a pre-defined “become king” or “rule the colony”
goal; ambitions at that scale emerge later from episodes and promotions.

### 4.4 Equipment on Wakeup: Basic Suits

Every colonist wakes up with:

- a **basic personal suit**:
  - durable, minimal exo/soft-suit capable of:
    - limited protection against ambient hazards outside sealed pods,
    - moderate moisture capture from respiration and sweat,
    - basic temperature buffering,
  - **not** optimized for long-range expeditions or heavy industry.

- suit properties (conceptual):
  - `suit_protection_rating` (vs outer hazards),
  - `suit_moisture_capture_efficiency` (low to moderate),
  - `suit_durability` (good baseline; can withstand early explorations).

This guarantees:

- stepping outside a bunk pod into unsealed facilities is dangerous but not
  instantly lethal,
- early exploration and resource handling are viable without heavy
  industrial suits.

Additional specialized suits (heavy exo-bays, high-efficiency capture suits,
etc.) appear later via industry and R&D, not at tick 0.

---

## 5. Initial Environment & Layout

### 5.1 Sealed Bunk Pods

- Colonists are assigned to **sealed bunk pods**, each:
  - environmentally controlled and safe without suits,
  - housing ~10–50 colonists,
  - with 1–2 controlled exits into unsealed corridors / facilities.

- Bunk pods are grouped in rings or clusters around the Well core:
  - the inner-most pods are closest to the Well chamber access.
  - pod layout follows `bunk_ring_layout`.

### 5.2 Unsealed Facilities & Corridors

Outside the bunk pods:

- **Corridors and facilities are unsealed**:
  - ambient atmosphere is hostile without a suit:
    - low humidity,
    - temperature stress,
    - particulates and/or toxins depending on `outer_hazard_gradient`.

- Within the **well_core_radius**:
  - some structural advantages (less hazard than further out),
  - but still unsealed unless explicitly flagged as a sealed module
    (e.g. medical bay, control room).

- There exist:
  - **supply depots** near pods (within unsealed space),
  - machinery rooms,
  - access tunnels leading outward.

To move between bunk pods or to reach depots, agents must:

- exit a sealed pod,
- traverse unsealed corridors in their basic suits.

### 5.3 Well & Core Structures

- A central **Well chamber**:
  - physical placement at the heart of the core region,
  - machinery and valves controlling water extraction,
  - initial access limited via doors, warning signage, and basic interlocks.

- Adjacent **utility bays**:
  - housing fundamental support systems:
    - pumps, filters, power distribution, minimal HVAC.

These core structures are **recognized visually** (by architecture and
signage) as important, but not yet attached to any living institution or
protocol enforcement body.

---

## 6. Early Action Set

To get the desired universal early behavior, this scenario constrains the
initial action set to a small subset of the global Agent_Action_API.

### 6.1 Orientation Actions

- `inspect_bunk`
  - learn bunk-local layout and occupants,
  - generate first social episodes.

- `exit_pod_to_corridor`
  - don suit (if not already worn),
  - step into unsealed corridor with hazard exposure depending on
    `outer_hazard_gradient`.

- `walk_corridor_local`
  - move a short distance within the safe core band,
  - generate simple spatial and hazard episodes.

- `inspect_depot`
  - approach and visually inspect supply crates,
  - read labels/pictograms,
  - generate episodes linking crate locations to contents.

- `approach_well_chamber`
  - approach Well access doors or viewing panels,
  - perceive machinery, signage, possible access restrictions.

### 6.2 Social Actions

- `talk_neighbor`
  - exchange basic information and impressions with nearby agents,
  - generate initial person-beliefs and trust relations.

- `form_pod`
  - adopt a small set of bunkmates as a mutual-support unit,
  - set early kin/pod-like ties even if they are not genetic family.

- `politic_local`
  - propose informal norms within bunk/pod:
    - shared watch rotation,
    - sharing information about depots,
    - rules about who opens the pod door and when.

### 6.3 Exploration & Hazard Probing

- `probe_outer_corridor`
  - walk slightly beyond the well_core safe band with suit protection,
  - generate episodes about increased hazard, visibility, and risk.

- `observe_hazard`
  - explicitly attend to environmental cues:
    - frost/heat on surfaces,
    - fogging or heating of suit,
    - audible alarms or warnings.

These actions seed the **first wave of episodes** that later support:

- local trust graphs,
- identifying competent organizers,
- crude risk maps of the immediate environment.

---

## 7. Emergent Proto-Politics & Surveys (Scenario Expectations)

The scenario does **not** hard-code councils or task-forces. Instead, it
defines **emergent behavior expectations** that can be used for validation
and tuning.

### 7.1 Proto-Politics Emergence

Expected qualitative milestones:

- By T₁ (e.g. within first 3–7 days, tunable):
  - most colonists belong to a **pod** of size ≥ 5.
  - multiple pods have agents with:
    - high Control/Order goals,
    - repeated successful conflict-resolution episodes,
    - emergent status as local “spokespeople”.

- By T₂ (e.g. within first 7–14 days):
  - spokespeople from different pods meet at corridor junctions or shared
    depots to:
    - negotiate small-scale norms,
    - coordinate access to supplies and corridors.
  - these repeated meetings effectively form a **proto-council**:
    - no explicit “Council object,” but a recognizable set of agents through
      whom many decisions flow.

### 7.2 Surveys & Task-Forces Emergence

As the proto-council accumulates episodes of:

- “we ran out of rations earlier than expected,”
- “unknown hazards beyond corridor X caused incidents,”
- “we don’t know who is where in the bunk network,”

expected behavior:

- body-level goals like:
  - `Map_Area(region_id)`
  - `Census_Population(locality_id)`
  - `Assess_Risk(asset_id)` appear in the political body’s goal stack.

- **Task-forces** are then assembled by:
  - selecting pods or subgroups and assigning them roles:
    - scout, note-keeper, guard, medic, etc.
  - sending them into unsealed facilities and outward corridors using their
    basic suits.

- Returned survey episodes:
  - update spatial patterns and hazard maps,
  - influence pod placement and movement,
  - begin to inform the first **formal protocols** for:
    - movement,
    - ration distribution,
    - hazard avoidance.

These milestones can be tracked in the runtime as **emergent success
criteria** for this scenario.

---

## 8. Integration with WORLD / Worldgen

This scenario assumes a WORLD layer that can:

- instantiate geometry per `worldgen_template`,
- enforce the invariant:
  - sealed bunk pods vs unsealed external facilities,
- apply `outer_hazard_gradient` to unsealed space.

The Founding Wakeup spec:

- **does not** define exact topology,
- **does** constrain:
  - relative placement of pods, depots, and the Well,
  - sealed vs unsealed regions,
  - minimal action set and agent initial conditions.

WORLD documents (e.g. D-WORLD-000X) WILL define:

- the actual layout variations,
- how hazard bands evolve over time,
- how later ward structures and sealed-core expansions unfold.

---

## 9. Future Work

Future documents SHOULD:

- define the machine-readable YAML:
  - `S-0002_Founding_Wakeup.yaml` matching this spec.
- specify:
  - minimal vs detailed geometry for early tests,
  - parameter sweeps for `colonist_count`, `supply_profile`, and
    `worldgen_template`.
- connect:
  - early Founding Wakeup outputs to later Phase 0→1 transitions
    (Campaign Phases, D-CAMPAIGN-0001),
  - early proto-councils to formalized political bodies and protocols
    (D-LAW-0011, D-LAW-0012).

D-SCEN-0002 is the canonical starting scenario: the moment where sealed bunk
pods open onto a hostile world, everyone has only a basic suit and a few
neighbors, and the entire later city is latent in how they choose to organize.

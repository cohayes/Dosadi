---
title: Garrison_Structure_and_Deployment_Zones
doc_id: D-MIL-0002
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-MIL-0003            # Response_Cadences_and_Alert_Levels
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-ECON-0004           # Black_Market_Networks
  - D-IND-0003            # Guild_Influence_and_Bargaining_Power
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 14_military · Garrison Structure and Deployment Zones (D-MIL-0002)

## 1. Purpose

This document defines how **military forces are physically distributed across
wards** on Dosadi, and how garrisons interact with:

- Ward attributes (D-WORLD-0002),
- Force types and infrastructure (D-MIL-0001),
- Alert levels and response cadences (D-MIL-0003),
- Guild hubs (D-IND-0003),
- Black market networks (D-ECON-0004),
- Rumor and informal channels (D-INFO-0006).

Goals:

- Provide a **ward-level garrison model** (indices and node types).
- Define **deployment zone archetypes** (outer ring, cores, hinges, chokepoints).
- Explain how garrison patterns:
  - Shape and respond to guild and cartel influence,
  - Affect unrest, rumor, and the likelihood of crackdowns,
  - Anchor agent occupations (troopers, officers, liaison roles).

This is a **logic document** for simulation and scenario design; it does not
prescribe a single canonical layout for all runs.

---

## 2. Relationship to Other MIL Documents

- **D-MIL-0001_Force_Types_and_Infrastructure**  
  - Defines military force categories (street troops, corridor troops,
    exo-cadres, investigators, etc.) and their infrastructure needs
    (barracks, exo-bays, armories, holding sites).

- **D-MIL-0003_Response_Cadences_and_Alert_Levels**  
  - Defines how the regime escalates from normal patrols to sweeps,
    curfews, and full crackdowns.

This document **slots between** them by answering:

- *Where* those forces are normally based,
- *Which wards* they can reach quickly,
- *What the default posture* looks like before and after alert changes.

---

## 3. Ward-Level Garrison Attributes

Each ward `w` extends its schema (D-WORLD-0002) with:

```yaml
garrison_presence: float        # 0–1, general thickness of troops and posts
checkpoint_density: float       # 0–1, frequency of corridor checkpoints
exo_bay_density: float          # 0–1, access to heavy suits and exo-cadres
reserve_capacity: float         # 0–1, ability to surge forces into or from this ward
militia_integration_score: float# 0–1, cooperation with local guilds/bishops
```

Interpretation:

- **garrison_presence**  
  - 0.0–0.2: Minimal permanent forces; occasional patrols only.  
  - 0.3–0.5: Regular patrols, small barracks, visible uniforms.  
  - 0.6–0.8: Heavy presence, multiple posts, frequent inspections.  
  - 0.9–1.0: Saturated; ward feels like a barracks with civilians attached.

- **checkpoint_density**  
  - How often corridors are broken by controlled crossings. High values make
    movement slow, predictable, and easy to monitor.

- **exo_bay_density**  
  - Availability of heavy exo-suits and mech support. High in industrial and
    outer-defense wards, lower in sealed cores.

- **reserve_capacity**  
  - Indicates whether this ward hosts **staging grounds** and logistics for
    moving troops to other wards (lift hubs, armored corridors, mustering yards).

- **militia_integration_score**  
  - High when militia cooperate with bishop_guild, guilds, and local elites.  
  - Low when militia are seen as occupiers or rival power.

These attributes are shaped by:

- Ward geography (outer ring vs core),
- Industry mix (`industry_weight`),
- Political importance (`dominant_owner`, presence of dukes, bishops),
- Threat history (recent unrest/incidents).

---

## 4. Deployment Zone Archetypes

While each scenario can define its own layout, we assume several **common
deployment archetypes**. A ward can mix traits from multiple archetypes.

### 4.1 Outer Ring Industrial Bastions

Characteristics:

- High `garrison_presence` (0.6–0.9),
- Medium–high `exo_bay_density`,
- Medium `checkpoint_density`,
- High `reserve_capacity` (staging areas for outward or inward operations),
- High `industry_weight` in FABRICATION, SUITS, ENERGY_MOTION.

Role:

- Guard high-risk industry and outer approaches.
- Serve as first-line response to external or large-scale threats.
- Host exo-cadres and artillery or heavy suppression tools where appropriate.

Tensions:

- Strong interactions with industrial guilds (D-IND-0003).
- Cartels may focus on smuggling parts and mods through these wards.
- Rumor and unrest often shaped by accidents, strikes, and safety disputes.

### 4.2 Inner Sealed Cores

Characteristics:

- Moderate `garrison_presence` (0.4–0.7) but **high capability** units,
- Lower `exo_bay_density` (space prioritized for governance and sealed systems),
- High `checkpoint_density` at **entry points**,
- High `militia_integration_score` with central_audit_guild and duke_house,
- Higher rates of sealed wards with controlled HVAC.

Role:

- Protect core governance, major data centers, and high-ranking nobles.
- Control traffic into and out of the administrative heart.

Tensions:

- Guild presence may be lower in raw capacity but higher in influence per unit
  (specialized SUITS/INFO guilds).
- Black markets focus on insider access, data leaks, and permits/identity games.

### 4.3 Hinge / Interface Wards

Characteristics:

- Moderate `garrison_presence`,
- Medium–high `checkpoint_density`,
- Medium `reserve_capacity`,
- High `corridor_centrality` in world schema (major transit corridors).

Role:

- Act as **funnels** between outer bastions and inner cores.
- Host layered checkpoints, inspection hubs, and swing forces that can flex
  to nearby wards.

Tensions:

- Favored ground for cartels to infiltrate or bribe checkpoints.
- Frequent focus of espionage branch activity (D-INFO-0002) watching flows.

### 4.4 Corridor Choke Wards

Characteristics:

- High `checkpoint_density`,
- Focused `garrison_presence` along key routes rather than broad saturation,
- Low–medium `exo_bay_density` (light, mobile units dominate).

Role:

- Control a small number of crucial corridors, lifts, or pressure doors.
- Serve as **gatekeepers** in the barrel cadence and logistics flows.

Tensions:

- Corridor vendors, clerks, and troopers are natural rumor and cartel hooks.
- Small shifts in discipline or corruption here have outsized effects.

### 4.5 Reserve / Overflow Wards

Characteristics:

- Low–medium `garrison_presence` in normal times,
- High `reserve_capacity` (spaces that can be rapidly converted to barracks),
- Often strong bishop_guild presence (bunkhouses, canteens).

Role:

- In peacetime: cheap habitation and civil services.  
- In crisis: quickly filled with troops and displaced civilians.

Tensions:

- Conversion to military use can **displace residents**, raising `unrest_index`.
- Bishops may negotiate hard to protect food/beds, clashing with militia needs.

---

## 5. Garrison Node Types

Within wards, garrison presence is realized as specific **node types**:

```yaml
GarrisonNode:
  id: string
  ward_id: string
  type: "barracks" | "checkpoint" | "exo_bay" | "rapid_response_hub" |
        "holding_site" | "liaison_post"
  capacity: int              # troops or suit slots
  readiness: float           # 0–1, how quickly it can deploy
  visibility: float          # 0–1, how obvious it is to residents
  integration_with_locals: float  # 0–1, cooperation vs hostility
```

### 5.1 Barracks

- House troops and support staff.
- Strong anchors for **local patrol patterns**.
- Nearby civic services (canteens, bunkhouses, clinics) see heavy trooper
  presence, affecting rumor and black market behavior.

### 5.2 Checkpoints

- Control corridors, lifts, and key doorways.  
- High-impact on:
  - travel time,
  - smuggling risk,
  - daily harassment/visibility of the regime.

### 5.3 Exo-Bays

- Specialized facilities for heavy suits, powered frames, or other major
  assets defined in D-MIL-0001.
- Usually clustered with FABRICATION and SUITS guild facilities.
- High-value targets for sabotage, theft, or covert “upgrades”.

### 5.4 Rapid Response Hubs

- Nodes optimized for **movement** rather than static control.
- Linked to high-capacity corridors or lift systems.
- Heavily referenced by D-MIL-0003 in higher alert levels.

### 5.5 Holding Sites

- Short-term detention, interrogation, and triage facilities.
- Influence local `rumor_fear_index` and `unrest_index` strongly, especially
  when abuse or disappearances are common.

### 5.6 Liaison Posts

- Small offices or desks embedded in civic or guild spaces:
  - in canteens, clinics, guild halls, large bunkhouses.
- Soft power presence; sometimes more effective than overt troops.

---

## 6. Interplay with Guilds and Cartels

### 6.1 With Industrial Guild Hubs (D-IND-0003)

Patterns:

- Wards where critical guilds are **GUILD_DOMINANT/HEGEMONIC** often see:
  - Higher `garrison_presence` *around* key facilities,
  - Liaison posts embedded in yards and workshops,
  - Exo-bays co-located with SUITS and FABRICATION guild assets.

- Where guilds and militia cooperate:
  - `militia_integration_score` rises,
  - Checkpoints may be lighter, with more guild self-policing.

- Where guilds and militia clash:
  - Checkpoint_density and holding_sites increase,
  - Risk of strikes and sabotage rises (D-IND-0003 guild levers).

### 6.2 With Cartels and Black Markets (D-ECON-0004)

Patterns:

- High `black_market_intensity` + high `checkpoint_density`:
  - Encourages corruption and side deals at checkpoints.
  - Creates shadow corridors where cartel control supplants formal control.

- Cartels may target:
  - Barracks supplies, weapons, and personal needs,
  - Holding sites (for rescues or silencing),
  - Liaison posts (to gain influence or information).

- Regime may respond by:
  - Increasing `detection_pressure(w)` (D-ECON-0004),
  - Shifting garrisons to break cartel circuits or protect specific wards.

### 6.3 With Bishop Guild and Civic Spaces

Bishop_guild infrastructure (canteens, bunkhouses, clinics) frequently sits:

- Adjacent to barracks and checkpoints,
- In reserve/overflow wards used to stage troops.

Result:

- Civic spaces become **mixed military-civil rumor hubs**.
- Bishops gain leverage as providers of food and beds to troops,
  and militia gain leverage as protectors or occupiers of civic spaces.

---

## 7. Hooks into Alert Levels and Incidents

Garrison structure shapes how the regime responds to incidents.

### 7.1 Baseline posture vs alert shifts

- At **ALERT_0 / ALERT_1** (from D-MIL-0003):
  - Patrol frequency and checkpoint strictness follow baseline `garrison_presence`
    and `checkpoint_density`.
  - Rapid response hubs operate at lower readiness.

- At **ALERT_2+**:
  - Reserve wards are activated, increasing effective `garrison_presence`
    in key zones.
  - Checkpoints tighten (more searches, longer delays).
  - Exo-bays push more suits into rotation.

### 7.2 Incident routing

Different incident types may **route** to different garrison structures:

- Industrial sabotage → outer bastions and guild-heavy wards.
- Cartel violence → hinge wards and corridor chokepoints.
- Political unrest → inner cores and high-symbolism wards.

The presence of nearby rapid response hubs and exo-bays reduces **response
time**, while absence of such nodes may force slower, improvised responses.

---

## 8. Agent-Level Implications

### 8.1 Occupations and daily contact

Certain occupations are strongly exposed to garrison patterns:

- `occ_corridor_vendor`, `occ_canteen_worker`, `occ_bunkhouse_steward` near
  checkpoints and barracks see frequent troop custom and harassment.
- `occ_exo_tech`, `occ_clandestine_modder` in exo-bay wards have direct
  access to high-grade military kit.
- `occ_ration_clerk`, `occ_audit_scribe` in interface wards constantly process
  movement and supply linked to garrisons.

These roles become **natural bridges** between militias, guilds, cartels, and
civil residents.

### 8.2 Drives and loyalties

Garrison saturation and integration shape agent drives:

- In heavily garrisoned wards:
  - Fear and dependence on militia rise.
  - Cartel involvement may either drop (due to risk) or become more deeply
    entangled (through corruption).

- In lightly garrisoned but high-risk wards:
  - Residents may look more to guilds, cartels, or bishops for security.
  - Rumors of "the militia never comes here unless it's to hurt someone"
    affect cooperation and intelligence quality.

---

## 9. Implementation Sketch (Non-Normative)

A minimal sim implementation could:

1. Define global **deployment patterns** for a scenario:
   - Outer, inner, hinge, choke, reserve tags per ward.

2. For each ward `w`, compute initial:
   - `garrison_presence`, `checkpoint_density`, `exo_bay_density`,
     `reserve_capacity`, `militia_integration_score` based on:
     - distance from core,
     - industry mix,
     - guild/cartel influence,
     - political importance.

3. Place **GarrisonNode** instances per ward according to archetypes.

4. On alert changes (D-MIL-0003):
   - Adjust posture (readiness, patrol frequency, checkpoint strictness).
   - Activate reserve wards as staging zones.

5. Let incidents and guild/cartel actions feed back into:
   - Node readiness (attacks, sabotage, bribes),
   - `militia_integration_score` (good/bad behavior),
   - Future deployment adjustments (shifting forces over longer arcs).

Exact formulas and thresholds are left to implementation; this document
provides the conceptual layout and key variables.

---

## 10. Future Extensions

Possible follow-ups:

- `D-MIL-0101_Checkpoint_Types_and_Search_Procedures`  
  - Detailed checkpoint behaviors, search intensities, and how they interface
    with smuggling and identity/permit systems.

- `D-MIL-0102_Barracks_Culture_and_Discipline_Profiles`  
  - How different garrison cultures alter corruption, brutality, and
    responsiveness.

- Integration with future LAW pillar:
  - How sanctions, curfews, and emergency decrees change deployment patterns
    and garrison legal authority.

---
title: Guild-Militia_Bargains_and_Side_Contracts
doc_id: D-IND-0105
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-WORLD-0003          # Ward_Evolution_and_Specialization_Dynamics
  - D-IND-0001            # Industry_Taxonomy_and_Types
  - D-IND-0002            # Industry_Suitability_and_Evolution
  - D-IND-0003            # Guild_Influence_and_Bargaining_Power
  - D-IND-0101            # Guild_Templates_and_Regional_Leagues
  - D-IND-0102            # Named_Guilds_and_Internal_Factions
  - D-IND-0103            # Guild_Charters_and_Obligations
  - D-IND-0104            # Guild_Strikes_Slowdowns_and_Sabotage_Plays
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-ECON-0004           # Black_Market_Networks
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-MIL-0002            # Garrison_Structure_and_Deployment_Zones
  - D-MIL-0003            # Response_Cadences_and_Alert_Levels
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 13_industry · Guild–Militia Bargains and Side Contracts (D-IND-0105)

## 1. Purpose

This document describes the **informal and semi-formal deals** struck between
industrial guilds and militia forces on Dosadi.

Where D-IND-0103 (Guild Charters and Obligations) covers the **official**
regime–guild relationship, this doc covers:

- **Off-ledger bargains** between guild leaders, militia officers, and
  garrison commanders,
- How these bargains:
  - shape enforcement (who gets searched, raided, or ignored),
  - bend charters and law in practice,
  - influence ward evolution and guild power,
- Typical **breach patterns** and how betrayals cascade through LAW, MIL, and
  rumor systems.

The focus is on **logic and patterns**, not exhaustive enumeration.

---

## 2. Relationship to Other Pillars

- **Industry & Guilds (D-IND-0001/0003/0101–0104)**  
  - Provides the industrial roles, guild families, internal factions,
    charters, and collective action plays that motivate bargains.

- **Military (D-MIL-0001/0002/0003)**  
  - Defines forces, garrisons, and alert levels; bargains are often struck at
    the level of **garrison commanders**, exo-bay chiefs, and corridor officers.

- **Law (D-LAW-0001–0003)**  
  - Officially determines sanctions and procedures; bargains partially
    decide **when those tools are actually used**.

- **World & Ward Evolution (D-WORLD-0002/0003)**  
  - Persistent bargains contribute to **ward specialization** and
    **shadow governance**.

- **Economy & Black Markets (D-ECON-0001/0004)**  
  - Many bargains involve side channels, skimming, or protection rackets.

- **Information & Rumor (D-INFO-0001/0003/0006)**  
  - Bargains depend on control of information and are fragile to leaks.

---

## 3. Conceptual Model: Bargain Objects

We model a bargain as a **relational object** between a guild (or faction)
and a militia node (garrison, unit, commander).

```yaml
GuildMilitiaBargain:
  id: string
  guild_family_id: string         # e.g. GF_SUITS_BRINE_CHAIN
  guild_faction_name: string | null
  militia_node_id: string         # e.g. garrison:ward:07, exo_bay:outer:03
  scope:
    wards:
      - ward_id
    facilities:
      - "yard:hook:12"
      - "exo_bay:outer:03"
  terms_guild_provides:
    - "priority_repairs_for_militia_exo"
    - "shadow_upgrades_for_select_units"
  terms_militia_provides:
    - "inspection_relief_for_guild_facilities"
    - "advance_warning_of_raids"
  secrecy_level: "whisper" | "cell" | "open_secret"
  stability_rating: float          # 0–1, how likely it is to endure
  breach_triggers:
    - "audit_probe_on_node"
    - "command_rotation"
    - "guild_strike_event"
  last_review_tick: int
```

Bargains may be:

- **Personal** (between a single officer and a faction),
- **Institutionalized** (passed on as a “tradition” within a garrison),
- **League-level norms** (shared practices across a cluster of wards).

---

## 4. Bargain Categories

### 4.1 Protection and Non-Interference

Guild provides:

- Efficient support to **militia needs** in its domain.
- Quiet favours (e.g. quick suit fixes, priority lift slots, extra food).

Militia provides:

- Reduced search and raid frequency at guild sites.
- “Blind spots” in patrol patterns.
- **Gentle handling** of guild members caught in minor offenses.

Effects:

- Lower effective `sanction_intensity` on guild-linked agents/facilities.
- Increased `impunity_index` as perceived by guild workers.
- Guild power consolidates within protected wards.

Risks:

- Attracts cartel interest (“you have protection; help us move things”).
- If exposed, likely triggers **Audit Commissions** and targeted LAW actions.

### 4.2 Priority Servicing and Uptime Guarantees

Guild (SUITS, ENERGY, FABRICATION) promises:

- **Preferential uptime** for militia infrastructure:
  - exo-bays, lifts to garrisons, corridor power.
- Accepts harsher conditions and cost overruns in militia-linked tasks.

Militia:

- Applies pressure on **other branches** (audits, dukes) to:
  - preserve guild charters,
  - deflect sanctions,
  - shield key staff from tribunals.

Effects:

- MIL readiness stays high even during guild slowdowns elsewhere.
- Guild draws resentment from:
  - rival guilds,
  - civilians seeing MIL lines kept running while their systems fail.

Risks:

- Over-reliance: if guild withdraws support, MIL is abruptly vulnerable.
- Political blowback when preferential treatment becomes too obvious.

### 4.3 Side Payment Channels and Skims

Guild:

- Skims off parts, food, or water in small percentages.
- Offers **unlogged upgrades**, “second-ration” deals, or hush payments.

Militia:

- Facilitates:
  - transit of skims through checkpoints,
  - storage in nominally secure MIL areas,
  - resale or redistribution via trusted NCOs.

Effects:

- Raises `black_market_intensity(w)` especially near garrisons.
- Creates **loyalty circuits**:
  - certain militia units become financially tied to specific guild factions.

Risks:

- Telemetry anomalies (D-INFO-0001) or Quiet Ledger investigations expose
  mismatches.
- Factional infighting when skims are unevenly distributed.

### 4.4 Intelligence and Deniability Deals

Guild:

- Provides **situational awareness**:
  - workers overhear things in canteens, yards, lifts, and bunkhouses.
- Acts as an early warning system for:
  - strikes,
  - cartel moves,
  - Bishop or Quiet Ledger agitation.

Militia:

- Turns a blind eye to:
  - minor charter drift,
  - shadow production,
  - certain guild-side collective actions (if they don’t threaten MIL).

Effects:

- Shifts INFO flows:
  - militia gains more **unofficial** sources,
  - central_audit_guild may be sidelined or deceived.
- Guild becomes a **broker** of rumor, choosing which narratives to share.

Risks:

- If multiple branches compete for guild intel (MIL vs audits vs dukes),
  guild may be accused of double-dealing.
- Cartel infiltration in guild info channels can **poison** MIL decision-making.

### 4.5 Strike Management and “Controlled Burn” Deals

Guild:

- Promises to:
  - limit strikes to symbolic stoppages,
  - keep sabotage below certain thresholds,
  - restrain dissident factions.

Militia:

- Promises to:
  - avoid lethal crackdowns,
  - advocate for modest charter concessions,
  - keep Security Tribunals out unless absolutely forced.

Effects:

- Creates a pattern of **ritualized conflict**:
  - predictable strikes,
  - staged concessions,
  - a sense of “everyone knows their lines.”

- Helps maintain ward **equilibria**:
  - guild power, law severity, and MIL posture remain in a low-level tension.

Risks:

- Radical factions (Burnhands, Shadowscript, etc.) may reject the script.
- Regime hardliners may see these deals as weakness and intervene.

---

## 5. Spatial Patterns of Bargains

### 5.1 Outer Industrial Bastions

- High exposure to accidents and sabotage; MIL needs guild cooperation.
- Bargains skew toward:
  - **uptime guarantees** (exo-bays, barrel hardware),
  - **non-interference** with guild-controlled strikes if they avoid MIL assets.

Typical example:

- Yardhook Rigbosses cut a deal with local garrison: in exchange for
  protecting garrison supply lines, MIL focuses crackdowns on unaffiliated
  scavs instead of guild yards.

### 5.2 Hinge and Lift Ring Wards

- Strategic transit points: lifts, condensate branches, corridor choke points.
- Bargains emphasize:
  - **priority routing** of MIL and ducal traffic,
  - **selective blockage** of undesired flows (rebels, suspected agitators).

Typical example:

- Lift Crown Schedulers promise that “no duke will ever be stuck in a shaft”
  in exchange for MIL suppressing audit inspections of lift maintenance logs.

### 5.3 Civic Feed and Bishop-Dense Wards

- Heavy overlap between FOOD, WATER, and bishop_guild spaces.
- Bargains often triadic: guild–MIL–bishop.

Patterns:

- MIL tolerates bishop-led “calming” of unrest in canteens and bunks,
  while bishops pressure FOOD/WATER guilds to avoid pushing people into
  open revolt.

Typical example:

- Vat Chain Feeders quietly overfeed militia-friendly wards before a crackdown.
- MIL ensures bishops and Vat Chain avoid the harshest sanctions afterward.

### 5.4 Shadow Wards

- Weak formal guild power; cartels and shadow guilds dominate.
- MIL–guild bargains are fragile and often mediated by cartels.

Patterns:

- MIL units might:
  - accept bribes for **corridor access** or **targeted blindness**,
  - rely on shadow guilds for intelligence on cartel rivals.

Risks:

- High chance of contamination:
  - MIL units drift toward cartel loyalties,
  - state authority hollowed out behind uniforms.

---

## 6. Example Bargain Archetypes (Non-Normative)

### 6.1 “Steel Lungs Pact” – Brine Chain & Outer Garrison

- Parties:
  - Guild: Brine Chain Fabricators (Gaugecutters + Linekeepers).
  - MIL: garrison:outer:12 exo-bay command.

- Terms:
  - Guild:
    - guarantees fast turnaround on exo repairs,
    - installs slightly overclocked environmental systems for select units.
  - MIL:
    - flags Brine Chain workshops as “low priority” for routine inspections,
    - tips Gaugecutters when central_audit_guild plans surprise visits.

- Effects:
  - Outer ward garrison is unusually effective.
  - Brine Chain’s shadow mods spread among favored squads.
  - Rumor: “Exo crews with Steel Lungs walk where others choke.”

### 6.2 “Kept Yard Accord” – Yardhook & Corridor Patrols

- Parties:
  - Guild: Yardhook Assembly (Rigbosses).
  - MIL: corridor patrol command for barrel routes through the ward.

- Terms:
  - Guild:
    - minimizes uncontrolled “accidents” on barrel lines,
    - ensures rapid crane response for MIL logistics.
  - MIL:
    - focuses enforcement on non-guild scavs,
    - avoids heavy presence inside yard perimeters.

- Effects:
  - Yard becomes a **de facto micro-fief** of Yardhook.
  - Scavs and unaffiliated workers are pushed into more dangerous tacit zones.
  - Shadow recruitment for Burnhands thrives in neglected corners.

### 6.3 “Quiet Shaft Understanding” – Lift Crown & MIL Transit

- Parties:
  - Guild: Lift Crown Syndicate (Schedulers + Spanners).
  - MIL: transit oversight for a Lift Ring League segment.

- Terms:
  - Guild:
    - reserves emergency lift capacity for MIL units even during strikes.
    - ensures MIL routes remain safest (fewest failures).
  - MIL:
    - supports Lift Crown in charter renegotiations,
    - uses force against rival guild cells trying to break Lift Crown monopoly.

- Effects:
  - Lift Crown effectively “owns” movement in the region.
  - Civilian resentment grows as MIL glides while they climb dead stairs.
  - Rumor: “Shafts kneel to the Crown, not to the dukes.”

---

## 7. Breach and Betrayal Dynamics

### 7.1 Guild-side breach

- Causes:
  - Hardline faction seizes control (Burnhands, Ghostfitters, Skimmers).
  - Cartel pressure forces more aggressive shadow use.
  - Perceived MIL betrayal or failure to deliver promised protection.

- Consequences:
  - Sudden strikes, slowdowns, or sabotage targeting MIL assets.
  - MIL retaliation:
    - raids on guild facilities,
    - pushing for charter revocation,
    - calling in Security Tribunals.

- Ward-level effects:
  - Spikes in `sanction_intensity(w)`, `rumor_fear_index(w)`.
  - Potential shift of wards from industrial equilibria toward Shadow conditions.

### 7.2 Militia-side breach

- Causes:
  - Command rotation brings in a more doctrinaire officer.
  - Central directives prohibit existing bargains.
  - MIL decides guild is “too big” and must be cut down.

- Consequences:
  - Surprise inspections and raids,
  - Public arrests of previously protected guild figures,
  - Abrupt enforcement of long-ignored charter clauses.

- Guild responses:
  - Escalation to high-impact plays:
    - sabotage of MIL routes,
    - revelations of MIL corruption via Quiet Ledgers,
    - appeals to dukes or bishops.

### 7.3 Leak and exposure

- Any bargain is vulnerable to:
  - audit investigations,
  - Shadowscript leaks,
  - cartel manipulation.

Key patterns:

- Exposure can be:
  - weaponized by rival guilds (“look how corrupt they are”),
  - used by regime hardliners to justify crackdowns,
  - turned into **martyr stories** if crackdowns are brutal.

---

## 8. Implementation Sketch (Non-Normative)

A minimal sim integration:

1. For each ward and key guild–MIL pair, optionally instantiate
   `GuildMilitiaBargain` objects based on archetypes and scenario needs.

2. On relevant triggers (sanctions, accidents, charters up for review,
   command rotations, rumor spikes), evaluate:

   - whether new bargains are proposed,
   - whether existing bargains are strengthened, modified, or broken.

3. When active bargains exist, modify:

   - MIL enforcement pattern:
     - lower search/raid probability on protected guild facilities,
     - bias case-routing away from harsh LAW paths for guild-aligned agents.
   - Guild behavior:
     - lower probability of the harshest sabotage plays targeting MIL,
     - higher probability of cartel-linked side flows.

4. When bargains are breached or exposed:

   - Spawn events:
     - raids, strikes, tribunals, charters revoked or reassigned.
   - Adjust:
     - `G_power[w][guild_family]`,
     - `garrison_presence(w)` and alert/legal states,
     - rumor templates emphasizing betrayal, corruption, or heroic defiance.

5. Log bargain events for narrative/UI layers:

   - e.g. “Kept Yard Accord broken in Ward 17,”
   - which can seed new scenario hooks and player/agent choices.

---

## 9. Future Extensions

Potential follow-ups:

- `D-ECON-0102_Strike_Funds_and_Mutual_Aid_Pools`
  - Economic underpinnings enabling guilds to endure long conflicts with MIL.

- `D-MIL-0102_Officer_Doctrines_and_Patronage_Networks`
  - Different MIL cultures (hardline vs patronage-oriented) and how they
    shape bargain frequency and form.

- Scenario-specific bargain maps
  - Prebuilt sets of bargains and fault lines for arcs like:
    - pre-Sting Wave tensions in Industrial Spine,
    - famine-era Civic Feed leagues where FOOD–MIL–bishop triangles
      decide who starves.

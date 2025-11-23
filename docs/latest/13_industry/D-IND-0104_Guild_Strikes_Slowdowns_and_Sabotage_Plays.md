---
title: Guild_Strikes_Slowdowns_and_Sabotage_Plays
doc_id: D-IND-0104
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
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-ECON-0004           # Black_Market_Networks
  - D-MIL-0002            # Garrison_Structure_and_Deployment_Zones
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 13_industry · Guild Strikes, Slowdowns, and Sabotage Plays (D-IND-0104)

## 1. Purpose

This document catalogs **collective action plays** available to industrial guilds
on Dosadi:

- Strikes, slowdowns, and work-to-rule campaigns,
- Quota games and “creative compliance,”
- Technical sabotage and engineered accidents.

It connects these plays to:

- Guild archetypes and families (D-IND-0101, D-IND-0102),
- Charters and obligations (D-IND-0103),
- Ward evolution and specialization (D-WORLD-0003),
- Legal and military responses (D-LAW-*, D-MIL-0002),
- Rumor and black market dynamics (D-INFO-0006, D-ECON-0004).

The goal is to give scenarios and simulation code a **library of moves** that
guilds can deploy in pursuit of leverage, survival, or revenge, and to describe
their typical consequences.

---

## 2. Action Taxonomy

We classify guild actions along three axes:

- **Visibility**
  - overt (everyone knows),
  - deniable (plausible accident),
  - covert (intended to be invisible).
- **Scope**
  - local (specific shop, corridor, or facility),
  - ward-level,
  - regional / league-level.
- **Escalation Level**
  - low (symbolic, reversible),
  - medium (disruptive),
  - high (system-threatening).

Core types:

1. **Symbolic strikes and stoppages**  
   - Visible, time-bound halts to send a message.

2. **Slowdowns and work-to-rule**  
   - Technical compliance while slashing throughput.

3. **Quota games and shadow throughput**  
   - Undershooting or overshooting charters in selective ways.

4. **Technical sabotage and accidents**  
   - Failures engineered for leverage or punishment.

5. **Shadow production and diversion**  
   - Building a parallel economy beneath charter metrics.

6. **Information plays**  
   - Selective leaks, misreports, or record manipulation.

Each type can be flavored and parameterized per guild family and faction.

---

## 3. Symbolic Strikes and Stoppages

### 3.1 Description

Overt, time-limited refusal to work or to perform key tasks, often accompanied
by slogans, banners, or mass gatherings in visible spaces (yards, lifts,
canteens).

Examples:

- Yardhook Assembly crews down tools and occupy crane gantries.
- Vat Chain tank crews refuse to serve rations for a watch.
- Lift Crown operators halt non-emergency lifts.

### 3.2 Mechanical hooks

- **Visibility:** high. Immediate change in ward-level:
  - `unrest_index(w)` (up),
  - `rumor_density(w)` (up),
  - `tribunal_frequency(w)` (may rise in response).

- **Short-term effects:**
  - Drop in `industry_intensity[w][I]` for affected industries.
  - Potential delays in barrel cadence and troop movement.

- **Long-term effects depend on outcome:**
  - Successful strike (concessions granted):
    - `G_power[w][guild_family]` increases,
    - Charters revised favorably,
    - Imitation attempts in other wards.
  - Crushed strike:
    - loss of guild power,
    - increased `sanction_intensity(w)` and `impunity_index(w)`,
    - possible growth in cartel recruitment among the defeated.

### 3.3 Likely responses

- **LAW:**
  - Procedural path: Administrative Handling → Guild Arbitration → Audit Review
    or Security Tribunal if seen as political.
  - Sanctions: ration cuts, targeted arrests, charter threats.

- **MIL:**
  - Enhanced garrison presence in yards and civic spaces.
  - Curfews and emergency decrees focused on assembly controls.

---

## 4. Slowdowns and Work-to-Rule

### 4.1 Description

Workers follow rules **exactly as written**, or add “safety checks,” “QA
steps,” and documentation tasks, leading to slower work without outright
declaring a strike.

Examples:

- Brine Chain Linekeepers triple-check suit seals before release.
- Stillwater Balancers insist on multi-step calibration before opening valves.
- Quiet Ledger Balancers demand full cross-checks on every shipment.

### 4.2 Mechanical hooks

- **Visibility:** medium. Often noticed first as “mysterious inefficiency.”
- **Effects:**
  - Gradual reduction in effective `industry_intensity[w][I]`.
  - Increase in `case_backlog(w)` if tied to clerical processes.
  - Possible uptick in `legal_opacity(w)` as rules feel weaponized.

- **Advantages for guilds:**
  - Plausible deniability: hard to prove deliberate sabotage.
  - Opportunity to frame slowdowns as compliance with **charter safety
    clauses** or emergency procedures.

### 4.3 Likely responses

- **LAW:**
  - Administrative investigations and Audit Reviews examining “efficiency.”
  - Potential charter revisions narrowing guild discretion.

- **MIL:**
  - Pressure on guilds to prioritize military or core-facing tasks.
  - Threat of declaring local emergencies or martial states to override
    work-to-rule actions.

---

## 5. Quota Games and Shadow Throughput

### 5.1 Description

Manipulating production and reporting to:

- Meet charters **on paper** while shifting real output,
- Over-deliver selectively to favored clients,
- Underdeliver to pressure the regime or rivals.

Examples:

- Lift Crown Schedulers meet uptime quotas on paper while subtly biasing
  lift access away from disfavored wards.
- Vat Chain Counters massage numbers to hide quiet overfeeds to starving
  wards or black markets.
- Yardhook Ledgerhooks under-report actual throughput to skim parts.

### 5.2 Mechanical hooks

- **Visibility:** low to medium; primarily shows up in telemetry and audits.
- **Effects:**
  - Mismatch between:
    - recorded vs experienced shortages,
    - expected vs observed MIL readiness.
  - Drives Audit Commissions and info-conflicts (D-INFO-0001/0003).

### 5.3 Likely responses

- **LAW:**
  - If discovered: Audit Review → sanctions on guild leadership, charter
    renegotiations, potential tribunal cases for “economic sabotage.”
- **WORLD:**
  - Gradual ward evolution as “favored” wards feel buffered and “unfavored”
    wards drift toward Shadow or unrest attractors.
- **ECON:**
  - Black markets exploit and amplify these imbalances, offering
    “true quotas for the right price.”

---

## 6. Technical Sabotage and Engineered Accidents

### 6.1 Description

Deliberate creation of faults, breakdowns, or disasters framed as accidents:

- Overstressing lifts to fail at symbolic moments.
- Loosening suit fittings or skipping safety steps for particular units.
- Introducing contaminants into food or condensate systems.

### 6.2 Mechanical hooks

- **Visibility:** medium to high once accidents occur, but intent may be hidden.
- **Effects:**
  - Sudden dips in `industry_intensity[w][I]`.
  - Spikes in:
    - `rumor_fear_index(w)`,
    - `unrest_index(w)`,
    - MIL and LAW presence.

- **Risk:**
  - If sabotage is traced to guild factions:
    - severe sanctions,
    - charters revoked or transferred,
    - Security Tribunals and martial states likely.

### 6.3 Typical guild motivations

- Retaliation for sanctions or broken promises.
- Preemptive moves in guild-vs-guild competition.
- Coerced actions under cartel or rebel pressure.

---

## 7. Shadow Production and Diversion

### 7.1 Description

Running parallel lines, off-book vats, or hidden repair bays:

- Producing extra food, suits, or parts for cartels, rebels, or favored wards.
- Diverting waste streams into profitable “side industries.”
- Refurbishing condemned gear for black market sale.

### 7.2 Mechanical hooks

- **Visibility:** low; emerges as rumors and unexplained secondary markets.
- **Effects:**
  - Raises `black_market_intensity(w)` and cartel leverage.
  - May partially buffer wards from sanctions and shortages.
  - Increases risk of catastrophic failures if quality is poor.

### 7.3 Responses

- **INFO/Law:**
  - Investigations triggered by rumor or telemetry anomalies.
  - If discovered: seizure of facilities, mass sanctions on guild members,
    potential co-optation of shadow lines into “legitimate” operations.

- **WORLD:**
  - Shadow-heavy wards tend toward Shadow League patterns, with state law
    replaced by guild/cartel hybrid rulesets.

---

## 8. Information Plays

### 8.1 Description

Using data and narrative rather than machines:

- Quiet Ledger Redactors selectively “lose” sanction records or quotas.
- Shadowscript factions leak internal reports to cartels, bishops, or rebels.
- SUITS or WATER guilds circulate rumors about rival unreliability or danger.

### 8.2 Mechanical hooks

- **Visibility:** varies; sometimes visible as pamphlets, sometimes only as
  shifts in indices.
- **Effects:**
  - Changes in `report_credibility`, `rumor_density`, and `procedure_alignment`.
  - Can shift LAW procedure patterns:
    - pushing cases toward Audit or Tribunal,
    - undermining certain forums’ legitimacy.

- **Opportunities:**
  - Guilds may use info plays to:
    - pre-empt harsher sanctions,
    - frame accidents as inevitable or someone else’s fault,
    - build public support or fear.

---

## 9. Factional Preferences by Guild Family

Using D-IND-0102 families, we can sketch who favors which plays:

- **Brine Chain Gaugecutters**
  - Strong on: slowdowns, quota games, shadow production tied to cartels.
- **Golden Mask Ghostfitters**
  - Strong on: shadow production (elite-only mods), information plays (masking
    telemetry).
- **Stillwater Skimmers**
  - Strong on: quota games (flow differentials), shadow production (secret taps).
- **Vat Chain Feeders**
  - Strong on: symbolic stoppages (canteen closures), shadow overfeeding.
- **Lift Crown Spanners**
  - Strong on: technical sabotage and accidents involving lifts/energy.
- **Yardhook Burnhands**
  - Strong on: overt strikes, violent sabotage framed as “inevitable accidents.”
- **Quiet Ledger Redactors**
  - Strong on: information plays, quota games, erasures.

Scenarios can weight these preferences when choosing guild reactions to
sanctions or incidents.

---

## 10. Interaction with Charters, Law, and MIL

### 10.1 Charters as framing devices

Guild actions are often defended as:

- “Operating within charter safety clauses,”
- “Exercising the right to halt unsafe work,”
- “Temporary deviation under emergency strain.”

D-IND-0103 charters give the **language and clauses** that factional leaders
invoke, while LAW documents describe how those arguments fare.

### 10.2 Law and procedural consequences

Per D-LAW-0001/0002/0003:

- Low-visibility plays may stay within:
  - Administrative Handling,
  - Guild Arbitration.

- High-visibility or high-damage plays escalate to:
  - Audit Commissions,
  - Security Tribunals,
  - emergency decrees or martial states in affected wards.

This feedback loop is central to ward evolution (D-WORLD-0003):

- Repeated harsh responses can push wards into Shadow or Bastion attractors.
- Successful guild plays without heavy sanction solidify guild power
  and specialization.

### 10.3 MIL responses

D-MIL-0002/0003 define:

- How garrisons reorganize around troublesome wards,
- Use of:
  - increased checkpoint density,
  - curfews,
  - targeted raids on guild facilities.

Guilds anticipate this and pick plays accordingly:

- Shadow production in low-garrison Shadow wards,
- Symbolic stoppages where bishop or popular support is strong,
- Quiet slowdowns in heavily garrisoned Industrial Spine wards.

---

## 11. Implementation Sketch (Non-Normative)

A minimal simulation approach:

1. For each guild family and faction, define a **playbook**:

```yaml
GuildFactionPlaybook:
  id: "GF_SUITS_BRINE_CHAIN::Gaugecutters"
  preferred_plays:
    - "slowdown"
    - "quota_game"
    - "shadow_production"
  risk_tolerance: float
  martyrdom_taste: float
  cartel_entanglement: float
```

2. At macro-steps or in response to triggers (sanctions, charter threats,
   shortages), factions evaluate:

- Expected benefits (charter concessions, power gains, relief),
- Expected risks (sanctions, revocation, MIL crackdown).

3. The sim selects plays and applies:

- Immediate effects on industry, law, MIL, and ward indices,
- Case creation and routing events in LAW,
- Rumor generation events in INFO.

4. Outcomes of plays (success, suppression, co-optation) feed back into:

- Guild power indices `G_power[w][F]`,
- Charter lifecycle events,
- Future playbook adjustments (factions become bolder or more cautious).

---

## 12. Future Extensions

Potential follow-ups:

- `D-IND-0105_Guild-Militia_Bargains_and_Side_Contracts`
  - How guilds and MIL cut deals to soften or weaponize guild actions.

- `D-ECON-0102_Strike_Funds_and_Mutual_Aid_Pools`
  - Economic mechanics behind sustained guild resistance.

- Scenario-specific playbooks
  - Pre-tuned guild action sets for particular arcs (e.g. “Pre-uprising
    Industrial Spine,” “Famine-era Civic Feed League”).

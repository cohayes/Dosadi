---
title: Black_Market_Networks
doc_id: D-ECON-0004
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-22
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-IND-0001            # Industry_Taxonomy_and_Types
  - D-IND-0002            # Industry_Suitability_and_Evolution
  - D-IND-0003            # Guild_Influence_and_Bargaining_Power
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-MIL-0003            # Response_Cadences_and_Alert_Levels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 12_economy · Black Market Networks (D-ECON-0004)

## 1. Purpose

This document defines the **structure and logic of black market networks** on
Dosadi, with a focus on:

- How cartels operate as a **shadow economic and intelligence branch**,
- How they exploit or mirror official logistics (water cadence, corridors,
  guild flows),
- How their presence is represented in ward-level attributes and agent roles,
- How they interact with guilds, nobles, civic stewards, and the military.

It provides a **mechanical backbone** for:

- Smuggling, contraband, off-ledger trade,
- Informal protection and coercion,
- Information liquidity (who knows what, where, and how quickly).

---

## 2. Core Concepts

### 2.1 Cartels and black market cells

For this document, **cartel** is an umbrella for:

- Organized groups that run **unofficial flows** of goods, services, and
  information, parallel to or parasitic on official systems.
- Structures ranging from:
  - Ward-scale crews (“the folks who run the night market”),
  - Up to multi-ward networks with internal hierarchy and specialization.

We model them as overlapping layers:

- **Cells** – local operational units anchored in a ward or corridor segment.
- **Circuits** – smuggling routes and information channels that link cells.
- **Syndicates** – higher-level structures coordinating pricing, territory,
  and relationships with nobles, guilds, and militia.

### 2.2 Shadow vs official flows

Cartel networks rarely build entirely new infrastructure; they:

- **Ride on top of official flows** (water cadence, ration distribution,
  guild logistics, bunkhouse and canteen supply).
- Exploit **knowledge gaps** between what is recorded (central_audit_guild)
  and what actually moves (handlers, clerks, stewards).

This document focuses on how to represent:

- Where black market activity is **dense**,
- Which official roles and routes are **captured**,
- How quickly **rumors, orders, and goods** move along shadow circuits.

---

## 3. Ward-Level Black Market Attributes

We extend and refine the existing `black_market_intensity` (D-WORLD-0002).

For each ward `w` we define:

```yaml
black_market_intensity: float     # 0–1, density of illicit flows vs official
black_market_visibility: float    # 0–1, how obvious activity is to ordinary people
black_market_capture_officials: float # 0–1, degree of co-opted officials
black_market_specialization:      # main shadows in this ward
  - "water_skimming"
  - "suit_modding"
  - "meds_and_drugs"
  - "weapon_supply"
  - "identity_docs"
  - "intel_brokerage"
```

Interpretation:

- **Intensity** – “How much business runs through the shadows?”  
  High values: black channels rival or exceed official ones.

- **Visibility** – “How in-your-face is it?”  
  - Low visibility + high intensity → quiet, disciplined networks.
  - High visibility + high intensity → open markets, tolerated or feared.

- **Capture of officials** – degree to which:
  - Ration clerks, barrel handlers, troopers, bishops’ stewards, etc.
    are on cartel payroll or under coercion.
  - High values indicate that **formal crackdown efforts are likely to leak**.

- **Specialization** – which categories dominate; helps scenario authoring and
  AI behavior (what goods/rumors can be found here?).

These values are **not** static; they evolve based on regime pressure,
guild influence (D-IND-0003), and successful/failed operations.

---

## 4. Cartel Structure: Cells, Circuits, Syndicates

### 4.1 Cells

A **cell** is a small, semi-autonomous unit operating in one ward or a few
adjacent corridors.

Schema (conceptual):

```yaml
cell_id: string
home_ward: string     # ward_id
territory_wards:
  - string
domains:              # shadows they specialize in
  - "water_skimming"
  - "suit_modding"
links_to_guilds:      # which industry guilds they parasitize or partner with
  - "SUITS"
  - "SCRAP_MATERIALS"
links_to_branches:    # high-level branches they lean on
  nobles: float       # 0–1 patronage
  militia: float      # 0–1 collusion
  bishop_guild: float # 0–1 quiet arrangements
  central_audit: float# 0–1 infiltration
  cartel_syndicate: float # 0–1 obedience to wider cartel structures
discipline: float     # 0–1, willingness to obey higher orders vs go freelance
```

Cells are where most **agent-level roles** live:

- `occ_cadence_smuggler`
- `occ_clandestine_modder`
- Street-level enforcers on cartel payroll,
- Corridor vendors and bunkhouse stewards acting as lookouts or brokers.

### 4.2 Circuits

A **circuit** is a **route** (physical or informational) that connects cells.

Conceptual attributes:

```yaml
circuit_id: string
type: "physical" | "informational"
nodes:          # ordered list of wards / junctions
  - ward: "ward:03"
  - ward: "ward:07"
  - ward: "ward:12"
capacity_index: float   # 0–1, how much can be moved per unit time
stealth_index: float    # 0–1, how hard to detect
resilience_index: float # 0–1, how easy to reroute after disruption
dominating_cells:
  - cell_id
```

- Physical circuits correspond to **hidden or tolerated routes**:
  - Back corridors, service shafts, unmonitored lifts,
  - “Protected” segments where corrupted troopers look away.

- Informational circuits are **gossip paths**, signal relays, or courier chains.

These circuits tie into **response time and detection** in D-MIL-0003:
- High stealth routes → slower detection, lower incident weights.
- High capacity routes → can flood a ward with goods or fighters quickly.

### 4.3 Syndicates

A **syndicate** coordinates policy across many cells and circuits.

Attributes:

```yaml
syndicate_id: string
influence_region:
  - ward_id
stance_toward_branches:
  duke_house: "hostile" | "neutral" | "ally_in_practice"
  militia:    "avoid" | "infiltrate" | "partner"
  bishop_guild: "protect_clients" | "exploit" | "capture"
  central_audit: "subvert" | "evade"
  industry_guilds: "partner" | "coerce" | "replace"
trade_focus:
  - "water_skimming"
  - "weapon_supply"
  - "suit_modding"
discipline_doctrine: "loose_federation" | "tight_command"
```

Syndicates are where **large-scale moves** originate:
- Region-wide price shocks,
- Coordinated strikes in tandem with guilds,
- Traitor deals with nobles or militia commanders.

---

## 5. Black Market Actions & Effects

We define standard **black market actions** that AI/cartel logic can choose,
with predictable hooks into ward attributes and incident streams.

### 5.1 Routine operations

- **Incremental skimming** (water, rations, parts):
  - Slight reductions in effective `water_quota`, `food_buffer`, or
    industry outputs in affected wards.
  - Typically raise `black_market_intensity` and `capture_officials` slowly.

- **Shadow credit/tab systems**:
  - Cartel extends informal credit to agents or wards.
  - Increases dependence and future leverage, may reduce unrest in the short
    term while increasing long-term volatility.

### 5.2 Surges and dumps

- **Flood a ward with goods** (food, meds, weapons, suits):
  - Temporarily lowers `shortage_index(w)`,
  - Raises `black_market_visibility`,
  - May reduce `unrest_index(w)` or re-target it (gratitude/fear toward cartel).

- **Withhold goods** to punish a ward or faction:
  - Raises `shortage_index(w)`,
  - Can fuel anti-regime sentiment or turn people against rival guilds.

These behaviors are especially common where cartel and guild interests diverge.

### 5.3 Targeted favors and “insurance”

Cartels often provide **selective help**:

- Safe passage along circuits for specific agents or cargos,
- Quiet medical aid via street medics,
- Suit mods or exo maintenance for favored clients.

Mechanically:

- Modify specific agents’ **risk calculations** (they feel safer moving),
- Grant **temporary bonuses** to certain operations,
- Increase recipients’ **loyalty_pressure** toward cartel in their drives.

### 5.4 Coercion and enforcement

- **Shakedowns** of vendors, stewards, or clerks:
  - Extract resources or information,
  - Increase `black_market_capture_officials`.

- **Targeted intimidation or violence**:
  - Incidents like ASSASSINATION_ATTEMPT, SHOP_TORCHED, CLINIC_RAID,
    feeding directly into the incident system of D-MIL-0003.

This can provoke:

- Increased `audit_intensity`,
- Shifts in `alert_level(w)`,
- Retaliation by guilds or militia.

---

## 6. Interaction with Guilds and Branches

### 6.1 With Industrial Guilds (D-IND-0003)

Relationships range from:

- **Partner** – black market moves excess production, bypasses taxes, finds
  buyers for “too good” parts or rejected batches.
- **Parasite** – cartel skims from guild flows without permission, corrupting
  handlers and clerks.
- **Rival** – guild builds its own grey channels and tries to push out cartel
  intermediaries.

We can express a simple stance per `(guild_family, ward)`:

```yaml
guild_cartel_stance:
  SUITS: "partner"
  FABRICATION: "rival"
  FOOD_BIOMASS: "parasite"
```

Stance modifies:

- `protection_factor_F(w)` in guild power (D-IND-0003),
- Likelihood of joint actions (e.g. guild strike + cartel withholding).

### 6.2 With Nobles and Militia

- **Nobles (`duke_house`)**:
  - May tolerate cartel operations that keep certain wards “quiet”,
  - May secretly use cartels to bypass their own audit structures.

- **Militia**:
  - May run **protection rackets** through cartel fronts,
  - Sometimes receive off-book pay, weapons, or intel,
  - At other times tasked with cartel suppression.

We can track per-ward:

```yaml
cartel_branch_alignment:
  duke_house: float     # 0–1
  militia: float
  bishop_guild: float
  central_audit: float  # usually low; infiltration rather than alignment
```

High alignment with militia and nobles often means:

- Higher **impunity** (low risk of raids),
- But also **higher stakes** if a political shift targets the cartel as scapegoat.

### 6.3 With Bishop Guild (Civic Stewards)

Cartels and bishop_guild share concern for:

- Food, shelter, basic survival infrastructure—just with different priorities.

Common patterns:

- Cartel supplies bunkhouses and canteens when official flows fail,
- Bishop guild quietly tolerates markets that keep people from starving,
- But conflict arises when cartel violence or exploitation undercuts civic goals.

Mechanically, bishop-collaboration may:

- Boost `food_buffer` or `habitation` resilience,
- While raising `black_market_intensity` and blurring lines of authority.

---

## 7. Detection, Audits, and Rumor

### 7.1 Detection pressure

Central_audit_guild and militia generate **detection pressure** on black markets.

A conceptual formula for ward `w`:

```text
detection_pressure(w) ≈
    γ1 * audit_intensity(w)
  + γ2 * INFO_ADMIN_weight(w)
  + γ3 * (alert_level(w) > ALERT_1_TENSE)
```

This interacts with:

- `black_market_visibility(w)`,
- `black_market_intensity(w)`,
- `black_market_capture_officials(w)` (captured officials reduce effective pressure).

High detection pressure + high visibility → frequent seizures and arrests, but
also more **incidents** and potential for escalation.

### 7.2 Rumor channels

Cartel circuits are also **rumor networks**:

- Canteen workers, bunkhouse stewards, corridor vendors, and street medics
  all act as **sensor nodes**.
- Cartel can often learn about:
  - Imminent raids,
  - Shifts in alert level,
  - Guild strikes or concessions,
  - Personal vulnerabilities of notable agents.

Simulation can grant cartel-linked agents:

- Higher chance to **overhear** key events,
- Faster **propagation** of select information between wards on the same circuit.

This plugs directly into any future **rumor/infosec pillar**.

---

## 8. Hooks into Agent Design

Black market networks matter most at the **agent** level.

### 8.1 Occupations with cartel hooks

Many occupations defined in D-AGENT-0101 naturally interface with cartels:

- `occ_cadence_smuggler` – direct cartel-employed role,
- `occ_clandestine_modder` – elite technical role,
- `occ_corridor_vendor` – soft interface/eyes-and-ears,
- `occ_bunkhouse_steward`, `occ_canteen_worker`, `occ_street_medic` –
  potential informants or protected clients.

For each such occupation, scenarios can specify:

```yaml
cartel_integration_level: "none" | "occasional_client" | "regular_asset" | "full_member"
```

Which modifies:

- Loot/earnings profile,
- Risk profile (legal vs physical),
- Drive hooks (“debts to cartel”, “family protection”, etc.).

### 8.2 Personal credit and leverage

Cartels maintain **informal ledgers** on individuals:

- Debts (water, meds, suit repairs),
- Favors owed,
- Secrets known.

Mechanically, each relevant agent may have:

```yaml
cartel_debt_index: float    # 0–1
cartel_trust_index: float   # 0–1
```

These indices:

- Influence whether cartel offers help or demands favors,
- Change how risky it is for an agent to defect or inform for other branches.

---

## 9. Implementation Sketch (Non-Normative)

A minimal loop for integrating black markets into the sim:

1. Initialize `black_market_intensity`, `visibility`, `capture_officials` per ward,
   plus initial cells and circuits where relevant.
2. Each tick or time slice:
   - Process routine cartel operations (skimming, quiet trade).
   - Update `shortage_index`, `unrest_index` as goods flow or are withheld.
   - Apply detection pressure and resolve:
     - Seizures, arrests, or failed raids (incidents to D-MIL-0003).
   - Allow syndicates/guilds/branches to choose higher-level moves:
     - Joint strikes, purges, negotiated truces.
3. Feed outcomes into:
   - Ward attributes (updated intensities, capture, shortages),
   - Agent states (debt/trust, injuries, promotions),
   - Scenario hooks and narrative events.

The objective is to make black markets feel:

- **Structurally necessary** (they arise from real scarcity and gaps),
- **Dangerous but rational** (actors respond to incentives and pressures),
- A key **vector for play** (routes, rumors, and deals the player can interact with).

---

## 10. Future Extensions

Likely follow-up documents:

- `D-INFO-0001_Information_Flows_and_Rumor_Graphs`
- `D-LAW-0002_Sanction_Types_and_Enforcement_Chains`
- Scenario-specific cartel briefs (named syndicates, rivalries, and customs).

Those should treat the attributes and structures here as their shared substrate
for modeling shadow economies and their political effects.

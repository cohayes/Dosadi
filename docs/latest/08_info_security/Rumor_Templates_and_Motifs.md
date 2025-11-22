---
title: Rumor_Templates_and_Motifs
status: helper_draft
owners: [cohayes]
last_updated: 2025-11-22
depends_on:
  - D-INFO-0003          # Information_Flows_and_Report_Credibility
  - D-INFO-0006          # Rumor_Networks_and_Informal_Channels
  - D-ECON-0004          # Black_Market_Networks
  - D-AGENT-0101         # Occupations_and_Industrial_Roles
---

# Rumor Templates and Motifs (Helper Doc)

This helper document offers **ready-to-use rumor patterns** for Dosadi. Each
template can be attached to:

- A specific **event** (e.g. a water seizure, exo accident),
- A **location** (ward, canteen, bunkhouse, corridor),
- Or a **character/faction** (guild, cartel, bishop, noble, militia).

It complements the structural logic of D-INFO-0006 by giving **concrete
payloads** that scenario authors (or generators) can slot into the rumor graph.

---

## 1. Template Schema

Each template follows this lightweight schema:

```yaml
id: string
label: string
payload_type: "event" | "threat" | "opportunity" | "character" | "policy"
typical_sources:
  - string         # occupations or locations
typical_targets:
  - string         # who/what the rumor is about
ward_bias:
  prefers_wards_with:
    - string       # tags like "high_black_market", "sealed_core"
base_tone: "fear" | "hope" | "resentment" | "awe" | "greed" | "paranoia"
mechanical_hooks:
  affects:
    - "unrest_index"
    - "loyalty_to_regime"
    - "black_market_intensity"
    - "strike_risk"
  notes: string    # short description of expected pressure
example_variants:
  - string         # a few sample phrasings at street level
```

Scenario authors can duplicate and specialize these templates per ward or
scenario.

---

## 2. Scarcity & Survival Rumors

### 2.1 "The Barrels Went Missing"

```yaml
id: rumor_missing_barrels
label: "The Barrels Went Missing"
payload_type: "event"
typical_sources:
  - "occ_barrel_handler"
  - "occ_cadence_smuggler"
  - "canteen_workers"
typical_targets:
  - "duke_house"
  - "militia"
  - "cartel"
ward_bias:
  prefers_wards_with:
    - "high_corridor_centrality"
    - "low_food_buffer"
    - "water_stress"
base_tone: "fear"
mechanical_hooks:
  affects:
    - "unrest_index"
    - "loyalty_to_regime"
  notes: >
    People fear cuts to rations and suspect theft or sabotage. Unrest rises,
    and loyalty to whoever controls water declines unless a convincing scapegoat
    is provided.
example_variants:
  - "Three barrels never made it past Checkpoint Nine."
  - "Foreman says the numbers don't match, and someone is hiding it."
  - "They'll cut us first to make the books balance."
```

### 2.2 "Thinner Rations, Same Counts"

```yaml
id: rumor_ration_dilution
label: "Thinner Rations, Same Counts"
payload_type: "policy"
typical_sources:
  - "occ_canteen_worker"
  - "occ_ration_clerk"
  - "bunkhouse_residents"
typical_targets:
  - "bishop_guild"
  - "central_audit_guild"
ward_bias:
  prefers_wards_with:
    - "high_habitation_density"
    - "recent_unrest_incidents"
base_tone: "resentment"
mechanical_hooks:
  affects:
    - "unrest_index"
    - "trust_in_bishop_guild"
  notes: >
    Accusations that someone is watering down rations. Can either hit civic
    stewards (if they seem complicit) or be redirected to higher authorities.
example_variants:
  - "Same ladle as last month, but it slips off like water."
  - "The books say we're fine. Tell that to my ribs."
  - "Someone up the chain is eating our share."
```

---

## 3. Power & Corruption Rumors

### 3.1 "The Troopers Take a Cut"

```yaml
id: rumor_trooper_racket
label: "The Troopers Take a Cut"
payload_type: "character"
typical_sources:
  - "occ_corridor_vendor"
  - "occ_cadence_smuggler"
  - "occ_bunkhouse_steward"
typical_targets:
  - "militia"
ward_bias:
  prefers_wards_with:
    - "medium_black_market_intensity"
    - "high_corridor_centrality"
base_tone: "resentment"
mechanical_hooks:
  affects:
    - "loyalty_to_regime"
    - "cartel_branch_alignment.militia"
  notes: >
    Normalizes the idea that militia are already compromised. Lowers respect for
    official force, but may make people more comfortable using cartel routes.
example_variants:
  - "Nothing moves through Gate Three without a tithe to the troopers."
  - "You pay once to the cartel and once to the boys in armor."
  - "They don't stop smuggling. They tax it."
```

### 3.2 "The Audit is a Knife"

```yaml
id: rumor_audit_purge
label: "The Audit is a Knife"
payload_type: "threat"
typical_sources:
  - "occ_ration_clerk"
  - "occ_audit_scribe"
  - "guild_foremen"
typical_targets:
  - "central_audit_guild"
  - "industry_guilds"
ward_bias:
  prefers_wards_with:
    - "high_audit_intensity"
    - "strong_guild_presence"
base_tone: "paranoia"
mechanical_hooks:
  affects:
    - "guild_cartel_stance"
    - "willingness_to_bribe_auditors"
  notes: >
    Frames audits as political weapons rather than neutral checks, pushing
    guilds and cartels toward pre-emptive corruption or resistance.
example_variants:
  - "They already know who they're coming for. The numbers are just an excuse."
  - "If a duke wants your yard, an audit will find something."
  - "Clean books won't save you; clean friends might."
```

---

## 4. Opportunity & Grey-Market Rumors

### 4.1 "Extra Barrels If You Know Who to Ask"

```yaml
id: rumor_extra_barrels
label: "Extra Barrels If You Know Who to Ask"
payload_type: "opportunity"
typical_sources:
  - "occ_cadence_smuggler"
  - "corridor_vendors"
  - "canteen_workers"
typical_targets:
  - "cartel"
ward_bias:
  prefers_wards_with:
    - "high_black_market_intensity"
    - "moderate_detection_pressure"
base_tone: "greed"
mechanical_hooks:
  affects:
    - "black_market_intensity"
    - "cartel_debt_index"
  notes: >
    Encourages residents to use cartel channels for extra water, increasing
    shadow dependence and future leverage over them.
example_variants:
  - "You don't have to go thirsty if you've got something to trade."
  - "The line at the back door is shorter and wetter."
  - "Official rations are the floor, not the ceiling."
```

### 4.2 "Suit Mods That Don’t Show on Logs"

```yaml
id: rumor_ghost_mods
label: "Suit Mods That Don’t Show on Logs"
payload_type: "opportunity"
typical_sources:
  - "occ_exo_tech"
  - "occ_clandestine_modder"
  - "exo_pilots"
typical_targets:
  - "BLACK_MARKET_SUITS"
ward_bias:
  prefers_wards_with:
    - "exo_bays"
    - "SUITS_guild_presence"
base_tone: "awe"
mechanical_hooks:
  affects:
    - "demand_for_illegal_mods"
    - "cartel_trust_index"
  notes: >
    Drives interest in clandestine modders, changing the balance between
    official maintenance and black-market tech.
example_variants:
  - "There's a bay where your suit walks like a ghost through scans."
  - "If the safeties 'accidentally' fail, maybe someone paid for that."
  - "The best gear never passes inspection—because it never appears on paper."
```

---

## 5. Fear, Reprisals, and Martyrdom Rumors

### 5.1 "They Disappeared After Speaking Up"

```yaml
id: rumor_disappeared_for_talking
label: "They Disappeared After Speaking Up"
payload_type: "threat"
typical_sources:
  - "bunkhouse_residents"
  - "canteen_workers"
  - "clinic_orderlies"
typical_targets:
  - "militia"
  - "espionage_branch"
ward_bias:
  prefers_wards_with:
    - "recent_purges_or_raids"
    - "high_rumor_fear_index"
base_tone: "fear"
mechanical_hooks:
  affects:
    - "rumor_fear_index"
    - "open_speech_frequency"
  notes: >
    Suppresses open talk, shifting rumor to quieter, higher-trust edges while
    making overt dissent rarer and more costly.
example_variants:
  - "She complained in line, and two days later her bunk was empty."
  - "They called it a transfer. No one has seen him in any ward."
  - "They don't argue with you. They erase you."
```

### 5.2 "The One Who Didn’t Break"

```yaml
id: rumor_unbroken_witness
label: "The One Who Didn’t Break"
payload_type: "character"
typical_sources:
  - "street_medics"
  - "bunkhouse_whispers"
  - "corridor_vendors"
typical_targets:
  - "dissidents"
  - "cartel_or_guild_heroes"
ward_bias:
  prefers_wards_with:
    - "recent_rebellions_or_strikes"
base_tone: "awe"
mechanical_hooks:
  affects:
    - "willingness_to_resist"
    - "solidarity_index"
  notes: >
    Creates local heroes whose stories raise the threshold for surrender and
    encourage collective action, even at high cost.
example_variants:
  - "They broke his fingers and he still wouldn't sign."
  - "She came back from the cells and smiled at the bishop."
  - "They can kill you, but they can't make you kneel."
```

---

## 6. Using Templates in Practice

- **Scenario seeding**:
  - At scenario start, assign 3–7 rumor templates to key wards.
  - Instantiate them with specific names, locations, and recent incidents.

- **Dynamic generation**:
  - When an event fires (raid, failure, strike), choose a compatible template
    and spawn a rumor instance with:
    - origin_ward,
    - initial confidence/sharpness,
    - attached factions/characters.

- **Play-facing surfaces**:
  - Canteen and bunkhouse dialogues,
  - Overheard corridor talk,
  - Cartel or guild briefings.

This helper doc is intentionally lightweight. Designers are encouraged to copy,
tweak, and expand these templates to fit specific arcs and factions.

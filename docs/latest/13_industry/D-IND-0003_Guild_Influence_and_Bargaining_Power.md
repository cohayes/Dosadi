---
title: Guild_Influence_and_Bargaining_Power
doc_id: D-IND-0003
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-22
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-IND-0001            # Industry_Taxonomy_and_Types
  - D-IND-0002            # Industry_Suitability_and_Evolution
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-MIL-0003            # Response_Cadences_and_Alert_Levels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 13_industry · Guild Influence and Bargaining Power (D-IND-0003)

## 1. Purpose

This document defines how **industrial guilds** emerge from ordinary industry,
and how their **influence and bargaining power** are tracked at the ward level.

Goals:

- Provide a **mechanical bridge** between:
  - Industry presence (D-IND-0001 / D-IND-0002),
  - Ward attributes (D-WORLD-0002),
  - The political branches (duke_house, bishop_guild, militia, central_audit_guild, cartel).
- Describe how guilds move from **mere producers** to **political actors** with
  bargaining leverage over nobles, civic stewards, and cartels.
- Offer simple indices and thresholds that can be used by simulation code to
  decide when and how guilds can:
  - Negotiate quotas and contracts,
  - Withhold production (slowdowns, strikes, “maintenance”),
  - Ally with or resist other branches.

This is a **logic document**. It does not prescribe specific guild names or
histories; those belong to concrete scenarios.

---

## 2. Baseline Concepts

### 2.1 Industry families and guild seeds

From D-IND-0001, each ward has industry presence across families such as:

- `WATER_ATMOSPHERE`
- `FOOD_BIOMASS`
- `BODY_HEALTH`
- `SCRAP_MATERIALS`
- `FABRICATION`
- `SUITS`
- `ENERGY_MOTION`
- `HABITATION`
- `INFO_ADMIN`
- `BLACK_MARKET`

These are tracked in the ward schema (D-WORLD-0002) as:

```yaml
industry_weight:
  WATER_ATMOSPHERE: float
  FOOD_BIOMASS: float
  ...
```

Industrial guilds are **emergent organizations** built on top of:

- High `industry_weight` in one or more families,
- Concentrations of **skilled occupations** (D-AGENT-0101),
- Control over **choke-point infrastructure** (e.g. exo-bays, pump shops).

### 2.2 Guild presence vs guild power

We distinguish between:

- **Guild presence** – “Are there enough skilled workers and workshops to form
  a cohesive guild identity?”
- **Guild power** – “Can this guild meaningfully bargain with nobles, civic
  stewards, cartels, or the military?”

Presence is mostly about **capacity**; power is about **leverage**.

---

## 3. Guild Presence Index

For each ward `w` and each relevant industry family `F`, define a **guild
presence index** `G_presence(w, F)` in `[0, 1]`.

A non-normative formulation:

```text
G_presence(w, F) ≈
    α1 * industry_weight_F(w)
  + α2 * skilled_labor_density_F(w)
  + α3 * infra_choke_score_F(w)
```

Where:

- `industry_weight_F(w)` is taken from `industry_weight` in D-WORLD-0002.
- `skilled_labor_density_F(w)` is a normalized measure of **skilled and elite
  occupations** in family `F` (e.g. `occ_exo_tech` for SUITS, `occ_vat_tech` for
  FOOD_BIOMASS).
- `infra_choke_score_F(w)` reflects whether `w` hosts unique or hard-to-replace
  infrastructure for that family (e.g. only exo-bays in a region).

Implementation details:

- Coefficients `α1, α2, α3` are scenario-tunable but should sum to ≈ 1.0.
- Presence indices may also be smoothed across neighboring wards to model
  **regional guilds**.

Interpretation:

- `G_presence ≈ 0.0` → scattered workshops and workers, no real guild coherence.
- `G_presence ≈ 0.3` → recognizable guild-like structure at ward scale.
- `G_presence ≥ 0.6` → strong guild hub; likely contains leadership figures.
- `G_presence ≥ 0.8` → key regional center for that guild.

---

## 4. Guild Power Index

Presence alone is not enough. Power depends on **who needs what** and **who can
go elsewhere**.

For each ward `w` and family `F`, define **guild power index** `G_power(w, F)`
in `[0, 1]`.

A non-normative formulation:

```text
G_power(w, F) ≈ G_presence(w, F)
              * demand_pressure_F(w)
              * substitutability_factor_F(w)
              * protection_factor_F(w)
```

Where:

- `demand_pressure_F(w)` – how badly other factions need outputs from `F` in or
  through ward `w`.
  - Depends on:
    - Local and neighboring `industry_weight` in dependent families.
    - `garrison_presence`, `water_quota`, `food_buffer`, etc.
- `substitutability_factor_F(w)` – “How easily could the regime bypass this guild
  with another ward or technology?”
  - We invert it: **lower substitutability → higher multiplier**.
- `protection_factor_F(w)` – how much coverage the guild has from powerful allies
  and its own assets:
  - Support from `duke_house` (patronage contracts),
  - Ties to `bishop_guild` (shared care infrastructure),
  - Cartel alignment (off-book income and enforcement),
  - Access to exo-suit cadres or other hard power via MIL pillar.

Implementation hint:

- `demand_pressure_F(w)` may be normalized by looking at:
  - How much of the city’s total capacity in `F` is within a region around `w`.
  - How many essential systems (water, food, power, suits) depend on `F` nearby.
- `substitutability_factor_F(w)` can be approximated as:
  - `1 / (1 + alt_capacity_fraction)` where `alt_capacity_fraction` is the share
    of capacity easily reachable elsewhere.
- `protection_factor_F(w)` may be a composite of:
  - Local `loyalty_to_regime`,
  - `black_market_intensity` (cartel protection),
  - `garrison_presence` and `military_weight` when the guild and militia cooperate.

Interpretation:

- `G_power < 0.2` → guild exists but has little bargaining leverage.
- `0.2 ≤ G_power < 0.5` → able to negotiate better terms, but regime can coerce.
- `0.5 ≤ G_power < 0.8` → serious actor; can credibly threaten slowdowns or shifts.
- `G_power ≥ 0.8` → near-monopoly or regionally critical; regime must treat as peer.

---

## 5. Guild Influence Levels

To keep systems simple, we map `G_power(w, F)` onto qualitative **influence levels**.

Example mapping for each `(w, F)`:

```yaml
GUILD_NONE:
  range: [0.0, 0.1)
  description: "No coherent guild; scattered workshops."
GUILD_DEPENDENT:
  range: [0.1, 0.3)
  description: "Small guild under tight noble or cartel control."
GUILD_BARGAINING:
  range: [0.3, 0.6)
  description: "Recognized guild with some negotiating power."
GUILD_DOMINANT:
  range: [0.6, 0.85)
  description: "Key industrial bloc; nobles and civic stewards must court them."
GUILD_HEGEMONIC:
  range: [0.85, 1.0]
  description: "Near-monopoly; guild can dictate terms in this domain."
```

These levels can be cached per ward and family:

```yaml
ward_guild_influence:
  SUITS: "GUILD_BARGAINING"
  FABRICATION: "GUILD_DOMINANT"
  FOOD_BIOMASS: "GUILD_DEPENDENT"
```

Sim and narrative systems then refer to these **symbolic levels** to decide:

- How hard nobles can squeeze them,
- How attractive they are as cartel partners,
- How dangerous a strike or slowdown would be.

---

## 6. Guild Levers and Actions

When guilds have influence, what can they *do*? We define a small set of
standard **guild actions** that can be invoked by AI factions or scenario logic.

### 6.1 Soft leverage: negotiation and drift

At `GUILD_BARGAINING` and above, guilds can:

- **Renegotiate quotas and schedules**:
  - Slightly delay deliveries,
  - Request more water/power allocation,
  - Lobby for safety upgrades or new exo-bays.

Effects:

- Small adjustments to:
  - `water_quota(w)` or `power_quota(w)`,
  - Local pay scales for guild-linked occupations,
  - Maintenance priorities for shared infra.

Mechanically, these appear as **parameter nudges** rather than dramatic events.

### 6.2 Slowdowns, “maintenance,” and quality games

At `GUILD_BARGAINING` and especially `GUILD_DOMINANT`:

- Guilds can threaten or enact **slowdowns**:
  - Increased failure rates,
  - Longer repair times,
  - Reduced throughput.

- Or they can play **quality games**:
  - Under-spec parts for disfavored wards,
  - Prioritize the “friends” of the guild.

These actions:

- Raise `shortage_index(w)` or neighboring wards’ shortage index.
- Raise `unrest_index(w)` if shortages hit ordinary people.
- Increase **incident** probabilities tied to infrastructure in D-MIL-0003
  (e.g. pump failures, power outages, suit failures).

### 6.3 Strikes and coordinated stoppages

At `GUILD_DOMINANT` or `GUILD_HEGEMONIC`, and under certain triggers:

- Guilds can attempt **partial or full strikes** in one or more wards.

Triggers might include:

- Repeated quota over-demands by `duke_house`,
- Brutal crackdowns by `militia` in guild-heavy wards,
- Aggressive audits exposing guild side deals.

Mechanically:

- Drastic drops in `industry_weight_F(w)` effective output,
- Sudden spikes in relevant `shortage_index` and `unrest_index`,
- Potential new incident types (e.g. STRIKE_OCCUPATION, SABOTAGE_CAMOUFLAGED_AS_STRIKE).

Regime response:

- May escalate `alert_level(w)` (see D-MIL-0003),
- Use militia to break strikes,
- Offer concessions, or invite/cartelize rival workshops.

### 6.4 Alliance and capture by other branches

Guilds can align with:

- **duke_house** – in exchange for:
  - Stable contracts, limited audits, protection from cartels.
- **bishop_guild** – joint projects in bunkhouses, canteens, clinics,
  integrating guild-built equipment and maintenance.
- **cartel** – for:
  - Off-book payments, contraband access, muscle.
- **militia** – providing specialized gear, favors, and maintenance priority.

Mechanically, these alliances:

- Modify `protection_factor_F(w)` and thus `G_power(w, F)`.
- Shift **who responds** to guild actions:
  - Strike vs “negotiation table” vs targeted arrests.

---

## 7. Interaction with Ward Ownership and Dominant Power

Wards already have a `dominant_owner` (D-WORLD-0002), e.g.:

```yaml
dominant_owner: "duke_house" | "bishop_guild" | "cartel" | "militia" | "central_audit_guild" | "mixed"
```

Guilds **do not start** as dominant owners. Instead:

- Their influence is initially captured in `ward_guild_influence`,
- Their political impact is mediated through existing owners.

### 7.1 Shifts in effective control

However, at high influence levels, guilds can **reshape effective control**.

Non-normative patterns:

- If one or more critical families (e.g. `SUITS`, `ENERGY_MOTION`, `WATER_ATMOSPHERE`)
  reach `GUILD_DOMINANT`/`GUILD_HEGEMONIC` in ward `w`, and:
  - `loyalty_to_regime(w)` is low, and
  - `black_market_intensity(w)` is moderate-to-high,

then simulation MAY:

- Consider `dominant_owner` drifting toward `"mixed"`,
- Or introduce a scenario flag indicating **guild-backed autonomy**.

Over longer arcs, a whole **region** of wards could adopt:

- An emergent meta-state like `"industry_guild"` as de facto power, even if
  nobles are still nominally in charge.

### 7.2 Guild vs cartel vs civic stewards

Characteristic tensions:

- **Guild vs cartel**:
  - Guilds want stable, predictable flows and margins.
  - Cartels profit from scarcity, diversion, and information asymmetry.
  - In some wards, guilds may ally with cartels **against** nobles/militia; in
    others, they may ally with nobles to crack cartels.

- **Guild vs bishop_guild**:
  - Both care about continued survival infrastructure (food, beds, clinics).
  - Guilds may resent civic stewards for “wasting” resources on “nonproductive”
    dependents, or may see them as allies ensuring a stable workforce.

- **Guild vs central_audit_guild**:
  - Audits threaten guild side incomes and quiet deals.
  - High `G_power` + high `audit_intensity` is fertile ground for:
    - Bribery,
    - Quiet war on inspectors,
    - Data falsification games.

These relationships can be expressed via **scenario-level stance matrices**,
but this document defines where such tensions *come from* mechanically.

---

## 8. Hooks into Agents and Occupations

Guild influence should be **felt** at the agent level.

### 8.1 Employment security and risk

For agents with guild-linked occupations (D-AGENT-0101), e.g. `occ_exo_tech`,
`occ_vat_tech`, `occ_suit_stitcher`:

- In wards with **low** `G_power`:
  - Jobs are precarious, more subject to noble whim and cartel extortion.
  - Drives may emphasize **personal survival and patron shopping**.

- In wards with **high** `G_power`:
  - Guild can protect members (legal defense, replacement income, housing).
  - Agents may feel more confident resisting exploitation, or more obligated
    to follow guild lines during conflicts.

### 8.2 Mobility and promotion

Guilds provide **internal ladders**:

- Unskilled → semi-skilled → skilled → guild cadre/overseer.
- `growth_paths` in occupations (D-AGENT-0101) are more **available and rewarding**
  when `G_presence` and `G_power` are high.

This can be used for:

- Long-term NPC arcs (“worked my way up from rubble crew to yard overseer”),
- Player choices about which guilds to align with, join, or betray.

### 8.3 Informational leverage

Guild-linked agents sit at **critical information chokepoints**:

- See flows of materials, parts, and failures.
- Can monitor which wards are under- or over-supplied.
- Can quietly manipulate maintenance schedules.

Simulation can treat guild-linked agents as having:

- Higher baseline **knowledge** about relevant infra and industry states,
- Better access to rumors about planned strikes, accidents, or sabotage.

---

## 9. Implementation Sketch (Non-Normative)

A minimal implementation loop for guilds might:

1. For each ward `w`, compute `G_presence(w, F)` for key families `F`.
2. From presence, compute demand, substitutability, and protection factors.
3. Derive `G_power(w, F)` and map to influence levels.
4. Allow high-influence guilds to propose or execute actions:
   - Soft negotiations (parameter nudges),
   - Slowdowns / quality games,
   - Strikes,
   - Alliances with other branches.
5. Feed the consequences into:
   - `shortage_index`, `unrest_index`,
   - Incident streams (for D-MIL-0003 escalation),
   - Scenario and narrative hooks.

The details can be tuned per scenario. The aim is that **industrial power is
earned and maintained through actual production, infrastructure, and social
ties**, not simply granted by narrative fiat.

---

## 10. Extension & Future Documents

Potential follow-ups building on this document:

- `D-IND-0101_Guild_Templates_and_Regional_Leagues`  
  - Named guild archetypes (e.g. Exo-Fabricators League, River-Condensate Cartel),
    with characteristic stances and behaviors.

- `D-ECON-0002_Black_Market_Networks` (referenced elsewhere)  
  - Detailed overlap and rivalry between guild logistics and shadow logistics.

- `D-LAW-0xxx_Guild_Charters_and_Sanction_Systems`  
  - Formal rules governing guild recognition, revocation, and justified crackdowns.

These should treat `G_presence`, `G_power`, and influence levels defined here
as their shared quantitative backbone.

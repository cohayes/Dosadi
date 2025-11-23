---
title: Counterintelligence_Tradecraft_and_Signatures
doc_id: D-INFO-0009
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
  - D-MIL-0102            # Officer_Doctrines_and_Patronage_Networks
  - D-MIL-0108            # Counterintelligence_and_Infiltration_Risk
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0002           # Espionage_Branch
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002            # Procedural_Paths_and_Tribunals
  - D-LAW-0003            # Curfews_Emergency_Decrees_and_Martial_States
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 08_info_security · Counterintelligence Tradecraft and Signatures (D-INFO-0009)

## 1. Purpose

This document describes **counterintelligence (CI) tradecraft and signatures**
used by the Espionage Branch and allied organs on Dosadi.

Where D-MIL-0108 describes CI from a **militia-centered** view, this document
provides the **INFO-side frame**:

- CI as a cross-pillar function:
  - monitoring MIL, guild, cartel, and ducal factions,
  - exploiting telemetry, ledgers, and rumor networks.
- A library of **behavioral and data signatures** that indicate infiltration,
  corruption, or covert operations.
- Tools and patterns used by CI operators:
  - asset handling,
  - operations design,
  - signal triage.

The goal is to provide scenarios and simulation code with a shared vocabulary
for **“what looks suspicious”** and **how the system tries to notice it.**

---

## 2. Relationship to Other Documents

- **Espionage Branch (D-INFO-0002)**  
  - Defines institutional structure and mandate for CI and espionage.

- **Telemetry & Audit (D-INFO-0001)**  
  - Provides raw data channels and instrumentation.

- **Information Flows & Report Credibility (D-INFO-0003)**  
  - Defines how reports are weighted, cross-checked, and disputed.

- **Rumor Networks (D-INFO-0006)**  
  - Provides informal, human-sourced signals that CI can exploit or
    misinterpret.

- **MIL CI View (D-MIL-0108)**  
  - Defines CI from inside MIL; this doc is the umbrella INFO-side mirror.

- **Guilds, Black Markets, LAW, WORLD**  
  - Provide the **background noise** in which CI must spot meaningful patterns.

---

## 3. CI Conceptual Stack

We frame CI in three layers:

1. **Sources** – where signals come from:
   - telemetry streams,
   - ledger and audit data,
   - human sources (informants, officer reports, guild defects),
   - rumor and pamphlet networks.

2. **Signatures** – patterns that **might** indicate:
   - infiltration,
   - covert networks,
   - coup or revolt preparations,
   - CI operations by rival factions.

3. **Tradecraft** – how CI operators:
   - collect and protect sources,
   - test and exploit signatures,
   - shape the environment (stings, false flags, selective leaks).

This document focuses on layers 2 and 3.

---

## 4. Signature Categories

We define several broad **signature categories**:

1. **Telemetry anomalies**  
   - Patterns in flows, logs, or metrics that deviate from expected baselines.

2. **Behavioral anomalies**  
   - Unusual actions by units, guilds, or nodes relative to doctrine and
     incentives.

3. **Network anomalies**  
   - Changes in patronage graphs, contact patterns, or rumor pathways.

4. **Content anomalies**  
   - Shifts in language, slogans, and narrative motifs across media.

5. **Structural anomalies**  
   - Sudden changes in who gets sanctioned, raided, or promoted.

Each category is used to define **signatures**: structured hypotheses about what
a given anomaly might mean.

---

## 5. Telemetry Signatures

### 5.1 Example signature: Protected Corridor

**Hypothesis:** a corridor or checkpoint is under guild/cartel protection.

Indicators:

- Seizure rates and inspection frequencies:
  - significantly lower than neighboring nodes,
  - despite similar or higher risk environment.

- Flow metrics:
  - consistent throughput even during high alert levels,
  - abnormal survival rates for shipments linked to certain guilds.

- Incident pattern:
  - few recorded confrontations or violence in the protected zone,
  - but downstream or upstream nodes show surges.

Tradecraft:

- CI compares:
  - node statistics against **regional baselines** (D-INFO-0001),
  - adjusting for ward type (D-WORLD-0002/0003) and doctrine mix (D-MIL-0102).

- If flagged:
  - escalate to HUMINT probes,
  - integrity checks and stings (D-MIL-0108).

---

### 5.2 Example signature: Phantom Losses

**Hypothesis:** quiet sabotage or diversion is occurring.

Indicators:

- Repeated minor discrepancies between:
  - industrial outputs (IND),
  - recorded consumption and losses (ECON),
  - MIL and LAW seizure reports.

- Discrepancies localized to:
  - specific lifts, barrels, or yard segments.

Tradecraft:

- CI cross-references:
  - Quiet Ledger data,
  - guild charters and obligations (D-IND-0103),
  - known guild collective action plays (D-IND-0104).

- Plausible readings:
  - shadow production/diversion supporting black markets,
  - MIL units collaborating with guild or cartel cells.

---

### 5.3 Example signature: Sudden Cleanliness

**Hypothesis:** an infiltrated or compromised node is attempting to **scrub** its
profile under scrutiny.

Indicators:

- Long history of anomalous patterns abruptly disappearing without obvious
  structural change:
  - same leadership, same ward context, same flows.

- Logs become:
  - extremely regular,
  - highly compliant with ideal distributions.

Tradecraft:

- CI treats too-perfect data as itself suspicious.
- May:
  - increase HUMINT effort,
  - plant controlled anomalies to see if node behaves “too perfectly.”

---

## 6. Behavioral Signatures

### 6.1 Garrison Over-Caution or Under-Reaction

**Hypothesis:** command or key nodes are compromised or conflicted.

Indicators:

- Hardline commanders **failing** to escalate under doctrinal expectations,
- Professional officers repeatedly:
  - delaying execution of harsh orders,
  - seeking procedural “clarity” that buys time.

Tradecraft:

- CI compares behavior against doctrinal archetypes (D-MIL-0102):
  - constructs a **behavioral deviation index**.

- Possible interpretations:
  - infiltration or sympathies to guilds/bishops/rebels,
  - trauma and morale collapse (D-MIL-0105),
  - tactical prudence that may or may not align with regime interests.

CI must distinguish these via:

- targeted debriefings,
- triangulating with rumor and guild/cartel intelligence.

---

### 6.2 Guild Strikes with Unusual Impunity

**Hypothesis:** high-level protection or collusion.

Indicators:

- Guild collective actions (strikes, slowdowns, sabotage, D-IND-0104) occur:
  - near MIL nodes that **do not respond** as expected,
  - without subsequent purge or charter sanctions.

Tradecraft:

- CI maps:
  - which MIL and LAW nodes **consistently** fail to act on guild provocations.

- Possible readings:
  - deep guild infiltration of MIL/LAW in that ward,
  - ducal patronage shielding a particular guild,
  - deliberate containment strategy (letting pressure vent locally).

---

## 7. Network Signatures

### 7.1 Patronage Drift

**Hypothesis:** patronage networks are re-wiring in ways that signal infiltration
or coup preparation.

Indicators:

- Increasing density of:
  - officer ↔ guild_faction edges,
  - officer ↔ cartel_cell edges,

without corresponding:

- official structural reasons (e.g., new charter, redeployment).

Tradecraft:

- CI monitors **PatronageEdge** changes (D-MIL-0102, D-IND-0105):
  - unusual convergence around a small number of nodes,
  - emergent subgraphs that cross usual faction boundaries.

Possible interpretations:

- cartel capturing critical MIL nodes,
- dukes or bishops preparing to challenge other elites,
- Espionage Branch itself building networks in anticipation of a purge.

---

### 7.2 Rumor Echo Chambers

**Hypothesis:** someone is deliberately shaping rumor routes.

Indicators:

- Certain rumor motifs (D-INFO-0006) are:
  - over-represented in specific corridors or bunkhouses,
  - under-represented elsewhere despite similar conditions.

- Cross-ward echoes:
  - same phrasing or specific slogans appearing in widely separated zones,
  - particularly those with shared guild or MIL links.

Tradecraft:

- CI uses rumor tracing to identify:
  - “loud nodes” (gossip hubs),
  - unnatural alignment with specific political narratives.

Possible readings:

- covert propaganda from ducal or cartel agents,
- guild psychological operations ahead of strikes,
- counter-ops by Espionage Branch shaping perceptions.

---

## 8. Content and Structural Signatures

### 8.1 Content markers

Examples:

- Repeated use of:
  - certain metaphors,
  - coded phrases in graffiti, pamphlets, overheard conversations.

- Shifts in **unit slang**:
  - adoption of guild/cartel terms,
  - ideological motifs from zealot factions.

CI can use language analysis to:

- cluster units and wards by narrative alignment,
- detect infiltration by foreign ideological streams.

### 8.2 Structural justice anomalies

Indicators:

- Shift in who is:
  - punished vs spared in tribunals (D-LAW-0002),
  - targeted by purges (D-MIL-0103).

- Patterns where:
  - defendants consistently belong to rival guilds or factions,
  - favored actors rarely face consequences despite many allegations.

Tradecraft:

- CI examines **sanction distributions**:
  - by role, faction, ward origin.

Possible readings:

- infiltration of LAW by certain factions,
- Espionage Branch or duke_house using LAW as a weapon,
- a sign of looming regime fracture.

---

## 9. CI Tradecraft: Tools and Practices

### 9.1 Signal Triage and Confidence Levels

Each signature is associated with a **confidence level**:

```yaml
SignatureAssessment:
  signature_id: string
  source_mix:
    telemetry_weight: float
    ledger_weight: float
    human_weight: float
    rumor_weight: float
  confidence_level: "low" | "medium" | "high"
  competing_hypotheses:
    - "guild_infiltration"
    - "morale_collapse"
    - "ducal_power_play"
  recommended_actions:
    - "monitor"
    - "sting"
    - "purge_recommendation"
```

Tradecraft:

- Avoid acting on **single-source** signatures when possible.
- Prioritize convergence:
  - telemetry + ledger + human sources,
  - or repeated rumor motifs plus at least one concrete anomaly.

---

### 9.2 Asset Handling

Types of CI assets:

- **Inside MIL**:
  - officers or enlisted unhappy with patronage regimes,
  - zealots who report “impure” behavior,
  - professionals disturbed by corruption.

- **Inside guilds**:
  - factions marginalized by current leadership,
  - technicians with access to sensitive systems (SUITS, Lift, Stillwater).

- **Inside cartels and Shadow**:
  - ambitious intermediaries seeking advancement,
  - defectors seeking amnesty.

Tradecraft themes:

- Compartmentalization:
  - assets do not know other assets,
  - CI cells limited in scope.

- Doubt management:
  - constant testing of asset reliability,
  - recognition that assets themselves may be double or triple agents.

---

### 9.3 Stings and Controlled Operations

Examples:

- **Controlled corridor runs**:
  - sending tagged shipments through suspected compromised nodes,
  - observing which ones survive or “vanish.”

- **Fake conspiracies**:
  - staging talk of rebellion or guild strike to see who carries it onward.

- **Shadow arrests**:
  - quietly grabbing suspected infiltrators and feeding disinformation through
    back channels.

Tradecraft requirement:

- Stings must be carefully scoped to avoid:
  - needless disruption of industrial or ward stability,
  - self-inflicted panic that degrades morale and trust.

---

## 10. CI Failures and Misreads

CI is rarely clean. Common failure modes:

- **Overfitting**:
  - seeing patterns where none exist,
  - launching purges that actually weaken the regime.

- **Underfitting**:
  - dismissing genuine signals as “noise,”
  - allowing guilds/cartels to entrench.

- **Capture**:
  - CI units themselves infiltrated or bought,
  - using CI powers to attack rivals.

Simulation and scenarios should reflect:

- Some signatures are **ambiguous**,
- Rational choices can still lead to bad outcomes,
- Factional CI (ducal, guild, cartel) may compete with central Espionage
  Branch.

---

## 11. Integration with Other Systems

### 11.1 With MIL CI (D-MIL-0108)

- MIL-facing CI:
  - focuses on garrison-level infiltration and survival,
  - may resist Espionage Branch interference.

- INFO CI:
  - has broader cross-pillar perspective,
  - may see MIL as just another surface (and threat).

Tensions:

- Espionage Branch may:
  - trigger purges that MIL sees as unjust or destabilizing.
- MIL may:
  - hide internal compromises to avoid external punishment.

---

### 11.2 With LAW

- CI feeds:
  - cases into Security Tribunals,
  - evidence packets for purge campaigns.

- LAW feeds back:
  - outcomes that validate or embarrass CI assessments.

Signature feedback loop:

- Successes:
  - reinforce current CI tradecraft,
  - risk entrenching blind spots.

- Failures:
  - trigger doctrine and personnel changes,
  - might push regime toward more paranoid CIPosture levels.

---

### 11.3 With Rumor Networks

- CI uses rumor both as:
  - early warning,
  - a weapon (seeding stories to stress target networks).

- Rumor networks use CI:
  - as content (stories of purges, stings, hidden prisons),
  - as threat (deterrent for open organizing).

This interplay shapes:

- public risk calculus for guild members, MIL, and civilians,
- the perceived **opacity** vs **legibility** of power.

---

## 12. Implementation Sketch (Non-Normative)

1. **Define signature templates**:

   - For each category (telemetry, behavior, network, content, structural):
     - conditions for activation,
     - possible hypotheses,
     - confidence thresholds.

2. **At each macro-step**:

   - Collect data from:
     - WORLD, IND, ECON, MIL, LAW, INFO, RUMOR layers.
   - Instantiate SignatureAssessment objects for activated templates.
   - Update CIState and CIPosture per ward/region.

3. **CI decision step**:

   - For each significant assessment:
     - choose action: ignore/monitor/sting/purge-recommendation.
   - Generate:
     - CI operations events (stings, raids),
     - LAW cases or purge proposals.

4. **Update world state**:

   - Incorporate:
     - successful and failed CI operations,
     - backlash and unintended consequences,
     - rumor and morale changes.

5. **Expose to dashboards and scenarios**:

   - Show:
     - active high-confidence signatures,
     - CI operations in progress,
     - contested interpretations (“guild capture” vs “regime overreach”).

---

## 13. Future Extensions

Potential follow-ups:

- `D-INFO-0014_Security_Dashboards_and_Threat_Surfaces`
  - How CI, MIL, LAW, and WORLD status is visualized and consumed by
    in-world actors and by the simulation UI.

- Scenario packs focused on CI campaigns
  - e.g. “The Quiet Ring Crackdown,” where the player or AI navigates
    ambiguous signatures and political risk.

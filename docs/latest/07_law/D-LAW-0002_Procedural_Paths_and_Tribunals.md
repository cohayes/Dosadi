---
title: Procedural_Paths_and_Tribunals
doc_id: D-LAW-0002
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-RUNTIME-0001        # Simulation_Timebase
  - D-LAW-0001            # Sanction_Types_and_Enforcement_Chains
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-MIL-0002            # Garrison_Structure_and_Deployment_Zones
  - D-MIL-0003            # Response_Cadences_and_Alert_Levels
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-ECON-0004           # Black_Market_Networks
  - D-IND-0003            # Guild_Influence_and_Bargaining_Power
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-AGENT-0101          # Occupations_and_Industrial_Roles
---

# 09_law · Procedural Paths and Tribunals (D-LAW-0002)

## 1. Purpose

This document defines the **procedural routes** by which cases move (or fail to
move) through Dosadi’s formal and quasi-formal justice mechanisms.

It answers:

- What counts as a **case** and who opens one.
- Which **paths** a case may follow: ignored, handled informally, processed
  through civic/administrative channels, or escalated to special tribunals.
- How those paths differ by:
  - Ward and branch (militia, bishops, guilds, audits, nobles),
  - Severity and political sensitivity,
  - Current alert level.
- How procedure interacts with **sanctions** (D-LAW-0001) and the
  **information ecosystem** (D-INFO-0001/0003/0006).

The goal is **not** to impose a single uniform legal code, but to give
simulation and scenario design a common structure for “what happens after
someone reports, accuses, or gets caught.”

---

## 2. Cases and Procedural Objects

### 2.1 Case object

A **case** is any situation that might trigger a formal or semi-formal response.

Conceptual schema:

```yaml
Case:
  id: string
  origin_ward: string
  category: "petty_offense" | "economic_violation" | "guild_dispute" |
            "cartel_activity" | "security_threat" | "political_dissent" |
            "military_misconduct" | "other"
  severity: int           # e.g. 1–5
  sensitivity: int        # e.g. 1–5, how politically dangerous the truth is
  complainant_branch: "bishop_guild" | "militia" | "central_audit_guild" |
                      "industry_guild" | "duke_house" | "cartel" | "none"
  accused_roles:          # occupations or branches implicated
    - string
  linked_incidents:       # MIL or ECON incident IDs
    - string
  current_path_stage: string
  status: "open" | "stalled" | "closed_formal" | "closed_informal"
```

Cases arise from:

- **Formal reports** (D-INFO-0003): lodged by clerks, audits, officers,
  guild stewards, bishops, or citizens.
- **Telemetry anomalies** (D-INFO-0001): missing barrels, doctored counts,
  sensor flags.
- **Rumor signals** (D-INFO-0006): persistent, specific rumors about
  sabotage, disappearances, or corruption.
- **Direct orders** from duke_house or high command.

### 2.2 Path abstractions

Instead of one big “court system,” we define **procedural path archetypes**:

- **Administrative Handling** – routine, paperwork-heavy resolution.
- **Civic / Pastoral Handling** – bishop-led mediation, restitution.
- **Guild Arbitration** – handled inside or between guilds.
- **Audit Review / Commission** – central_audit_guild-driven inquiries.
- **Security Tribunal** – closed, accelerated processes for high-severity,
  high-sensitivity cases.
- **Extrajudicial Handling** – skipped procedure; direct sanctions.

A given case may move between these as pressure and politics change.

---

## 3. Path Archetypes

### 3.1 Administrative Handling (Civic / Low-Level)

Used for:

- Petty offenses, minor economic violations, low-level disputes,
- Low-severity, low-sensitivity cases where maintaining routine is valued.

Typical actors:

- Ward-level administrative clerks,
- Low-ranking militia officers,
- Bishop_guild stewards (for shared spaces).

Process characteristics:

- **Paper-heavy**; generates records (D-INFO-0005 surfaces),
- Sanctions skew toward **economic**, **movement**, and **record** types,
- Appeals possible but limited; usually internal to the same ward admins.

Mechanical hooks:

- Increases `sanction_intensity(w)` without dramatically raising
  `rumor_fear_index(w)` unless badly abused.
- Contributes to **case_backlog** if overloaded (see §7).

### 3.2 Civic / Pastoral Handling (Bishop-led)

Used for:

- Interpersonal conflicts,
- Resource-sharing disputes in bunkhouses, canteens, clinics,
- Misconduct within civic institutions.

Typical actors:

- Bishop_guild stewards and overseers,
- Civic mediators.

Process characteristics:

- Emphasis on **restitution** and **re-assignment** rather than overt punishment.
- Sanctions often take the form of work duty, shifts in bunk assignment,
  reduced access to certain amenities.

Mechanical hooks:

- Can **reduce unrest** if seen as fair,
- May **clash** with militia when they prefer harsher responses,
- Provides an alternative to cartel “justice” in lower wards.

### 3.3 Guild Arbitration

Used for:

- Disputes within or between guilds,
- Quality failures, missed quotas, suspected sabotage in guild domains,
- Conflicts between guild members and external clients.

Typical actors:

- Guild elders, foremen, internal investigators,
- Sometimes with liaison officers from duke_house or militia.

Process characteristics:

- Largely **off-book**; limited visibility to central audits unless leaked.
- Sanctions include blacklisting within the guild, reassignment, fines,
  hidden bodily punishment, or expulsions.

Mechanical hooks:

- In guild-strong wards, many cases **never reach state law**; they die
  or transform inside guild channels.
- Successful guild justice can stabilize production; predatory guild
  justice can drive people toward cartels or revolt.

### 3.4 Audit Review / Commission

Used for:

- Complex economic violations,
- Systemic discrepancies in water, rations, or accounts,
- Allegations involving officials, nobles, or large enterprises.

Typical actors:

- Central_audit_guild investigators,
- Special commissions containing mixed representatives
  (auditors, militia, duke appointees).

Process characteristics:

- Slow, data-heavy; multiple phases of preliminary review,
  on-site inspections, hearings, and findings.
- Often creates **politically shaped truths** rather than neutral ones.

Mechanical hooks:

- Raises `legal_opacity` if outcomes seem predetermined or arbitrary,
- Can trigger high-level sanctions (D-LAW-0001) against guilds,
  bishops, or even dukes,
- Case outcomes feed into rumor templates about audits as knives.

### 3.5 Security Tribunals

Used for:

- Alleged security threats, political dissent, espionage,
  major cartel/guild collusion, mutiny.

Typical actors:

- Militia high command,
- Espionage branch representatives (D-INFO-0002),
- Select judges loyal to duke_house.

Process characteristics:

- Closed, accelerated procedures,
- Rules of evidence are loose or secret,
- Outcomes skew toward **bodily**, **terminal**, and **collective** sanctions.

Mechanical hooks:

- Strong increases to `rumor_fear_index(w)` and `impunity_index(w)`,
- Can suppress short-term unrest but deepen long-term hatred,
- May provoke guild or cartel retaliation if seen as illegitimate.

### 3.6 Extrajudicial Handling

Used when:

- Authorities or cartels see procedure as an obstacle,
- Time is “too short” for proper process,
- They wish to send a message without generating records.

Actors:

- Militia officers, cartel enforcers, corrupt guild foremen,
- Occasionally bishop or duke agents operating off the books.

Process characteristics:

- No or minimal paperwork,
- Direct application of sanctions (beatings, disappearances, rigged accidents),
- Partial or full denial that any case exists.

Mechanical hooks:

- Bypasses formal case queues and record systems,
- Strongly shapes rumors and fear, especially when patterns emerge,
- Undermines faith in due process; drives people toward non-state protections.

---

## 4. Mapping Cases to Paths

### 4.1 Initial routing

When a case `C` is created, the system chooses an **initial path** based on:

- `category` and `severity`,
- `complainant_branch`,
- Ward-level indices (`sanction_intensity`, `legal_opacity`,
  `due_process_index`),
- Current `alert_level(w)`.

Conceptual rule:

```text
initial_path(C) ≈ f(category, severity, complainant_branch,
                     alert_level(origin_ward),
                     guild_cartel_power(origin_ward),
                     political_sensitivity)
```

Examples:

- Petty theft in a bishop-heavy ward → **Civic Handling** or light
  **Administrative Handling**.
- Large water discrepancy spanning multiple wards → **Audit Review**.
- Guild strike in a key industry → **Guild Arbitration** + threat of
  **Security Tribunal** for leaders.
- High-profile dissent in a core ward under ALERT_2 → direct **Security Tribunal**
  or **Extrajudicial Handling**.

### 4.2 Path drift and interference

Cases may **drift** between paths over time:

- A civic mediation that fails and is re-reported up the chain,
- A guild arbitration that spills into public unrest,
- An audit case that becomes politically explosive and is moved to
  Security Tribunal.

Factors that drive drift:

- New incidents (violence, sabotage, mass protests),
- Intervention by powerful actors (dukes, major guilds, large cartels),
- Rumor spread changing perceived stakes or guilt.

---

## 5. Tribunals and Forums

We define several **forum types** where decisions formally occur.

### 5.1 Ward Administrative Panels

Composition:

- Ward administrator,
- Militia liaison,
- Bishop or civic representative,
- Occasionally a guild delegate.

Scope:

- Local disputes, petty crimes, day-to-day regulation.

Output:

- Orders for minor sanctions (fines, ration cuts, work assignments,
  notes on records).

### 5.2 Bishop Councils

Composition:

- Senior bishop_guild staff,
- Representatives of affected canteens, bunkhouses, clinics.

Scope:

- Conflicts in civic spaces,
- Moral/behavioral issues impacting survival infrastructure.

Output:

- Restitution plans, reassignments, bans from specific facilities,
  rare referrals up the chain.

### 5.3 Guild Councils and Arbitration Boards

Composition:

- Guild elders, technical leads,
- Possibly neutral third-party observers (other guilds, bishops).

Scope:

- Internal misconduct, sabotage accusations,
- Contract and quota disputes between guilds or with regime.

Output:

- Internal sanctions, contract rulings, recommendations to state structures,
  or veiled threats of strike/slowdown.

### 5.4 Audit Commissions

Composition:

- Central_audit_guild officials,
- Selected militia and duke_house envoys,
- Occasionally technical experts from guilds (under tight control).

Scope:

- Large-scale discrepancies,
- Alleged corruption among officials and elites.

Output:

- Formal reports that trigger high-level sanctions,
- Recommendations for structural changes, new quotas, or purges.

### 5.5 Security Tribunals

Composition:

- High-ranking militia officers,
- Espionage branch delegates,
- Trusted legal technicians loyal to duke_house.

Scope:

- High-severity security/political cases,
- Cases the regime considers too sensitive for open handling.

Output:

- Quick, often secret decisions resulting in severe sanctions,
- Limited or doctored records.

---

## 6. Ward-Level Procedural Indices

To capture how procedure “feels” in each ward, we introduce:

```yaml
case_backlog: float              # 0–1, how jammed formal paths are
informal_resolution_rate: float  # 0–1, share of cases handled outside state law
tribunal_frequency: float        # 0–1, rate of high-feared tribunals
appeal_success_rate: float       # 0–1, perceived chance appeals help
procedure_alignment_index: float # 0–1, whether formal paths align with local norms
```

Interpretation:

- **case_backlog**  
  - High: cases stall; people assume nothing will be resolved fairly or at all.

- **informal_resolution_rate**  
  - High: guilds, cartels, bishops settle most disputes; state law is peripheral.

- **tribunal_frequency**  
  - High: people fear being swept into severe paths; rumors circulate about
    who gets picked and why.

- **appeal_success_rate**  
  - High: some faith in formal redress remains; low: people see appeals as
    dangerous or pointless.

- **procedure_alignment_index**  
  - High: local customs and state procedure roughly agree on what is “fair.”  
  - Low: formal outcomes clash with what locals consider legitimate, fueling
    unrest and shadow justice.

These indices feed into behavioral models for reporting, cooperation,
resistance, and recourse to guilds or cartels.

---

## 7. Interaction with Sanctions and Rumor

### 7.1 From path to sanction

D-LAW-0001 defines sanctions; this doc defines **which paths lead to which
sanctions with what likelihood**.

Examples:

- Administrative Handling:
  - Mostly economic and record sanctions,
  - Occasional movement penalties.

- Civic Handling:
  - Resource-sharing sanctions and reassignments,
  - Rare bodily sanctions except in extreme cases.

- Guild Arbitration:
  - Heavy on economic and work sanctions,
  - Hidden bodily or terminal sanctions against insiders.

- Audit Review:
  - Structural economic sanctions, record-level reprisals,
  - Occasional high-level bodies and disappearances.

- Security Tribunals / Extrajudicial:
  - Bodily, terminal, and collective sanctions.

### 7.2 Rumor, deterrence, and perceived justice

Rumor system (D-INFO-0006) responds differently to each path:

- Fair-seeming civic or guild resolutions boost **perceived legitimacy**,
  damping unrest.
- Secretive tribunals and extrajudicial killings boost **fear** and
  **impunity_index**, driving rumor toward paranoia and martyrdom motifs.
- Case_backlog and legal_opacity produce rumors of **futility**,
  encouraging people to seek non-state protection or revenge.

Scenario authors can attach **rumor templates** (from Rumor_Templates helper)
to each forum type, describing how people talk about those processes.

---

## 8. Implementation Sketch (Non-Normative)

A minimal implementation could:

1. Represent cases as objects with category, severity, and origin data.
2. On creation, route each case to an initial path based on ward indices,
   alert level, and branch involvement.
3. At each relevant tick/phase:
   - Advance cases along their path:
     - resolve, stall, escalate, or be diverted to another path.
   - Apply sanctions selected from D-LAW-0001 appropriate to the path.
   - Update ward-level law indices (case_backlog, tribunal_frequency, etc.).
4. Generate rumor events tied to:
   - High-profile cases,
   - Perceived injustices or rare fair outcomes.
5. Allow high-level actors (duke_house, major guilds, syndicates) to
   **intervene** in paths:
   - Forcing escalation or dismissal,
   - Redirecting a case to a different forum (e.g. from audit to tribunal).

Exact numeric implementations are left to scenario and engine design;
this document supplies the conceptual skeleton.

---

## 9. Future Extensions

Potential follow-ups:

- `D-LAW-0003_Curfews_Emergency_Decrees_and_Martial_States`  
  - Formal mechanisms for locking down wards or imposing city-wide measures,
    and how these interact with garrisons, supply, and law indices.

- `D-LAW-0101_Community_Rulesets_and_Factional_Codes`  
  - A more detailed look at non-state normative systems and how their rules
    intersect or collide with state law and procedure.

- Scenario-specific procedural tweaks  
  - E.g., special commissions for major disasters, truth-and-reconciliation
    style bodies, or kangaroo courts in crisis periods.

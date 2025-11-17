---
title: Record_Types_and_Information_Surfaces
doc_id: D-INFO-0005
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-17
depends_on:
  - D-INFO-0001   # Telemetry_and_Audit_Infrastructure
  - D-INFO-0002   # Espionage_Branch
  - D-INFO-0003   # Information_Flows_and_Report_Credibility
  - D-INFO-0004   # Scholars_and_Clerks_Branch
  - D-WORLD-0003  # Ward_Branch_Hierarchies
  - D-ECON-0001   # Ward_Resource_and_Water_Economy
  - D-ECON-0002   # Dosadi_Market_Microstructure
  - D-ECON-0003   # Credits_and_FX
  - D-ECON-0009   # Financial_Ledgers_and_Taxation
---

# Record Types & Information Surfaces

> Define **where “truth” lives on Dosadi**:
> - The main types of records (numeric, narrative, ephemeral).
> - Who creates, reads, and modifies each record type.
> - Latency, retention, and default credibility.
> - The “surfaces” where information becomes visible to agents.

This document is the glue between:

- **Telemetry & audits** (hard numbers; D-INFO-0001).
- **Espionage & investigations** (stolen and contested records; D-INFO-0002).
- **Report flows & credibility models** (D-INFO-0003).
- **Scholars & clerks** (who actually keep the books; D-INFO-0004).
- **Economic structures** (water, markets, credits, ledgers; ECON docs).

It defines the common vocabulary for simulation systems that need to ask:

- *What records exist about this event?*
- *Who can see or tamper with them?*
- *How much should an agent trust them?*

---

## 1. Record Taxonomy (What Exists)

We define **six primary record families**:

1. **Telemetry Records** (meters & counters)
2. **Operational Logs** (facility-level tallies)
3. **Financial & Resource Ledgers** (double-entry books)
4. **Formal Reports & Dossiers** (narrative & summary docs)
5. **Legal & Coercive Records** (charges, confessions, interrogations)
6. **Informal & Shadow Records** (rumor files, black ledgers, private notes)

Each family has different:

- Producers (who creates it).
- Formats (numeric, textual, hybrid).
- Latency (near-real-time vs end-of-cycle).
- Mutability (append-only vs editable vs destroyable).
- Surfaces (where/how it appears to agents).
- Default **credibility weight** in the knowledge model.

---

## 2. Telemetry Records

**Source:** sensors, meters, counters, automated infrastructure (D-INFO-0001).

### 2.1 Examples

- `FLOW_METER` readings at well head and ward inlets.
- `TANK_LEVEL` measures at storage cisterns.
- `RECLAIM_OUTPUT` from recycling and dehumidifier banks.
- `TURNSTILE_COUNT` at kitchens, bunkhouses, clinics (if instrumented).
- `POWER_DRAW` for industrial or civic facilities.

### 2.2 Properties

- **Format:** numeric time series, discrete events.
- **Latency:** near-real-time to low delay (seconds to minutes).
- **Mutability:** generally append-only; modification requires:
  - Direct sensor tampering, or
  - Skilled data manipulation in telemetry archives.
- **Visibility:**
  - Raw streams: seen by technical staff, some clerks, auditors.
  - Aggregates & alerts: exposed on dashboards to ward lords, branch heads.

### 2.3 Default Credibility

- High **baseline trust**:
  - Shrunk if:
    - Sensors are known to be faulty.
    - Facility or branch has history of tampering.
- Used as:
  - Primary reference for **variance checks** vs ledgers and reports.

### 2.4 Data Shape (Sketch)

```json
{
  "record_type": "TELEMETRY",
  "source_id": "W21_TANK_03_LEVEL",
  "time": 120345,
  "value": 1832.5,
  "unit": "L",
  "quality": 0.94,
  "flags": ["auto", "trusted"]
}
```

---

## 3. Operational Logs

**Source:** facility supervisors and automated counters.

### 3.1 Examples

- `KITCHEN_SERVICE_LOG`:
  - Meals served by tier (LOW/MID/HIGH) per tick.
- `BUNK_OCCUPANCY_LOG`:
  - Number of bunks filled per sleep block.
- `CLINIC_TREATMENT_LOG`:
  - Cases handled, triage categories.
- `MAINTENANCE_TASK_LOG`:
  - Tasks completed, parts consumed, labor hours.

### 3.2 Properties

- **Format:** numeric tallies with light narrative fields.
- **Latency:** end-of-shift, end-of-day, or per-batch.
- **Mutability:** editable by:
  - Facility bosses or sub-bosses.
  - Local clerks attached to the facility.
- **Visibility:**
  - Local facility staff and branch sub-chiefs.
  - Aggregated upward to branch chiefs and clerical bureaus.

### 3.3 Default Credibility

- Medium to high:
  - **High** when:
    - Logs match telemetry & ledgers.
  - **Lowered** when:
    - Facility or boss is under suspicion.
    - Counts repeatedly diverge from sensor or ledger totals.

### 3.4 Data Shape (Sketch)

```json
{
  "record_type": "OP_LOG",
  "facility_id": "W21_KITCHEN_01",
  "time_block": "cycle_482",
  "metrics": {
    "meals_LOW": 340,
    "meals_MID": 110,
    "meals_HIGH": 18
  },
  "notes": "Short on MID rations; substituted LOW.",
  "author": "boss_W21_KITCHEN_01",
  "signoffs": ["subchief_civic_W21"],
  "flags": []
}
```

---

## 4. Financial & Resource Ledgers

**Source:** treasuries, clerks, and accounting staff (D-ECON-0009, D-INFO-0004).

### 4.1 Examples

- Ward water rights account changes.
- Market trades and FX conversions.
- Facility inventory accounts (rations, suits, parts).
- Tax and fee flows into ward and crown pools.

### 4.2 Properties

- **Format:** structured rows with:
  - `time, entity, account_id, item, delta, counterparty, source_event, annotations`.
- **Latency:** near-real-time for market & FX; batched for some internal allocations.
- **Mutability:**
  - Append-only in principle; in practice:
    - Skilled clerks can backdate or alter entries under pressure or bribe.
- **Visibility:**
  - Treasury and branch leadership see aggregates.
  - Clerks & auditors can see line-level data.
  - Most agents see at best summaries (prices, budgets, “ward broke” signals).

### 4.3 Default Credibility

- Medium–high for **official ledgers**:
  - Elevated when:
    - Telemetry and operational logs align.
  - Reduced when:
    - Repeated variance alerts.
    - Known “creative accounting” culture.
- Very low baseline for:
  - Known **black ledgers** (shadow books used by criminals, corrupt branches).

---

## 5. Formal Reports & Dossiers

**Source:** branch chiefs, facility bosses, auditors, scholars/clerks.

### 5.1 Types

- **Branch Performance Reports**
  - Civic/Industrial/Military monthly status.
- **Ward Situation Reports**
  - Compiled for lords, dukes, and sometimes the crown.
- **Audit Summaries**
  - Investigative findings and recommendations.
- **Dossiers**
  - Collected records about a person, guild, or facility.

### 5.2 Properties

- **Format:** narrative + aggregated statistics.
- **Latency:** slow; often per phase or per major incident.
- **Mutability:**
  - Draft → edited by clerks → finalized with seals.
  - Final versions are *considered* immutable but can be:
    - Withdrawn, replaced, or selectively destroyed.
- **Visibility:**
  - Highly tiered:
    - Ward-level reports: lords, branch heads, senior clerks.
    - Dossiers: investigators, espionage handlers, high nobles.

### 5.3 Default Credibility

- Strongly dependent on:
  - Credibility of the **authoring branch**.
  - Cross-checks against telemetry, ledgers, and operational logs.
- Often treated as:
  - “Official version of events” until disproven.

### 5.4 Data Shape (Sketch)

```json
{
  "record_type": "FORMAL_REPORT",
  "report_id": "W21_CIVIC_STATUS_0482",
  "scope": "ward_W21_civic",
  "period": "cycles_470-482",
  "author": "chief_admin_W21",
  "compiled_by": "clerk_bureau_W21",
  "metrics_summary": { "...": "..." },
  "narrative": "Overall ration coverage stable, with localized shortages...",
  "sources": ["TELEMETRY", "OP_LOG", "LEDGER"],
  "seals": ["lord_W21"],
  "flags": ["political_pressure:moderate"]
}
```

---

## 6. Legal & Coercive Records

**Source:** judges, investigators, interrogators, militia scribes.

### 6.1 Types

- **Charges & Indictments**
  - Formal accusations, often signed by a judge or lord’s delegate.
- **Trial Records**
  - Proceedings summaries, verdicts, penalties.
- **Confessions & Testimonies**
  - Statements extracted under various degrees of coercion.
- **Warrants & Search Orders**
  - Authorizations used by Investigators and militias.

### 6.2 Properties

- **Format:** textual, sometimes with structured charges.
- **Latency:** event-driven; appear during conflicts and investigations.
- **Mutability:**
  - In principle:
    - Durable and archived by legal/clerical offices.
  - In practice:
    - Can be altered, sealed, or “lost” under pressure.
- **Visibility:**
  - Restricted; often visible only to:
    - Legal staff, investigators, espionage branch, and relevant leaders.
  - Public posting:
    - Sometimes done for deterrence (selected cases).

### 6.3 Default Credibility

- Highly variable:
  - **Charges** may be political weapons.
  - **Confessions** are suspect if:
    - Extracted under torture.
    - Contradicted by telemetry/ledger evidence.
- In the simulation:
  - These records heavily impact:
    - Reputation, risk of arrest, and social distance.
  - Their truth value is evaluated via:
    - Cross links to other record families.

---

## 7. Informal & Shadow Records

**Source:** spies, informants, internal security, paranoid bosses.

### 7.1 Types

- **Rumor Files**
  - Handwritten or mental lists of who is suspected of what.
- **Shadow Dossiers**
  - Espionage-branch or internal security compilations.
- **Black Ledgers**
  - Off-book financial records for smuggling, bribes, secret reserves.
- **Personal Notes**
  - Private notebooks of bosses, clerks, or investigators.

### 7.2 Properties

- **Format:** free-form, highly idiosyncratic.
- **Latency:** opportunistic; updated when something “interesting” happens.
- **Mutability:**
  - Extremely mutable; owners can edit, destroy, or fabricate at will.
- **Visibility:**
  - Narrow; usually:
    - Single owner + a few trusted subordinates.
  - Espionage and Investigators:
    - Attempt to steal or replicate these for leverage.

### 7.3 Default Credibility

- Highly **context-dependent**:
  - As raw rumor: low baseline.
  - Once multiple independent shadow records agree:
    - Credibility climbs, especially if:
      - Indirect support from telemetry/ledger anomalies.
- Mechanically:
  - Feed directly into:
    - D-INFO-0003’s rumor and report credibility machinery.
    - Espionage branch decisions and investigative leads.

---

## 8. Information Surfaces (Where Records Show Up)

“Surfaces” are **points of contact** where records become visible and actionable.

We group them into:

1. **Dashboards & Control Rooms**
2. **Administrative Offices & Clerk Desks**
3. **Public Posting Boards & Media Outlets**
4. **Interrogation Rooms & Courts**
5. **Back Rooms & Safehouses**

### 8.1 Dashboards & Control Rooms

- **Users:** ward lords, branch heads, senior clerks, military coordinators.
- **Feeds:**
  - Aggregated telemetry, key ledger totals, risk & variance alerts.
- **Simulation Role:**
  - Primary surface for:
    - Macro decisions: quota allocation, sanctions, raids, subsidies.

### 8.2 Administrative Offices & Clerk Desks

- **Users:** clerks, record-keepers, middle-tier administrators.
- **Feeds:**
  - Raw or lightly-filtered ledgers, operational logs, report drafts.
- **Simulation Role:**
  - Core of:
    - Record creation, updating, and tampering.
  - Espionage targets:
    - Steal or alter documents here.

### 8.3 Public Posting Boards & Media Outlets

- **Users:** general population, small traders, rumor-mongers.
- **Feeds:**
  - Prices, quotas, ration rules, bans, announced punishments.
- **Simulation Role:**
  - Directly shapes:
    - Agent expectations (wages, prices, risks).
  - Mismatch between postings and reality:
    - Generates cynicism and rumor.

### 8.4 Interrogation Rooms & Courts

- **Users:** investigators, judges, militia captains, accused parties.
- **Feeds:**
  - Charges, testimonies, selected telemetry & ledger excerpts, dossiers.
- **Simulation Role:**
  - Strong **state update** surface for:
    - Reputation and legal status of agents and factions.

### 8.5 Back Rooms & Safehouses

- **Users:** spies, handlers, criminal bosses, corrupt officials.
- **Feeds:**
  - Shadow ledgers, rumor files, stolen documents.
- **Simulation Role:**
  - High-leverage but low-certainty:
    - Where plans are made to exploit gaps in official knowledge.

---

## 9. Credibility Weights & Combination

D-INFO-0003 defines more detailed math, but this doc specifies **default weights**:

Rough baseline (can be tuned per ward):

- Telemetry: `w_telemetry ≈ 0.8`
- Operational Logs: `w_op ≈ 0.6`
- Official Ledgers: `w_ledger ≈ 0.7`
- Formal Reports: `w_report ≈ 0.5`
- Legal Records: `w_legal ≈ 0.4`
- Shadow Records: `w_shadow ≈ 0.3`
- Rumor (unrecorded): `w_rumor ≈ 0.2`

Combination sketch for an event `E`:

```python
belief_E = normalize(
    w_telemetry * evidence_from_telemetry(E) +
    w_op        * evidence_from_op_logs(E) +
    w_ledger    * evidence_from_ledgers(E) +
    w_report    * evidence_from_reports(E) +
    w_legal     * evidence_from_legal(E) +
    w_shadow    * evidence_from_shadow(E)
)
```

Branch, ward, and agent-specific biases modulate these weights:

- Paranoid ward:
  - Down-weights official reports, up-weights shadow records.
- Highly legitimate ward:
  - Up-weights ledgers and formal reports.

---

## 10. Simulation Hooks

### 10.1 Record Metadata

All record types should share a minimal common header:

```json
{
  "record_id": "string",
  "record_type": "TELEMETRY|OP_LOG|LEDGER|FORMAL_REPORT|LEGAL|SHADOW",
  "origin_ward": "W21",
  "created_at": 120345,
  "created_by": "agent_or_role_id",
  "visibility_scope": ["branch_civic_W21", "lord_W21"],
  "credibility_base": 0.0,
  "flags": []
}
```

### 10.2 Agent Perception

Agents in the sim:

- Do **not** see all records; they see:
  - A filtered subset determined by:
    - Role, rank, faction, and access.
- Maintain:
  - A local belief state updated via the combination rules above.
- Can:
  - Act to acquire, forge, or destroy records at specific surfaces.

### 10.3 Espionage & Investigation Actions

Common actions (D-INFO-0002 hooks):

- `steal_record(record_id)`
- `forge_record(base_record_id, modifications)`
- `destroy_record(record_id)`
- `leak_record(record_id, surface="media" | "posting_board")`

Each action:

- Alters:
  - Availability, credibility, and rumor dynamics.
- May:
  - Trigger Telemetry/Audit alerts (if ledgers / telemetry archives touched).

---

## 11. Open Questions

For future ADRs / revisions:

- How much **per-agent memory** do we want to allocate to “I saw X record once”?
- Should some wards rely heavily on **oral-only traditions**, minimizing written records?
- Do we want explicit **record lifetimes** (decay / purge policies) to:
  - Enable forgetfulness and “lost archives” gameplay?
- How heavy should **document tampering mechanics** be in early prototypes?

For now we bias toward:

- A **limited but distinct** set of record types.
- Clear, simulation-friendly metadata.
- Enough richness that:
  - “Who controls which records” can become a genuine source of power.

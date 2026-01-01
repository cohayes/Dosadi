---
title: Royal_Mandates_Water_Shares_and_Vassal_Replacement
doc_id: D-ECON-0012
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2026-01-01
depends_on:
  - D-ECON-0001   # Ward_Resource_and_Water_Economy
  - D-ECON-0011   # Water_Allocation_and_Access_Control
  - D-WORLD-0002  # Ward_Attribute_Schema
  - D-WORLD-0005  # Ward_Branch_Hierarchies
  - D-LAW-0001    # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002    # Procedural_Paths_and_Tribunals / Justice_Contracts
  - D-INFO-0001   # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003   # Information_Flows_and_Report_Credibility
---

# Royal Mandates, Water Shares, and Vassal Replacement v1

## Intent

On Dosadi, **water is sovereignty**—but sovereignty must be *spent* to stay sovereign.

This document defines the core political-economic loop by which the King:
- issues mandates (products, quotas, infrastructure, population controls),
- rewards compliance with **water shares** (and privilege),
- punishes failure via **reallocation**, **sanctions**, or **replacement** of vassals,
- and keeps the system *legible enough* to control, while *opaque enough* to deny responsibility.

This is the “machine” the player lives inside:
> **Usefulness as a cog in someone else’s machine earns you water access.**

## Scope

This spec covers:
- The **Mandate Cycle** (issue → execute → audit → reward/punish → revise).
- Water share contracts for vassals/factions and their dependent wards.
- Replacement and succession mechanics (peaceful and violent).
- How legitimacy is produced through procedure (“the institution demanded it”).
- Hooks for player and agent gameplay: errands, audits, bribes, sabotage, framing, and whistleblowing.

Out of scope (handled elsewhere):
- Detailed faction formation/governance mechanics (see LAW proto-bodies).
- Detailed market pricing and FX (ECON microstructure).
- Full violence/combat systems (MIL pillar).
- Full info-security/censorship (INFO_SECURITY pillar).

---

## 1) Core Concepts

### 1.1 Mandate
A **Mandate** is a time-bounded, measurable demand from the King (or a delegated authority) that binds:
- a **recipient** (vassal faction, branch directorate, ward steward),
- a **domain** (CIVIC / IND / MIL / ESP / CLERICAL / RECLAIMERS),
- **deliverables** (outputs, behaviors, prohibitions),
- **verification** rules (telemetry, inspections, ledgers),
- and **stakes** (water share, privileges, sanctions).

Mandates must be **auditable** (or plausibly auditable). The appearance of auditability is itself a control lever.

### 1.2 Water Share
A **Water Share** is the allocative reward: liters/day (or week) granted to a faction/vassal, often subdivided:
- faction overhead (guards, clerks, workshops),
- ward allotments,
- pay/benefit pools (elite rations),
- discretionary “dark budget” (quiet favors, bribes, deniable ops).

Shares are not purely economic. They are:
- *permission to exist* near the Well,
- *status*,
- *a monopoly on mercy* within a local domain.

### 1.3 Compliance and “Procedure”
Dosadi’s moral texture relies on procedure:
- Individuals commit violence, confiscation, exile, or starvation **as procedure**.
- Responsibility is displaced upward: “take it up with my superior.”

Mechanically: when force is used under a recognized mandate/path, the actor receives:
- reduced blame,
- higher probability that witnesses interpret it as “lawful,”
- and greater institutional protection.

### 1.4 Replacement
Replacement is how the King keeps the machine *adaptive*:
- **Replace the vassal** (leadership swap, charter revocation, “reassignment”).
- **Replace the charter** (rewrite success criteria, change audit rules).
- **Replace the ward** (redistricting, forced migration, sealing/unsealing, deprivation).

Replacement is costly; it is triggered when the expected value of continued compliance falls below the value of switching patrons.

---

## 2) The Mandate Cycle (System Loop)

### 2.1 Lifecycle
1. **Issue**
   - Mandate is created and announced through authorized channels.
2. **Execution**
   - Recipient creates sub-tasks/contracts; mobilizes labor and materials.
3. **Audit & Evidence**
   - Telemetry and clerical systems collect evidence; inspectors and investigators resolve disputes.
4. **Decision**
   - Reward, punish, revise, or defer.
5. **Propagation**
   - Updated protocols are posted; enforcement begins.
6. **Memory**
   - Episodes are logged; narratives are shaped (success stories, scapegoats, “accidents”).

### 2.2 Mandate Cadence
Mandates exist on multiple cadences:
- **Daily/Weekly**: rations quotas, patrol targets, work rosters.
- **Monthly/Seasonal**: facility upgrades, training quotas, cleanup drives.
- **Campaign-level**: population reduction, ward consolidation, coup purges.

Cadence matters because *audit latency* becomes a vulnerability:
- If audits are slow, recipients can “win on paper” before reality catches up.

---

## 3) Data Model (Minimum Viable)

### 3.1 Entities
**Mandate**
```json
{
  "mandate_id": "mand:K-12-073",
  "issuer": "faction:king",
  "recipient": "faction:vassal_iron_ward",
  "domain": "INDUSTRIAL|CIVIC|MIL|ESP|CLERICAL|RECLAIM",
  "title": "Pump Seal Replacement Campaign",
  "start_tick": 120000,
  "end_tick": 240000,
  "success_metrics": [
    {"key": "facility_uptime", "target": 0.96, "scope": "ward:12"},
    {"key": "leak_rate", "target": 0.009, "scope": "ward:12"}
  ],
  "verification": {
    "telemetry_required": ["meter:WELL_12_OUT", "meter:WARD12_RES_A"],
    "inspection_min": 3,
    "ledger_required": ["LEDGER_PARTS", "WORK_ORDERS"]
  },
  "stakes": {
    "water_share_delta_if_pass": +0.05,
    "water_share_delta_if_fail": -0.10,
    "sanctions_if_fail": ["FINE", "PERMIT_SUSPEND", "LEADERSHIP_REVIEW"]
  },
  "reason_codes": ["SAFETY", "EFFICIENCY", "EMERGENCY"],
  "classification": "PUBLIC|RESTRICTED|SECRET",
  "status": "ISSUED|ACTIVE|AUDIT|ADJUDICATED|CLOSED"
}
```

**WaterShareContract**
```json
{
  "contract_id": "share:king->vassal_iron_ward:2026Q1",
  "grantor": "faction:king",
  "grantee": "faction:vassal_iron_ward",
  "W_base_lpd": 120000,
  "W_bonus_lpd": 0,
  "W_discretion_lpd": 6000,
  "review_cadence_days": 14,
  "linked_mandates": ["mand:K-12-073"],
  "revocation_risk": 0.12,
  "notes": ["bonus tied to uptime", "discretion for emergencies"]
}
```

**ReplacementCase**
```json
{
  "case_id": "repl:ward12:case_004",
  "trigger": "MANDATE_FAILURE|AUDIT_DISCOVERY|UNREST|COUP_ATTEMPT",
  "target": "faction:vassal_iron_ward",
  "options": ["WARN", "SANCTION", "CHARTER_REWRITE", "LEADERSHIP_SWAP", "FULL_REPLACE"],
  "decision_tick": 248000,
  "chosen": "LEADERSHIP_SWAP",
  "justification": ["PUBLIC_SAFETY", "THEFT", "INSUBORDINATION"],
  "evidence_bundle": ["audit:12:Q1", "witness_set:19", "cam:gateA:clips"],
  "enforcement_chain": ["mil:ward_captain", "clerical:arbiter_7"]
}
```

### 3.2 Key State Variables (per faction/vassal)
- `water_share_ratio` (0–1): fraction of baseline allocation currently held.
- `loyalty_to_king` (0–1): political alignment (used for protection/forgiveness).
- `performance_index` (0–1): rolling score from mandate outcomes.
- `audit_risk` (0–1): probability of deeper review, driven by discrepancies.
- `legitimacy` / `corruption` (0–1): governance metrics.
- `retributive_index` / `arbiter_consistency`: law metrics shaping violence legitimacy.

---

## 4) Success Metrics and the “Gameable Gap”

### 4.1 Metric Types
Mandates prefer metrics that can be measured:
- **Production/Throughput**: kg/day, lots/day, uptime.
- **Security**: incidents per week, contraband seizure count.
- **Civic**: queue incident rate, clinic caseload, permit backlog.
- **Espionage**: “useful reports,” interdictions, disruption success.
- **Clerical**: audit closure rate, ledger reconciliation accuracy.
- **Reclaimers**: recovery rates, contamination containment.

### 4.2 The Gameable Gap
Every metric creates a shadow:
- Meeting quotas **on paper** while diverting real output.
- Creating “engineered accidents” that justify emergency allocations.
- Suppressing reports to maintain “stability.”

Mechanically:
- Each mandate has a `gap` parameter representing exploitability:
  - Higher gap ⇒ easier to falsify success and avoid immediate punishment,
  - but increases long-term `audit_risk` due to discrepancies.

---

## 5) Punishment, Reward, and Legitimacy

### 5.1 Reward Menu
Rewards are not only water:
- `ΔW_share` (more water for the vassal/ward),
- expanded permit authority (licenses, movement privileges),
- protected status (“VIP cog” shielding),
- discretionary violence rights (expanded arrest/seizure scope),
- access to better suits, parts, narcotics allotments.

### 5.2 Punishment Menu
Punishments follow LAW sanction types:
- water share reductions,
- fines/taxes, debt claims,
- permit suspension,
- forced labor levies,
- confiscation of assets,
- exile/relocation,
- leadership review (soft threat),
- leadership removal / charter revocation.

### 5.3 Procedural Legitimacy (Tone Law)
A punishment is *stable* when it is legible as procedure:
- posted reasoning,
- chain-of-command signatures,
- ritualized hearing (even if rigged),
- and a narrative that frames it as necessity.

Mechanically: “procedural legitimacy” reduces unrest spillover and vendetta escalation *unless* counter-evidence spreads.

---

## 6) Replacement and Succession Mechanics

### 6.1 Replacement Triggers
Replacement becomes likely when one or more thresholds are crossed:
- repeated mandate failures within a window,
- telemetry/ledger discrepancies beyond tolerance,
- unrest exceeds a ward-level limit,
- coup plot indicators,
- loss of military confidence,
- reputational collapse among key audiences.

### 6.2 Replacement Options (Escalation Ladder)
1. **Warning**
2. **Targeted Sanctions**
3. **Audit Commission / Arbiter Review**
4. **Charter Rewrite** (change the rules midstream)
5. **Leadership Swap** (replace figureheads; preserve structure)
6. **Full Replace** (install new vassal; seize assets; redistrict)

Each step:
- has a cost in violence, disruption, and legitimacy,
- but can increase control and future compliance.

### 6.3 Succession Patterns
Common patterns (choose per worldgen seed):
- **Heir Apparent**: internal successor groomed by the King.
- **Auction**: competing factions bid with promises (and hostages).
- **Emergency Appointment**: military installs “temporary” command.
- **Quiet Coup**: espionage removes leadership and manufactures cause.

---

## 7) Player Hooks (Cog-Level Gameplay)

Players do not control the system; they **work inside it**.

### 7.1 Entry Roles (per branch)
The player can take early roles aligned with the big service categories:
- **CIVIC**: permit runner, queue marshal, clerk aide, court messenger.
- **INDUSTRIAL**: apprentice tech, parts runner, maintenance assistant.
- **MIL**: checkpoint aide, escort, investigator’s runner.
- **ESPIONAGE**: courier, spotter, smuggler, rumor broker.
- **CLERICAL**: ledger scribe, audit assistant, archive runner.
- **RECLAIMERS**: retrieval aide, contamination watch, body chain handler.

### 7.2 Core “Mandate” Verbs
Mandates generate actionable verbs (not exhaustive):
- empathize, negotiate, analyze, modify, inspect, intimidate,
- conceal, sneak, record, forge.

These verbs map to:
- evidence quality,
- detection probability,
- reputation shifts by audience,
- and consequences under procedure.

### 7.3 Failure Feel Progression (Player Learning Arc)
- **I misread the system**: wrong norms/protocols; punished “fairly.”
- **I misread the people**: wrong alignment; betrayed or scapegoated.
- **I misread the physics**: attempted the impossible; died to reality.

### 7.4 Evidence and Adjudication Loop
When something goes wrong, a case is built:
- witnesses, camera clips, ledgers, telemetry anomalies.
Investigators and arbiters (formal or crooked) resolve it.

The player’s leverage is:
- providing evidence,
- destroying evidence,
- shaping witness stories,
- bribing the chain,
- or triggering a higher-level audit that shifts blame upward.

---

## 8) Integration Notes (Other Pillars)

### LAW
- Mandate enforcement must call procedural paths:
  - sanction issuance, arrests, hearings, confiscations.
- Arbiter consistency modulates outcomes and player predictability.

### INFO / INFO_SECURITY
- Telemetry and audits are power tools:
  - “truth is expensive” because verification has costs and gatekeepers.
- Report credibility and channel control determine whether counter-narratives spread.

### RUNTIME / WORLD
- Mandate cadence affects global stress, legitimacy drift, and fragmentation.
- Worldgen should seed:
  - baseline water shares,
  - vassal distribution,
  - audit strictness,
  - and historical “replacement scars” (myths, riots, purges).

---

## 9) Policy Knobs (Tuning)

```yaml
mandates:
  cadence_days:
    minor: 7
    major: 28
    campaign: 180
  gap_default: 0.25              # exploitability of metrics
  audit_latency_days: 7
  audit_escalation_threshold: 0.18
  evidence_weight:
    telemetry: 0.45
    ledger: 0.25
    witness: 0.20
    video: 0.10
  procedural_legitimacy_bonus: 0.12
  scapegoat_bias: 0.20           # tendency to punish low-status actors
shares:
  base_share_floor: 0.35
  bonus_cap: 0.15
  punishment_cap: -0.30
  discretion_ratio: 0.05
replacement:
  fail_window_days: 56
  fail_threshold: 2
  unrest_threshold: 0.65
  coup_signal_threshold: 0.40
  leadership_swap_cost: 0.12
  full_replace_cost: 0.28
  vendetta_escalation_factor: 0.30
```

---

## 10) Events (Telemetry / Debug)

Emit events with enough detail to debug the machine:
- `MandateIssued`, `MandateTaskCreated`, `MandateProgressUpdated`
- `AuditOpened`, `AuditFinding`, `AuditClosed`
- `ShareAdjusted`, `PrivilegeGranted`, `SanctionIssued`
- `ReplacementConsidered`, `ReplacementExecuted`
- `ProcedureInvoked` (who invoked, what authority, what reason code)
- `EvidenceAdded`, `EvidenceDestroyed`, `WitnessStatementRecorded`

---

## 11) Pseudocode (Reference)

```python
def mandate_tick(world, tick):
    for m in active_mandates(world, tick):
        update_progress(m, world)
        if tick >= m.end_tick and m.status == "ACTIVE":
            m.status = "AUDIT"
            emit("AuditOpened", mandate=m.mandate_id)

def adjudicate_mandate(mandate, evidence_bundle):
    score = compute_score(mandate.success_metrics, evidence_bundle)
    gap = mandate_gap(mandate)
    audit_risk = discrepancy_risk(evidence_bundle, gap)
    outcome = decide(score, audit_risk, mandate.stakes)
    apply_outcome(outcome)
    emit("MandateAdjudicated", mandate=mandate.mandate_id, outcome=outcome)

def consider_replacement(faction):
    if failures_in_window(faction) >= FAIL_THRESHOLD or unrest(faction.home_ward) > UNREST_TH:
        case = open_replacement_case(faction)
        option = choose_option(case, costs, legitimacy, coup_risk)
        execute(case, option)
        emit("ReplacementExecuted", case=case.id, option=option)
```

---

## 12) Explainability (Player-Facing and Dev-Facing)

For each mandate and share adjustment, keep:
- “why” in plain language:
  - which metric failed,
  - what evidence was used,
  - what procedure was invoked,
  - who signed it,
  - what alternatives were considered.
- counterfactual:
  - “If uptime +3% or leak_rate −0.002, share would not have been reduced.”
- blame chain trace:
  - which actor was punished, and why the institution claims it was necessary.

This is critical to making Dosadi playable:
- the world must be harsh,
- but not random,
- and not opaque without recourse.

---

### End of Royal Mandates, Water Shares, and Vassal Replacement v1

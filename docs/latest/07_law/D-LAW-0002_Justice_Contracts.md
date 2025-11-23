---
title: Justice_Contracts
doc_id: D-LAW-0002
version: 1.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-11
depends_on:
  - D-RUNTIME-0001    # scheduler/events
  - D-ECON-0001       # economy signals (fines, penalties)
  - D-LAW-0001        # Law & Governance Core (if separate)
includes:
  - D-LAW-0003        # Evidence Scoring (extracted if needed)
---

# Overview
Consolidates **Law_and_Contract_Systems (v1)**, **Contract_and_Case_State_Machines (v1)**, and **Case_Evidence_Scoring (v1)** into a single operational spec for contracts, disputes, and adjudication.

## Scope
- Contract lifecycle (draft → active → breach → remedy/closure).
- Case workflow and state machines.
- Evidence scoring and decision thresholds.
- Events, penalties, and integration with economy/security.

---

## Interfaces (Inputs/Outputs)
### Inputs
- Contract objects (parties, terms, collateral, jurisdiction).
- Incidents (breach events, claims, counterclaims).
- Evidence submissions (type, source, weight, chain-of-custody).
- Governance/legitimacy signal for venue weighting.

### Outputs
- **Events**:
  - `ContractCreated {id, parties, hash}`
  - `CaseOpened {case_id, contract_id, jurisdiction}`
  - `EvidenceSubmitted {case_id, ev_id, type, weight}`
  - `JudgmentIssued {case_id, outcome, penalties}`
  - `ContractClosed {id, reason}`
- **State updates** to parties (reputation, reliability) and to economy (fines, confiscations).

**Contracts**
- All contracts hashed (`sha256`) with canonical serialization.
- Remedies must specify units (credits, barrels, labor-hours) & time-to-pay.

---

## Data & Schemas
### Contract
| field | type | notes |
|---|---|---|
| id | UUID | |
| parties | list<AgentID> | may include faction |
| terms | map | normalized clauses |
| collateral | map | assets pledged |
| venue | enum | court/arbitration |
| jurisdiction | enum | ward/faction |
| hash | bytes32 | canonical digest |

### Case
| field | type | notes |
|---|---|---|
| case_id | UUID | |
| contract_id | UUID | optional (torts without contract) |
| stage | enum | OPEN, HEARING, DELIBERATION, JUDGMENT, CLOSED |
| judge | AgentID | |
| ledger | list<EventID> | audit trail |

### Evidence
| field | type | notes |
|---|---|---|
| ev_id | UUID | |
| type | enum | {testimony, document, physical, telemetry} |
| source | AgentID/Faction | provenance |
| weight | float | base reliability (0..1) |
| chain | list | custody record |
| hash | bytes32 | content digest |

---

## Algorithms / Logic
### State machines
**Contract:** DRAFT → ACTIVE → (BREACH?) → REMEDY → CLOSED  
**Case:** OPEN → HEARING → DELIBERATION → JUDGMENT → CLOSED

Transitions are driven by events and guard conditions (collateral posted, deadlines met, quorum present).

### Evidence scoring
Let base weight \(w\in[0,1]\); adjust by source reliability \(r\) and chain integrity \(q\).  
\[
W = w\cdot (\lambda_r r + \lambda_q q)\qquad
\text{Decision threshold: } \sum W \ge \tau
\]
Default: \(\lambda_r=0.6,\lambda_q=0.4,\tau=0.7\).

### Remedies
- Monetary: credits fine; schedule with penalties for delay.
- In-kind: barrels or labor-hours; escrow integration available.
- Mixed: split remedy across units with conversion indices.

### Reputation & reliability
Judgments propagate to parties’ reliability/legitimacy scores with decay \(\rho\).

---

## Runtime Integration
- **Phases**: Intake (OPEN), Hearing, Deliberation, Judgment, Enforcement.
- **Events produced**: as above; all with TTL and priority for scheduler.
- **Economy hooks**: fines/escrow update the market & FX indices.
- **Security hooks**: breach of judgment spawns `SecurityIncident` for enforcement.

---

## Examples & Test Notes
- **Late delivery**: compute penalties; verify collateral seizure on default.
- **Conflicting testimony**: low chain integrity drops below \(\tau\).
- **Faction court**: venue bias modifies \(\tau\) via legitimacy.

### Test checklist
- ✓ Deterministic hashing of contracts.
- ✓ Case transitions are guarded; no illegal skips.
- ✓ Judgment events create economy adjustments atomically.

---

## Open Questions
- Should faction courts emit public bulletins (rumor coupling)?
- Do we need appellate stages or just retrial via new case?

## Changelog
- 1.1.0 — Merge of Law & Contract Systems, Case State Machines, Evidence Scoring.


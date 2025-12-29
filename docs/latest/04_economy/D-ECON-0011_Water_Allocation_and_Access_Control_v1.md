---
title: Water_Allocation_and_Access_Control
doc_id: D-ECON-0011
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-29
depends_on:
  - D-ECON-0001   # Ward_Resource_and_Water_Economy
  - D-WORLD-0002  # Ward_Attribute_Schema
  - D-WORLD-0005  # Ward_Branch_Hierarchies
  - D-LAW-0001    # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002    # Justice_Contracts / Procedural_Paths_and_Tribunals
  - D-INFO-0001   # Telemetry_and_Audit_Infrastructure
---

# Water Allocation and Access Control v1

## Intent

Water is not “money” in Dosadi. Water is **sovereignty**.

This spec defines the **allocation ladder** (Well → Crown → vassals/branches → wards → facilities → persons) and the **access-control surfaces** (permits, checkpoints, ledgers, audits) that make “water goes to useful cogs” true in practice.

This document is written to support:
- **Simulation correctness** (flows, quotas, leak detection, sanctions)
- **Phase evolution** (Golden Age → Realization of Limits → Dark Age)
- **Embodied play** (a player-cog can gain/lose access via jobs, favors, procedure)
- **Tier‑3 learning hooks** (policy levers + measurable outcomes)

Non-goals: hydrology/chemistry realism, detailed pipe physics, or UI/dashboard design.


## Glossary (operational)

- **Well**: the single potable source. The only origin of “legitimate” water.
- **Unit**: smallest accounted water unit (choose one: liters, “sips”, or abstract `WU`).
- **Allocation**: planned assignment of units to an org or area (budget).
- **Entitlement**: person-level right to receive units over time (payroll/rations).
- **Permit**: authorization to be *present* at a water surface (facility, queue, route).
- **Credential**: proof token for a permit/entitlement (badge, seal, ledger key).
- **Ledger truth**: what “counts” institutionally (auditable records).
- **Witness truth**: what people believe happened (rumor/witness statements).
- **Leakage**: water moved outside authorized accounting (theft, corruption, loss).
- **Vassal share**: water budget assigned by Crown authority to an enforcing group.


## Design principles

1) **Water is payroll, not loot.** People don’t “find” water; they are *paid* access.
2) **Procedure is reality.** Access is governed by permits, logs, and checkpoints.
3) **Scarcity politicizes.** Phase shifts increase enforcement, stratification, violence.
4) **Leakage is inevitable.** Control is a contest between audits and evasion.
5) **Embodied leverage.** A cog influences outcomes via info, relationships, procedure.


## Allocation ladder (who decides what)

### Level 0 — Well origin (Crown control)
- Output: `well_yield_per_tick` (or per day), plus buffers/reserves.
- Crown defines:
  - reserve targets (how much to hold back)
  - emergency release conditions
  - secrecy policy about finiteness (Phase 1)

### Level 1 — Crown budget to vassals / branches
Crown assigns **shares** to:
- royal loyalists / palace apparatus
- major vassals (duke houses / gangs with enforcement jurisdiction)
- branch-wide allocations (civic, industrial, military, espionage, clerical)
- reclaimers (special hazard budgets)

This is where “useful cogs” becomes organizational:
> A vassal that sustains control, meets mandates, and prevents unrest is watered.

### Level 2 — Branch → ward allocations
Each branch distributes its share across wards using local metrics:
- ward population, productivity, hazard load
- political loyalty / compliance
- strategic value (industry hubs, transit chokepoints, archive centers)

### Level 3 — Ward → facility quotas
Facilities (bunkhouses, food halls, clinics, workshops, checkpoints) receive quotas:
- daily ration budgets
- “worksite hydration” budgets
- emergency/triage budgets
- “discipline budgets” (punitive cuts, conditional releases)

### Level 4 — Facility → individual entitlements
Individuals receive water via entitlements tied to:
- role/job and schedule
- housing status (bunkhouse assignment)
- dependents (if recognized by civic records)
- sanctions status (curfews, probation, ration cuts)
- patron overrides (VIP pulls)


## Access control surfaces

### A) Physical surfaces (where water is dispensed)
- Wellhead / main cistern gates (highest security)
- ward cisterns / barrel depots
- food halls / soup kitchens
- clinics / triage stations
- industrial hydrators (worksite)
- reclaimer staging caches

### B) Control points (how you get approved)
- **Queues** (social + procedural choke point)
- **Checkpoints** (inspection + credential verification)
- **Clerks** (ledger entries, permit issuance, reconciliation)
- **Guards** (discretion, bribes, “procedure demanded it”)
- **Auditors** (post-hoc reality; detect leakage and fraud)


## Credentials, permits, and entitlements

### Credential types (v1 set)
- **Badge/Seal**: branch/ward affiliation marker (visual + serial).
- **Ledger key**: cryptographic-ish token (simulated), binds to a person/org.
- **Paper permit**: printable, forgeable, but auditable by serial reconciliation.
- **Ration chit**: single-use token redeemed at facility.
- **Escort order**: temporary “jurisdiction bubble” to move through checkpoints.

### Permit lifecycle
1. Issue (by an authorized clerk / officer)
2. Activate window (time & location bounded)
3. Verify (checkpoint / facility)
4. Redeem or expire
5. Reconcile (ledger aggregation)
6. Audit (spot checks; cross-ward)

### Revocation triggers
- sanctions applied (court / arbiter)
- flagged for contraband / theft suspicion
- affiliation change (fired, exiled, transferred)
- Phase tightening (martial state, emergency decree)


## Leakage, corruption, and black markets (expected behavior)

Leakage channels:
- pilfering at depots and in transit
- falsified headcounts at facilities
- counterfeit permits/chits
- bribed checkpoint discretion
- “lost barrels” attributed to hazard/maintenance
- VIP skimming and patronage kickbacks

Detection channels:
- reconciliation gaps (quota vs redemption)
- anomaly telemetry (flow spikes, route deviations)
- whistleblowers (rumor + witness truth)
- targeted audits after unrest events

Design stance:
- leakage is *never* zero
- the system aims for **acceptable leakage** under stability constraints
- Phase 2 weaponizes audits as political tools


## Phase behavior (how this evolves)

### Phase 0 — Golden Age baseline
- more transparent quotas
- broad “minimum hydration” entitlements
- sanctions exist but are infrequent
- audits focus on safety and throughput

### Phase 1 — Realization of Limits
- secrecy, compartmentalization of yield data
- ration multipliers begin diverging by ward/branch
- permit friction increases (more checkpoints, more paperwork)
- rumor becomes a strategic threat to legitimacy

### Phase 2 — Dark Age (main gameplay)
- water stratification becomes overt and normalized
- narcotics + propaganda are used to manage unrest and compliance
- enforcement discretion expands (“procedure demanded it”)
- audits become punitive and factional
- violence is common; survivable violence requires:
  - **A) jurisdictional cover** or
  - **B) deniable initiation**


## Gameplay hooks (embodied cog)

A player-cog can influence water access by:
- **job selection** (branch affiliation grants entitlements and permits)
- **procedure mastery** (knowing what’s checked, when, and by whom)
- **relationships** (patrons, favors, bribes, protection claims)
- **information advantage** (shift schedules, find lax checkpoints, expose leakage)
- **fabrication/forgery** (create or alter ledger truth at risk)
- **petitioning** (formal requests, exceptions, emergency grants)

Typical “water drama” scenarios:
- your entitlement window doesn’t match your work shift
- a clerk “misfiles” your badge renewal
- a checkpoint changes its inspection strictness midweek
- your ward quota is cut because a rival ward’s unrest is blamed on you
- an audit is used as a factional purge


## Data model (minimal v1)

### Core records
- `WaterAccount`
  - `account_id` (ward/org/facility/person)
  - `balance_units` (optional; often planned budgets rather than balances)
  - `allocation_budget_units_per_day`
  - `reserve_target_units`
- `Entitlement`
  - `person_id`
  - `units_per_day`
  - `windows[]` (time/location)
  - `issuer_org_id`
  - `sanction_modifiers[]`
- `Permit`
  - `permit_id`, `holder_id`
  - `scope` (route/facility/queue)
  - `valid_from`, `valid_to`
  - `issuer_id`, `issuer_org_id`
  - `revoked_at?`, `revoked_reason?`
- `LedgerEntry`
  - `entry_id`, `timestamp`, `actor_id`
  - `entry_type` (issue/redeem/reconcile/revoke/audit)
  - `subject_ids[]` (permit, person, facility)
  - `units_delta`
  - `evidence_refs[]` (camera log, witness id, note)
- `AuditEvent`
  - `audit_id`, `scope`
  - `findings[]` (anomalies, suspected fraud)
  - `recommended_actions[]` (sanctions, protocol changes)

### Eventing (runtime integration)
Emit events suitable for:
- reconciliation
- rumor seeding (“ward quota cut”)
- enforcement response
- Tier‑3 learning logs

Suggested events:
- `water.allocation.set`
- `water.entitlement.issued`
- `water.permit.verified`
- `water.units.dispensed`
- `water.ledger.reconciled`
- `water.audit.findings`
- `water.sanction.applied`


## Tier‑3 ML / RL readiness hooks (non-binding)

### Policy levers (actions)
- set ward ration multipliers by branch
- allocate audit budget (frequency/strictness) per ward
- set checkpoint inspection intensity schedules
- choose sanction defaults for leakage/fraud
- choose secrecy policy about yield data (Phase 1)

### Observables (state/features)
- mortality/dehydration incidents
- unrest / violence incidents
- production output (industrial)
- compliance rates (permits honored vs bypass attempts)
- leakage estimates (reconciliation gaps)
- rumor volatility / credibility around “Well finiteness”

### Rewards (examples)
- maximize stability and output while keeping mortality below threshold
- minimize unrest while maintaining reserve targets
- maximize long-term Well longevity under legitimacy constraints


## Implementation checklist (Codex-facing)

1) Add this doc to `docs/latest/04_economy/`.
2) Ensure `D-ECON-0001` references this doc as the “access-control & permits” companion.
3) Add minimal record types (`Entitlement`, `Permit`, `LedgerEntry`, `AuditEvent`) in the economy domain model.
4) Add event emissions (names above) to the world event bus layer.
5) Add a first-pass reconciliation loop:
   - facility redemption totals vs facility quotas
   - ward totals vs branch allocation
   - emit `water.audit.findings` when thresholds exceeded
6) Add a simple permit verifier usable by checkpoints and facilities.
7) Add Phase hooks:
   - Phase 0: lower friction defaults
   - Phase 1: secrecy + diverging multipliers
   - Phase 2: stratification + punitive audits


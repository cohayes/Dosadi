---
title: Service_Branch_Entry_Roles_and_Career_Ladders
doc_id: D-ECON-0013
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2026-01-01
depends_on:
  - D-WORLD-0005   # Ward_Branch_Hierarchies
  - D-ECON-0010    # Work_and_Labor_Markets
  - D-ECON-0011    # Water_Allocation_and_Access_Control
  - D-ECON-0012    # Royal_Mandates_Water_Shares_and_Vassal_Replacement
  - D-LAW-0001     # Sanction_Types_and_Enforcement_Chains
  - D-LAW-0002     # Procedural_Paths_and_Tribunals / Justice_Contracts
  - D-INFO-0001    # Telemetry_and_Audit_Infrastructure
---

# Service Branch Entry Roles & Career Ladders v1

## 1) Intent

Dosadi is a labor economy where **water access is earned by usefulness**.

This document defines:

- how the five service branches (CIVIC / INDUSTRIAL / MILITARY / ESPIONAGE / CLERICAL) + RECLAIMERS
  expose **entry-level roles**,
- how those roles climb into **middle management** and **protocol authors** (Tier-2/Tier-3),
- and how “what you can do” is expressed as a shared **action grammar** (verbs), rather than bespoke class kits.

It is deliberately dual-use:

- **simulation**: job generation, staffing, training, promotions, capture, and replacement
- **player**: “what can I do in the world?” and “how do I become harder to replace?”

## 2) Core Concepts (Definitions)

**Branch**  
A citywide service domain with a recognizable mission, protocols, and status hierarchy. Branches are *institutional machines*.

**Role**  
A named slot within a branch (e.g., *Queue Marshal*, *Pump Tender*, *Gate Inspector*). Roles carry:
- authority scope (what you can demand / inspect / seize / record),
- obligations (what procedures you must follow),
- and access (where you can go, what you can touch, baseline water ration tier).

**Career Ladder**  
A directed graph of roles (not a single line). Promotions are not “level ups”; they are **institutional bets**:
the org trades you more access and water in exchange for higher leverage and higher liability.

**Credential**  
A permit, license, oath, or ritual mark that makes your role legible in the system (ID seals, stamped ledgers,
colored armbands, clinic tags, guild rings, etc.). Credentials are both *safety* and *chains*.

**Sponsorship**  
A superior vouching for you. Sponsorship is how most ladders really move in Dosadi.

## 3) The Branches as “Machines”

This is a *role-feel* summary to keep all ladders aligned.

### CIVIC (order at the human scale)
- Runs: bunkhouses, food halls, clinics intake, local queues, low-level courts.
- Wins by: preventing daily chaos; settling disputes before they become riots.
- Corrupts by: selling “smoothness” (permits, queue priority, case outcomes).

### INDUSTRIAL (matter, energy, and throughput)
- Runs: extraction, manufacturing, maintenance, power, HVAC/canopy, condensers, workshops.
- Wins by: keeping the physical city alive; meeting mandates.
- Corrupts by: quota games, “engineered accidents,” parts skims.

### MILITARY (force, checkpoints, and jurisdiction)
- Runs: patrols, gates, inspections, detentions, punitive raids (often “procedural”).
- Wins by: visible dominance; credible retaliation.
- Corrupts by: protection rackets, selective enforcement, “accidental” violence.

### ESPIONAGE (information control and shadow logistics)
- Runs: informants, smuggling, sabotage, counter-surveillance, rumor shaping.
- Wins by: asymmetry (knowing first, striking first, framing first).
- Corrupts by: blackmail economies, planted evidence, engineered feuds.

### CLERICAL (records as reality)
- Runs: ledgers, audits, permits, case files, charters, precedent, census, quotas.
- Wins by: making the world legible; making procedure enforceable.
- Corrupts by: redaction, forgery, backdating, “vanishing” people.

### RECLAIMERS (the king’s sacred maintenance arm)
- Runs: reclamation infrastructure, corpses/waste processing, suit recovery, salvage rights.
- Wins by: making waste into water; controlling the dead; controlling the margins.
- Corrupts by: “accidental” losses, selective salvage, protected brutality.

## 4) Action Grammar v1 (Shared Verbs)

The player and agents should not think “I am a class,” but rather:
> “I can do these verbs, in these places, under these procedures, with these risks.”

### 4.1 Canonical verbs (starter set)

- **Empathize** (read intentions, detect lies, vibe checks)
- **Negotiate** (trade, bargain, recruit, threaten-with-terms)
- **Analyze** (diagnose, appraise, infer condition, spot anomalies)
- **Modify** (repair, assemble/disassemble, improvise, sabotage)
- **Inspect** (search people/cargo, verify seals, validate permits)
- **Intimidate** (coerce through credible violence / jurisdiction)
- **Conceal** (hide objects, launder provenance, reduce detectability)
- **Sneak** (move unseen; route choice + timing + posture)
- **Record** (create legible logs; certify truth; create official memory)
- **Forge** (misrepresent logs; counterfeit permits; reshape memory)

You can extend later with: *Treat (medical)*, *Reclaim (salvage)*, *Teach (training)*, *Command (unit control)*.

### 4.2 Verb → Branch affinity (defaults, not locks)

- CIVIC: Empathize, Negotiate, Inspect, Record
- INDUSTRIAL: Analyze, Modify, Record
- MILITARY: Inspect, Intimidate, Record
- ESPIONAGE: Conceal, Sneak, Forge, Empathize
- CLERICAL: Record, Analyze, Inspect, Forge
- RECLAIMERS: Modify, Inspect, Intimidate, Record

### 4.3 Verb outcomes (what the sim should output)

Each verb produces:

1. **World effects** (objects moved/changed, doors opened, people delayed, equipment fixed)
2. **Institutional effects**:
   - legitimacy change (small, local),
   - “paper reality” change (records updated),
   - heat/suspicion change (per INFO + LAW),
3. **Personal effects**:
   - reputation deltas by faction,
   - reliability deltas (for labor),
   - injury/heat-stress risks (for physical verbs),
   - memory episodes (for future beliefs).

## 5) Entry Roles (what a new cog can plausibly be)

These are *templates* for worldgen and the starting job board. Each role should be generated per ward with:
- employer identity (ward office / guild / unit),
- venue (kitchen, gate, clinic, plant, archive),
- baseline ration tier (probationary → standard),
- and a procedural “what you must do” list.

### 5.1 CIVIC entry roles
- **Queue Attendant** (food hall / water line): Inspect (tokens), Empathize (tension), Record (incidents).
- **Bunkhouse Steward’s Runner**: Record deliveries, Negotiate small favors, carry messages.
- **Clinic Intake Aide**: Empathize triage, Record symptoms, Inspect credentials.
- **Minor Case Clerk**: Record case intake, schedule hearings, maintain dockets.

### 5.2 INDUSTRIAL entry roles
- **Workshop Apprentice**: Modify (basic repairs), Analyze (diagnostics), Record (parts used).
- **Pump/Valve Tender**: Inspect seals, Modify adjustments, Record flows (links to telemetry).
- **Runner for Parts Guild**: Negotiate deliveries, Inspect manifests, Conceal (if bribed).

### 5.3 MILITARY entry roles
- **Gate Assistant**: Inspect cargo, Record entries, Intimidate (soft) under supervision.
- **Patrol Junior**: Presence + report writing; observe routines; escalate to senior.
- **Detention Aide**: Escort, Record, Inspect; high corruption risk.

### 5.4 ESPIONAGE entry roles
- **Courier (Shadow)**: Sneak routes, Conceal packages, Empathize target moods.
- **Watcher**: Observe patterns, Record privately, Negotiate info trades.
- **Smuggle Loader**: Conceal goods, Inspect “safe” compartments, coordinate timing.

### 5.5 CLERICAL entry roles
- **Ledger Copyist**: Record faithfully; learn stamps/format; become forgery-capable later.
- **Permit Counter**: Inspect seals, Record renewals, Reject/approve by procedure.
- **Audit Runner**: Collect meter readings and receipts; a walking source of leverage.

### 5.6 RECLAIMER entry roles
- **Salvage Sorter**: Inspect finds, Record claims, Modify (strip gear safely).
- **Waste Hauler**: Intimidate-by-presence, procedural authority, high hazard pay.
- **Suit Recovery Aide**: Inspect seals, Modify patching, Record provenance.

## 6) Career Ladders (promotion as institutional leverage)

### 6.1 Generic ladder structure

Most ladders follow a pattern:

1. **Probation role** (low access; easy to replace)
2. **Credentialed operator** (touches critical systems; water tier increases)
3. **Specialist** (harder to replace; becomes a choke point)
4. **Supervisor / Team lead** (Tier-2): allocates shifts, signs logs, controls small sanctions
5. **Protocol author / Auditor / Captain / Master** (Tier-3): writes procedure; shapes reality

### 6.2 Promotion gates (what must be true)

Promotions should be gated by *a mix* of:

- **Reliability** (no-show rate, task completion, incident rate)
- **Skill threshold(s)** (branch verbs; measured by outcomes and training)
- **Credential** (license, oath, stamp access)
- **Sponsorship** (a superior’s risk tolerance + faction politics)
- **Risk tolerance** (for dangerous postings; “hazard premium” jobs)
- **Cleanliness** (cases, sanctions, investigation flags; may be falsified)
- **Faction standing** (vendettas and protection matter)

### 6.3 Lateral moves (changing machines)

Changing branches is allowed but expensive:
- requires a **new sponsor** and usually a **new credential**,
- creates enemies (old org reads it as betrayal),
- and changes what your failures “mean” (misread system vs misread people).

This supports your intended failure arc:
1) misread norms → 2) misread alignments → 3) misread physics.

## 7) Water Access Coupling (the paycheck that matters)

Water access is the branch’s main lever.

Mechanically:
- each role has a **ration tier** and a **water risk** (how easily it can be suspended),
- disciplinary actions and investigations can trigger:
  - temporary ration cuts,
  - “probation” rations,
  - forced relocation to a punitive ward,
  - or protected status if you’re “too useful.”

This doc does not replace D-ECON-0011; it defines how access is *experienced* through work.

## 8) Simulation Hooks (Data Model)

Minimal structures (names flexible):

```python
@dataclass
class RoleArchetype:
    role_id: str                  # e.g. "civic.queue_attendant"
    branch: str                   # CIVIC/IND/MIL/ESP/CLERICAL/RECLAIMER
    tier: int                     # 1/2/3
    verbs: list[str]              # action grammar surface
    venue_types: list[str]        # FOOD_HALL, GATE, PLANT, ARCHIVE, etc.
    ration_tier: str              # PROBATION|STANDARD|PRIVILEGED
    requires_credentials: list[str]
    promotion_to: list[str]       # next archetype ids
    risk_profile: dict            # {"hazard":0.2,"corruption":0.5,"visibility":0.8}
```

```python
@dataclass
class Credential:
    cred_id: str                  # "permit_stamp_A", "mil_badge_lvl1"
    issuer: str                   # org/faction id
    scope: dict                    # where it works, what it unlocks
    revocable: bool
```

Core events:
- `RoleAssigned`, `RoleRevoked`, `CredentialGranted`, `CredentialRevoked`
- `PromotionGranted`, `DemotionApplied`
- `SponsorshipChanged`
- `DisciplinaryCaseOpened` / `CaseClosed`
- `WaterRationTierChanged`

These events should feed:
- INFO (who knows; what becomes rumor),
- LAW (what procedure is invoked),
- ECON (wages, hazard premiums),
- and player UI explainability.

## 9) Policy Knobs (YAML sketch)

```yaml
careers:
  promotion:
    min_reliability: 0.65
    min_skill_delta: 1
    sponsor_weight: 0.35
    scandal_penalty: 0.25
    vendetta_penalty: 0.30
  lateral_move:
    base_cost_credits: 20
    base_cost_water_days: 1
    sponsor_required: true
  ration_by_tier:
    PROBATION: 1
    STANDARD: 2
    PRIVILEGED: 3
  role_generation:
    per_ward_min_slots:
      CIVIC: 12
      INDUSTRIAL: 10
      MILITARY: 8
      ESPIONAGE: 3
      CLERICAL: 6
      RECLAIMER: 4
```

## 10) Failure Modes & Story Cracks (Design Targets)

- **Sponsor capture**: a Tier-2 becomes a choke point; promotions become political favors.
- **Credential inflation**: too many permits → clerical bottlenecks → bribery.
- **Procedural violence**: MIL (and others) shield actions with “I followed protocol.”
- **Scapegoat demotions**: when mandates fail, someone must “take the blame” to preserve legitimacy.
- **Shadow ladders**: ESP creates parallel promotion paths via blackmail and leverage.

## 11) Implementation Notes (How to start simple)

MVP path:
1. Represent roles as **tags** on agents + a small **role registry** (archetypes).
2. Generate per-ward job postings from `per_ward_min_slots` and local facility needs.
3. Use the existing labor market utility to match agents to jobs (D-ECON-0010).
4. Add a periodic `promotion_review()` (DayTick or WeekTick) that:
   - checks reliability + skill gains,
   - applies sponsor bias,
   - emits `PromotionGranted` or `DemotionApplied`.
5. Couple ration tier to role (D-ECON-0011) with explicit events for explainability.

### End of Service Branch Entry Roles & Career Ladders v1

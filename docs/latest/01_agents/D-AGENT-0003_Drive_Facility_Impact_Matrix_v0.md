---
title: Drive_Facility_Impact_Matrix_v0
doc_id: D-AGENT-0003
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-AGENT-0001  # Agent_Core_Schema_v0
  - D-AGENT-0002  # Agent_Decision_Rule_v0
  - D-CIV-0000    # Civic_Microdynamics_Index
  - D-CIV-0001    # Civic_Microdynamics_Soup_Kitchens_and_Bunkhouses
  - D-CIV-0002    # Civic_Microdynamics_Clinics_and_Triage_Halls
  - D-CIV-0003    # Civic_Microdynamics_Posting_Boards_and_Permit_Offices
  - D-CIV-0004    # Civic_Microdynamics_Courts_and_Justice_Halls
  - D-CIV-0005    # Civic_Microdynamics_Body_Disposal_and_Reclamation
  - D-CIV-0006    # Civic_Microdynamics_Entertainment_and_Vice_Halls
---

# Drive–Facility Impact Matrix v0

> This document defines **baseline effects** of facility interactions on agent drives and stress.
> - It provides tunable defaults for the Agent Decision Rule v0 (D-AGENT-0002).
> - It links civic microdynamics (CIV docs) to the drive stack in Agent Core Schema (D-AGENT-0001).
> - It is meant to be **simple and legible**, not exact; ward- and facility-level tuning layers sit on top.

The matrix is intended as a **starting point**. Later ADRs may:

- Split facility archetypes more finely.
- Add faction-/ward-specific modifiers.
- Introduce substance-specific addiction tracks.

---

## 1. Conventions

### 1.1 Drives and Stress

We use the standard drive keys from D-AGENT-0001:

- `SURVIVAL`  – hunger, thirst, health, sleep.
- `SAFETY`    – avoiding immediate harm and punishment.
- `BELONG`    – social ties, group identity.
- `STATUS`    – rank, respect, not being humiliated.
- `CONTROL`   – autonomy, ability to shape own life.
- `NOVELTY`   – curiosity, stimulation.
- `MORAL`     – alignment with internalized codes/ethos.

Plus:

- `STRESS`    – scalar modifier that amplifies other drives.

### 1.2 Delta Semantics

All deltas are **expected changes** per “interaction block” with a facility.

- Drives are modeled as `value` in `[0, 1]`:
  - `0`   → fully satisfied.
  - `1.0` → desperate/unmet.
- A **negative delta** (e.g. `-0.3`) means:
  - The unmet-need value *decreases* (drive is more satisfied).
- A **positive delta** (e.g. `+0.2`) means:
  - Unmet-need value *increases* (need becomes more urgent).

Stress is a scalar in `[0, 1]`:

- `ΔSTRESS = -0.3` → stress is relieved.
- `ΔSTRESS = +0.2` → stress increases.

These are **baseline** deltas, before:

- Belief adjustments (e.g., unfair or unsafe facility).
- Ward tuning (e.g., harder wards might soften relief or amplify penalties).
- Personal traits and addictions.

### 1.3 Matrix Structure

For each facility interaction type we specify:

- **Context** – what interaction we are modeling.
- **Typical deltas** – suggested default scalars for:
  - `ΔSURVIVAL`, `ΔSAFETY`, `ΔBELONG`, `ΔSTATUS`, `ΔCONTROL`, `ΔNOVELTY`, `ΔMORAL`, `ΔSTRESS`.
- **Notes** – how to interpret these and where to add nuance later.

---

## 2. Kitchens & Bunkhouses (D-CIV-0001)

### 2.1 Soup Kitchen Meal

Context: agent spends a block at a civic soup kitchen, receives at least minimal rations.

| Drive     | Typical Δ   | Notes                                                        |
|----------:|------------:|-------------------------------------------------------------|
| SURVIVAL  | -0.5        | Strong relief: hydration/nutrition for the block.          |
| SAFETY    | +0.0        | Neutral; small + if queues volatile, small - if heavily policed. |
| BELONG    | -0.1        | Mild relief if regulars/own faction often present.         |
| STATUS    | +0.0        | Neutral or slight +0.05 if kitchen is “better” than usual. |
| CONTROL   | +0.05       | Mild loss of control (standing in line, dependency).       |
| NOVELTY   | +0.0        | Usually neutral; can be negative in rare “festival” events.|
| MORAL     | -0.05       | Mild relief if access feels fair/legitimate.               |
| STRESS    | -0.1        | Some relief from hunger and predictable routine.           |

### 2.2 Kitchen Rejection / Turned Away

Context: agent queues but is denied service (ration exhausted, blacklist, biased staff).

| Drive     | Typical Δ   | Notes                                                         |
|----------:|------------:|--------------------------------------------------------------|
| SURVIVAL  | +0.1        | Need remains unmet and is more salient.                      |
| SAFETY    | +0.05       | Increased sense of vulnerability.                            |
| BELONG    | +0.2        | Feels excluded; group belonging frustrated.                  |
| STATUS    | +0.1        | Public embarrassment or perceived low worth.                 |
| CONTROL   | +0.2        | Strong sense of powerlessness.                               |
| NOVELTY   | +0.0        | Neutral.                                                     |
| MORAL     | +0.2        | Code dissonance if the system is seen as unfair.            |
| STRESS    | +0.3        | Significant frustration and anxiety.                         |

### 2.3 Bunkhouse Sleep Block

Context: agent obtains a bunk and gets a meaningful rest interval.

| Drive     | Typical Δ   | Notes                                                        |
|----------:|------------:|-------------------------------------------------------------|
| SURVIVAL  | -0.3        | Sleep and mild recovery.                                    |
| SAFETY    | -0.05       | Feels a bit safer if bunk is perceived as stable.           |
| BELONG    | -0.05       | Mild sense of shared hardship if bunk is communal.          |
| STATUS    | +0.0        | Neutral; ~0.05 if bunk is “upgraded” class.                 |
| CONTROL   | -0.05       | Small relief: having a guaranteed place to sleep.           |
| NOVELTY   | +0.05       | Mild boredom: routine.                                      |
| MORAL     | +0.0        | Neutral.                                                    |
| STRESS    | -0.3        | Strong stress relief from sleep and temporary safety.       |

### 2.4 Sleeping Rough (Alley / Unlicensed Spot)

Context: no bunk; agent sleeps in unsafe or marginal space.

| Drive     | Typical Δ   | Notes                                                        |
|----------:|------------:|-------------------------------------------------------------|
| SURVIVAL  | -0.1        | Some rest but with health risk.                             |
| SAFETY    | +0.2        | Increased vulnerability to violence/theft.                  |
| BELONG    | +0.1        | Feels excluded from normal shelter.                         |
| STATUS    | +0.1        | Visible mark of marginalization.                            |
| CONTROL   | +0.1        | May feel pushed to this by lack of options.                 |
| NOVELTY   | +0.0        | Neutral or small + if eventful.                             |
| MORAL     | +0.05       | Dissonance if system “should” provide shelter.              |
| STRESS    | -0.05       | Slight physical relief, but not true recovery.              |

---

## 3. Clinics & Triage Halls (D-CIV-0002)

### 3.1 Basic Clinic Treatment (Successful)

Context: agent receives low-tier treatment for common injuries/illness.

| Drive     | Typical Δ   | Notes                                                        |
|----------:|------------:|-------------------------------------------------------------|
| SURVIVAL  | -0.4        | Significant recovery from health risk.                      |
| SAFETY    | -0.1        | Feels more secure against immediate death.                  |
| BELONG    | +0.0        | Neutral; can be -0.05 if staff show care.                   |
| STATUS    | +0.0        | Neutral; -0.05 if feels like “charity case”.                |
| CONTROL   | -0.05       | Mild relief: condition now “handled”.                        |
| NOVELTY   | +0.0        | Neutral.                                                    |
| MORAL     | -0.05       | Relief if treatment perceived as just/right.                |
| STRESS    | -0.25       | Substantial stress relief.                                  |

### 3.2 Clinic Rejection / Priced Out

Context: agent needs care but is denied (no permit, lack of funds, blacklist).

| Drive     | Typical Δ   | Notes                                                        |
|----------:|------------:|-------------------------------------------------------------|
| SURVIVAL  | +0.2        | Immediate fear of decline or death.                         |
| SAFETY    | +0.2        | System seen as unable/unwilling to protect.                 |
| BELONG    | +0.1        | Exclusion from “cared-for” group.                           |
| STATUS    | +0.1        | Humiliation at being refused.                               |
| CONTROL   | +0.2        | Strong sense of helplessness.                               |
| NOVELTY   | +0.0        | Neutral.                                                    |
| MORAL     | +0.3        | Acute dissonance at systemic unfairness.                    |
| STRESS    | +0.4        | Very high stress spike.                                     
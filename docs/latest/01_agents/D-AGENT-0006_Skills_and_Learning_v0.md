---
title: Skills_and_Learning_v0
doc_id: D-AGENT-0006
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0002   # Agent_Decision_Rule_v0
  - D-AGENT-0004   # Agent_Action_API_v0
  - D-AGENT-0005   # Perception_and_Memory_v0
  - D-RUNTIME-0001 # Simulation_Timebase
---

# 1. Purpose

This document defines the **Skills & Learning** subsystem for Dosadi agents.

It provides:

- A compact **skill representation** on the agent.
- A **skill taxonomy** oriented around survival, perception, social manipulation and work.
- A generic **skill check** mechanism used by actions (work, social, stealth, etc.).
- A **learning model** (practice + training) that updates skills over time.
- Hooks for the decision rule (D-AGENT-0002) to:
  - Predict success chances,
  - Evaluate long-term value of investing in a skill.

The intent is compatible with a **point-buy style system**, but implemented as a lightweight, Codex-friendly interface.

---

# 2. Design Goals & Constraints

1. **Point-buy compatible**  
   - Skills are discrete ranks with non-linear difficulty.
   - Higher ranks get **progressively more expensive** to improve.

2. **Attribute-informed, not attribute-dominated**  
   - Checks can incorporate base attributes (`body`, `mind`, `social`, etc.) without making skills irrelevant.
   - Attributes define *potential ceiling*; skills define *realized competence*.

3. **Practice-based learning**  
   - Agents get better by **using** skills in context (jobs, sneaking, talking, observing).
   - Training actions (future) can accelerate growth.

4. **Action-centric**  
   - Skill checks are invoked from **actions** defined in D-AGENT-0004:
     - `PERFORM_JOB`
     - `OBSERVE_AREA`
     - `TALK_TO_AGENT`
     - `REPORT_TO_AUTHORITY`
     - Later: stealth, combat, fabrication, etc.

5. **Implementation-friendly**  
   - Clear Python dataclasses & functions:
     - `Skill`, `SkillState`, `SkillCheckContext`, `perform_skill_check`, `apply_skill_xp`.

6. **Expandable**  
   - v0 defines a small core skill set.
   - New skills can be added without changing the engine.

---

# 3. Data Model

## 3.1 Skill identifiers

Skills are referenced by stable string IDs:

- `perception`
- `streetwise`
- `conversation`
- `intimidation`
- `labor_kitchen`
- `labor_industrial`
- `bureaucracy`
- `stealth`
- `medicine_basic`
- `weapon_handling`  *(placeholder; not necessarily combat-focused yet)*

These IDs are used in:

- Agent skill maps,
- Job slot requirements,
- Action handlers and Codex code.

## 3.2 Skill definition (static)

Static skill metadata lives in a registry (world-level or module-level):

```python
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass(frozen=True)
class SkillDefinition:
    skill_id: str                 # e.g. "perception"
    name: str                     # human-readable
    difficulty: str               # "easy" | "standard" | "hard" | "elite"
    primary_attribute: Optional[str]  # e.g. "mind", "social", or None
    secondary_attribute: Optional[str]
    description: str
    tags: List[str]               # e.g. ["SENSE", "SOCIAL", "WORK"]
```

A simple registry:

```python
SKILL_DEFS: Dict[str, SkillDefinition] = {}
```

Populated at setup; skills are considered immutable during runtime.

## 3.3 Skill state (per agent)

Each agent has a `SkillState` per known skill plus a container:

```python
from dataclasses import dataclass, field

@dataclass
class SkillState:
    skill_id: str
    rank: int                 # integer rank, typically 0..10
    progress: float           # 0..1 progress toward next rank
    xp_total: float           # cumulative XP for analytics / future use
    last_used_tick: int       # for decay / atrophy if needed


@dataclass
class SkillSet:
    skills: Dict[str, SkillState] = field(default_factory=dict)

    def get(self, skill_id: str) -> SkillState:
        # ensure existence; default rank 0
        ...
```

In `D-AGENT-0001`, `agent.skills: SkillSet` (or equivalent) should be defined; this doc specifies its internal semantics.

---

# 4. Skill Checks

Skill checks are used to resolve uncertain outcomes for actions.

## 4.1 SkillCheckContext

```python
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class SkillCheckContext:
    agent: Any                 # Agent instance (typed later)
    world: Any                 # World / Simulation
    skill_id: str
    base_difficulty: float     # baseline difficulty (0..1, higher is harder)
    situational_mod: float     # situational modifier (-1..1; negative = easier)
    consequence_tag: str       # e.g. "JOB_PERFORMANCE", "SOCIAL_RISK"
    tick: int
    metadata: dict             # free-form extra info (job type, target, etc.)
```

## 4.2 Effective skill score

Effective competence is a function of:

- Skill rank,
- Relevant attributes,
- Situational modifiers.

Suggested normalized score in `[0, 1]`:

```text
skill_component      = rank / RANK_MAX             # e.g. RANK_MAX = 10
attr_primary_comp    = primary_attr_value / ATTR_MAX
attr_secondary_comp  = secondary_attr_value / ATTR_MAX

effective_score =
    w_skill    * skill_component
  + w_primary  * attr_primary_comp
  + w_secondary* attr_secondary_comp
```

Where weights are runtime constants tuned per game mode (e.g. `w_skill=0.6, w_primary=0.3, w_secondary=0.1`).

## 4.3 Success probability

Difficulty is also normalized `[0, 1]`. One simple function:

```text
# Clamp difficulty into [0, 1]
difficulty = clamp(base_difficulty + situational_adjustment, 0, 1)

# Example logistic-ish success curve:
margin = effective_score - difficulty                # [-1, 1]
p_success = 0.5 + margin * curve_steepness           # curve_steepness ~ 0.4
p_success = clamp(p_success, 0.0, 1.0)
```

Codex should implement a concrete function:

```python
def perform_skill_check(ctx: SkillCheckContext, rng) -> dict:
    """
    Returns:
      {
        "success": bool,
        "p_success": float,   # probability used
        "roll": float,        # actual random draw 0..1
        "effective_score": float,
      }
    """
    ...
```

Actions like `PERFORM_JOB`, `OBSERVE_AREA`, `TALK_TO_AGENT`, `REPORT_TO_AUTHORITY` will call this to gate outcomes and set side effects.

---

# 5. Learning & XP

## 5.1 XP award model

Agents gain XP when they **attempt** skillful actions. Suggested rules:

- Always award a **base XP** on attempt, regardless of outcome (practice matters).
- Award **bonus XP** on success, especially for harder tasks.
- Optionally award slightly more XP when failing at something challenging (to model steep learning).

Example abstract rule:

```text
xp_attempt = XP_ATTEMPT_BASE * difficulty_factor
xp_bonus_success = XP_SUCCESS_BASE * difficulty_factor

IF success:
    xp_gain = xp_attempt + xp_bonus_success
ELSE:
    xp_gain = xp_attempt * XP_FAIL_MULTIPLIER    # e.g. 0.5..1.0
```

Where `difficulty_factor` rescales difficulty into a reasonable range (e.g. `1 + 2 * base_difficulty`).

Codex function:

```python
def apply_skill_xp(skill_set: SkillSet, skill_id: str, xp: float, tick: int) -> None:
    """
    Apply XP to a skill:
    - Ensure SkillState exists.
    - Convert XP into progress toward next rank.
    - Increment rank when progress >= threshold.
    """
    ...
```

## 5.2 Rank-up cost curves

Higher ranks should be more expensive. Define **XP thresholds per rank** via difficulty tier:

```python
RANK_XP_TABLE = {
    "easy":    [10, 20, 40, 80, 160, ...],
    "standard":[20, 40, 80, 160, 320, ...],
    "hard":    [30, 60, 120, 240, 480, ...],
    "elite":   [40, 80, 160, 320, 640, ...],
}
```

For each skill:

- Look up its difficulty tier.
- For current rank `r`, required XP to go to `r+1` is `RANK_XP_TABLE[difficulty][r]` (if defined).

`SkillState.progress` can be maintained as:

```text
progress_fraction = xp_since_last_rank / xp_required_for_next_rank
```

When progress reaches `≥ 1.0`, rank up:

```text
rank += 1
progress = leftover_fraction  # carry over surplus XP if desired
```

## 5.3 Atrophy / decay (optional)

Later docs may define explicit skill atrophy. For v0:

- We only **track `last_used_tick`**.
- Runtime may use that plus simple rules (e.g. if unused for N days, apply small negative XP pulses).

---

# 6. Core Skill Set (v0)

This set is intentionally small and tightly coupled to early gameplay (soup kitchen / bunkhouse / enforcement).

Each skill lists: **role**, **actions**, and **typical checks**.

## 6.1 Perception (`perception`)

- **Role:** Improve what `OBSERVE_AREA` sees and how well threats/opportunities are detected.
- **Primary attr:** `mind`
- **Actions:**
  - `OBSERVE_AREA`
  - Passive modifiers to spotting hostile agents or patrol patterns.
- **Effect examples:**
  - Better success detecting:
    - Enforcement presence,
    - Suspicious agents,
    - Hidden queues / alternative entrances.

## 6.2 Streetwise (`streetwise`)

- **Role:** Reading neighborhoods, informal rules, and black/gray markets.
- **Primary attr:** `mind`
- **Actions:**
  - Influences facility choice & route planning in decision rule.
  - Improves outcomes for:
    - `TALK_TO_AGENT` (when scoping favors, safehouses, illicit services),
    - Future actions like `FIND_FENCE`, `FIND_SMUGGLER`.
- **Effect examples:**
  - Better chance to:
    - Identify safe rumor zones,
    - Avoid obvious traps,
    - Learn about opportunities from rumors.

## 6.3 Conversation (`conversation`)

- **Role:** General social handling, persuasion, rapport-building.
- **Primary attr:** `social`
- **Actions:**
  - `TALK_TO_AGENT`
  - `REQUEST_SERVICE` (especially where discretion or charm matter).
- **Effect examples:**
  - Higher probability of:
    - Gaining cooperation,
    - Extracting useful info from conversations,
    - Reducing suspicion / improving affinity.

## 6.4 Intimidation (`intimidation`)

- **Role:** Coercion, threat display, making others back down.
- **Primary attr:** mix `body` / `social`
- **Actions:**
  - `TALK_TO_AGENT` with `"THREAT"` topics.
  - Future enforcement/bully actions.
- **Effect examples:**
  - Higher chance to:
    - Force queue cuts,
    - Extract info from frightened targets,
    - Raise long-term suspicion/resentment in others.

## 6.5 Kitchen Labor (`labor_kitchen`)

- **Role:** Efficient work in food halls (prep, serving, cleanup).
- **Primary attr:** `body` (with some `mind` / coordination)
- **Actions:**
  - `PERFORM_JOB` in soup kitchen roles.
- **Effect examples:**
  - More rations/credits per tick,
  - Lower fatigue/stress per unit work,
  - Higher chance of being retained / favored by soup staff.

## 6.6 Industrial Labor (`labor_industrial`)

- **Role:** Heavy industry, lifting, repetitive or dangerous physical work.
- **Primary attr:** `body`
- **Actions:**
  - `PERFORM_JOB` in industrial/exo-suit environments.
- **Effect examples:**
  - Better pay / output,
  - Fewer accidents,
  - Smoother use of exo-suits (when we formalize them).

## 6.7 Bureaucracy (`bureaucracy`)

- **Role:** Dealing with forms, ledgers, permits, clerks.
- **Primary attr:** `mind` / `social`
- **Actions:**
  - `REQUEST_SERVICE` in high-bureaucracy facilities.
  - Future actions involving taxes, ledgers, permits.
- **Effect examples:**
  - Higher chance of:
    - Getting assigned a bed, job, or permit,
    - Avoiding fines or administrative penalties.

## 6.8 Stealth (`stealth`)

- **Role:** Moving unseen / unnoticed.
- **Primary attr:** `body` / `mind`
- **Actions (future):**
  - `MOVE_TO_FACILITY` with stealth mode.
  - Special actions like `SHADOW_AGENT`, `SLIP_PAST_GUARD`.
- **Effect examples:**
  - Reduced detection chance by enforcement,
  - Better chance to overhear conversations.

## 6.9 Basic Medicine (`medicine_basic`)

- **Role:** First aid and low-level medical care.
- **Primary attr:** `mind`
- **Actions:**
  - Future `TREAT_AGENT`, `SELF_TREAT`.
- **Effect examples:**
  - Better recovery from injuries,
  - Lower risk when working in dangerous jobs.

## 6.10 Weapon Handling (`weapon_handling`)

- **Role:** Safe, effective use of tools as weapons (sticks, knives, improvised).
- **Primary attr:** `body`
- **Actions (future):**
  - Any action representing armed threats or defense.
- **Effect examples:**
  - Modulates threat level when others perceive the agent,
  - Improves success of intimidation when visibly armed.

---

# 7. Integration with Actions & Decision Rule

## 7.1 Skill use from actions

Each action in D-AGENT-0004 that can require skill must:

1. Determine relevant `skill_id` (if any).
2. Construct a `SkillCheckContext`.
3. Call `perform_skill_check(ctx, rng)`.
4. Apply `apply_skill_xp()` with appropriate XP.
5. Use the check result to:
   - Determine resource gain/loss,
   - Update `agent.memory`,
   - Adjust drives (stress, ambition, fear, etc.).

Examples:

- `PERFORM_JOB` → `labor_kitchen` or `labor_industrial`.
- `OBSERVE_AREA` → `perception`.
- `TALK_TO_AGENT` with `"RUMOR"` → `conversation` or `streetwise`.
- `TALK_TO_AGENT` with `"THREAT"` → `intimidation` + `weapon_handling` (if armed).
- `REQUEST_SERVICE` in bureaucratic offices → `bureaucracy`.

## 7.2 Decision rule hooks

The decision rule (D-AGENT-0002) can use skills to:

- Estimate **p_success** for candidate actions via a simulated skill check (no XP awarded).
- Compare **expected value** of:
  - Working in a job they’re good at,
  - Attempting risky skill growth,
  - Investing in social maneuvering.

Suggested helper:

```python
def estimate_action_success(agent, world, action, rng_stub) -> float:
    """
    Use the same skill check machinery with a deterministic RNG stub
    to estimate p_success for planning / decision rule.
    """
    ...
```

---

# 8. Roadmap & Extensions

Future docs building on this:

- **D-AGENT-0007_Rumor_and_Gossip_Dynamics_v0**
  - Uses `conversation`, `streetwise`, and `perception` to drive:
    - Rumor spread,
    - Rumor filtering (credibility),
    - Loyalty / betrayal calculations.

- **D-AGENT-0008_Job_Slots_and_Qualifications_v0**
  - Specifies job requirements using skill thresholds.
  - Handles advancement and role specialization.

- **D-AGENT-0009_Skill_Synergies_and_Pressure_Signals_v0**
  - Formalizes “skills in demand” signals:
    - Wards broadcasting skill prices,
    - Social cues that specific skills open opportunities.
  - Encourages agents to **climb** certain skill trees in response to environmental pressure.

The v0 Skills & Learning system defined here should be stable enough that Codex can implement:

- A `skills.py` module,
- Skill checks in `actions.py`,
- And incremental improvements over time without breaking compatibility.

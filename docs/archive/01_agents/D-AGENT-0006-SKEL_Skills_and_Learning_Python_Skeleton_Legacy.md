---
title: Skills_and_Learning_Python_Skeleton
doc_id: D-AGENT-0006-SKEL
version: 0.1.0
status: legacy_idea
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0002   # Agent_Decision_Rule_v0
  - D-AGENT-0004   # Agent_Action_API_v0
  - D-AGENT-0005   # Perception_and_Memory_v0
  - D-AGENT-0006   # Skills_and_Learning_v0
  - D-RUNTIME-0001 # Simulation_Timebase
---

```python
"""
D-AGENT-0006 Skills_and_Learning_v0
Core data structures and APIs for agent skills & learning.

Depends on:
- D-AGENT-0001 Agent_Core_Schema_v0
- D-AGENT-0002 Agent_Decision_Rule_v0
- D-AGENT-0004 Agent_Action_API_v0
- D-AGENT-0005 Perception_and_Memory_v0
- D-RUNTIME-0001 Simulation_Timebase
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# ---------------------------------------------------------------------------
# Static skill definitions (registry)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SkillDefinition:
    skill_id: str                 # e.g. "perception"
    name: str                     # human-readable
    difficulty: str               # "easy" | "standard" | "hard" | "elite"
    primary_attribute: Optional[str]   # e.g. "mind", "social", or None
    secondary_attribute: Optional[str] # e.g. "body", "mind", etc.
    description: str
    tags: List[str]               # e.g. ["SENSE", "SOCIAL", "WORK"]


SKILL_DEFS: Dict[str, SkillDefinition] = {}


def register_default_skills() -> None:
    """Populate SKILL_DEFS with the core v0 skill set."""
    global SKILL_DEFS

    SKILL_DEFS = {
        "perception": SkillDefinition(
            skill_id="perception",
            name="Perception",
            difficulty="standard",
            primary_attribute="mind",
            secondary_attribute=None,
            description="Reading the environment; spotting threats and opportunities.",
            tags=["SENSE"],
        ),
        "streetwise": SkillDefinition(
            skill_id="streetwise",
            name="Streetwise",
            difficulty="standard",
            primary_attribute="mind",
            secondary_attribute="social",
            description="Understanding informal rules, gossip, and neighborhood dynamics.",
            tags=["SOCIAL", "NAVIGATION"],
        ),
        "conversation": SkillDefinition(
            skill_id="conversation",
            name="Conversation",
            difficulty="standard",
            primary_attribute="social",
            secondary_attribute="mind",
            description="Persuasion, rapport, and handling social exchanges.",
            tags=["SOCIAL"],
        ),
        "intimidation": SkillDefinition(
            skill_id="intimidation",
            name="Intimidation",
            difficulty="standard",
            primary_attribute="social",
            secondary_attribute="body",
            description="Coercion and threat display.",
            tags=["SOCIAL"],
        ),
        "labor_kitchen": SkillDefinition(
            skill_id="labor_kitchen",
            name="Kitchen Labor",
            difficulty="easy",
            primary_attribute="body",
            secondary_attribute="mind",
            description="Prep, serving and cleanup work in food halls.",
            tags=["WORK"],
        ),
        "labor_industrial": SkillDefinition(
            skill_id="labor_industrial",
            name="Industrial Labor",
            difficulty="standard",
            primary_attribute="body",
            secondary_attribute=None,
            description="Heavy or repetitive physical work in industrial settings.",
            tags=["WORK"],
        ),
        "bureaucracy": SkillDefinition(
            skill_id="bureaucracy",
            name="Bureaucracy",
            difficulty="standard",
            primary_attribute="mind",
            secondary_attribute="social",
            description="Dealing with forms, ledgers, permits, and clerks.",
            tags=["SOCIAL", "ADMIN"],
        ),
        "stealth": SkillDefinition(
            skill_id="stealth",
            name="Stealth",
            difficulty="hard",
            primary_attribute="body",
            secondary_attribute="mind",
            description="Moving unseen and avoiding detection.",
            tags=["SENSE", "MOBILITY"],
        ),
        "medicine_basic": SkillDefinition(
            skill_id="medicine_basic",
            name="Basic Medicine",
            difficulty="hard",
            primary_attribute="mind",
            secondary_attribute=None,
            description="First aid and low-level medical care.",
            tags=["CARE", "HEALTH"],
        ),
        "weapon_handling": SkillDefinition(
            skill_id="weapon_handling",
            name="Weapon Handling",
            difficulty="standard",
            primary_attribute="body",
            secondary_attribute=None,
            description="Safe, effective use of tools as weapons.",
            tags=["THREAT", "COMBAT_ADJACENT"],
        ),
    }


# ---------------------------------------------------------------------------
# Per-agent skill state
# ---------------------------------------------------------------------------

@dataclass
class SkillState:
    skill_id: str
    rank: int = 0               # integer rank, typically 0..10
    progress: float = 0.0       # 0..1 progress toward next rank
    xp_total: float = 0.0       # cumulative XP
    last_used_tick: int = 0     # for decay / atrophy


@dataclass
class SkillSet:
    skills: Dict[str, SkillState] = field(default_factory=dict)

    def get(self, skill_id: str) -> SkillState:
        """Return the SkillState for skill_id, creating a default state if needed."""
        if skill_id not in self.skills:
            self.skills[skill_id] = SkillState(skill_id=skill_id)
        return self.skills[skill_id]


# ---------------------------------------------------------------------------
# Skill check context
# ---------------------------------------------------------------------------

@dataclass
class SkillCheckContext:
    agent: Any                 # Agent instance (typed in agent module)
    world: Any                 # World / Simulation
    skill_id: str
    base_difficulty: float     # baseline difficulty (0..1, higher is harder)
    situational_mod: float     # situational modifier (-1..1; negative = easier)
    consequence_tag: str       # e.g. "JOB_PERFORMANCE", "SOCIAL_RISK"
    tick: int
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Rank cost tables & constants
# ---------------------------------------------------------------------------

RANK_MAX = 10
ATTR_MAX = 10.0  # assumed normalization baseline for attributes

# XP thresholds per rank, indexed by current rank.
RANK_XP_TABLE: Dict[str, List[float]] = {
    "easy":     [10, 20, 40, 80, 160, 320, 640, 1280, 2560, 5120],
    "standard": [20, 40, 80, 160, 320, 640, 1280, 2560, 5120, 10240],
    "hard":     [30, 60, 120, 240, 480, 960, 1920, 3840, 7680, 15360],
    "elite":    [40, 80, 160, 320, 640, 1280, 2560, 5120, 10240, 20480],
}

# Weights for combining skill rank and attributes into an effective score
W_SKILL = 0.6
W_ATTR_PRIMARY = 0.3
W_ATTR_SECONDARY = 0.1

# Logistic-ish curve control
CURVE_STEEPNESS = 0.4

# XP parameters
XP_ATTEMPT_BASE = 1.0
XP_SUCCESS_BASE = 2.0
XP_FAIL_MULTIPLIER = 0.7


# ---------------------------------------------------------------------------
# Core skill check function
# ---------------------------------------------------------------------------

def perform_skill_check(ctx: SkillCheckContext, rng) -> Dict[str, Any]:
    """
    Perform a skill check given context and RNG.

    Returns:
      {
        "success": bool,
        "p_success": float,    # probability used (0..1)
        "roll": float,         # actual random draw 0..1
        "effective_score": float,
      }

    This function is intentionally generic. Actions (D-AGENT-0004) are
    expected to interpret the result according to their semantics.
    """
    agent = ctx.agent
    skill_id = ctx.skill_id
    skill_def = SKILL_DEFS.get(skill_id)

    # --- 1. Get current skill state -----------------------------------
    skill_state: SkillState = agent.skills.get(skill_id)

    skill_component = skill_state.rank / float(RANK_MAX)

    # --- 2. Attribute components --------------------------------------
    # We assume agent has something like agent.attributes["mind"], etc.
    # If missing, we fall back to neutral values (ATTR_MAX/2).
    attr_primary_comp = 0.5
    attr_secondary_comp = 0.5

    if skill_def is not None:
        if skill_def.primary_attribute:
            primary_val = _get_agent_attribute(agent, skill_def.primary_attribute, fallback=ATTR_MAX / 2.0)
            attr_primary_comp = primary_val / ATTR_MAX

        if skill_def.secondary_attribute:
            secondary_val = _get_agent_attribute(agent, skill_def.secondary_attribute, fallback=ATTR_MAX / 2.0)
            attr_secondary_comp = secondary_val / ATTR_MAX

    # --- 3. Effective score -------------------------------------------
    effective_score = (
        W_SKILL * skill_component
        + W_ATTR_PRIMARY * attr_primary_comp
        + W_ATTR_SECONDARY * attr_secondary_comp
    )
    effective_score = _clamp(effective_score, 0.0, 1.0)

    # --- 4. Difficulty & success probability --------------------------
    difficulty = ctx.base_difficulty + ctx.situational_mod
    difficulty = _clamp(difficulty, 0.0, 1.0)

    margin = effective_score - difficulty  # [-1, 1]
    p_success = 0.5 + margin * CURVE_STEEPNESS
    p_success = _clamp(p_success, 0.0, 1.0)

    # --- 5. Actual roll -----------------------------------------------
    roll = rng.random()
    success = roll <= p_success

    return {
        "success": success,
        "p_success": p_success,
        "roll": roll,
        "effective_score": effective_score,
    }


def estimate_skill_success_probability(ctx: SkillCheckContext) -> float:
    """Deterministic estimate of success probability for planning/decision rule."""
    dummy_rng = _DummyRNG()
    result = perform_skill_check(ctx, dummy_rng)
    return result["p_success"]


# ---------------------------------------------------------------------------
# XP / learning
# ---------------------------------------------------------------------------

def compute_xp_gain_from_check(
    ctx: SkillCheckContext,
    check_result: Dict[str, Any],
) -> float:
    """Compute XP awarded for a skill check attempt (no mutation)."""
    difficulty_factor = 1.0 + 2.0 * _clamp(ctx.base_difficulty, 0.0, 1.0)
    xp_attempt = XP_ATTEMPT_BASE * difficulty_factor
    xp_bonus_success = XP_SUCCESS_BASE * difficulty_factor

    if check_result["success"]:
        return xp_attempt + xp_bonus_success
    else:
        return xp_attempt * XP_FAIL_MULTIPLIER


def apply_skill_xp(skill_set: SkillSet, skill_id: str, xp: float, tick: int) -> None:
    """
    Apply XP to a skill:

    - Ensure SkillState exists.
    - Convert XP into progress toward next rank.
    - Increment rank when progress >= threshold.
    """
    state = skill_set.get(skill_id)
    if xp <= 0:
        return

    state.xp_total += xp
    state.last_used_tick = tick

    skill_def = SKILL_DEFS.get(skill_id)
    difficulty = skill_def.difficulty if skill_def is not None else "standard"

    rank = state.rank
    if rank >= RANK_MAX:
        # Already at cap; optionally still update last_used_tick and xp_total.
        return

    thresholds = RANK_XP_TABLE.get(difficulty, RANK_XP_TABLE["standard"])
    if rank >= len(thresholds):
        # No threshold defined; treat as capped.
        return

    xp_required = thresholds[rank]
    # Convert xp into fraction of threshold
    progress_increment = xp / float(xp_required)
    state.progress += progress_increment

    # Rank up while progress >= 1.0 (allowing overflow)
    while state.rank < RANK_MAX and state.progress >= 1.0:
        state.progress -= 1.0
        state.rank += 1

        # Recompute xp_required for new rank if possible
        if state.rank >= len(thresholds):
            # At or beyond defined table; clamp progress and break
            state.progress = 0.0
            break


# ---------------------------------------------------------------------------
# Helpers and utilities
# ---------------------------------------------------------------------------

def _get_agent_attribute(agent: Any, attr_name: str, fallback: float) -> float:
    """
    Retrieve a numeric attribute from an agent.

    This is intentionally loose; D-AGENT-0001 should define the actual
    shape of agent attributes. Here we just support a couple of patterns:

      - agent.attributes[attr_name]
      - getattr(agent, attr_name, fallback)
    """
    val = fallback

    # Try mapping-style access first
    attrs = getattr(agent, "attributes", None)
    if isinstance(attrs, dict) and attr_name in attrs:
        raw = attrs[attr_name]
        try:
            val = float(raw)
        except (TypeError, ValueError):
            val = fallback
        return val

    # Fallback to direct attribute
    raw = getattr(agent, attr_name, None)
    if raw is not None:
        try:
            val = float(raw)
        except (TypeError, ValueError):
            val = fallback

    return val


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


class _DummyRNG:
    """Minimal RNG stub for deterministic estimation (returns 0.5)."""
    def random(self) -> float:
        return 0.5
```

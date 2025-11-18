---
title: Agent_Decision_Rule_Python_Skeleton
doc_id: D-AGENT-0002-SKEL
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-AGENT-0000   # Agent_System_Overview_v1
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0003   # Agent_Drives_v0
  - D-AGENT-0004   # Agent_Action_API_v0
  - D-AGENT-0005   # Perception_and_Memory_v0
  - D-AGENT-0006   # Skills_and_Learning_v0
  - D-AGENT-0007   # Rumor_and_Gossip_Dynamics_v0
  - D-RUNTIME-0001 # Simulation_Timebase
---

```python
"""
D-AGENT-0002 Agent_Decision_Rule_v0
Skeleton implementation for agent decision-making.

Depends on:
- D-AGENT-0000 Agent_System_Overview_v1
- D-AGENT-0001 Agent_Core_Schema_v0
- D-AGENT-0003 Agent_Drives_v0
- D-AGENT-0004 Agent_Action_API_v0
- D-AGENT-0005 Perception_and_Memory_v0
- D-AGENT-0006 Skills_and_Learning_v0
- D-AGENT-0007 Rumor_and_Gossip_Dynamics_v0
- D-RUNTIME-0001 Simulation_Timebase
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

# These imports assume a typical layout; adjust paths to your repo.
# from .core import Agent
# from .drives import Drives
# from .memory import Memory
# from .skills import SkillSet, SkillCheckContext, estimate_skill_success_probability
# from .rumors import SpaceProfile
# from . import actions as act


# ---------------------------------------------------------------------------
# Action kinds & candidate representation
# ---------------------------------------------------------------------------

class ActionKind(Enum):
    """High-level action types the decision rule can choose between."""
    # These should map cleanly onto handlers in agents/actions.py (D-AGENT-0004).
    IDLE = auto()
    MOVE_TO_FACILITY = auto()
    PERFORM_JOB = auto()
    OBSERVE_AREA = auto()
    TALK_TO_AGENT = auto()
    REQUEST_SERVICE = auto()
    REPORT_TO_AUTHORITY = auto()


@dataclass
class CandidateAction:
    """Decision-time representation of a possible action."""
    # 'payload' should contain whatever fields the Action API needs:
    #   - facility_id, target_agent_id, mode, etc.
    kind: ActionKind
    payload: Dict[str, Any]
    # Optional scoring debug fields
    survival_score: float = 0.0
    long_term_score: float = 0.0
    risk_score: float = 0.0
    skill_success_prob: float = 0.0   # p_success from skills/rumors if relevant

    @property
    def total_score(self) -> float:
        """Combined EV score used for comparison."""
        # This is intentionally simple in v0; designers can adjust weights
        # or move this into a configuration map.
        # Basic example: reward survival & long-term, penalize risk.
        return self.survival_score + self.long_term_score - self.risk_score


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def choose_action(agent: Any, world: Any, tick: int, rng) -> CandidateAction:
    """Main decision entry point."""
    # Expected outer loop (see D-AGENT-0000):
    #   - World has already produced a PerceptionSnapshot and agent.memory
    #     has been updated for this tick.
    #   - Drives have been updated based on physical + social state.
    #
    # This function:
    #   1. Builds a small set of CandidateActions.
    #   2. Scores each candidate with a rough EV heuristic.
    #   3. Returns the best-scoring candidate (ties broken by small randomness).

    # 1. Enumerate candidates
    candidates = enumerate_candidate_actions(agent, world, tick)

    if not candidates:
        # Always allow IDLE as a fallback if something goes wrong.
        return CandidateAction(kind=ActionKind.IDLE, payload={})

    # 2. Score candidates
    scored = [
        score_candidate_action(agent, world, cand, tick, rng)
        for cand in candidates
    ]

    # 3. Choose best by total_score; break ties slightly randomly
    scored.sort(key=lambda c: c.total_score, reverse=True)

    best = scored[0]
    # Optionally, with some exploration:
    #   - with small probability, pick from top-k instead.
    return best


# ---------------------------------------------------------------------------
# Candidate enumeration
# ---------------------------------------------------------------------------

def enumerate_candidate_actions(agent: Any, world: Any, tick: int) -> List[CandidateAction]:
    """Build a small set of candidate actions for this tick."""
    # Based on:
    #   - Drives (hunger, thirst, fatigue, fear, ambition, curiosity, loyalty).
    #   - Memory (known safe facilities, jobs, threats, rumors).
    #   - Simple environment queries (facilities reachable this tick).
    #
    # v0 aim: *small* action set each tick (e.g., 3–7 candidates).

    candidates: List[CandidateAction] = []

    drives = getattr(agent, "drives", None)
    memory = getattr(agent, "memory", None)

    # Fallbacks if drives/memory not wired yet
    hunger = getattr(drives, "hunger", 0.0) if drives is not None else 0.0
    thirst = getattr(drives, "thirst", 0.0) if drives is not None else 0.0
    fatigue = getattr(drives, "fatigue", 0.0) if drives is not None else 0.0
    fear = getattr(drives, "fear", 0.0) if drives is not None else 0.0
    ambition = getattr(drives, "ambition", 0.0) if drives is not None else 0.0
    curiosity = getattr(drives, "curiosity", 0.0) if drives is not None else 0.0

    need_food = hunger > 0.5 or thirst > 0.5
    need_rest = fatigue > 0.7
    feel_threatened = fear > 0.6
    want_progress = ambition > 0.4
    want_info = curiosity > 0.4

    # 1) Survival: get food/water/job at nearby facility
    if need_food and memory is not None:
        facility_id = _choose_feeding_facility(agent, memory)
        if facility_id is not None:
            candidates.append(
                CandidateAction(
                    kind=ActionKind.MOVE_TO_FACILITY,
                    payload={"facility_id": facility_id, "purpose": "FOOD"},
                )
            )

    # 2) Rest: move to bunkhouse / safe place
    if need_rest and memory is not None:
        rest_facility_id = _choose_rest_facility(agent, memory)
        if rest_facility_id is not None:
            candidates.append(
                CandidateAction(
                    kind=ActionKind.MOVE_TO_FACILITY,
                    payload={"facility_id": rest_facility_id, "purpose": "REST"},
                )
            )

    # 3) Safety: move away from perceived threats
    if feel_threatened and memory is not None:
        safer_fac_id = _choose_safer_facility(agent, memory)
        if safer_fac_id is not None:
            candidates.append(
                CandidateAction(
                    kind=ActionKind.MOVE_TO_FACILITY,
                    payload={"facility_id": safer_fac_id, "purpose": "SAFETY"},
                )
            )

    # 4) Work: perform job if already at a job-capable facility
    if want_progress:
        # TODO: consult world/memory to see if current facility has jobs.
        candidates.append(
            CandidateAction(
                kind=ActionKind.PERFORM_JOB,
                payload={"job_type": "DEFAULT"},  # refined later
            )
        )

    # 5) Information gathering: observe area
    if want_info or feel_threatened:
        candidates.append(
            CandidateAction(
                kind=ActionKind.OBSERVE_AREA,
                payload={},
            )
        )

    # 6) Social: talk to someone nearby (could involve rumors)
    if want_info or ambition > 0.2:
        target_id = _choose_conversation_partner(agent, memory)
        if target_id is not None:
            candidates.append(
                CandidateAction(
                    kind=ActionKind.TALK_TO_AGENT,
                    payload={
                        "target_agent_id": target_id,
                        "topic_token": "RUMOR",  # or "SMALL_TALK", etc.
                    },
                )
            )

    # 7) Fallback: IDLE
    if not candidates:
        candidates.append(CandidateAction(kind=ActionKind.IDLE, payload={}))

    return candidates


# ---------------------------------------------------------------------------
# Candidate scoring (EV heuristic)
# ---------------------------------------------------------------------------

def score_candidate_action(
    agent: Any,
    world: Any,
    candidate: CandidateAction,
    tick: int,
    rng,
) -> CandidateAction:
    """Compute survival_score, long_term_score, risk_score, and skill_success_prob."""
    # This is deliberately rough in v0; Codex and future-you can refine:
    #   - weights,
    #   - drive contributions,
    #   - integration with rumors & skills.

    drives = getattr(agent, "drives", None)
    memory = getattr(agent, "memory", None)
    skills = getattr(agent, "skills", None)

    # Initialize scores
    survival, long_term, risk = 0.0, 0.0, 0.0
    p_success = 1.0

    # Example: weight survival vs long term differently per drive intensity.
    hunger = getattr(drives, "hunger", 0.0) if drives is not None else 0.0
    thirst = getattr(drives, "thirst", 0.0) if drives is not None else 0.0
    fatigue = getattr(drives, "fatigue", 0.0) if drives is not None else 0.0
    fear = getattr(drives, "fear", 0.0) if drives is not None else 0.0
    ambition = getattr(drives, "ambition", 0.0) if drives is not None else 0.0

    if candidate.kind == ActionKind.MOVE_TO_FACILITY:
        purpose = candidate.payload.get("purpose", "")
        facility_id = candidate.payload.get("facility_id")

        # Survival: moving to food/rest/safe facility
        if purpose == "FOOD":
            survival += 0.6 * max(hunger, thirst)
        elif purpose == "REST":
            survival += 0.5 * fatigue
        elif purpose == "SAFETY":
            survival += 0.5 * fear

        # Long-term: ambition might like moving to better wards/jobs
        long_term += 0.3 * ambition

        # Risk: based on facility danger from memory, if known
        if memory is not None and facility_id is not None:
            risk += _estimate_facility_risk(agent, memory, facility_id)

    elif candidate.kind == ActionKind.PERFORM_JOB:
        # Survival: jobs yield food/credits; more urgent when hungry/thirsty
        survival += 0.4 * max(hunger, thirst)

        # Long-term: jobs advance status, build skills
        long_term += 0.5 * ambition

        # Risk: industrial jobs might be dangerous; ask memory/world
        risk += _estimate_job_risk(agent, world, candidate)

        # Skill success: use skills to estimate performance probability
        p_success = _estimate_job_success(agent, world, candidate)

    elif candidate.kind == ActionKind.OBSERVE_AREA:
        # Survival: observation is useful when afraid/uncertain
        survival += 0.3 * fear

        # Long-term: information is valuable, especially for ambitious agents
        long_term += 0.2 * ambition

        # Risk: observational actions are usually low risk, but not zero
        risk += 0.1 * fear

        p_success = _estimate_observe_success(agent, world, candidate)

    elif candidate.kind == ActionKind.TALK_TO_AGENT:
        # Survival: talking can secure help, warnings, or betrayals.
        survival += 0.1 * hunger + 0.2 * fear

        # Long-term: high potential for leverage, alliances, or info
        long_term += 0.5 * ambition

        # Risk: social exposure; risk grows with fear and existing suspicion
        risk += _estimate_social_risk(agent, candidate, memory)

        p_success = _estimate_talk_success(agent, world, candidate)

    elif candidate.kind == ActionKind.REQUEST_SERVICE:
        # Example: using bureaucracy, asking for bunk, ration, permit.
        survival += 0.4 * max(hunger, thirst, fatigue)
        long_term += 0.3 * ambition
        risk += 0.2 * fear
        p_success = _estimate_request_success(agent, world, candidate)

    elif candidate.kind == ActionKind.REPORT_TO_AUTHORITY:
        # Snitching / formal reports.
        # Survival: maybe secure protection or rewards (esp. frightened agents).
        survival += 0.5 * fear
        long_term += 0.4 * ambition  # e.g. career with authority

        # Risk: retaliation from others, moral cost vs loyalty.
        risk += _estimate_report_risk(agent, candidate, memory)

        p_success = _estimate_report_success(agent, world, candidate)

    elif candidate.kind == ActionKind.IDLE:
        # Idle is low risk, but does not directly address needs.
        survival += 0.0
        long_term += 0.0
        risk += 0.05 * (hunger + thirst + fatigue + fear)  # risk of neglect

        p_success = 1.0

    # Simple integration of p_success: scale benefits by success probability.
    survival *= p_success
    long_term *= p_success

    candidate.survival_score = survival
    candidate.long_term_score = long_term
    candidate.risk_score = risk
    candidate.skill_success_prob = p_success

    return candidate


# ---------------------------------------------------------------------------
# Helper heuristics (stubs; refine as needed)
# ---------------------------------------------------------------------------

def _choose_feeding_facility(agent: Any, memory: Any) -> Optional[str]:
    """Pick a facility id likely to provide food/water."""
    # For now:
    #   - Look through memory.known_facilities,
    #   - Filter by tags like 'soup_kitchen', 'canteen', etc. if available,
    #   - Prefer ones with high perceived_safety / past positive experiences.
    # TODO: Implement actual logic; placeholder returns None.
    return None


def _choose_rest_facility(agent: Any, memory: Any) -> Optional[str]:
    """Choose a facility for rest (bunkhouse, safehouse, etc.)."""
    # TODO: Implement from FacilityBelief.
    return None


def _choose_safer_facility(agent: Any, memory: Any) -> Optional[str]:
    """Move to a facility perceived as safer than current conditions."""
    # TODO: Implement from FacilityBelief.threat / safety index.
    return None


def _choose_conversation_partner(agent: Any, memory: Any) -> Optional[str]:
    """Pick someone nearby or known in memory to talk to."""
    # v0: just a placeholder; later, use:
    #   - affinity,
    #   - suspicion,
    #   - proximity (if available),
    #   - faction alignment.
    # TODO: Use memory.known_agents.
    return None


def _estimate_facility_risk(agent: Any, memory: Any, facility_id: str) -> float:
    """Use FacilityBelief to estimate risk (0..1) of going to a facility."""
    # Factors:
    #   - Enforcement presence,
    #   - Rumored crackdowns,
    #   - Past bad events.
    # TODO: Use memory.known_facilities[facility_id]
    return 0.3  # placeholder


def _estimate_job_risk(agent: Any, world: Any, candidate: CandidateAction) -> float:
    """Estimate risk of performing a job."""
    # Could depend on:
    #   - job_type,
    #   - facility danger,
    #   - agent health/fatigue.
    return 0.2  # placeholder


def _estimate_job_success(agent: Any, world: Any, candidate: CandidateAction) -> float:
    """Use skills (labor_kitchen, labor_industrial, etc.) to estimate job success."""
    # TODO: Build SkillCheckContext and call estimate_skill_success_probability.
    return 0.8  # placeholder


def _estimate_observe_success(agent: Any, world: Any, candidate: CandidateAction) -> float:
    """Perception skill modulates how effective OBSERVE_AREA is."""
    # TODO: Build SkillCheckContext with skill_id="perception".
    return 0.9  # placeholder


def _estimate_talk_success(agent: Any, world: Any, candidate: CandidateAction) -> float:
    """Conversation / streetwise skills affect social success."""
    # TODO: Use skills + maybe rumors EV.
    return 0.7  # placeholder


def _estimate_social_risk(agent: Any, candidate: CandidateAction, memory: Any) -> float:
    """Estimate risk of TALK_TO_AGENT, based on suspicion & space."""
    # Factors:
    #   - suspicion between agents,
    #   - space alignment (requires SpaceProfile from world),
    #   - possible rumor content.
    # TODO: Use memory.known_agents + world.get_space_profile.
    return 0.3  # placeholder


def _estimate_request_success(agent: Any, world: Any, candidate: CandidateAction) -> float:
    """REQUEST_SERVICE often uses bureaucracy / conversation skills."""
    return 0.6  # placeholder


def _estimate_report_success(agent: Any, world: Any, candidate: CandidateAction) -> float:
    """REPORT_TO_AUTHORITY success = being believed, not punished."""
    return 0.7  # placeholder


def _estimate_report_risk(agent: Any, candidate: CandidateAction, memory: Any) -> float:
    """Risk that reporting backfires (retaliation, social cost)."""
    # Factors:
    #   - how dangerous the target is,
    #   - how leaky the space is,
    #   - agent's reputation as snitch.
    return 0.4  # placeholder
```

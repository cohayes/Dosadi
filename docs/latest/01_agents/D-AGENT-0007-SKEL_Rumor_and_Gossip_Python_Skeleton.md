---
title: Rumor_and_Gossip_Python_Skeleton
doc_id: D-AGENT-0007-SKEL
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0002   # Agent_Decision_Rule_v0
  - D-AGENT-0004   # Agent_Action_API_v0
  - D-AGENT-0005   # Perception_and_Memory_v0
  - D-AGENT-0006   # Skills_and_Learning_v0
  - D-AGENT-0007   # Rumor_and_Gossip_Dynamics_v0
  - D-RUNTIME-0001 # Simulation_Timebase
---

```python
"""
D-AGENT-0007 Rumor_and_Gossip_Dynamics_v0
Skeleton implementation for rumor & gossip logic.

Depends on:
- D-AGENT-0001 Agent_Core_Schema_v0
- D-AGENT-0002 Agent_Decision_Rule_v0
- D-AGENT-0004 Agent_Action_API_v0
- D-AGENT-0005 Perception_and_Memory_v0
- D-AGENT-0006 Skills_and_Learning_v0
- D-RUNTIME-0001 Simulation_Timebase
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# These imports assume typical layout; adjust paths to match your repo.
# from .memory import Memory, Rumor, ConversationEvent
# from .skills import SkillSet, SkillCheckContext, estimate_skill_success_probability


# ---------------------------------------------------------------------------
# Types & helpers
# ---------------------------------------------------------------------------

@dataclass
class SpaceProfile:
    """Rumor-relevant profile for a location / facility."""
    alignment: str              # "PRO_AUTH" | "ANTI_AUTH" | "MIXED"
    enforcement_level: float    # 0..1
    gossip_risk: float          # 0..1  (chance words travel upward / sideways)
    gossip_density: float       # 0..1  (how many eavesdroppers/passers-on)


@dataclass
class RumorPolicy:
    """Per-agent rumor thresholds / risk appetite."""
    min_credibility_to_act: float = 0.6
    min_payoff_to_act: float = 0.3
    min_credibility_to_forward: float = 0.5
    min_payoff_to_forward: float = 0.2
    risk_tolerance: float = 0.5  # 0..1 (higher = more risk-seeking)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_rumor_share(
    agent: Any,
    rumor: Any,                        # Memory.Rumor instance
    listener: Any,
    space: SpaceProfile,
) -> float:
    """Compute a scalar EV for sharing 'rumor' with 'listener' in 'space'."""
    # Positive = beneficial to speak.
    # Negative = better to remain silent or change topic.

    # --- 1. Extract basic fields --------------------------------------
    payload: Dict[str, Any] = rumor.payload
    category: str = payload.get("category", "EVENT")
    promised_payoff: float = float(payload.get("promised_payoff", 0.5))
    claimed_conf: float = float(payload.get("claimed_confidence", rumor.credibility))

    # Relationship terms from memory (if available)
    affinity_to_listener = _get_affinity(agent, listener)
    suspicion_of_listener = _get_suspicion(agent, listener)

    # Agent’s rumor policy (fallback defaults if not present)
    policy: RumorPolicy = getattr(agent, "rumor_policy", RumorPolicy())

    # --- 2. Benefit estimate ------------------------------------------
    benefit = _estimate_benefit_share(
        agent=agent,
        rumor=rumor,
        listener=listener,
        space=space,
        category=category,
        promised_payoff=promised_payoff,
        affinity_to_listener=affinity_to_listener,
    )

    # --- 3. Risk estimate ---------------------------------------------
    risk = _estimate_risk_share(
        agent=agent,
        rumor=rumor,
        listener=listener,
        space=space,
        suspicion_of_listener=suspicion_of_listener,
        claimed_confidence=claimed_conf,
    )

    # --- 4. EV and risk tolerance -------------------------------------
    # Simple tradeoff: EV = benefit - risk, scaled by risk_tolerance.
    # Higher risk_tolerance → less penalty from risk.
    effective_risk_weight = 1.0 + (1.0 - policy.risk_tolerance)  # 1..2
    ev_share = benefit - effective_risk_weight * risk

    return ev_share


def speaker_choose_rumor(
    agent: Any,
    memory: Any,                      # Memory instance
    listener: Any,
    space: SpaceProfile,
) -> Optional[Any]:
    """Select which rumor, if any, to share in this conversation."""
    # TODO: refine filtering criteria; for v0 we just get "interesting" rumors.
    candidate_rumors: List[Any] = list(memory.rumors.values())

    # Filter by minimum credibility / payoff from policy.
    policy: RumorPolicy = getattr(agent, "rumor_policy", RumorPolicy())
    filtered: List[Tuple[Any, float]] = []

    for r in candidate_rumors:
        payload = r.payload
        promised_payoff = float(payload.get("promised_payoff", 0.0))
        if r.credibility < policy.min_credibility_to_forward:
            continue
        if promised_payoff < policy.min_payoff_to_forward:
            continue

        ev = evaluate_rumor_share(agent, r, listener, space)
        filtered.append((r, ev))

    if not filtered:
        return None

    # Choose the rumor with the highest EV, if it's actually positive.
    filtered.sort(key=lambda t: t[1], reverse=True)
    best_rumor, best_ev = filtered[0]
    if best_ev <= 0:
        return None

    return best_rumor


def listener_update_from_rumor(
    listener: Any,
    speaker: Any,
    event: Any,                       # ConversationEvent
    space: SpaceProfile,
) -> None:
    """Update listener's memory and beliefs after hearing a rumor."""
    memory = listener.memory

    # 1. Baseline ingestion into memory
    memory.update_from_conversation(event)

    # 2. Skill-based skepticism (streetwise, perception, etc.)
    # (Pseudo): compute a skepticism factor and nudge rumor credibility.
    rumor_key = _derive_rumor_id_from_event(memory, event)
    rumor = memory.rumors.get(rumor_key)
    if rumor is None:
        return

    skepticism = _compute_skepticism(listener, speaker, event, space)
    # Higher skepticism reduces credibility, but not below zero.
    rumor.credibility = max(0.0, rumor.credibility - skepticism)

    # 3. Optional: immediate adjustment of belief about speaker
    # e.g., if speaker is obviously self-serving or space is hostile.
    # TODO: Hook into memory.adjust_suspicion / adjust_affinity as desired.


def resolve_rumor_outcomes(world_events: List[Any], agents: List[Any]) -> None:
    """World-level function to reconcile rumors with actual events."""
    # For each resolved event (e.g. crackdown actually happened or was cancelled):
    #   - Determine which rumors were true/false.
    #   - For each agent:
    #       * adjust rumor.credibility (if still stored),
    #       * adjust speaker trust / suspicion based on confirmed true/false.
    #
    # This is intentionally a stub; actual wiring depends on how world events
    # are represented in your simulation.
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _estimate_benefit_share(
    agent: Any,
    rumor: Any,
    listener: Any,
    space: SpaceProfile,
    category: str,
    promised_payoff: float,
    affinity_to_listener: float,
) -> float:
    """Rough heuristic benefit estimate."""
    # Ideas:
    #   - THREAT: high payoff if protecting self/faction or currying favor
    #             with authority in PRO_AUTH spaces.
    #   - OPPORTUNITY: high payoff if agent or listener can exploit it.
    #   - STATUS / IDENTITY: benefit from elevating self or undermining rival.

    base = promised_payoff

    # Slight bonus for helping allies
    if affinity_to_listener > 0:
        base *= (1.0 + 0.2 * affinity_to_listener)

    # Alignment tweak: PRO_AUTH spaces reward pro-authority / snitchy rumors,
    # but we don't encode the sign of the rumor here in v0.
    # TODO: optionally inspect payload or category to polarize this.
    if space.alignment == "PRO_AUTH" and category in ("THREAT", "IDENTITY"):
        base *= 1.1
    elif space.alignment == "ANTI_AUTH" and category in ("OPPORTUNITY", "THREAT"):
        base *= 1.1

    # Clamp to [0, 1]
    return _clamp(base, 0.0, 1.0)


def _estimate_risk_share(
    agent: Any,
    rumor: Any,
    listener: Any,
    space: SpaceProfile,
    suspicion_of_listener: float,
    claimed_confidence: float,
) -> float:
    """Rough heuristic risk estimate."""
    # Risk sources:
    #   - Space gossip_risk / enforcement_level.
    #   - Listener might relay rumor to hostile faction.
    #   - Rumor might be wrong (claimed_confidence low).

    # Baseline from space characteristics
    r_space = 0.5 * space.gossip_risk + 0.5 * space.enforcement_level

    # Listener-specific risk
    r_listener = suspicion_of_listener

    # Rumor reliability: low confidence -> higher risk
    r_conf = (1.0 - claimed_confidence)

    risk = 0.4 * r_space + 0.3 * r_listener + 0.3 * r_conf
    return _clamp(risk, 0.0, 1.0)


def _compute_skepticism(
    listener: Any,
    speaker: Any,
    event: Any,
    space: SpaceProfile,
) -> float:
    """Compute how skeptical the listener is of a given rumor."""
    # Higher return value -> reduce credibility more.

    # Start with a neutral baseline
    skepticism = 0.0

    # Skills: streetwise makes you more skeptical.
    # We assume listener.skills is a SkillSet and streetwise rank is meaningful.
    streetwise_rank = 0
    try:
        streetwise_state = listener.skills.get("streetwise")
        streetwise_rank = streetwise_state.rank
    except Exception:
        pass

    skepticism += 0.05 * streetwise_rank  # up to ~0.5 at rank 10

    # If space is highly mixed & risky, increase skepticism.
    mixedness = 1.0 if space.alignment == "MIXED" else 0.0
    skepticism += 0.2 * mixedness * space.gossip_risk

    # If listener already has strong contradictory beliefs, increase skepticism.
    # TODO: look into listener.memory to detect contradictions.
    # For now, just clamp.
    return _clamp(skepticism, 0.0, 0.8)


def _derive_rumor_id_from_event(memory: Any, event: Any) -> str:
    """Derive the same rumor_id that Memory._derive_rumor_id would have used."""
    # This is a convenience so we can look up the Rumor just ingested from
    # update_from_conversation().

    # If Memory already has a helper, prefer to use that; this is a fallback.
    # For now, mimic the pattern from D-AGENT-0005-SKEL.
    topic = getattr(event, "topic_token", "RUMOR")
    payload = getattr(event, "payload", {}) or {}
    tgt_agent = payload.get("target_agent_id", "")
    tgt_fac = payload.get("target_facility_id", "")
    return f"{topic}:{tgt_agent}:{tgt_fac}"


def _get_affinity(agent: Any, other: Any) -> float:
    """Lookup affinity(agent -> other) from agent.memory, if available."""
    # Return 0.0 if unknown.
    memory = getattr(agent, "memory", None)
    if memory is None:
        return 0.0

    other_id = getattr(other, "agent_id", None)
    if other_id is None:
        return 0.0

    belief = memory.known_agents.get(other_id)
    return float(getattr(belief, "affinity", 0.0)) if belief is not None else 0.0


def _get_suspicion(agent: Any, other: Any) -> float:
    """Lookup suspicion(agent -> other) from agent.memory, if available."""
    # Return 0.5 if unknown (neutral suspicion).
    memory = getattr(agent, "memory", None)
    if memory is None:
        return 0.5

    other_id = getattr(other, "agent_id", None)
    if other_id is None:
        return 0.5

    belief = memory.known_agents.get(other_id)
    return float(getattr(belief, "suspicion", 0.5)) if belief is not None else 0.5


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x
```

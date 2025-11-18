---
title: Agent_Action_API_Python_Skeleton
doc_id: D-AGENT-0004-SKEL
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-AGENT-0000   # Agent_System_Overview_v1
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0002   # Agent_Decision_Rule_v0
  - D-AGENT-0003   # Agent_Drives_v0
  - D-AGENT-0005   # Perception_and_Memory_v0
  - D-AGENT-0006   # Skills_and_Learning_v0
  - D-AGENT-0007   # Rumor_and_Gossip_Dynamics_v0
  - D-RUNTIME-0001 # Simulation_Timebase
---

```python
"""
D-AGENT-0004 Agent_Action_API_v0
Skeleton implementation for the Agent Action API.

This module defines the *runtime actions* that agents can take and how those
actions are applied to the world. It is the concrete counterpart to the
high-level Action vocabulary described in D-AGENT-0004 and used by the
decision rule (D-AGENT-0002).

Depends on:
- D-AGENT-0000 Agent_System_Overview_v1
- D-AGENT-0001 Agent_Core_Schema_v0
- D-AGENT-0002 Agent_Decision_Rule_v0
- D-AGENT-0003 Agent_Drives_v0
- D-AGENT-0005 Perception_and_Memory_v0
- D-AGENT-0006 Skills_and_Learning_v0
- D-AGENT-0007 Rumor_and_Gossip_Dynamics_v0
- D-RUNTIME-0001 Simulation_Timebase
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional


# These imports assume a typical layout; adjust paths to your repo.
# from .core import Agent
# from .skills import SkillCheckContext, perform_skill_check
# from .memory import PerceptionSnapshot
# from .rumors import SpaceProfile, speaker_choose_rumor, listener_update_from_rumor


# ---------------------------------------------------------------------------
# Action types
# ---------------------------------------------------------------------------

class ActionType(Enum):
    """Canonical runtime actions an agent can perform."""
    IDLE = auto()
    MOVE_TO_FACILITY = auto()
    PERFORM_JOB = auto()
    OBSERVE_AREA = auto()
    TALK_TO_AGENT = auto()
    REQUEST_SERVICE = auto()
    REPORT_TO_AUTHORITY = auto()


@dataclass
class Action:
    """Concrete action instance chosen by the decision rule."""
    type: ActionType
    payload: Dict[str, Any]


# Convenience constructors so code stays explicit & readable.
def idle_action() -> Action:
    return Action(type=ActionType.IDLE, payload={})


def move_to_facility_action(facility_id: str, purpose: str = "") -> Action:
    return Action(
        type=ActionType.MOVE_TO_FACILITY,
        payload={
            "facility_id": facility_id,
            "purpose": purpose,  # e.g. "FOOD", "REST", "SAFETY"
        },
    )


def perform_job_action(job_type: str = "DEFAULT", facility_id: Optional[str] = None) -> Action:
    return Action(
        type=ActionType.PERFORM_JOB,
        payload={
            "job_type": job_type,
            "facility_id": facility_id,
        },
    )


def observe_area_action() -> Action:
    return Action(
        type=ActionType.OBSERVE_AREA,
        payload={},
    )


def talk_to_agent_action(
    target_agent_id: str,
    topic_token: str = "RUMOR",
) -> Action:
    return Action(
        type=ActionType.TALK_TO_AGENT,
        payload={
            "target_agent_id": target_agent_id,
            "topic_token": topic_token,
        },
    )


def request_service_action(
    facility_id: str,
    service_type: str,
) -> Action:
    return Action(
        type=ActionType.REQUEST_SERVICE,
        payload={
            "facility_id": facility_id,
            "service_type": service_type,  # e.g. "BUNK", "RATION", "PERMIT"
        },
    )


def report_to_authority_action(
    facility_id: str,
    target_agent_id: Optional[str],
    report_payload: Dict[str, Any],
) -> Action:
    return Action(
        type=ActionType.REPORT_TO_AUTHORITY,
        payload={
            "facility_id": facility_id,
            "target_agent_id": target_agent_id,
            "report_payload": report_payload,
        },
    )


# ---------------------------------------------------------------------------
# Public API: applying actions
# ---------------------------------------------------------------------------

def apply_action(agent: Any, world: Any, action: Action, tick: int, rng) -> None:
    """Dispatch an Action to the appropriate handler."""
    if action.type == ActionType.IDLE:
        _handle_idle(agent, world, action, tick, rng)
    elif action.type == ActionType.MOVE_TO_FACILITY:
        _handle_move_to_facility(agent, world, action, tick, rng)
    elif action.type == ActionType.PERFORM_JOB:
        _handle_perform_job(agent, world, action, tick, rng)
    elif action.type == ActionType.OBSERVE_AREA:
        _handle_observe_area(agent, world, action, tick, rng)
    elif action.type == ActionType.TALK_TO_AGENT:
        _handle_talk_to_agent(agent, world, action, tick, rng)
    elif action.type == ActionType.REQUEST_SERVICE:
        _handle_request_service(agent, world, action, tick, rng)
    elif action.type == ActionType.REPORT_TO_AUTHORITY:
        _handle_report_to_authority(agent, world, action, tick, rng)
    else:
        # Unknown action type: safest is to do nothing.
        _handle_idle(agent, world, action, tick, rng)


# ---------------------------------------------------------------------------
# Handlers (v0 stubs)
# ---------------------------------------------------------------------------

def _handle_idle(agent: Any, world: Any, action: Action, tick: int, rng) -> None:
    """Agent does nothing this tick.

    v0: This is a no-op, but could:
      - increment a 'loiter' counter,
      - modestly increase boredom or decrease fatigue.
    """
    # TODO: Optionally hook into drives (fatigue recovery, boredom increase).
    return None


def _handle_move_to_facility(agent: Any, world: Any, action: Action, tick: int, rng) -> None:
    """Move the agent towards / into a facility.

    Expected world responsibilities:
      - Validate that the facility_id exists and is reachable.
      - Update agent's location (cell, room, facility).
      - Optionally enqueue movement over multiple ticks (not instant teleport).
    """
    facility_id = action.payload.get("facility_id")
    purpose = action.payload.get("purpose", "")

    # TODO:
    #   - world.move_agent_to_facility(agent_id, facility_id)
    #   - record visit in memory: agent.memory.note_facility_visit(...)
    #   - adjust drives partially toward need resolution if close enough.
    _ = facility_id, purpose, world, agent, tick, rng
    return None


def _handle_perform_job(agent: Any, world: Any, action: Action, tick: int, rng) -> None:
    """Perform a job at the current facility.

    Example jobs:
      - soup kitchen labor,
      - industrial loading,
      - bureaucratic paperwork.

    Expected world responsibilities:
      - Determine job availability & payoffs (food, credits, status).
      - Use skills & attributes to compute job success/quality.
      - Apply fatigue, risk of injury, etc.
    """
    job_type = action.payload.get("job_type", "DEFAULT")
    facility_id = action.payload.get("facility_id") or world.get_agent_facility(agent)

    # TODO:
    #   - Build SkillCheckContext from job_type & facility.
    #   - Call perform_skill_check(ctx, rng).
    #   - Apply rewards/penalties:
    #       * food/water/credits,
    #       * fatigue/health,
    #       * XP to relevant skills.
    _ = job_type, facility_id, world, agent, tick, rng
    return None


def _handle_observe_area(agent: Any, world: Any, action: Action, tick: int, rng) -> None:
    """Observe surroundings and update memory."

    Expected world responsibilities:
      - Produce a PerceptionSnapshot for the agent:
          snapshot = world.produce_perception_snapshot(agent, tick)
      - Agent consumes snapshot via:
          agent.memory.update_from_observation(snapshot)
    """
    # TODO:
    #   snapshot = world.produce_perception_snapshot(agent, tick)
    #   agent.memory.update_from_observation(snapshot)
    _ = world, agent, tick, rng
    return None


def _handle_talk_to_agent(agent: Any, world: Any, action: Action, tick: int, rng) -> None:
    """Carry out a conversation between two agents.

    v0 focus:
      - Support rumor-based conversations (D-AGENT-0007).
      - Update both speaker and listener memory accordingly.

    Expected world responsibilities:
      - Resolve target_agent_id to an Agent object.
      - Supply a SpaceProfile for the current location.
    """
    target_id = action.payload.get("target_agent_id")
    topic_token = action.payload.get("topic_token", "RUMOR")

    if target_id is None:
        return None

    target = world.get_agent_by_id(target_id)
    if target is None:
        return None

    # Example rumor pathway (pseudo-code, left for implementation):
    #
    # space_profile: SpaceProfile = world.get_space_profile(agent.location)
    #
    # if topic_token == "RUMOR":
    #     # Speaker chooses rumor (if any) based on EV.
    #     rumor = speaker_choose_rumor(agent, agent.memory, target, space_profile)
    #     if rumor is None:
    #         return None
    #
    #     event = ConversationEvent(
    #         tick=tick,
    #         speaker_id=agent.agent_id,
    #         listener_id=target.agent_id,
    #         topic_token="RUMOR",
    #         payload=rumor.payload,
    #         perceived_sincerity=...,  # could depend on skills & rng
    #     )
    #
    #     # Listener updates memory & beliefs from the rumor.
    #     listener_update_from_rumor(target, agent, event, space_profile)
    #
    # else:
    #     # Non-rumor small talk / relationship nudging could go here.
    #     pass

    _ = world, agent, target, topic_token, tick, rng
    return None


def _handle_request_service(agent: Any, world: Any, action: Action, tick: int, rng) -> None:
    """Request a service from a facility (bunk, ration, permit, treatment).

    Expected world responsibilities:
      - Check whether the facility provides the requested service_type.
      - Apply access rules (faction, reputation, permits, queue order).
      - Use skills (bureaucracy, conversation) to determine success.
      - Update agent state (rest, food, legal flags).
    """
    facility_id = action.payload.get("facility_id")
    service_type = action.payload.get("service_type")

    # TODO:
    #   - facility = world.get_facility(facility_id)
    #   - if facility.supports_service(service_type):
    #         ctx = SkillCheckContext(...)
    #         result = perform_skill_check(ctx, rng)
    #         world.apply_service_result(agent, facility, service_type, result)
    _ = facility_id, service_type, world, agent, tick, rng
    return None


def _handle_report_to_authority(agent: Any, world: Any, action: Action, tick: int, rng) -> None:
    """Report information to an authority-linked facility.

    This covers:
      - Snitching on other agents,
      - Filing formal complaints,
      - Providing intel in exchange for protection or favors.

    Expected world responsibilities:
      - Validate that facility_id is an authority node (garrison, office, etc.).
      - Interpret report_payload (targets, events).
      - Adjust:
          * authority's beliefs and plans,
          * agent's reputation (with authority & with street),
          * downstream crackdown or protection behaviors.
    """
    facility_id = action.payload.get("facility_id")
    target_agent_id = action.payload.get("target_agent_id")
    report_payload = action.payload.get("report_payload", {})

    # TODO:
    #   - authority = world.get_facility(facility_id)
    #   - world.process_report(agent, authority, target_agent_id, report_payload, tick)
    #   - Hook into rumor resolution / reputation systems.
    _ = facility_id, target_agent_id, report_payload, world, agent, tick, rng
    return None
```

from __future__ import annotations

import random
from typing import Optional, Tuple

from dosadi.agents.core import AgentState, Goal
from dosadi.runtime.queues import QueueLifecycleState, QueueState
from dosadi.state import WorldState
from dosadi.runtime.facility_choice import choose_facility_for_service


SERVICE_QUEUE_DEFAULTS = {
    "suit_issue": ("queue:suit-issue", "queue:suit-issue:front"),
    "assignment_hall": ("queue:assignment", "queue:assignment:front"),
}


def _find_queue_for_facility(world: WorldState, facility_id: str) -> Optional[QueueState]:
    for queue in world.queues.values():
        if queue.associated_facility == facility_id:
            return queue
    return None


def choose_queue_for_goal(
    agent: AgentState,
    world: WorldState,
    focus_goal: Optional[Goal],
    rng: Optional[random.Random] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Decide which queue (if any) is relevant for the agent's current focus goal.

    Returns (queue_id, queue_location_id).

    MVP:
    - get_suit      -> (queue:suit-issue, queue:suit-issue:front)
    - get_assignment -> (queue:assignment, queue:assignment:front)
    """
    if focus_goal is None:
        return None, None

    kind = getattr(focus_goal, "kind", None)
    service_type: Optional[str] = None

    if kind == "get_suit":
        service_type = "suit_issue"
    elif kind == "get_assignment":
        service_type = "assignment_hall"

    if service_type:
        effective_rng = rng or getattr(world, "rng", None) or random.Random(getattr(world, "seed", 0))
        target_facility_id = choose_facility_for_service(
            agent=agent,
            service_type=service_type,
            world=world,
            rng=effective_rng,
        )

        if target_facility_id is not None:
            queue = _find_queue_for_facility(world, target_facility_id)
            if queue is not None:
                return queue.queue_id, queue.location_id

        default_queue = SERVICE_QUEUE_DEFAULTS.get(service_type)
        if default_queue:
            return default_queue

    return None, None


def attempt_join_queue(
    agent: AgentState,
    world: WorldState,
    queue_id: str,
    tick: int,
) -> bool:
    """
    Try to add the agent to the specified queue.

    Preconditions (not enforced here):
    - Agent is at the queue's location_id.
    - Agent is not already in a queue.

    Returns True if the agent was successfully added.
    """
    queue: Optional[QueueState] = world.queues.get(queue_id)
    if queue is None:
        return False

    if agent.current_queue_id == queue_id:
        return True

    if agent.current_queue_id is not None:
        return False

    if queue.state is not QueueLifecycleState.ACTIVE:
        return False

    if agent.id not in queue.agents_waiting:
        queue.agents_waiting.append(agent.id)

    agent.current_queue_id = queue_id
    agent.queue_join_tick = tick
    return True


def step_agent_movement_toward_target(agent: AgentState, world: WorldState) -> None:
    """
    MVP movement: teleport one hop directly to the navigation_target_id.

    This is intentionally simple; pathfinding and multi-hop routing can be added later.
    """
    if not agent.navigation_target_id:
        return

    if agent.location_id == agent.navigation_target_id:
        return

    agent.location_id = agent.navigation_target_id

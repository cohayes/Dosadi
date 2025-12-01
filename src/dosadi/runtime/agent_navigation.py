from __future__ import annotations

from typing import Optional, Tuple

from dosadi.agents.core import AgentState, Goal
from dosadi.runtime.queues import QueueLifecycleState, QueueState
from dosadi.state import WorldState


def choose_queue_for_goal(
    agent: AgentState,
    world: WorldState,
    focus_goal: Optional[Goal],
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
    if kind == "get_suit":
        return "queue:suit-issue", "queue:suit-issue:front"

    if kind == "get_assignment":
        return "queue:assignment", "queue:assignment:front"

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

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Sequence, TYPE_CHECKING

from dosadi.agents.core import AgentState
from dosadi.runtime.queue_episodes import QueueEpisodeEmitter

if TYPE_CHECKING:
    from dosadi.state import WorldState

AgentID = str


class QueuePriorityRule(Enum):
    FIFO = auto()
    SEVERITY = auto()
    ROLE_BIASED = auto()


class QueueLifecycleState(Enum):
    ACTIVE = auto()
    PAUSED = auto()
    CANCELED = auto()


@dataclass
class QueueStats:
    total_processed: int = 0
    total_denied: int = 0
    max_wait_ticks: int = 0
    avg_wait_ticks: float = 0.0


@dataclass
class QueueState:
    """
    Runtime representation of a logical queue.

    See D-RUNTIME-0202 for semantics.
    """

    queue_id: str
    location_id: str
    associated_facility: Optional[str] = None

    priority_rule: QueuePriorityRule = QueuePriorityRule.FIFO
    processing_rate: int = 1
    process_interval_ticks: int = 100

    state: QueueLifecycleState = QueueLifecycleState.ACTIVE

    agents_waiting: List[AgentID] = field(default_factory=list)

    last_processed_tick: int = 0
    stats: QueueStats = field(default_factory=QueueStats)


def process_all_queues(
    world: "WorldState",
    tick: int,
    episode_emitter: Optional[QueueEpisodeEmitter] = None,
) -> None:
    """
    Process all ACTIVE queues that are due for a processing step.

    Does not implement queue-specific side effects beyond basic accounting.
    Queue-specific policies (suits, assignments, etc.) will be added later.
    """
    if episode_emitter is None:
        episode_emitter = QueueEpisodeEmitter()

    for queue in world.queues.values():
        if queue.state is not QueueLifecycleState.ACTIVE:
            continue
        if tick - queue.last_processed_tick < queue.process_interval_ticks:
            continue
        process_queue(world, queue, tick, episode_emitter)


def process_queue(
    world: "WorldState",
    queue: QueueState,
    tick: int,
    episode_emitter: QueueEpisodeEmitter,
) -> None:
    """
    Generic queue processing:

    - Select up to `processing_rate` agents according to `priority_rule`.
    - Mark them as 'served' in the generic sense (clear queue membership).
    - Emit queue_served episodes.
    - Stats update, but no detailed domain-specific side effects yet.
    """
    waiting_ids: List[AgentID] = list(queue.agents_waiting)
    if not waiting_ids:
        queue.last_processed_tick = tick
        return

    ranked_ids = _rank_waiting_agents(world, queue, waiting_ids)

    served_ids = ranked_ids[: queue.processing_rate]
    remaining_ids = ranked_ids[queue.processing_rate :]

    queue.agents_waiting = remaining_ids

    served_agents: List[AgentState] = []
    for agent_id in served_ids:
        agent = world.agents.get(agent_id)
        if agent is None:
            continue
        _clear_agent_queue_membership(agent, tick, queue, queue.stats)
        served_agents.append(agent)

    if served_agents:
        episode_emitter.queue_served(
            tick=tick,
            queue_location_id=queue.location_id,
            served_agents=served_agents,
            observers=_collect_queue_observers(world, queue, exclude=served_ids),
            event_id=None,
        )

    queue.last_processed_tick = tick


def _rank_waiting_agents(
    world: "WorldState",
    queue: QueueState,
    waiting_ids: Sequence[AgentID],
) -> List[AgentID]:
    """
    Return waiting agent ids sorted according to the queue's priority rule.
    MVP: FIFO; others can be implemented as simple stubs.
    """
    if queue.priority_rule is QueuePriorityRule.FIFO:
        return list(waiting_ids)

    return list(waiting_ids)


def _clear_agent_queue_membership(
    agent: AgentState,
    tick: int,
    queue: QueueState,
    stats: QueueStats,
) -> None:
    """
    Clear the agent's queue membership and update simple wait stats.
    """
    if agent.queue_join_tick is not None:
        wait = tick - agent.queue_join_tick
        if wait > stats.max_wait_ticks:
            stats.max_wait_ticks = wait
        if stats.total_processed > 0:
            stats.avg_wait_ticks = (
                stats.avg_wait_ticks * stats.total_processed + wait
            ) / (stats.total_processed + 1)
        else:
            stats.avg_wait_ticks = float(wait)
        stats.total_processed += 1
    agent.current_queue_id = None
    agent.queue_join_tick = None


def _collect_queue_observers(
    world: "WorldState",
    queue: QueueState,
    exclude: Sequence[AgentID] = (),
) -> List[AgentState]:
    """
    MVP: observers are other agents still waiting in the same queue.
    """
    exclude_set = set(exclude)
    observers: List[AgentState] = []
    for agent_id in queue.agents_waiting:
        if agent_id in exclude_set:
            continue
        agent = world.agents.get(agent_id)
        if agent is not None:
            observers.append(agent)
    return observers

"""Action primitives and execution pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, MutableMapping, Optional

from ..event import Event, EventPriority, EventBus
from ..state import AgentState, WorldState


@dataclass(slots=True)
class Action:
    action_id: str
    actor: str
    verb: str
    start_tick: int
    eta_ticks: int
    target: MutableMapping[str, Optional[str]]
    params: MutableMapping[str, object]
    preconditions_checked: bool = False
    status: str = "QUEUED"
    outcome: MutableMapping[str, object] = field(default_factory=dict)


Precondition = Callable[[WorldState, Action], bool]
Executor = Callable[[WorldState, EventBus, Action], None]


@dataclass(slots=True)
class ActionDefinition:
    verb: str
    preconditions: Iterable[Precondition]
    executor: Executor

    def check(self, world: WorldState, action: Action) -> bool:
        return all(check(world, action) for check in self.preconditions)


class ActionProcessor:
    """Simple action queue with deterministic ordering."""

    def __init__(self, world: WorldState, bus: EventBus):
        self.world = world
        self.bus = bus
        self.definitions: Dict[str, ActionDefinition] = {}
        self._queue: List[Action] = []

    def register(self, definition: ActionDefinition) -> None:
        self.definitions[definition.verb] = definition

    def enqueue(self, action: Action) -> None:
        self._queue.append(action)

    def run(self, current_tick: int) -> None:
        self._queue.sort(key=lambda action: (action.start_tick, action.action_id))
        ready: List[Action] = []
        for action in self._queue:
            if current_tick < action.start_tick + action.eta_ticks:
                continue
            definition = self.definitions.get(action.verb)
            if definition is None:
                action.status = "FAIL"
                action.outcome["notes"] = "Unknown verb"
                continue
            if not definition.check(self.world, action):
                action.status = "FAIL"
                action.outcome["notes"] = "Preconditions failed"
                continue
            action.preconditions_checked = True
            definition.executor(self.world, self.bus, action)
            ready.append(action)
        self._queue = [action for action in self._queue if action not in ready]


# ---------------------------------------------------------------------------
# Generic preconditions used by multiple verbs
# ---------------------------------------------------------------------------


def agent_is_available(world: WorldState, action: Action) -> bool:
    return action.actor in world.agents


def target_facility_exists(world: WorldState, action: Action) -> bool:
    facility = action.target.get("facility")
    if facility is None:
        return True
    # Facilities are not yet explicitly modelled; accept symbolic names.
    return True


def create_event(action: Action, *, event_type: str, priority: EventPriority = EventPriority.NORMAL, payload: Optional[dict] = None) -> Event:
    payload = payload or {}
    payload = dict(payload)
    payload.setdefault("action_id", action.action_id)
    payload.setdefault("actor", action.actor)
    return Event(
        id=f"{action.action_id}:{event_type}",
        type=event_type,
        tick=action.start_tick + action.eta_ticks,
        ttl=300,
        payload=payload,
        priority=priority,
        emitter="ActionProcessor",
    )


__all__ = [
    "Action",
    "ActionDefinition",
    "ActionProcessor",
    "agent_is_available",
    "create_event",
    "target_facility_exists",
]


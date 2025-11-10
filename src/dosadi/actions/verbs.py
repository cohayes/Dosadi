"""Implementation of representative agent verbs.

The goal is not to cover every verb listed in the design documents but to
provide a cross-section that exercises the action processor and touches
multiple subsystems.  Additional verbs can be added by registering new
``ActionDefinition`` instances.
"""

from __future__ import annotations

from .base import ActionDefinition, ActionProcessor, agent_is_available, create_event
from ..event import EventPriority
from ..state import AgentState, WorldState


def _consume_ration(world: WorldState, action: Action) -> None:
    agent = world.agents[action.actor]
    item_id = action.params.get("item_id")
    inventory = agent.inventory.get("owned", [])
    if item_id in inventory:
        inventory.remove(item_id)
        agent.body.nutrition = min(8000.0, agent.body.nutrition + 500.0)
        agent.body.water = min(10.0, agent.body.water + 0.3)
        action.status = "SUCCESS"
        action.outcome["effects"] = {"nutrition": agent.body.nutrition, "water": agent.body.water}
    else:
        action.status = "FAIL"
        action.outcome["notes"] = "Ration missing"


def _labor(world: WorldState, action: Action) -> None:
    agent = world.agents[action.actor]
    ward = world.wards[agent.ward]
    ward.stocks.delta_water(0.1)
    ward.stocks.delta_biomass(0.05)
    agent.body.stamina = max(0.0, agent.body.stamina - 2.0)
    agent.body.nutrition = max(0.0, agent.body.nutrition - 120.0)
    action.status = "SUCCESS"
    action.outcome["effects"] = {"production": {"water": 0.1, "biomass": 0.05}}


def _observe(world: WorldState, action: Action) -> None:
    agent = world.agents[action.actor]
    rumor_id = f"rumor:{action.action_id}"
    agent.memory.events.append(rumor_id)
    action.status = "SUCCESS"
    action.outcome["rumor_stub"] = rumor_id


def register_default_verbs(processor: ActionProcessor) -> None:
    definitions = [
        ActionDefinition(
            verb="ConsumeRation",
            preconditions=[agent_is_available],
            executor=lambda world, bus, action: (
                _consume_ration(world, action),
                bus.publish(
                    create_event(
                        action,
                        event_type="RationConsumed",
                        priority=EventPriority.NORMAL,
                        payload={"item_id": action.params.get("item_id")},
                    )
                ),
            ),
        ),
        ActionDefinition(
            verb="Labor",
            preconditions=[agent_is_available],
            executor=lambda world, bus, action: (
                _labor(world, action),
                bus.publish(
                    create_event(
                        action,
                        event_type="ProductionReported",
                        priority=EventPriority.HIGH,
                        payload={"ward": world.agents[action.actor].ward},
                    )
                ),
            ),
        ),
        ActionDefinition(
            verb="Observe",
            preconditions=[agent_is_available],
            executor=lambda world, bus, action: (
                _observe(world, action),
                bus.publish(
                    create_event(
                        action,
                        event_type="WitnessStubCreated",
                        priority=EventPriority.LOW,
                        payload={"ward": world.agents[action.actor].ward},
                    )
                ),
            ),
        ),
    ]
    for definition in definitions:
        processor.register(definition)


__all__ = ["register_default_verbs"]


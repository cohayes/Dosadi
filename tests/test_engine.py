from dosadi import SimulationEngine
from dosadi.actions.base import Action
from dosadi.worldgen import WorldgenConfig, generate_world


def test_engine_runs_and_registry_updates():
    world = generate_world(WorldgenConfig(seed=42, ward_count=3, faction_count=2, agents_per_faction=1))
    engine = SimulationEngine(world)
    engine.run(10)
    assert world.tick == 10
    assert engine.registry.get("tick") == float(world.tick)
    assert engine.registry.get("t_min") == float(world.minute)


def test_consume_ration_action_emits_event():
    world = generate_world(WorldgenConfig(seed=7, ward_count=2, faction_count=1, agents_per_faction=1))
    engine = SimulationEngine(world)
    agent_id = next(iter(world.agents))
    action = Action(
        action_id="a1",
        actor=agent_id,
        verb="ConsumeRation",
        start_tick=world.tick,
        eta_ticks=0,
        target={},
        params={"item_id": world.agents[agent_id].inventory["owned"][0]},
    )
    engine.action_processor.enqueue(action)
    engine.run(1)
    events = list(engine.bus.outbox)
    assert any(event.type == "RationConsumed" for event in events)


from dosadi import SimulationEngine
from dosadi.actions.base import Action
from dosadi.interfaces.contracts import validate_event_payload, validate_telemetry_snapshot
from dosadi.simulation.scheduler import Phase
from dosadi.worldgen import WorldgenConfig, generate_world


def test_engine_runs_and_registry_updates():
    config = WorldgenConfig.minimal(seed=42, wards=5)
    config.enable_agents = True
    config.agent_roll = type(config.agent_roll)(2, 4)
    world = generate_world(config)
    engine = SimulationEngine(world)
    engine.run(10)
    assert world.tick == 10
    assert engine.registry.get("tick") == float(world.tick)
    assert engine.registry.get("t_min") == float(world.minute)
    metrics = engine.scheduler.last_tick_metrics()
    assert metrics is not None
    assert {phase_metrics.phase for phase_metrics in metrics.phases} == set(Phase.ordered())
    telemetry = list(engine.bus.telemetry_log)
    assert telemetry
    for snapshot in telemetry:
        validate_telemetry_snapshot(snapshot.__dict__)
    assert engine.last_journal is not None
    assert engine.last_snapshot is not None


def test_consume_ration_action_emits_event():
    config = WorldgenConfig.minimal(seed=7, wards=3)
    config.enable_agents = True
    config.agent_roll = type(config.agent_roll)(1, 2)
    world = generate_world(config)
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
    for event in events:
        validate_event_payload(event.type, event.payload)


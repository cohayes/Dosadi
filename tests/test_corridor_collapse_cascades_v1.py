import copy

import pytest

from dosadi.runtime.corridor_cascade import (
    CorridorCascadeConfig,
    corridor_state,
    update_corridor_cascades,
)
from dosadi.runtime.events import ensure_event_bus
from dosadi.runtime.rng_service import ensure_rng_service
from dosadi.state import WorldState
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, _delivery_should_fail
from dosadi.world.survey_map import SurveyEdge, SurveyMap, edge_key


def _world_with_corridor(seed: int = 1) -> tuple[WorldState, str]:
    world = WorldState(seed=seed)
    world.tick = 0
    world.day = 0
    edge = SurveyEdge(a="loc:a", b="loc:b", distance_m=1.0, travel_cost=1.0, hazard=0.1)
    corridor_id = edge.key
    survey_map = SurveyMap(edges={corridor_id: edge})
    world.survey_map = survey_map
    ensure_event_bus(world)
    ensure_rng_service(world)
    return world, corridor_id


def test_cascade_progresses_under_pressure() -> None:
    world, corridor_id = _world_with_corridor()
    cfg: CorridorCascadeConfig = world.corridor_cascade_cfg
    cfg.health_decay_base = 0.15
    cfg.collapse_days = 3
    cfg.degraded_threshold = 0.9
    cfg.closed_threshold = 0.6
    cfg.collapse_threshold = 0.4
    world.corridor_stress = {corridor_id: 1.0}

    statuses: list[str] = []
    for day in range(6):
        update_corridor_cascades(world, day)
        statuses.append(corridor_state(world, corridor_id).collapse_status)

    assert "DEGRADED" in statuses
    assert "CLOSED" in statuses
    assert statuses[-1] == "COLLAPSED"


def test_maintenance_stabilizes_corridor() -> None:
    world, corridor_id = _world_with_corridor(seed=2)
    cfg: CorridorCascadeConfig = world.corridor_cascade_cfg
    cfg.health_decay_base = 0.10
    cfg.health_repair_base = 0.25
    cfg.degraded_threshold = 0.8
    cfg.closed_threshold = 0.6
    cfg.collapse_threshold = 0.4
    cfg.collapse_days = 5
    world.corridor_stress = {corridor_id: 0.9}
    world.corridor_maintenance_investment = {corridor_id: 1.0}

    for day in range(8):
        update_corridor_cascades(world, day)

    assert corridor_state(world, corridor_id).collapse_status != "COLLAPSED"
    assert corridor_state(world, corridor_id).health > 0.4


def test_escort_reduces_delivery_failure_probability() -> None:
    world, corridor_id = _world_with_corridor(seed=3)
    state = corridor_state(world, corridor_id)
    state.risk = 0.8
    world.logistics.deliveries = {}

    def _run_with_escort(level: float) -> int:
        world.corridor_escort_level = {corridor_id: level}
        failures = 0
        for idx in range(12):
            delivery_id = f"d{level}-{idx}"
            req = DeliveryRequest(
                delivery_id=delivery_id,
                project_id="proj",
                origin_node_id="loc:a",
                dest_node_id="loc:b",
                items={"water": 1.0},
                status=DeliveryStatus.REQUESTED,
                created_tick=0,
                route_edge_keys=[corridor_id],
                route_corridors=[corridor_id],
            )
            world.logistics.deliveries[delivery_id] = req
            if _delivery_should_fail(world, delivery_id, day=0):
                failures += 1
        return failures

    no_escort = _run_with_escort(0.0)
    escorted = _run_with_escort(1.0)

    assert escorted <= no_escort
    assert escorted < 12


def test_enforcement_reduces_pressure() -> None:
    base_world, corridor_id = _world_with_corridor(seed=4)
    enforced_world = copy.deepcopy(base_world)
    for world in (base_world, enforced_world):
        cfg: CorridorCascadeConfig = world.corridor_cascade_cfg
        cfg.health_decay_base = 0.08
        cfg.degraded_threshold = 0.85
        cfg.closed_threshold = 0.5
        cfg.collapse_threshold = 0.35
        world.corridor_stress = {corridor_id: 0.9}
    enforced_world.corridor_enforcement = {corridor_id: 1.0}

    for day in range(6):
        update_corridor_cascades(base_world, day)
        update_corridor_cascades(enforced_world, day)

    assert corridor_state(enforced_world, corridor_id).health > corridor_state(base_world, corridor_id).health
    assert corridor_state(enforced_world, corridor_id).risk < corridor_state(base_world, corridor_id).risk


def test_event_bus_emits_status_changes() -> None:
    world, corridor_id = _world_with_corridor(seed=5)
    cfg: CorridorCascadeConfig = world.corridor_cascade_cfg
    cfg.health_decay_base = 0.2
    cfg.degraded_threshold = 0.85
    cfg.closed_threshold = 0.65
    cfg.collapse_threshold = 0.4
    cfg.collapse_days = 2
    world.corridor_stress = {corridor_id: 1.0}

    events: list[str] = []
    bus = ensure_event_bus(world)

    def _handler(evt) -> None:
        events.append(evt.kind)

    bus.subscribe(_handler)
    for day in range(4):
        update_corridor_cascades(world, day)
        bus.drain()

    assert any(kind.endswith("CLOSED") for kind in events)
    assert any(kind.endswith("COLLAPSED") for kind in events)


def test_cascade_is_deterministic() -> None:
    world_a, corridor_id = _world_with_corridor(seed=6)
    world_b = copy.deepcopy(world_a)
    for world in (world_a, world_b):
        cfg: CorridorCascadeConfig = world.corridor_cascade_cfg
        cfg.health_decay_base = 0.12
        cfg.degraded_threshold = 0.9
        cfg.closed_threshold = 0.6
        cfg.collapse_threshold = 0.4
        world.corridor_stress = {corridor_id: 0.95}

    for day in range(5):
        update_corridor_cascades(world_a, day)
        update_corridor_cascades(world_b, day)

    assert world_a.corridor_cascade.signature() == world_b.corridor_cascade.signature()

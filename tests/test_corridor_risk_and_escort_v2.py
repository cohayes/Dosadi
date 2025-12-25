import pytest

from dosadi.runtime.corridor_risk import (
    edge_key,
    ensure_corridor_risk_config,
    ensure_corridor_risk_ledger,
    observe_edge_incident,
    observe_edge_traversal,
    risk_for_edge,
    update_edge_risk,
)
from dosadi.runtime.escort_policy_v2 import required_escorts_for_route, schedule_escorts_for_delivery
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WorldState
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus


def _world_with_risk_and_escort() -> WorldState:
    world = WorldState()
    world.risk_cfg.enabled = True
    world.escort2_cfg.enabled = True
    return world


def test_deterministic_risk_updates():
    world_a = _world_with_risk_and_escort()
    world_b = _world_with_risk_and_escort()

    for world in (world_a, world_b):
        observe_edge_traversal(world, "a|b", day=0, suit_damage=0.2)
        observe_edge_incident(world, "a|b", day=0, severity=0.5)
        observe_edge_traversal(world, "b|c", day=1, stalled=0.3)

    assert world_a.risk_ledger.signature() == world_b.risk_ledger.signature()


def test_incident_increases_risk():
    world = _world_with_risk_and_escort()
    update_edge_risk(world, "a|b", day=0)
    baseline = risk_for_edge(world, "a|b")

    observe_edge_incident(world, "a|b", day=0, severity=0.6)
    assert risk_for_edge(world, "a|b") > baseline


def test_decay_reduces_risk_over_time():
    world = _world_with_risk_and_escort()
    observe_edge_incident(world, "a|b", day=0, severity=0.8)
    initial = risk_for_edge(world, "a|b")

    update_edge_risk(world, "a|b", day=5)
    decayed = risk_for_edge(world, "a|b")

    assert decayed < initial


def test_escort_requirement_tiers():
    world = _world_with_risk_and_escort()
    ledger = ensure_corridor_risk_ledger(world)
    cfg = ensure_corridor_risk_config(world)
    cfg.enabled = True
    cfg.max_risk = 1.0
    cfg.risk_decay_per_day = 0.0

    edges = {
        "low": 0.2,
        "warn": 0.5,
        "high": 0.7,
        "critical": 0.9,
    }
    for name, risk in edges.items():
        rec = ledger.record(name)
        rec.risk = risk
        rec.last_updated_day = 0

    world.escort2_cfg.enabled = True
    assert required_escorts_for_route(world, ["low"]) == world.escort2_cfg.base_escort_count
    assert required_escorts_for_route(world, ["warn"]) == world.escort2_cfg.warn_escort_count
    assert required_escorts_for_route(world, ["high"]) == world.escort2_cfg.high_escort_count
    assert required_escorts_for_route(world, ["critical"]) == world.escort2_cfg.critical_escort_count


def test_no_duplicate_escort_scheduling():
    world = _world_with_risk_and_escort()
    delivery = DeliveryRequest(
        delivery_id="d1",
        project_id="p",
        origin_node_id="a",
        dest_node_id="b",
        items={},
        status=DeliveryStatus.REQUESTED,
        created_tick=0,
        due_tick=None,
        route_edge_keys=[edge_key("a", "b")],
    )

    observe_edge_incident(world, delivery.route_edge_keys[0], day=0, severity=0.9)
    world.risk_ledger.record(delivery.route_edge_keys[0]).risk = 0.9
    guards = ["g1", "g2", "g3"]

    schedule_escorts_for_delivery(world, delivery, available_guard_ids=guards, day=0)
    first_count = len(delivery.escort_mission_ids)
    schedule_escorts_for_delivery(world, delivery, available_guard_ids=guards, day=0)

    assert first_count > 0
    assert len(delivery.escort_mission_ids) == first_count
    assert len(delivery.escort_agent_ids) == first_count


def test_ledger_cap_eviction_deterministic():
    world = _world_with_risk_and_escort()
    world.risk_cfg.max_edges_tracked = 3

    for idx in range(5):
        update_edge_risk(world, f"e{idx}", day=idx, incident_severity=0.2 * idx)

    assert len(world.risk_ledger.edges) == 3
    remaining_keys = sorted(world.risk_ledger.edges)
    assert remaining_keys == ["e2", "e3", "e4"]


def test_snapshot_roundtrip_preserves_risk_and_escorts():
    world = _world_with_risk_and_escort()
    observe_edge_incident(world, "a|b", day=1, severity=0.7)

    delivery = DeliveryRequest(
        delivery_id="d2",
        project_id="p",
        origin_node_id="a",
        dest_node_id="b",
        items={},
        status=DeliveryStatus.REQUESTED,
        created_tick=0,
        due_tick=None,
        route_edge_keys=[edge_key("a", "b")],
    )
    schedule_escorts_for_delivery(world, delivery, available_guard_ids=["g1", "g2"], day=1)

    world.logistics.add(delivery)

    snap = snapshot_world(world, scenario_id="test")
    restored = restore_world(snap)

    assert restored.risk_ledger.signature() == world.risk_ledger.signature()
    restored_delivery = restored.logistics.deliveries[delivery.delivery_id]
    assert restored_delivery.escort_mission_ids == delivery.escort_mission_ids
    assert restored_delivery.escort_agent_ids == delivery.escort_agent_ids


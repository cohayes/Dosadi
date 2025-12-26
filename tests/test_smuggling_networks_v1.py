import copy
from pathlib import Path

import pytest

from dosadi.runtime.customs import BorderCrossing, CustomsConfig, process_customs_crossing
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.smuggling import (
    SmugglingNetworkState,
    ensure_smuggling_config,
    ensure_smuggling_state,
    plan_smuggling_shipments,
    record_smuggling_outcome,
)
from dosadi.state import FactionState, StockState, WardState, WorldState
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode, edge_key
from dosadi.runtime.culture_wars import WardCultureState
from dosadi.world.logistics import DeliveryStatus


def _basic_world() -> WorldState:
    world = WorldState(seed=7)
    world.customs_cfg = CustomsConfig(enabled=True, base_inspection_rate=1.0, contraband_detection_base=1.0)
    world.smuggling_cfg.enabled = True
    world.wards = {
        "ward:a": WardState(id="ward:a", name="A", ring=1, sealed_mode="OPEN"),
        "ward:b": WardState(id="ward:b", name="B", ring=1, sealed_mode="OPEN"),
    }
    world.culture_by_ward = {
        "ward:a": WardCultureState(ward_id="ward:a", norms={"norm:smuggling_tolerance": 0.9, "norm:corruption": 0.5}),
        "ward:b": WardCultureState(ward_id="ward:b", norms={"norm:smuggling_tolerance": 0.7, "norm:raider_alignment": 0.6}),
    }
    world.survey_map = SurveyMap(
        nodes={
            "node:a": SurveyNode(node_id="node:a", kind="ward", ward_id="ward:a"),
            "node:b": SurveyNode(node_id="node:b", kind="ward", ward_id="ward:b"),
        }
    )
    edge = SurveyEdge(a="node:a", b="node:b", distance_m=1.0, travel_cost=1.0, hazard=0.1)
    world.survey_map.edges[edge.key] = edge
    world.survey_map.rebuild_adjacency()
    world.factions = {
        "fac:raiders": FactionState(
            id="fac:raiders",
            name="Raiders",
            archetype="raider",
            home_ward="ward:a",
            assets=StockState(credits={"credits": 100.0}),
            smuggling_profile={"NARCOTICS": 1.0, "WEAPON_PARTS": 0.5},
        )
    }
    return world


def _ship_signature(shipments):
    return [
        (
            sh.delivery_id,
            sh.origin_node_id,
            sh.dest_node_id,
            tuple(sorted(sh.items.items())),
            tuple(sorted(getattr(sh, "smuggling_bribe_map", {}).items())),
        )
        for sh in shipments
    ]


def test_deterministic_planning():
    world = _basic_world()
    shipments_a = plan_smuggling_shipments(world, day=1)
    shipments_b = plan_smuggling_shipments(copy.deepcopy(world), day=1)
    assert shipments_a, "expected smuggling shipments"
    assert _ship_signature(shipments_a) == _ship_signature(shipments_b)


def test_bounded_edge_stats_and_caps():
    world = _basic_world()
    cfg = ensure_smuggling_config(world)
    cfg.max_shipments_per_day = 1
    shipments = plan_smuggling_shipments(world, day=2)
    assert len(shipments) == 1
    state = ensure_smuggling_state(world)
    net: SmugglingNetworkState = state["fac:raiders"]
    for idx in range(40):
        record_smuggling_outcome(net, day=idx, route_edge_keys=[edge_key("a", f"b{idx}")], seized=True)
    assert len(net.edge_stats) <= cfg.border_topk


def test_smuggling_bribes_reduce_seizure():
    world = _basic_world()
    shipments = plan_smuggling_shipments(world, day=3)
    shipment = shipments[0]
    shipment.status = DeliveryStatus.IN_TRANSIT
    crossing = BorderCrossing(border_at=shipment.route_edge_keys[0], from_control="ward:a", to_control="ward:b")

    # No targeted bribe should seize due to high detection
    bare = copy.deepcopy(shipment)
    bare.smuggling_bribe_map = {}
    event_bare = process_customs_crossing(world, day=3, shipment=bare, crossing=crossing)
    assert event_bare is not None
    assert event_bare.outcome == "SEIZED"

    # Targeted bribe clears
    bribed = copy.deepcopy(shipment)
    bribed.smuggling_bribe_map = {crossing.border_at: 5.0}
    event_bribed = process_customs_crossing(world, day=3, shipment=bribed, crossing=crossing)
    assert event_bribed.outcome == "CLEARED"
    assert event_bribed.bribe_paid == pytest.approx(5.0)


def test_learning_updates_route_preferences():
    world = _basic_world()
    state = ensure_smuggling_state(world)
    net = state.setdefault("fac:raiders", SmugglingNetworkState(faction_id="fac:raiders"))
    before = net.edge_stats.get("edge-1", None)
    record_smuggling_outcome(net, day=4, route_edge_keys=["edge-1"], seized=True)
    record_smuggling_outcome(net, day=5, route_edge_keys=["edge-1"], seized=False, bribe_paid=1.0)
    updated = net.edge_stats["edge-1"]
    assert updated.risk_est != (before.risk_est if before else 0.5)
    assert updated.cost_est >= 0.1


def test_snapshot_roundtrip_preserves_smuggling_state(tmp_path: Path):
    world = _basic_world()
    plan_smuggling_shipments(world, day=6)
    snap = snapshot_world(world, scenario_id="smuggling-test")
    restored = restore_world(snap)
    shipments_restored = plan_smuggling_shipments(restored, day=6)
    assert _ship_signature(shipments_restored)
    assert _ship_signature(shipments_restored) == _ship_signature(plan_smuggling_shipments(restored, day=6))

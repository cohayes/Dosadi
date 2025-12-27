from dosadi.runtime.comms import (
    _stable_float,
    get_comms_modifiers_for_hop,
    refresh_comms_modifiers,
    run_comms_day,
)
from dosadi.runtime.media import _comms_latency_add, process_media_for_day, send_media_message
from dosadi.runtime.snapshot import from_snapshot_dict, to_snapshot_dict
from dosadi.state import WardState, WorldState
from dosadi.world.survey_map import SurveyEdge, SurveyMap


def _basic_world() -> WorldState:
    world = WorldState(seed=2025)
    world.comms_cfg.enabled = True
    world.media_cfg.enabled = True
    world.survey_map = SurveyMap()
    world.wards = {
        "ward:a": WardState(id="ward:a", name="A", ring=1, sealed_mode="partial"),
        "ward:b": WardState(id="ward:b", name="B", ring=1, sealed_mode="partial"),
    }
    world.wards["ward:a"].facilities["RELAY_TOWER_L2"] = 1
    world.wards["ward:b"].facilities["RELAY_TOWER_L2"] = 1
    world.survey_map.upsert_edge(SurveyEdge(a="ward:a", b="ward:b", distance_m=1.0, travel_cost=1.0))
    return world


def _snapshot_clone(world: WorldState) -> WorldState:
    return from_snapshot_dict(to_snapshot_dict(world))


def test_comms_deterministic_transitions() -> None:
    world_a = _basic_world()
    world_b = _snapshot_clone(world_a)

    run_comms_day(world_a, day=1)
    run_comms_day(world_b, day=1)

    assert {nid: node.status for nid, node in world_a.comms_nodes.items()} == {
        nid: node.status for nid, node in world_b.comms_nodes.items()
    }


def test_relay_outage_forces_fallback() -> None:
    world = _basic_world()
    run_comms_day(world, day=0)
    world.comms_nodes["relay:ward:a"].status = "OUTAGE"

    msg = send_media_message(
        world,
        sender="inst",
        origin_ward="ward:a",
        dest_scope="WARD",
        dest_id="ward:b",
        kind="ORDER",
    )
    process_media_for_day(world, current_day=0)

    assert msg.channel == "COURIER"
    assert world.metrics.counters.get("comms.relay_fallbacks", 0) >= 1


def test_jamming_increases_latency_and_loss_modifiers() -> None:
    world = _basic_world()
    run_comms_day(world, day=0)
    world.comms_nodes["relay:ward:a"].status = "JAMMED"
    world.comms_nodes["relay:ward:b"].status = "JAMMED"
    refresh_comms_modifiers(world)

    path = ["ward:a", "ward:b"]
    added_latency = _comms_latency_add(world, path, "RELAY")
    modifiers = get_comms_modifiers_for_hop(world, "ward:a", "ward:b", "RELAY")

    assert added_latency > 0
    assert modifiers.loss_mult > 1.0


def test_maintenance_bias_improves_repair_probability() -> None:
    node_id = "relay:ward:a"
    world_low = _basic_world()
    world_high = _basic_world()
    world_low.comms_cfg.repair_rate = 0.05
    world_high.comms_cfg.repair_rate = 1.0
    world_high.comms_resilience_spend_bias = 0.5
    run_comms_day(world_low, day=1)
    run_comms_day(world_high, day=1)
    world_low.comms_nodes[node_id].status = "OUTAGE"
    world_high.comms_nodes[node_id].status = "OUTAGE"

    roll = _stable_float((node_id, 2, "repair"), world_low.comms_cfg.deterministic_salt)
    assert roll >= 0.0  # document the roll used for both worlds

    run_comms_day(world_low, day=2)
    run_comms_day(world_high, day=2)

    assert world_low.comms_nodes[node_id].status in {"OUTAGE", "DEGRADED"}
    assert world_high.comms_nodes[node_id].status != "OUTAGE"


def test_sabotage_hook_sets_outage() -> None:
    world = _basic_world()
    world.comms_sabotage_targets = {"relay:ward:a"}
    run_comms_day(world, day=0)

    assert world.comms_nodes["relay:ward:a"].status == "OUTAGE"

    msg = send_media_message(
        world,
        sender="inst",
        origin_ward="ward:a",
        dest_scope="WARD",
        dest_id="ward:b",
        kind="ORDER",
    )
    process_media_for_day(world, current_day=0)
    assert msg.channel == "COURIER"


def test_snapshot_roundtrip_preserves_comms_nodes() -> None:
    world = _basic_world()
    run_comms_day(world, day=0)
    world.comms_nodes["relay:ward:a"].status = "DEGRADED"
    world.comms_nodes["relay:ward:b"].status = "JAMMED"
    world.comms_events = [{"kind": "COMMS_JAMMED", "node": "relay:ward:b", "day": 0}]
    refresh_comms_modifiers(world)

    restored = _snapshot_clone(world)
    assert restored.comms_nodes["relay:ward:a"].status == "DEGRADED"
    assert restored.comms_nodes["relay:ward:b"].status == "JAMMED"
    assert restored.comms_events == world.comms_events


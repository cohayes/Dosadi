import pytest

from dosadi.runtime.media import (
    consume_order_messages,
    consume_propaganda,
    media_signature,
    process_media_for_day,
    send_media_message,
)
from dosadi.runtime.snapshot import from_snapshot_dict, to_snapshot_dict
from dosadi.state import WardState, WorldState
from dosadi.world.survey_map import SurveyEdge, SurveyMap


def _basic_world() -> WorldState:
    world = WorldState(seed=123)
    world.media_cfg.enabled = True
    world.survey_map = SurveyMap()
    world.wards = {
        "ward:a": WardState(id="ward:a", name="A", ring=1, sealed_mode="partial"),
        "ward:b": WardState(id="ward:b", name="B", ring=1, sealed_mode="partial"),
        "ward:c": WardState(id="ward:c", name="C", ring=1, sealed_mode="partial"),
    }
    world.survey_map.upsert_edge(SurveyEdge(a="ward:a", b="ward:b", distance_m=1.0, travel_cost=1.0))
    world.survey_map.upsert_edge(SurveyEdge(a="ward:b", b="ward:c", distance_m=1.0, travel_cost=1.0))
    world.risk_cfg.enabled = True
    return world


def _process_until(world: WorldState, end_day: int) -> None:
    for day in range(world.day, end_day + 1):
        world.day = day
        process_media_for_day(world, current_day=day)


def test_media_determinism_signature_stable():
    w1 = _basic_world()
    w2 = _basic_world()

    send_media_message(w1, sender="inst", origin_ward="ward:a", dest_scope="WARD", dest_id="ward:b", kind="ORDER")
    send_media_message(w2, sender="inst", origin_ward="ward:a", dest_scope="WARD", dest_id="ward:b", kind="ORDER")

    _process_until(w1, 3)
    _process_until(w2, 3)

    assert media_signature(w1) == media_signature(w2)


def test_media_queue_bounds_drop_lowest_priority():
    world = _basic_world()
    world.media_cfg.max_messages_per_ward_queue = 2
    send_media_message(
        world,
        sender="inst",
        origin_ward="ward:a",
        dest_scope="WARD",
        dest_id="ward:b",
        kind="ORDER",
        priority=2,
    )
    send_media_message(
        world,
        sender="inst",
        origin_ward="ward:a",
        dest_scope="WARD",
        dest_id="ward:b",
        kind="ORDER",
        priority=1,
    )
    third = send_media_message(
        world,
        sender="inst",
        origin_ward="ward:a",
        dest_scope="WARD",
        dest_id="ward:b",
        kind="ORDER",
        priority=0,
    )

    _process_until(world, 2)
    inbox = world.media_inbox_by_ward.get("ward:b")
    assert inbox is not None
    assert len(inbox) == 2
    assert third.status == "DROPPED"


def test_relay_speed_reduces_latency():
    world = _basic_world()
    world.media_cfg.enabled = True
    world.media_cfg.deterministic_salt = "relay-test"
    world.wards["ward:a"].facilities["RELAY_TOWER_L2"] = 1
    world.wards["ward:c"].facilities["RELAY_TOWER_L2"] = 1
    # make courier slower
    world.survey_map.upsert_edge(SurveyEdge(a="ward:a", b="ward:c", distance_m=1.0, travel_cost=3.5))

    courier_msg = send_media_message(
        world,
        sender="inst",
        origin_ward="ward:a",
        dest_scope="WARD",
        dest_id="ward:c",
        kind="ORDER",
        channel="COURIER",
    )
    relay_msg = send_media_message(
        world,
        sender="inst",
        origin_ward="ward:a",
        dest_scope="WARD",
        dest_id="ward:c",
        kind="ORDER",
    )

    _process_until(world, 5)

    assert courier_msg.notes["eta_day"] > relay_msg.notes["eta_day"]


def test_interception_deterministic_with_risk():
    world = _basic_world()
    world.media_cfg.intercept_rate_base = 1.0
    world.risk_ledger.record("ward:a|ward:b").risk = 1.0
    msg = send_media_message(
        world,
        sender="inst",
        origin_ward="ward:a",
        dest_scope="WARD",
        dest_id="ward:b",
        kind="INTEL",
    )

    _process_until(world, 1)
    assert msg.status == "INTERCEPTED"
    assert world.metrics.counters.get("media.intercepted", 0) >= 1


def test_stale_orders_have_reduced_effect():
    world = _basic_world()
    stale = send_media_message(
        world,
        sender="inst",
        origin_ward="ward:a",
        dest_scope="WARD",
        dest_id="ward:b",
        kind="ORDER",
        payload={"order_value": 10},
        ttl_days=5,
        day_sent=0,
    )
    world.day = 4
    fresh = send_media_message(
        world,
        sender="inst",
        origin_ward="ward:a",
        dest_scope="WARD",
        dest_id="ward:b",
        kind="ORDER",
        payload={"order_value": 10},
        ttl_days=5,
        day_sent=4,
    )
    _process_until(world, 5)
    applied = consume_order_messages(world, "ward:b", current_day=5)
    assert applied > 0
    assert fresh.msg_id not in world.media_inbox_by_ward.get("ward:b", [])
    assert stale.msg_id not in world.media_inbox_by_ward.get("ward:b", [])
    effects = world.inst_policy_by_ward["ward:b"].notes["order_effects"]
    assert effects[1] >= effects[0]


def test_snapshot_roundtrip_preserves_media_state():
    world = _basic_world()
    delivered = send_media_message(
        world,
        sender="inst",
        origin_ward="ward:a",
        dest_scope="WARD",
        dest_id="ward:b",
        kind="ORDER",
    )
    inflight = send_media_message(
        world,
        sender="inst",
        origin_ward="ward:b",
        dest_scope="WARD",
        dest_id="ward:c",
        kind="PROPAGANDA",
    )
    _process_until(world, 2)
    consume_propaganda(world, "ward:c", current_day=2)

    snapshot = to_snapshot_dict(world)
    restored = from_snapshot_dict(snapshot)

    assert isinstance(restored.media_in_flight[delivered.msg_id], type(delivered))
    assert restored.media_in_flight[delivered.msg_id].status == "DELIVERED"
    assert list(restored.media_inbox_by_ward.get("ward:c", [])) == []
    assert restored.media_in_flight[inflight.msg_id].status in {"IN_FLIGHT", "DELIVERED", "DROPPED", "INTERCEPTED"}

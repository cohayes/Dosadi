from collections import deque

from dosadi.runtime.health import WardHealthState
from dosadi.runtime.ideology import ensure_ward_ideology
from dosadi.runtime.institutions import ensure_policy, ensure_state
from dosadi.runtime.media import MediaMessage
from dosadi.runtime.religion import (
    ReligionConfig,
    ensure_religion_config,
    ensure_ward_religion,
    religion_signature,
    run_religion_for_week,
)
from dosadi.runtime.snapshot import from_snapshot_dict, to_snapshot_dict
from dosadi.state import WardState, WorldState


def _basic_world(day: int = 7) -> WorldState:
    world = WorldState(seed=123)
    world.day = day
    world.religion_cfg = ReligionConfig(enabled=True)
    world.wards = {"ward:a": WardState(id="ward:a", name="A", ring=1, sealed_mode="open")}
    ensure_policy(world, "ward:a")
    ensure_state(world, "ward:a")
    ensure_religion_config(world).enabled = True
    return world


def test_determinism_signature_stable():
    sig1 = religion_signature(_run_week())
    sig2 = religion_signature(_run_week())
    assert sig1 == sig2


def _run_week(day: int = 7) -> WorldState:
    world = _basic_world(day)
    run_religion_for_week(world, day=day)
    return world


def test_crisis_conversion_increases_adherence():
    normal = _run_week()
    crisis_world = _basic_world()
    crisis_world.health_by_ward["ward:a"] = WardHealthState(ward_id="ward:a", outbreaks={"WATERBORNE": 0.6})
    run_religion_for_week(crisis_world, day=crisis_world.day)

    base_share = normal.religion_by_ward["ward:a"].adherence.get("sect:heretic_network", 0.0)
    crisis_share = crisis_world.religion_by_ward["ward:a"].adherence.get("sect:heretic_network", 0.0)
    assert crisis_share > base_share


def test_suppression_tradeoff_reduces_hostile_share_and_increases_unrest():
    world = _basic_world()
    ward_state = ensure_ward_religion(world, "ward:a")
    ward_state.adherence["sect:heretic_network"] = 0.4
    ensure_policy(world, "ward:a").suppression_intensity = 0.8
    inst_state = ensure_state(world, "ward:a")
    inst_state.unrest = 0.0

    run_religion_for_week(world, day=world.day)

    updated = world.religion_by_ward["ward:a"].adherence.get("sect:heretic_network", 0.0)
    assert updated < 0.4
    assert inst_state.unrest > 0.0


def test_healing_rites_reduce_outbreak_intensity():
    world = _basic_world()
    health_state = WardHealthState(ward_id="ward:a", outbreaks={"RESPIRATORY": 0.4})
    world.health_by_ward["ward:a"] = health_state
    ward_state = ensure_ward_religion(world, "ward:a")
    ward_state.ritual_calendar["HEALING_RITES"] = world.day
    ward_state.adherence["sect:well_mystics"] = 0.7

    run_religion_for_week(world, day=world.day)

    assert health_state.outbreaks["RESPIRATORY"] < 0.4


def test_media_sermon_adjusts_adherence_and_axes():
    world = _basic_world()
    world.media_cfg.enabled = True
    msg = MediaMessage(
        msg_id="msg:test",
        day_sent=world.day,
        sender="clergy",
        origin_ward="ward:a",
        dest_scope="WARD",
        dest_id="ward:a",
        channel="COURIER",
        kind="SERMON",
        priority=1,
        ttl_days=3,
        payload={"sect_id": "sect:orthodox_church", "axis": "ORTHODOXY"},
    )
    world.media_in_flight[msg.msg_id] = msg
    world.media_inbox_by_ward.setdefault("ward:a", deque()).append(msg.msg_id)

    run_religion_for_week(world, day=world.day)

    ward_state = world.religion_by_ward["ward:a"]
    ideology_state = ensure_ward_ideology(world, "ward:a")
    assert ward_state.adherence.get("sect:orthodox_church", 0.0) > 0.0
    assert ideology_state.curriculum_axes.get("ORTHODOXY", 0.0) > 0.0


def test_snapshot_roundtrip_retains_religion_state():
    world = _run_week()
    snap = to_snapshot_dict(world)
    restored = from_snapshot_dict(snap)

    assert religion_signature(world) == religion_signature(restored)

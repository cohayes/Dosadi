from types import SimpleNamespace

from dosadi.runtime.leadership import ensure_leadership_state
from dosadi.runtime.policing import ensure_policing_state
from dosadi.runtime.reforms import (
    ReformConfig,
    ReformEvent,
    ReformMovement,
    WatchdogInstitution,
    ensure_reform_config,
    ensure_reform_events,
    ensure_reform_movements,
    ensure_watchdogs,
    load_reform_seed,
    reform_signature,
    run_reforms_for_day,
    export_reform_seed,
)
from dosadi.runtime.shadow_state import CorruptionIndex
from dosadi.runtime.sovereignty import ensure_sovereignty_state
from dosadi.runtime.snapshot import restore_world, snapshot_world


class DummyWard:
    def __init__(self, need_index: float):
        self.need_index = need_index


def _base_world(*, capture: float, shadow: float, hardship: float, legitimacy: float = 0.4):
    world = SimpleNamespace(seed=1, day=0)
    world.wards = {"ward:1": DummyWard(need_index=hardship)}
    world.corruption_by_ward = {
        "ward:1": CorruptionIndex(ward_id="ward:1", capture=capture, shadow_state=shadow, petty=0.1)
    }
    ensure_sovereignty_state(world, ward_ids=["ward:1"])
    lead = ensure_leadership_state(world, polities=["polity:empire"])["polity:empire"]
    lead.legitimacy = legitimacy
    lead.proc_legit = legitimacy
    ensure_policing_state(world, "ward:1")
    cfg: ReformConfig = ensure_reform_config(world)
    cfg.enabled = True
    cfg.cadence_days = 1
    return world


def test_deterministic_signature_matches():
    w1 = _base_world(capture=0.8, shadow=0.7, hardship=0.6)
    w2 = _base_world(capture=0.8, shadow=0.7, hardship=0.6)
    run_reforms_for_day(w1, day=0)
    run_reforms_for_day(w2, day=0)
    assert reform_signature(w1) == reform_signature(w2)


def test_high_exposure_and_hardship_form_more_movements():
    low = _base_world(capture=0.1, shadow=0.1, hardship=0.1)
    high = _base_world(capture=0.9, shadow=0.9, hardship=0.8)
    run_reforms_for_day(low, day=0)
    run_reforms_for_day(high, day=0)
    assert len(high.reform_movements) > len(low.reform_movements)


def test_watchdog_capture_drifts_with_exposure():
    world = _base_world(capture=0.4, shadow=0.4, hardship=0.5)
    ensure_watchdogs(world)["ward:1"] = WatchdogInstitution(
        watchdog_id="watchdog:ward:1",
        ward_id="ward:1",
        kind="AUDIT",
        sponsor_faction=None,
        independence=0.6,
        capture=0.1,
        capacity=0.5,
        last_update_day=-1,
    )
    run_reforms_for_day(world, day=0)
    watchdog = world.watchdogs["ward:1"]
    assert watchdog.capture > 0.1
    assert watchdog.independence < 0.6


def test_successful_reform_reduces_capture():
    world = _base_world(capture=0.9, shadow=0.6, hardship=0.6)
    movement = ReformMovement(
        movement_id="reform:ward:1:0",
        scope="WARD",
        ward_id="ward:1",
        polity_id="polity:empire",
        sponsor_faction=None,
        coalition={},
        agenda={"audit_strictness": 1.0},
        momentum=0.9,
        legitimacy_claim=0.5,
        risk_of_backlash=0.0,
        status="ACTIVE",
        start_day=0,
        last_update_day=-1,
    )
    ensure_reform_movements(world)[movement.movement_id] = movement
    before = world.corruption_by_ward["ward:1"].capture
    run_reforms_for_day(world, day=0)
    after = world.corruption_by_ward["ward:1"].capture
    assert after < before


def test_backlash_increases_terror_mix():
    world = _base_world(capture=0.7, shadow=0.7, hardship=0.4, legitimacy=0.2)
    cfg = ensure_reform_config(world)
    cfg.backlash_base = 1.0
    movement = ReformMovement(
        movement_id="reform:ward:1:1",
        scope="WARD",
        ward_id="ward:1",
        polity_id="polity:empire",
        sponsor_faction=None,
        coalition={},
        agenda={},
        momentum=0.9,
        legitimacy_claim=0.6,
        risk_of_backlash=1.0,
        status="ACTIVE",
        start_day=0,
        last_update_day=-1,
    )
    ensure_reform_movements(world)[movement.movement_id] = movement
    police = ensure_policing_state(world, "ward:1")
    police.doctrine_mix["TERROR"] = 0.2
    run_reforms_for_day(world, day=0)
    assert world.reform_movements[movement.movement_id].status != "ACTIVE"
    assert ensure_policing_state(world, "ward:1").doctrine_mix["TERROR"] >= 0.2


def test_snapshot_roundtrip_preserves_reforms():
    world = _base_world(capture=0.6, shadow=0.6, hardship=0.6)
    run_reforms_for_day(world, day=0)
    ensure_reform_events(world).append(ReformEvent(day=0, movement_id="m0", kind="FORMATION", payload={}))
    snap = snapshot_world(world, scenario_id="reform-test")
    restored = restore_world(snap)
    load_reform_seed(restored, export_reform_seed(world))
    assert reform_signature(restored) == reform_signature(world)

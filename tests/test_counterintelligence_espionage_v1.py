from dosadi.runtime.espionage import plan_intel_ops, resolve_intel_ops
from dosadi.runtime.ledger import LedgerAccount
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WardState, WorldState


def _base_world(seed: int = 1) -> WorldState:
    world = WorldState(seed=seed)
    world.espionage_cfg.enabled = True
    world.corridor_stress = {"edge:1": 0.8}
    world.media_stats = {"relay:alpha": 1.0}
    ward = WardState(id="ward:alpha", name="Alpha", ring=1, sealed_mode="OPEN")
    ward.need_index = 0.6
    world.wards[ward.id] = ward
    world.ledger_state.accounts["acct:state:treasury"] = LedgerAccount(
        acct_id="acct:state:treasury", balance=1.0
    )
    return world


def test_determinism_same_seed_same_outcomes():
    base = _base_world(seed=99)
    snap = snapshot_world(base, scenario_id="determinism")
    world_a = restore_world(snap)
    world_b = restore_world(snap)

    plan_intel_ops(world_a, day=3)
    plan_intel_ops(world_b, day=3)
    resolve_intel_ops(world_a, day=3)
    resolve_intel_ops(world_b, day=3)

    summary_a = [(o.op_id, o.status, o.effects, o.loot, o.notes) for o in world_a.intel_ops_history]
    summary_b = [(o.op_id, o.status, o.effects, o.loot, o.notes) for o in world_b.intel_ops_history]
    assert summary_a == summary_b


def test_counterintel_coverage_reduces_success():
    low_cov = _base_world(seed=7)
    high_cov = _base_world(seed=7)
    low_cov.espionage_cfg.max_ops_active = 1
    high_cov.espionage_cfg.max_ops_active = 1
    low_cov.espionage_cfg.base_detect_rate = 0.0
    low_cov.espionage_cfg.base_success_rate = 1.0
    high_cov.espionage_cfg.base_detect_rate = 0.2
    high_cov.espionage_cfg.base_success_rate = 1.0
    low_cov.media_stats.clear()
    high_cov.media_stats.clear()
    low_cov.counterintel_by_ward["edge:1"] = 0.0
    high_cov.counterintel_by_ward["edge:1"] = 1.0

    plan_intel_ops(low_cov, day=0)
    plan_intel_ops(high_cov, day=0)
    low_outcomes = resolve_intel_ops(low_cov, day=0)
    high_outcomes = resolve_intel_ops(high_cov, day=0)

    assert any(out.status == "SUCCEEDED" for out in low_outcomes)
    assert all(out.status != "SUCCEEDED" for out in high_outcomes)


def test_relay_sabotage_effect_applied():
    world = _base_world()
    world.espionage_cfg.max_ops_active = 1
    world.espionage_cfg.base_success_rate = 1.0
    world.corridor_stress.clear()
    plan_intel_ops(world, day=5)
    outcomes = resolve_intel_ops(world, day=5)
    assert any(out.status == "SUCCEEDED" for out in outcomes)
    assert world.media_stats.get("relay_loss:alpha", 0.0) > 0.0


def test_courier_bribery_increases_intercepts():
    world = _base_world()
    world.espionage_cfg.max_ops_active = 1
    world.espionage_cfg.base_success_rate = 1.0
    world.espionage_cfg.base_detect_rate = 0.0
    world.media_stats.clear()
    plan_intel_ops(world, day=2)
    outcomes = resolve_intel_ops(world, day=2)
    assert any(out.status == "SUCCEEDED" for out in outcomes)
    assert world.media_stats.get("intercept_bonus:edge:1", 0.0) > 0.0


def test_false_flag_propaganda_adds_message():
    world = _base_world()
    world.espionage_cfg.max_ops_active = 1
    world.espionage_cfg.base_success_rate = 1.0
    world.espionage_cfg.base_detect_rate = 0.0
    world.corridor_stress.clear()
    world.media_stats.clear()
    plan_intel_ops(world, day=8)
    outcomes = resolve_intel_ops(world, day=8)
    assert any(out.status == "SUCCEEDED" for out in outcomes)
    inbox = world.media_inbox_by_ward.get("ward:alpha", [])
    assert inbox
    assert inbox[-1]["spoofed"] is True


def test_ledger_theft_bounded_balance():
    world = _base_world()
    world.espionage_cfg.max_ops_active = 1
    world.espionage_cfg.base_success_rate = 1.0
    world.corridor_stress.clear()
    world.media_stats.clear()
    world.wards.clear()
    world.ledger_state.accounts["acct:state:treasury"].balance = 100.0
    plan_intel_ops(world, day=1)
    outcomes = resolve_intel_ops(world, day=1)
    acct = world.ledger_state.accounts["acct:state:treasury"]
    assert any(out.status == "SUCCEEDED" for out in outcomes)
    assert acct.balance >= 0
    assert acct.balance <= 100.0


def test_snapshot_roundtrip_preserves_ops_and_counterintel():
    world = _base_world()
    world.espionage_cfg.max_ops_active = 2
    world.counterintel_by_ward["edge:1"] = 0.5
    plan_intel_ops(world, day=4)

    snap = snapshot_world(world, scenario_id="espionage")
    restored = restore_world(snap)

    assert set(restored.intel_ops_active.keys()) == set(world.intel_ops_active.keys())
    assert restored.counterintel_by_ward == world.counterintel_by_ward

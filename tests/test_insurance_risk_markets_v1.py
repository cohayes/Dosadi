from __future__ import annotations

from dosadi.runtime.corridor_risk import CorridorRiskLedger, EdgeRiskRecord
from dosadi.runtime.insurance import (
    InsuredFlow,
    ensure_insurance_config,
    insurance_signature,
    pay_claims_for_corridor,
    run_insurance_week,
    shadow_risk_modifier,
)
from dosadi.state import WorldState
from dosadi.runtime.snapshot import restore_world, snapshot_world


def _base_world() -> WorldState:
    world = WorldState(seed=42)
    world.risk_ledger = CorridorRiskLedger(edges={"corr:1": EdgeRiskRecord(edge_key="corr:1", risk=0.3)})
    ensure_insurance_config(world).enabled = True
    return world


def test_deterministic_premiums():
    world_a = _base_world()
    world_b = _base_world()

    run_insurance_week(world_a, day=7)
    run_insurance_week(world_b, day=7)

    sig_a = insurance_signature(world_a)
    sig_b = insurance_signature(world_b)
    assert sig_a == sig_b


def test_premium_monotonic_with_risk():
    world = _base_world()
    world.risk_ledger.edges["corr:2"] = EdgeRiskRecord(edge_key="corr:2", risk=0.8)

    run_insurance_week(world, day=7)

    premiums = world.premiums_by_corridor
    state_insurer = "insurer:state"
    low = premiums["corr:1|insurer:state"].premium_rate
    high = premiums["corr:2|insurer:state"].premium_rate
    assert high > low


def test_claims_reduce_reserve_and_raise_premiums():
    world = _base_world()
    cfg = ensure_insurance_config(world)
    cfg.loss_lookback_weeks = 1
    world.insured_flows["flow:1"] = InsuredFlow(
        flow_id="flow:1", route_key="r1", corridors=["corr:1"], insurer_id="insurer:state", weekly_value=100.0
    )

    run_insurance_week(world, day=7)
    pre_premium = world.premiums_by_corridor["corr:1|insurer:state"].premium_rate
    pay_claims_for_corridor(world, "corr:1", loss_value=50.0, day=7)
    post_reserve = world.insurers["insurer:state"].reserve

    run_insurance_week(world, day=14)
    post_premium = world.premiums_by_corridor["corr:1|insurer:state"].premium_rate

    assert post_reserve < 10.0  # initial reserve was 10
    assert post_premium > pre_premium


def test_shadow_protection_modifies_risk():
    world = _base_world()
    world.insured_flows["flow:shadow"] = InsuredFlow(
        flow_id="flow:shadow",
        route_key="r2",
        corridors=["corr:1"],
        insurer_id="insurer:shadow:0",
        weekly_value=50.0,
    )

    lowered = shadow_risk_modifier(world, "corr:1", 0.6)

    world.insured_flows.pop("flow:shadow")
    world.smuggling_by_faction["f:1"] = object()
    raised = shadow_risk_modifier(world, "corr:1", 0.6)

    assert lowered < 0.6
    assert raised > 0.6


def test_bounds_and_no_negative_reserves():
    world = _base_world()
    cfg = ensure_insurance_config(world)
    cfg.max_premium = 0.05
    world.corridor_stress["corr:1"] = 5.0
    run_insurance_week(world, day=7)
    premium = world.premiums_by_corridor["corr:1|insurer:state"].premium_rate
    assert premium <= cfg.max_premium

    pay_claims_for_corridor(world, "corr:1", loss_value=10_000.0, day=7)
    assert world.insurers["insurer:state"].reserve >= 0.0


def test_snapshot_roundtrip():
    world = _base_world()
    world.insured_flows["flow:1"] = InsuredFlow(
        flow_id="flow:1", route_key="r1", corridors=["corr:1"], insurer_id="insurer:guild", weekly_value=20.0
    )
    run_insurance_week(world, day=7)

    snap = snapshot_world(world, scenario_id="test")
    restored = restore_world(snap)

    assert restored.insurers.keys() == world.insurers.keys()
    assert restored.premiums_by_corridor.keys() == world.premiums_by_corridor.keys()

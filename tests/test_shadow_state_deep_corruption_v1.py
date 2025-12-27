import copy

from dosadi.runtime.sanctions import SanctionRule, compute_leak_rate, ensure_sanctions_config
from dosadi.runtime.shadow_state import (
    CorruptionIndex,
    InfluenceEdge,
    ShadowAccount,
    apply_capture_modifier,
    ensure_shadow_ledgers,
    run_shadow_state_update,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import FactionState, StockState, WardState, WorldState


def _basic_world() -> WorldState:
    world = WorldState(seed=13)
    world.shadow_cfg.enabled = True
    world.wards = {
        "ward:a": WardState(id="ward:a", name="A", ring=1, sealed_mode="OPEN"),
        "ward:b": WardState(id="ward:b", name="B", ring=1, sealed_mode="OPEN"),
    }
    world.factions = {
        "fac:alpha": FactionState(
            id="fac:alpha",
            name="Alpha",
            archetype="trader",
            home_ward="ward:a",
            assets=StockState(credits={"credits": 100.0}),
        ),
        "fac:beta": FactionState(
            id="fac:beta",
            name="Beta",
            archetype="cartel",
            home_ward="ward:b",
            assets=StockState(credits={"credits": 80.0}),
        ),
    }
    return world


def _edge_signature(world: WorldState) -> list[tuple[str, str, str, float, float]]:
    edges, _, _, _ = ensure_shadow_ledgers(world)
    rows: list[tuple[str, str, str, float, float]] = []
    for ward_id, ward_edges in sorted(edges.items()):
        for edge in sorted(ward_edges, key=lambda e: (e.from_faction, e.to_domain)):
            rows.append((ward_id, edge.from_faction, edge.to_domain, round(edge.strength, 4), round(edge.exposure, 4)))
    return rows


def test_determinism_stable_edges_and_accounts():
    world_a = _basic_world()
    world_b = copy.deepcopy(world_a)

    run_shadow_state_update(world_a, day=1)
    run_shadow_state_update(world_b, day=1)

    assert _edge_signature(world_a) == _edge_signature(world_b)
    balances_a = {acc_id: round(acc.balance, 4) for acc_id, acc in world_a.shadow_accounts.items()}
    balances_b = {acc_id: round(acc.balance, 4) for acc_id, acc in world_b.shadow_accounts.items()}
    assert balances_a == balances_b


def test_smuggling_risk_increases_shadow_budgets():
    world = _basic_world()
    world.wards["ward:a"].smuggle_risk = 0.9
    world.wards["ward:b"].smuggle_risk = 0.1

    run_shadow_state_update(world, day=2)

    bal_a = world.shadow_accounts["shadow:fac:alpha:ward:a"].balance
    bal_b = world.shadow_accounts["shadow:fac:alpha:ward:b"].balance
    assert bal_a > bal_b


def test_capture_bias_reduces_enforcement_and_increases_leakage():
    base_world = _basic_world()
    low_capture_world = copy.deepcopy(base_world)
    high_capture_world = copy.deepcopy(base_world)

    high_capture_world.corruption_by_ward["ward:a"] = CorruptionIndex(
        ward_id="ward:a",
        petty=0.3,
        capture=0.8,
        shadow_state=0.5,
        exposure_risk=0.4,
    )
    high_capture_world.influence_edges_by_ward["ward:a"] = [
        InfluenceEdge(
            ward_id="ward:a",
            from_faction="fac:alpha",
            to_domain="CUSTOMS",
            strength=0.9,
            mode="BRIBE",
            exposure=0.3,
        )
    ]

    base_detection = 0.6
    adjusted, flags = apply_capture_modifier(
        high_capture_world, "ward:a", "CUSTOMS", base_detection, actor_faction_id="fac:alpha"
    )
    assert adjusted < base_detection
    assert flags

    rule = SanctionRule(
        rule_id="r1",
        issuer_id="council",
        treaty_id=None,
        kind="EMBARGO_GOOD",
        target_kind="WARD",
        target_id="ward:a",
        goods=[],
        severity=1.0,
        start_day=0,
        end_day=10,
        enforcement_required=0.5,
    )
    ensure_sanctions_config(low_capture_world).enabled = True
    ensure_sanctions_config(high_capture_world).enabled = True

    low_leak = compute_leak_rate(low_capture_world, rule, day=1, enforcement_override=0.5, smuggling_strength=0.0)
    high_leak = compute_leak_rate(high_capture_world, rule, day=1, enforcement_override=0.5, smuggling_strength=0.0)
    assert high_leak > low_leak


def test_scandal_triggers_when_exposure_high():
    world = _basic_world()
    world.shadow_cfg.enabled = True
    world.corruption_by_ward["ward:a"] = CorruptionIndex(
        ward_id="ward:a",
        petty=0.5,
        capture=0.9,
        shadow_state=0.8,
        exposure_risk=0.9,
    )
    world.influence_edges_by_ward["ward:a"] = [
        InfluenceEdge(
            ward_id="ward:a",
            from_faction="fac:alpha",
            to_domain="CUSTOMS",
            strength=0.9,
            mode="BRIBE",
            exposure=0.9,
        )
    ]
    world.shadow_accounts["shadow:fac:alpha:ward:a"] = ShadowAccount(
        account_id="shadow:fac:alpha:ward:a", faction_id="fac:alpha", ward_id="ward:a", balance=200.0
    )

    run_shadow_state_update(world, day=3)

    assert any(evt.get("type") == "SCANDAL_EXPOSED" for evt in world.shadow_events)


def test_reforms_reduce_capture_after_scandal():
    world = _basic_world()
    world.corruption_by_ward["ward:a"] = CorruptionIndex(
        ward_id="ward:a",
        petty=0.5,
        capture=0.9,
        shadow_state=0.9,
        exposure_risk=0.9,
    )
    world.influence_edges_by_ward["ward:a"] = [
        InfluenceEdge(
            ward_id="ward:a",
            from_faction="fac:alpha",
            to_domain="POLICING",
            strength=0.9,
            mode="BRIBE",
            exposure=0.9,
        )
    ]

    before = world.corruption_by_ward["ward:a"].capture
    run_shadow_state_update(world, day=4)
    after = world.corruption_by_ward["ward:a"].capture
    assert after < before


def test_snapshot_roundtrip_preserves_shadow_state():
    world = _basic_world()
    run_shadow_state_update(world, day=5)
    snap = snapshot_world(world, scenario_id="shadow-state")
    restored = restore_world(snap)
    assert set(restored.corruption_by_ward) == set(world.corruption_by_ward)
    restored_edge_sig = _edge_signature(restored)
    assert restored_edge_sig == _edge_signature(world)

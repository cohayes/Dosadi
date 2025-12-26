from __future__ import annotations

from copy import deepcopy

import pytest
from dosadi.runtime.institutions import WardInstitutionPolicy, ensure_state
from dosadi.runtime.ledger import (
    LedgerAccount,
    LedgerConfig,
    LedgerState,
    post_tx,
    run_ledger_for_day,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.telemetry import ensure_metrics
from dosadi.runtime.timewarp import _get_ticks_per_day
from dosadi.state import WardState, WorldState
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, LogisticsLedger
from dosadi.world.survey_map import SurveyMap, SurveyNode


def _basic_world(enabled: bool = True) -> WorldState:
    world = WorldState(seed=7)
    world.ledger_cfg = LedgerConfig(enabled=enabled, max_tx_retained=500)
    world.wards = {
        "ward:alpha": WardState(id="ward:alpha", name="Alpha", ring=1, sealed_mode="open"),
        "ward:beta": WardState(id="ward:beta", name="Beta", ring=2, sealed_mode="open"),
    }
    world.survey_map = SurveyMap(
        nodes={
            "node:alpha": SurveyNode(node_id="node:alpha", kind="hub", ward_id="ward:alpha"),
            "node:beta": SurveyNode(node_id="node:beta", kind="hub", ward_id="ward:beta"),
        }
    )
    world.logistics = LogisticsLedger()
    world.metrics = ensure_metrics(world)
    world.ledger_state = LedgerState()
    return world


def _add_delivery(world: WorldState, *, dest_node: str, items: dict[str, float], day: int = 0, idx: int = 0) -> None:
    ticks_per_day = _get_ticks_per_day(world)
    delivery = DeliveryRequest(
        delivery_id=f"del:{idx}",
        project_id="proj:test",
        origin_node_id=dest_node,
        dest_node_id=dest_node,
        items=items,
        status=DeliveryStatus.DELIVERED,
        created_tick=0,
        deliver_tick=day * ticks_per_day + 1,
        route_nodes=[dest_node],
        route_edge_keys=[],
        origin_owner_id=None,
        dest_owner_id=None,
    )
    world.logistics.add(delivery)


def _seed_balances(world: WorldState, **balances: float) -> None:
    state = world.ledger_state
    for acct_id, balance in balances.items():
        state.accounts[acct_id] = LedgerAccount(acct_id=acct_id, balance=balance)


def _assign_policy(world: WorldState, ward_id: str, **kwargs) -> None:
    policy = WardInstitutionPolicy(ward_id=ward_id, **kwargs)
    world.inst_policy_by_ward[ward_id] = policy
    ensure_state(world, ward_id).corruption = kwargs.get("corruption", ensure_state(world, ward_id).corruption)


def _leak_totals(state: LedgerState) -> dict[str, float]:
    totals: dict[str, float] = {}
    for tx in state.txs:
        if tx.reason != "CORRUPTION_LEAK":
            continue
        totals[tx.from_acct.replace("acct:ward:", "")] = totals.get(tx.from_acct.replace("acct:ward:", ""), 0.0) + tx.amount
    return totals


def test_determinism_same_inputs_produce_same_signature():
    world_a = _basic_world()
    _seed_balances(
        world_a,
        **{
            "acct:ward:ward:alpha": 50.0,
            "acct:ward:ward:beta": 40.0,
            "acct:state:treasury": 0.0,
        },
    )
    _assign_policy(world_a, "ward:alpha", levy_rate=0.1, enforcement_budget_points=5.0, audit_budget_points=1.0)
    _assign_policy(world_a, "ward:beta", levy_rate=0.08, enforcement_budget_points=4.0, audit_budget_points=1.0)
    _add_delivery(world_a, dest_node="node:alpha", items={"water": 10}, day=0, idx=0)
    _add_delivery(world_a, dest_node="node:beta", items={"water": 15}, day=0, idx=1)

    world_b = deepcopy(world_a)

    run_ledger_for_day(world_a, day=0)
    run_ledger_for_day(world_b, day=0)

    assert world_a.ledger_state.signature() == world_b.ledger_state.signature()


def test_spending_caps_to_available_balance():
    world = _basic_world()
    world.ledger_cfg.max_tx_retained = 50
    _seed_balances(world, **{"acct:ward:ward:alpha": 5.0, "acct:state:treasury": 0.0})
    _assign_policy(world, "ward:alpha", levy_rate=0.0, enforcement_budget_points=10.0, audit_budget_points=0.0)

    run_ledger_for_day(world, day=0)

    payer = world.ledger_state.accounts["acct:ward:ward:alpha"]
    treasury = world.ledger_state.accounts["acct:state:treasury"]
    assert payer.balance == 0.0
    assert treasury.balance == 5.0


def test_corruption_leak_scales_with_corruption():
    world = _basic_world()
    _seed_balances(
        world,
        **{
            "acct:ward:ward:alpha": 100.0,
            "acct:ward:ward:beta": 100.0,
            "acct:state:treasury": 0.0,
        },
    )
    _assign_policy(world, "ward:alpha", levy_rate=0.1)
    _assign_policy(world, "ward:beta", levy_rate=0.1)
    ensure_state(world, "ward:alpha").corruption = 0.8
    ensure_state(world, "ward:beta").corruption = 0.1
    _add_delivery(world, dest_node="node:alpha", items={"ore": 20}, day=0, idx=0)
    _add_delivery(world, dest_node="node:beta", items={"ore": 20}, day=0, idx=1)

    run_ledger_for_day(world, day=0)

    leaks = _leak_totals(world.ledger_state)
    assert leaks.get("ward:alpha", 0.0) > leaks.get("ward:beta", 0.0)
    assert world.ledger_state.accounts.get("acct:blackmarket") is not None


def test_total_balance_conserved_across_transfers():
    world = _basic_world()
    _seed_balances(
        world,
        **{
            "acct:ward:ward:alpha": 30.0,
            "acct:ward:ward:beta": 20.0,
            "acct:state:treasury": 0.0,
        },
    )
    _assign_policy(world, "ward:alpha", levy_rate=0.05, enforcement_budget_points=2.0)
    _assign_policy(world, "ward:beta", levy_rate=0.05, enforcement_budget_points=1.0)
    _add_delivery(world, dest_node="node:alpha", items={"ore": 10}, day=0, idx=0)
    _add_delivery(world, dest_node="node:beta", items={"ore": 5}, day=0, idx=1)

    before = sum(acct.balance for acct in world.ledger_state.accounts.values())
    run_ledger_for_day(world, day=0)
    after = sum(acct.balance for acct in world.ledger_state.accounts.values())

    assert pytest.approx(before) == after


def test_transaction_history_is_bounded_and_deterministic():
    world = _basic_world()
    world.ledger_cfg.max_tx_retained = 3
    _seed_balances(world, **{"acct:ward:ward:alpha": 100.0, "acct:state:treasury": 0.0})

    for idx in range(5):
        assert post_tx(
            world,
            day=0,
            from_acct="acct:ward:ward:alpha",
            to_acct="acct:state:treasury",
            amount=5.0,
            reason=f"TEST_{idx}",
        )

    tx_ids = [tx.tx_id for tx in world.ledger_state.txs]
    assert len(tx_ids) == 3
    assert tx_ids == ["0:000002", "0:000003", "0:000004"]


def test_snapshot_roundtrip_preserves_counters():
    world = _basic_world()
    _seed_balances(world, **{"acct:ward:ward:alpha": 20.0, "acct:state:treasury": 0.0})
    post_tx(
        world,
        day=0,
        from_acct="acct:ward:ward:alpha",
        to_acct="acct:state:treasury",
        amount=5.0,
        reason="TEST_SAVE",
    )

    signature_before = world.ledger_state.signature()
    snapshot = snapshot_world(world, scenario_id="ledger-test")
    restored = restore_world(snapshot)
    assert isinstance(restored.ledger_state, LedgerState)
    assert signature_before == restored.ledger_state.signature()

    post_tx(
        restored,
        day=1,
        from_acct="acct:state:treasury",
        to_acct="acct:ward:ward:alpha",
        amount=1.0,
        reason="TEST_RESTORE",
    )

    assert restored.ledger_state.txs[-1].tx_id == "1:000000"

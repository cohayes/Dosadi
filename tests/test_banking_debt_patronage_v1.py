from __future__ import annotations

from copy import deepcopy
import json

import pytest

from dosadi.runtime.finance import FinanceConfig, Loan, Patronage, finance_seed_payload, run_finance_week
from dosadi.runtime.ledger import LedgerConfig, LedgerState, get_or_create_account
from dosadi.runtime.class_system import WardClassState
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WardState, WorldState


def _finance_signature(world: WorldState) -> str:
    payload = finance_seed_payload(world) or {}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _basic_world() -> WorldState:
    world = WorldState(seed=11)
    world.finance_cfg = FinanceConfig(enabled=True, update_cadence_days=1, max_loans_total=10, max_loans_per_ward=3)
    world.ledger_cfg = LedgerConfig(enabled=True, max_tx_retained=500)
    world.ledger_state = LedgerState()
    world.wards = {
        "ward:alpha": WardState(id="ward:alpha", name="Alpha", ring=1, sealed_mode="open", need_index=0.6),
        "ward:beta": WardState(id="ward:beta", name="Beta", ring=1, sealed_mode="open", need_index=0.4),
    }
    world.class_by_ward = {
        "ward:alpha": WardClassState(ward_id="ward:alpha", hardship_index=0.5, inequality_index=0.3),
        "ward:beta": WardClassState(ward_id="ward:beta", hardship_index=0.2, inequality_index=0.2),
    }
    get_or_create_account(world, "acct:state:treasury").balance = 500.0
    get_or_create_account(world, "acct:ward:ward:alpha").balance = 120.0
    get_or_create_account(world, "acct:ward:ward:beta").balance = 80.0
    return world


def test_determinism_same_inputs_produce_same_loans_and_defaults():
    world_a = _basic_world()
    world_b = deepcopy(world_a)

    run_finance_week(world_a, day=7)
    run_finance_week(world_b, day=7)

    assert _finance_signature(world_a) == _finance_signature(world_b)


def test_interest_accrual_and_payment_reduce_outstanding():
    world = _basic_world()
    loan = Loan(
        loan_id="loan:test",
        instrument="LOAN_PUBLIC_WORKS",
        issuer_id="acct:state:treasury",
        borrower_id="acct:ward:ward:alpha",
        ward_id="ward:alpha",
        principal=100.0,
        rate_weekly=0.05,
        term_weeks=4,
        outstanding=100.0,
        payment_weekly=30.0,
    )
    world.loans[loan.loan_id] = loan

    run_finance_week(world, day=0)

    assert loan.outstanding < 100.0 * 1.05
    assert loan.status == "ACTIVE"


def test_default_then_seizure_when_payments_fail_and_hardship_high():
    world = _basic_world()
    world.class_by_ward["ward:alpha"].hardship_index = 0.9
    world.class_by_ward["ward:alpha"].inequality_index = 0.8
    get_or_create_account(world, "acct:ward:ward:alpha").balance = 0.0
    loan = Loan(
        loan_id="loan:default",
        instrument="LOAN_PUBLIC_WORKS",
        issuer_id="acct:state:treasury",
        borrower_id="acct:ward:ward:alpha",
        ward_id="ward:alpha",
        principal=50.0,
        rate_weekly=0.02,
        term_weeks=6,
        outstanding=50.0,
        payment_weekly=10.0,
    )
    world.loans[loan.loan_id] = loan

    run_finance_week(world, day=0)
    assert loan.status == "RESTRUCTURED"

    run_finance_week(world, day=1)
    assert loan.status == "SEIZED"


def test_seizure_increases_inequality_and_hardship():
    world = _basic_world()
    class_state = world.class_by_ward["ward:alpha"]
    start_inequality = class_state.inequality_index
    start_hardship = class_state.hardship_index
    get_or_create_account(world, "acct:ward:ward:alpha").balance = 0.0
    loan = Loan(
        loan_id="loan:seize",
        instrument="LOAN_PUBLIC_WORKS",
        issuer_id="acct:state:treasury",
        borrower_id="acct:ward:ward:alpha",
        ward_id="ward:alpha",
        principal=40.0,
        rate_weekly=0.02,
        term_weeks=4,
        outstanding=40.0,
        payment_weekly=15.0,
    )
    world.loans[loan.loan_id] = loan

    run_finance_week(world, day=0)
    run_finance_week(world, day=1)

    assert class_state.inequality_index > start_inequality
    assert class_state.hardship_index > start_hardship


def test_patronage_reduces_militancy_and_adds_corruption_pressure():
    world = _basic_world()
    world.patronage.append(
        Patronage(
            patron_id="acct:state:treasury",
            client_id="acct:ward:ward:alpha",
            ward_id="ward:alpha",
            weekly_transfer=5.0,
            loyalty_effect=0.6,
            corruption_effect=0.4,
        )
    )
    get_or_create_account(world, "acct:ward:ward:alpha").balance = 0.0

    run_finance_week(world, day=0)

    orgs = world.labor_orgs_by_ward["ward:alpha"]
    assert all(org.militancy < 0.05 for org in orgs)
    class_state = world.class_by_ward["ward:alpha"]
    assert class_state.inequality_index > 0.3
    assert class_state.hardship_index > 0.5


def test_snapshot_roundtrip_preserves_finance_state():
    world = _basic_world()
    loan = Loan(
        loan_id="loan:snap",
        instrument="LOAN_PUBLIC_WORKS",
        issuer_id="acct:state:treasury",
        borrower_id="acct:ward:ward:beta",
        ward_id="ward:beta",
        principal=30.0,
        rate_weekly=0.01,
        term_weeks=5,
        outstanding=30.0,
        payment_weekly=6.0,
    )
    world.loans[loan.loan_id] = loan
    world.patronage.append(
        Patronage(
            patron_id="acct:state:treasury",
            client_id="acct:ward:ward:beta",
            ward_id="ward:beta",
            weekly_transfer=2.0,
            loyalty_effect=0.2,
            corruption_effect=0.1,
        )
    )

    run_finance_week(world, day=0)
    signature_before = _finance_signature(world)

    snapshot = snapshot_world(world, scenario_id="finance-test")
    restored = restore_world(snapshot)

    assert isinstance(restored.loans.get("loan:snap"), Loan)
    assert _finance_signature(restored) == signature_before

import json

import pytest

from dosadi.runtime.ledger import ensure_ledger_config, ensure_ledger_state, get_or_create_account
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.treaties import (
    TreatyConfig,
    TreatyObligation,
    TreatyTerms,
    activate_treaty,
    propose_treaties_for_day,
    run_treaties_for_day,
    save_treaties_seed,
    should_accept_treaty,
)
from dosadi.state import WardState, WorldState


def _basic_world(seed: int = 1) -> WorldState:
    world = WorldState(seed=seed)
    world.treaty_cfg = TreatyConfig(enabled=True)
    world.wards = {
        "ward:a": WardState(id="ward:a", name="A", ring=1, sealed_mode="open", need_index=0.9, risk_index=0.6),
        "ward:b": WardState(id="ward:b", name="B", ring=1, sealed_mode="open", need_index=0.2, risk_index=0.3),
    }
    ensure_ledger_config(world).enabled = True
    ensure_ledger_state(world)
    return world


def test_treaty_proposals_are_deterministic():
    world = _basic_world(seed=42)
    terms_first = propose_treaties_for_day(world, day=0)
    terms_second = propose_treaties_for_day(world, day=0)

    assert len(terms_first) == len(terms_second) == 1
    assert terms_first[0].treaty_type == terms_second[0].treaty_type
    assert terms_first[0].party_a == terms_second[0].party_a
    assert should_accept_treaty(world, terms_first[0])

    state = activate_treaty(world, terms_first[0], day=0)
    assert state.treaty_id in world.treaties
    assert state.terms.treaty_type in {"RESOURCE_SWAP", "ESCORT_PACT", "SAFE_PASSAGE", "MAINTENANCE_COMPACT"}


def test_execution_scheduling_records_history_and_orders():
    world = _basic_world(seed=7)
    get_or_create_account(world, "acct:ward:a").balance = 10.0
    get_or_create_account(world, "acct:ward:b").balance = 10.0

    terms = TreatyTerms(
        treaty_type="RESOURCE_SWAP",
        party_a="ward:a",
        party_b="ward:b",
        obligations_a=[TreatyObligation(kind="deliver", material="water", amount=2, cadence_days=3)],
        obligations_b=[TreatyObligation(kind="deliver", material="food", amount=3, cadence_days=3)],
        consideration={"payment_from_a_to_b": 0.5, "payment_from_b_to_a": 0.75},
        duration_days=10,
    )
    state = activate_treaty(world, terms, day=0)

    run_treaties_for_day(world, day=0)
    run_treaties_for_day(world, day=3)

    deliveries = world.logistics.deliveries
    assert len(deliveries) >= 4
    assert any("water" in req.items for req in deliveries.values())
    assert any("food" in req.items for req in deliveries.values())
    assert len(state.history) >= 4
    assert all(entry.get("status") == "executed" for entry in state.history)


def test_breach_detection_marks_breached_when_payments_fail():
    world = _basic_world(seed=11)
    # zero balances so transfers fail
    terms = TreatyTerms(
        treaty_type="SAFE_PASSAGE",
        party_a="ward:a",
        party_b="ward:b",
        obligations_a=[TreatyObligation(kind="allow_passage", corridor_ids=["edge:1"])],
        obligations_b=[TreatyObligation(kind="allow_passage", corridor_ids=["edge:1"])],
        consideration={"payment_from_a_to_b": 5.0},
        duration_days=5,
    )
    state = activate_treaty(world, terms, day=0)

    for day in range(3):
        run_treaties_for_day(world, day=day)

    assert state.status == "breached"
    assert state.breach_score > world.treaty_cfg.breach_threshold


def test_penalties_applied_on_breach():
    world = _basic_world(seed=12)
    terms = TreatyTerms(
        treaty_type="ESCORT_PACT",
        party_a="ward:a",
        party_b="ward:b",
        obligations_a=[TreatyObligation(kind="escort", corridor_ids=["edge:alpha"], cadence_days=1)],
        obligations_b=[TreatyObligation(kind="escort", corridor_ids=["edge:alpha"], cadence_days=1)],
        consideration={"payment_from_a_to_b": 3.0},
        duration_days=4,
    )
    state = activate_treaty(world, terms, day=0)

    for day in range(3):
        run_treaties_for_day(world, day=day)

    assert state.status == "breached"
    assert world.treaty_penalties.get("ward:a") == pytest.approx(1.25)
    assert world.treaty_penalties.get("ward:b") == pytest.approx(1.25)


def test_treaties_persist_through_snapshot_and_seed(tmp_path):
    world = _basic_world(seed=21)
    terms = TreatyTerms(
        treaty_type="MAINTENANCE_COMPACT",
        party_a="ward:a",
        party_b="ward:b",
        obligations_a=[TreatyObligation(kind="maintain", corridor_ids=["edge:beta"], cadence_days=1)],
        obligations_b=[TreatyObligation(kind="maintain", corridor_ids=["edge:beta"], cadence_days=1)],
        consideration={},
        duration_days=5,
    )
    state = activate_treaty(world, terms, day=0)
    run_treaties_for_day(world, day=0)

    snapshot = snapshot_world(world, scenario_id="scenario:test")
    restored = restore_world(snapshot)

    restored_state = next(iter(restored.treaties.values()))
    assert restored_state.treaty_id == state.treaty_id
    assert restored_state.terms.treaty_type == "MAINTENANCE_COMPACT"

    seed_path = tmp_path / "vault"
    output_path = seed_path / "seeds" / "seed-1" / "treaties.json"
    save_treaties_seed(restored, output_path)
    with open(output_path, "r", encoding="utf-8") as fp:
        payload = json.load(fp)

    assert payload["schema"] == "treaties_v1"
    treaty_ids = [entry["treaty_id"] for entry in payload["treaties"]]
    assert treaty_ids == sorted(treaty_ids)


import pytest

from dosadi.runtime.mandates import (
    Mandate,
    MandateStakes,
    SuccessMetric,
    WaterShareContract,
    add_share_contract,
    issue_mandate,
    record_mandate_progress,
    run_mandate_system_for_day,
)
from dosadi.state import FactionState, WardState, WorldState


def test_mandate_success_adjusts_shares_and_performance():
    world = WorldState()
    world.mandate_cfg.mandates.audit_latency_days = 0

    faction = FactionState(id="faction:vassal", name="Vassal", archetype="WARD", home_ward="ward:1")
    faction.performance_index = 0.5
    world.factions[faction.id] = faction

    contract = WaterShareContract(
        contract_id="share:king->vassal:Q1",
        grantor="faction:king",
        grantee=faction.id,
        W_base_lpd=1000.0,
        current_ratio=0.8,
        linked_mandates=("mand:001",),
    )
    add_share_contract(world, contract)

    stakes = MandateStakes(water_share_delta_if_pass=0.1, water_share_delta_if_fail=-0.2)
    mandate = Mandate(
        mandate_id="mand:001",
        issuer="faction:king",
        recipient=faction.id,
        domain="CIVIC",
        title="Test Quota",
        start_day=0,
        end_day=0,
        success_metrics=(SuccessMetric(key="uptime", target=1.0, scope="ward:1"),),
        stakes=stakes,
        gap=0.2,
    )
    issue_mandate(world, mandate)
    record_mandate_progress(world=world, mandate_id=mandate.mandate_id, metric_key="uptime", value=1.0, day=0)

    run_mandate_system_for_day(world, day=0)

    assert world.mandate_state.mandates[mandate.mandate_id].status == "CLOSED"
    assert pytest.approx(world.factions[faction.id].performance_index, rel=1e-6) == 0.55
    assert pytest.approx(world.mandate_state.share_contracts[contract.contract_id].current_ratio, rel=1e-6) == 0.9


def test_mandate_failure_triggers_replacement_case():
    world = WorldState()
    world.mandate_cfg.mandates.audit_latency_days = 0
    world.mandate_cfg.replacement.fail_threshold = 1

    ward = WardState(id="ward:1", name="Ward 1", ring=1, sealed_mode="OPEN")
    ward.risk_index = 0.7
    world.wards[ward.id] = ward

    faction = FactionState(id="faction:vassal", name="Vassal", archetype="WARD", home_ward=ward.id)
    world.factions[faction.id] = faction

    stakes = MandateStakes(water_share_delta_if_pass=0.0, water_share_delta_if_fail=-0.1)
    mandate = Mandate(
        mandate_id="mand:fail",
        issuer="faction:king",
        recipient=faction.id,
        domain="CIVIC",
        title="Failing Quota",
        start_day=0,
        end_day=0,
        success_metrics=(SuccessMetric(key="uptime", target=1.0, scope="ward:1"),),
        stakes=stakes,
        gap=0.0,
    )
    issue_mandate(world, mandate)
    record_mandate_progress(world=world, mandate_id=mandate.mandate_id, metric_key="uptime", value=0.0, day=0)

    run_mandate_system_for_day(world, day=0)

    assert world.mandate_state.mandates[mandate.mandate_id].status == "CLOSED"
    assert len(world.mandate_state.replacement_cases) == 1
    case = next(iter(world.mandate_state.replacement_cases.values()))
    assert case.target == faction.id
    assert case.chosen == "FULL_REPLACE"

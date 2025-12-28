from __future__ import annotations

from dosadi.playbook.scenario_runner import run_scenario
from dosadi.runtime.success_contracts import (
    ContractConfig,
    Milestone,
    MilestoneStatus,
    SuccessContract,
    eval_first_delivery_completed,
    evaluate_contract,
)
from dosadi.state import WorldState


def _simple_contract(evaluator) -> SuccessContract:
    milestone = Milestone(
        milestone_id="m1",
        name="test",
        description="",
    )
    return SuccessContract(
        contract_id="c1",
        scenario_id="s1",
        milestones=[milestone],
        failure_conditions=[],
        stop_policy={"stop_on_success": True, "stop_on_failure": True},
        notes={"evaluators": {"m1": evaluator}, "required_ids": ["m1"]},
    )


def test_contract_determinism() -> None:
    report_a = run_scenario("founding_wakeup_mvp", overrides={"max_ticks": 50, "seed": 9})
    report_b = run_scenario("founding_wakeup_mvp", overrides={"max_ticks": 50, "seed": 9})

    assert report_a.contract_result is not None
    assert report_b.contract_result is not None
    assert report_a.contract_result.ended_reason == report_b.contract_result.ended_reason
    assert report_a.contract_result.tick_end == report_b.contract_result.tick_end


def test_stops_early_on_success() -> None:
    world = WorldState()
    contract = _simple_contract(lambda _: (True, {"evidence": "instant"}))
    world.active_contract = contract
    world.contract_cfg = ContractConfig(evaluation_cadence_ticks=1, timeout_ticks=10)

    result = evaluate_contract(world, 0)
    assert result is not None
    assert result.ended_reason == "SUCCESS"
    assert world.active_contract.milestones[0].status == MilestoneStatus.ACHIEVED


def test_timeout_when_never_reaching_success() -> None:
    world = WorldState()
    contract = _simple_contract(lambda _: (False, {}))
    world.active_contract = contract
    world.contract_cfg = ContractConfig(evaluation_cadence_ticks=1, timeout_ticks=3)

    result = None
    for tick in range(5):
        result = evaluate_contract(world, tick) or result
    assert result is not None
    assert result.ended_reason == "TIMEOUT"


def test_deadlock_detection_triggers() -> None:
    world = WorldState()
    contract = _simple_contract(lambda _: (False, {}))
    contract.failure_conditions.append({"type": "deadlock", "window_ticks": 2, "reason": "DEADLOCK"})
    world.active_contract = contract
    world.contract_cfg = ContractConfig(evaluation_cadence_ticks=1, timeout_ticks=10)

    result = None
    for tick in range(5):
        result = evaluate_contract(world, tick, progress_signature_fn=lambda _w, _c: (1,)) or result
        if result is not None:
            break
    assert result is not None
    assert result.ended_reason == "FAILURE"
    assert result.ended_detail == "DEADLOCK"


def test_evidence_boundedness() -> None:
    world = WorldState()

    def _noisy(_world):
        return False, {"note": "missing"}

    contract = _simple_contract(_noisy)
    world.active_contract = contract
    world.contract_cfg = ContractConfig(evaluation_cadence_ticks=1, timeout_ticks=5, max_evidence_items=2)

    for tick in range(5):
        evaluate_contract(world, tick)
    assert len(world.active_contract.milestones[0].evidence) <= 2


def test_missing_metric_diagnostic() -> None:
    world = WorldState()
    achieved, evidence = eval_first_delivery_completed(world)
    assert achieved is False
    assert "missing_metric" in evidence

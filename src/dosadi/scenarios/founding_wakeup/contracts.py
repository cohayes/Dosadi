from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from dosadi.runtime.success_contracts import (
    ContractConfig,
    Milestone,
    SuccessContract,
    eval_council_formed,
    eval_first_corridor_established,
    eval_first_depot_built,
    eval_first_delivery_completed,
    eval_first_protocol_authored,
    eval_first_scout_mission_completed,
)


@dataclass(frozen=True)
class FoundingWakeupContract:
    contract: SuccessContract
    config: ContractConfig


def build_founding_wakeup_contract(*, scenario_id: str, max_ticks: int | None = None) -> FoundingWakeupContract:
    milestones = [
        Milestone(
            milestone_id="council_formed",
            name="Proto Council Formed",
            description="At least one council formed with representatives",
            priority=0,
        ),
        Milestone(
            milestone_id="first_protocol_authored",
            name="First Protocol Authored",
            description="A movement/safety protocol has been authored and activated",
            priority=1,
        ),
        Milestone(
            milestone_id="first_scout_mission_completed",
            name="Scout Mission Completed",
            description="A scout mission reached completion",
            priority=2,
        ),
        Milestone(
            milestone_id="first_depot_built",
            name="Depot Built",
            description="At least one depot facility is present",
            priority=3,
        ),
        Milestone(
            milestone_id="first_corridor_established",
            name="Corridor Established",
            description="A corridor or route exists to connect sites",
            priority=4,
        ),
        Milestone(
            milestone_id="first_delivery_completed",
            name="Delivery Completed",
            description="A stockpile delivery completed",
            priority=5,
        ),
        Milestone(
            milestone_id="first_expansion_project_started",
            name="Expansion Project Started",
            description="Optional: any expansion project has begun",
            priority=6,
        ),
        Milestone(
            milestone_id="first_settlement_zone_marked",
            name="Settlement Zone Marked",
            description="Optional: a settlement zone or ward has been marked",
            priority=7,
        ),
    ]

    failure_conditions = [
        {"type": "collapsed_corridors", "threshold": 2, "reason": "too many corridor collapses"},
        {
            "type": "metric_below",
            "metric": "population.alive_ratio",
            "threshold": 0.7,
            "reason": "population below 70%",
        },
        {
            "type": "metric_at_least",
            "metric": "water.shortage.severe_days",
            "threshold": 5,
            "reason": "sustained water shortage",
        },
        {
            "type": "deadlock",
            "window_ticks": 5_000,
            "reason": "DEADLOCK",
        },
    ]

    evaluators = {
        "council_formed": eval_council_formed,
        "first_protocol_authored": eval_first_protocol_authored,
        "first_scout_mission_completed": eval_first_scout_mission_completed,
        "first_depot_built": eval_first_depot_built,
        "first_corridor_established": eval_first_corridor_established,
        "first_delivery_completed": eval_first_delivery_completed,
    }

    contract = SuccessContract(
        contract_id="founding_wakeup_contract_v1",
        scenario_id=scenario_id,
        milestones=milestones,
        failure_conditions=failure_conditions,
        stop_policy={"stop_on_success": True, "stop_on_failure": True},
        notes={
            "evaluators": evaluators,
            "required_ids": [m.milestone_id for m in milestones[:6]],
        },
    )

    config = ContractConfig(timeout_ticks=max_ticks)
    return FoundingWakeupContract(contract=contract, config=config)


__all__: Tuple[str, ...] = ("FoundingWakeupContract", "build_founding_wakeup_contract")

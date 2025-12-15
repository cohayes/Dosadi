"""Deterministic facility daily update loop."""

from __future__ import annotations

from typing import MutableMapping

from dosadi.world.facilities import Facility, FacilityLedger, ensure_facility_ledger, get_facility_behavior
from dosadi.world import stocks
from dosadi.world.workforce import AssignmentKind, ensure_workforce


def _effective_days(facility: Facility, *, day: int, days: int) -> int:
    target_end = day + max(1, days) - 1
    start = max(day, facility.last_update_day + 1)
    if start > target_end:
        return 0
    return target_end - start + 1


def _apply_outputs(world, facility: Facility, behavior, days: int, *, labor_ratio: float = 1.0) -> None:
    total_outputs = {
        item: qty * days * labor_ratio
        for item, qty in behavior.outputs_per_day.items()
    }
    for item, qty in total_outputs.items():
        stocks.add(world, item, qty)

    metrics: MutableMapping[str, object] = getattr(world, "metrics", {})
    world.metrics = metrics
    output_bucket: MutableMapping[str, float] = metrics.setdefault("facility_outputs", {})  # type: ignore[arg-type]
    output_bucket[facility.kind] = output_bucket.get(facility.kind, 0.0) + sum(total_outputs.values())


def _consume_inputs(world, behavior, days: int) -> bool:
    total_inputs = {item: qty * days for item, qty in behavior.inputs_per_day.items()}
    if not total_inputs:
        return True

    if not all(stocks.has(world, item, qty) for item, qty in total_inputs.items()):
        return False

    for item, qty in total_inputs.items():
        stocks.consume(world, item, qty)
    return True


def _staffing_ratio(world, facility: Facility, behavior) -> float:
    if not getattr(behavior, "requires_labor", False):
        return 1.0

    target = max(1, getattr(behavior, "labor_agents", 1))
    ledger = ensure_workforce(world)
    assigned = sum(
        1
        for assignment in ledger.assignments.values()
        if assignment.kind is AssignmentKind.FACILITY_STAFF
        and assignment.target_id == facility.facility_id
    )
    if assigned <= 0:
        return 0.0
    return min(1.0, assigned / target)


def update_facilities_for_day(world, *, day: int, days: int = 1) -> None:
    ledger: FacilityLedger = ensure_facility_ledger(world)

    for facility in ledger.values():
        if getattr(facility, "status", "ACTIVE") != "ACTIVE":
            continue

        active_days = _effective_days(facility, day=day, days=days)
        if active_days <= 0:
            continue

        try:
            behavior = get_facility_behavior(facility.kind)
        except KeyError:
            continue

        produced = _consume_inputs(world, behavior, active_days)
        if produced:
            labor_ratio = _staffing_ratio(world, facility, behavior)
            if labor_ratio > 0:
                _apply_outputs(world, facility, behavior, active_days, labor_ratio=labor_ratio)

        facility.last_update_day = day + active_days - 1


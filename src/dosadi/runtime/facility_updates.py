"""Deterministic facility daily update loop."""

from __future__ import annotations

from typing import MutableMapping

from dosadi.world.facilities import Facility, FacilityLedger, ensure_facility_ledger, get_facility_behavior
from dosadi.world import stocks


def _effective_days(facility: Facility, *, day: int, days: int) -> int:
    target_end = day + max(1, days) - 1
    start = max(day, facility.last_update_day + 1)
    if start > target_end:
        return 0
    return target_end - start + 1


def _apply_outputs(world, facility: Facility, behavior, days: int) -> None:
    total_outputs = {item: qty * days for item, qty in behavior.outputs_per_day.items()}
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
            _apply_outputs(world, facility, behavior, active_days)

        facility.last_update_day = day + active_days - 1


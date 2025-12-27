from __future__ import annotations

import random

from dosadi.runtime.health import WardHealthState
from dosadi.runtime.labor import LaborOrgState
from dosadi.runtime.workforce import (
    FacilityStaffing,
    WorkforceConfig,
    allocate_staffing_for_ward,
    apply_staffing_multiplier,
    compute_workforce_pools,
    staffing_ratio,
)
from dosadi.state import WorldState
from dosadi.world.facilities import Facility, FacilityKind, ensure_facility_ledger
from dosadi.runtime.education import WardEducationState
from dosadi.runtime.snapshot import restore_world, snapshot_world


def _world_with_facilities():
    world = WorldState(seed=7, rng=random.Random(7))
    world.workforce_cfg = WorkforceConfig(enabled=True)
    world.day = 3
    class WardStub:
        def __init__(self):
            self.id = "ward:alpha"
            self.name = "Alpha"
            self.ring = 0
            self.sealed_mode = "OPEN"
            self.population = 1200
            self.need_index = 0.0
            self.risk_index = 0.0
            self.facilities = {}

    world.register_ward(WardStub())

    edu = WardEducationState(ward_id="ward:alpha", domains={"ENGINEERING": 0.6, "LOGISTICS": 0.2})
    world.education_by_ward["ward:alpha"] = edu

    facilities = ensure_facility_ledger(world)
    facilities.add(
        Facility(
            facility_id="fac:water",
            kind=FacilityKind.WATER_WORKS,
            ward_id="ward:alpha",
            staff_req={"ENGINEER": 4.0, "MAINTAINER": 6.0, "GUARD": 2.0},
            role_tags={"water", "life_support"},
        )
    )
    facilities.add(
        Facility(
            facility_id="fac:refinery",
            kind=FacilityKind.REFINERY,
            ward_id="ward:alpha",
            staff_req={"ENGINEER": 4.0, "REFINER": 8.0, "GUARD": 2.0},
            role_tags={"industry"},
        )
    )
    facilities.add(
        Facility(
            facility_id="fac:clinic",
            kind=FacilityKind.OUTPOST,
            ward_id="ward:alpha",
            staff_req={"MEDIC": 6.0, "ADMIN": 2.0},
            role_tags={"health"},
        )
    )
    return world


def test_workforce_allocation_is_deterministic():
    world = _world_with_facilities()
    compute_workforce_pools(world, day=3)
    allocate_staffing_for_ward(world, "ward:alpha", day=3)
    ratios_first = {
        fid: staffing_ratio(world, fid)
        for fid in sorted(world.staffing_by_facility.keys())
    }

    restored = restore_world(snapshot_world(world, scenario_id="demo"))
    compute_workforce_pools(restored, day=3)
    allocate_staffing_for_ward(restored, "ward:alpha", day=3)
    ratios_second = {
        fid: staffing_ratio(restored, fid)
        for fid in sorted(restored.staffing_by_facility.keys())
    }

    assert ratios_first == ratios_second


def test_life_support_priority_wins_in_shortage():
    world = _world_with_facilities()
    world.workforce_cfg.max_facilities_scored_per_ward = 3
    compute_workforce_pools(world, day=3)
    world.workforce_by_ward["ward:alpha"].pools = {"ENGINEER": 6.0, "MAINTAINER": 4.0, "GUARD": 3.0}
    allocate_staffing_for_ward(world, "ward:alpha", day=3)
    water_ratio = staffing_ratio(world, "fac:water")
    refinery_ratio = staffing_ratio(world, "fac:refinery")
    assert water_ratio >= refinery_ratio


def test_partial_staffing_scales_output():
    world = _world_with_facilities()
    compute_workforce_pools(world, day=3)
    allocate_staffing_for_ward(world, "ward:alpha", day=3)
    base_output = 10.0
    scaled_output = apply_staffing_multiplier(base_output, world, "fac:water")
    assert 0.0 < scaled_output <= base_output


def test_strike_reduces_available_pools():
    world = _world_with_facilities()
    world.labor_orgs_by_ward["ward:alpha"] = [
        LaborOrgState(org_id="u1", org_type="UNION", sector="industry", ward_id="ward:alpha", status="STRIKE"),
    ]
    compute_workforce_pools(world, day=3)
    available = world.workforce_by_ward["ward:alpha"].notes.get("available_fte")
    assert available < 1200 * 0.35


def test_health_penalty_applies():
    world = _world_with_facilities()
    world.health_by_ward["ward:alpha"] = WardHealthState(ward_id="ward:alpha")
    world.health_by_ward["ward:alpha"].notes["labor_mult"] = 0.5
    compute_workforce_pools(world, day=3)
    pools = world.workforce_by_ward["ward:alpha"].pools
    total = sum(pools.values())
    assert total < 1200 * 0.35


def test_snapshot_roundtrip_keeps_pools_and_allocations():
    world = _world_with_facilities()
    compute_workforce_pools(world, day=3)
    allocate_staffing_for_ward(world, "ward:alpha", day=3)
    staffing_snapshot = {
        fid: FacilityStaffing(
            facility_id=fid,
            ward_id=staffing.ward_id,
            req=dict(staffing.req),
            alloc=dict(staffing.alloc),
            ratio=staffing.ratio,
        )
        for fid, staffing in world.staffing_by_facility.items()
    }

    restored = restore_world(snapshot_world(world, scenario_id="demo"))
    compute_workforce_pools(restored, day=3)
    allocate_staffing_for_ward(restored, "ward:alpha", day=3)

    assert set(restored.staffing_by_facility.keys()) == set(staffing_snapshot.keys())
    for fid, staffing in restored.staffing_by_facility.items():
        baseline = staffing_snapshot[fid]
        assert staffing.ratio == baseline.ratio
        assert staffing.alloc == baseline.alloc


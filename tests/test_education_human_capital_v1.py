from __future__ import annotations

from dosadi.runtime.education import (
    EducationConfig,
    WardEducationState,
    logistics_delay_multiplier,
    run_education_update,
    ward_competence,
)
from dosadi.runtime.tech_ladder import TechConfig, TechState, run_tech_for_day
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.institutions import WardInstitutionPolicy
from dosadi.runtime.health import WardHealthState
from dosadi.state import WardState, WorldState
from dosadi.world.materials import Material


def _baseline_world() -> WorldState:
    world = WorldState(seed=7)
    world.education_cfg = EducationConfig(enabled=True, update_cadence_days=1)
    world.tech_cfg = TechConfig(enabled=True)
    world.tech_state = TechState()
    return world


def _add_ward(world: WorldState, ward_id: str, facilities: dict[str, int] | None = None) -> None:
    world.wards[ward_id] = WardState(id=ward_id, name=ward_id, ring=1, sealed_mode="OP")
    world.wards[ward_id].facilities = facilities or {}
    world.inst_policy_by_ward[ward_id] = WardInstitutionPolicy(ward_id=ward_id, education_priority={})
    world.education_by_ward[ward_id] = WardEducationState(ward_id=ward_id)


def test_determinism_same_seed_and_inputs() -> None:
    world = _baseline_world()
    _add_ward(world, "ward:a")
    _add_ward(world, "ward:b", {"SCHOOLHOUSE_L1": 1})

    snap = snapshot_world(world, scenario_id="det")
    twin = restore_world(snap)

    run_education_update(world, day=0)
    run_education_update(twin, day=0)

    assert world.education_by_ward.keys() == twin.education_by_ward.keys()
    for ward_id in sorted(world.education_by_ward):
        assert ward_competence(world, ward_id) == ward_competence(twin, ward_id)


def test_facilities_improve_civics_and_trade_growth() -> None:
    world = _baseline_world()
    _add_ward(world, "ward:baseline")
    _add_ward(world, "ward:school", {"SCHOOLHOUSE_L1": 1})

    run_education_update(world, day=0)

    civics_baseline = ward_competence(world, "ward:baseline")["CIVICS"]
    civics_school = ward_competence(world, "ward:school")["CIVICS"]
    trade_baseline = ward_competence(world, "ward:baseline")["TRADE"]
    trade_school = ward_competence(world, "ward:school")["TRADE"]

    assert civics_school > civics_baseline
    assert trade_school > trade_baseline


def test_outbreak_penalty_slows_medicine_growth() -> None:
    world = _baseline_world()
    _add_ward(world, "ward:healthy")
    _add_ward(world, "ward:sick")
    world.health_by_ward["ward:sick"] = WardHealthState(ward_id="ward:sick", outbreaks={"flu": 0.8})

    run_education_update(world, day=0)

    medicine_healthy = ward_competence(world, "ward:healthy")["MEDICINE"]
    medicine_sick = ward_competence(world, "ward:sick")["MEDICINE"]

    assert medicine_sick < medicine_healthy


def test_logistics_competence_reduces_delay_multiplier() -> None:
    world = _baseline_world()
    _add_ward(world, "ward:logi")
    world.education_by_ward["ward:logi"].domains["LOGISTICS"] = 0.5

    baseline = logistics_delay_multiplier(world, "ward:logi")
    world.education_by_ward["ward:logi"].domains["LOGISTICS"] = 0.0
    reset = logistics_delay_multiplier(world, "ward:logi")

    assert baseline < reset


def test_tech_gating_blocks_until_competent() -> None:
    world = _baseline_world()
    _add_ward(world, "ward:core")
    world.tech_state.completed.add("tech:workshop:parts:t2")
    research_inv = world.inventories.inv("owner:state:research")
    research_inv.add(Material.FASTENERS, 4)
    research_inv.add(Material.SEALANT, 2)
    research_inv.add(Material.FILTER_MEDIA, 2)

    run_tech_for_day(world, day=0)
    assert not world.tech_state.active

    world.education_by_ward["ward:core"].domains["LOGISTICS"] = 0.5
    run_tech_for_day(world, day=1)
    assert world.tech_state.active


def test_snapshot_roundtrip_preserves_progression() -> None:
    world = _baseline_world()
    _add_ward(world, "ward:persist")
    run_education_update(world, day=0)

    snap = snapshot_world(world, scenario_id="persist")
    restored = restore_world(snap)
    run_education_update(restored, day=1)

    assert ward_competence(world, "ward:persist")["CIVICS"] <= ward_competence(restored, "ward:persist")["CIVICS"]

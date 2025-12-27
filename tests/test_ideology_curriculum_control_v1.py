from dosadi.runtime.education import (
    EducationConfig,
    WardEducationState,
    run_education_update,
    ward_competence,
)
from dosadi.runtime.ideology import (
    IdeologyConfig,
    ensure_ward_ideology,
    run_ideology_update,
)
from dosadi.runtime.institutions import WardInstitutionPolicy
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.tech_ladder import TechConfig, TechState, run_tech_for_day
from dosadi.state import WardState, WorldState
from dosadi.world.materials import Material


def _baseline_world() -> WorldState:
    world = WorldState(seed=17)
    world.ideology_cfg = IdeologyConfig(enabled=True, update_cadence_days=1)
    world.education_cfg = EducationConfig(enabled=True, update_cadence_days=1)
    world.tech_cfg = TechConfig(enabled=True)
    world.tech_state = TechState()
    return world


def _add_ward(
    world: WorldState,
    ward_id: str,
    *,
    propaganda: float = 0.0,
    censorship: float = 0.0,
    education_priority: dict[str, float] | None = None,
) -> None:
    world.wards[ward_id] = WardState(id=ward_id, name=ward_id, ring=1, sealed_mode="OP")
    world.inst_policy_by_ward[ward_id] = WardInstitutionPolicy(
        ward_id=ward_id,
        propaganda_budget_points=propaganda,
        censorship_bias=censorship,
        education_priority=education_priority or {},
    )
    world.education_by_ward[ward_id] = WardEducationState(ward_id=ward_id)


def test_determinism_same_inputs() -> None:
    world = _baseline_world()
    _add_ward(world, "ward:a", education_priority={"ENGINEERING": 1.0, "CIVICS": 0.5})
    _add_ward(world, "ward:b", propaganda=3.0, education_priority={"CIVICS": 1.0})

    snap = snapshot_world(world, scenario_id="ideo")
    twin = restore_world(snap)

    run_ideology_update(world, day=0)
    run_ideology_update(twin, day=0)

    for ward_id in sorted(world.ideology_by_ward):
        primary = ensure_ward_ideology(world, ward_id)
        mirrored = ensure_ward_ideology(twin, ward_id)
        assert primary.curriculum_axes == mirrored.curriculum_axes
        assert primary.censorship_level == mirrored.censorship_level


def test_propaganda_shifts_capture_share() -> None:
    world = _baseline_world()
    world.factions["faction:a"] = {"id": "faction:a"}
    world.factions["faction:b"] = {"id": "faction:b"}
    world.wards["ward:contested"] = WardState(
        id="ward:contested", name="contested", ring=1, sealed_mode="OP", governor_faction="faction:a"
    )
    world.inst_policy_by_ward["ward:contested"] = WardInstitutionPolicy(
        ward_id="ward:contested", propaganda_budget_points=5.0, censorship_bias=0.2
    )

    run_ideology_update(world, day=0)

    state = ensure_ward_ideology(world, "ward:contested")
    governor_share = state.influence.get("faction:a", 0.0)
    rival_share = state.influence.get("faction:b", 0.0)

    assert governor_share > rival_share


def test_censorship_hurts_technical_training_and_tech() -> None:
    world = _baseline_world()
    _add_ward(world, "ward:open", education_priority={"ENGINEERING": 1.0})
    _add_ward(world, "ward:closed", censorship=2.0, education_priority={"ENGINEERING": 1.0})

    world.tech_state.completed.add("tech:recycler:t1")
    research_inv = world.inventories.inv("owner:state:research")
    research_inv.add(Material.SCRAP_METAL, 6)
    research_inv.add(Material.FASTENERS, 1)
    research_inv.add(Material.SCRAP_INPUT, 8)
    research_inv.add(Material.SEALANT, 2)

    run_ideology_update(world, day=0)
    run_education_update(world, day=0)

    open_comp = ward_competence(world, "ward:open")["ENGINEERING"]
    closed_comp = ward_competence(world, "ward:closed")["ENGINEERING"]
    assert closed_comp < open_comp

    run_tech_for_day(world, day=0)
    assert world.tech_state.active
    active = next(iter(world.tech_state.active.values()))
    assert active.complete_day > 0

    closed_delay = active.complete_day
    # rerun with tech delay favoring open ward
    world.tech_state = TechState()
    world.inst_policy_by_ward["ward:open"].research_budget_points = 5.0
    run_ideology_update(world, day=1)
    run_tech_for_day(world, day=1)
    active_two = next(iter(world.tech_state.active.values()))
    assert active_two.complete_day <= closed_delay


def test_governance_penalties_accumulate_with_censorship() -> None:
    world = _baseline_world()
    _add_ward(world, "ward:tight", censorship=3.0)
    run_ideology_update(world, day=0)
    unrest_initial = world.inst_state_by_ward["ward:tight"].unrest
    run_ideology_update(world, day=1)
    unrest_followup = world.inst_state_by_ward["ward:tight"].unrest
    assert unrest_followup > unrest_initial


def test_snapshot_roundtrip_preserves_axes() -> None:
    world = _baseline_world()
    _add_ward(world, "ward:persist", propaganda=2.0, education_priority={"TRADE": 1.0})
    run_ideology_update(world, day=0)
    snap = snapshot_world(world, scenario_id="ideo:persist")
    restored = restore_world(snap)
    run_ideology_update(restored, day=1)
    run_ideology_update(world, day=1)

    orig_state = ensure_ward_ideology(world, "ward:persist")
    restored_state = ensure_ward_ideology(restored, "ward:persist")

    assert orig_state.curriculum_axes == restored_state.curriculum_axes
    assert orig_state.censorship_level == restored_state.censorship_level


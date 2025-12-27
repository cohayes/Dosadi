from __future__ import annotations

import copy

from dosadi.runtime.constitution import (
    ConstitutionConfig,
    Settlement,
    ensure_constitution_state,
    effective_rights,
    maybe_update_constitution,
    policing_constraints_for_polity,
)
from dosadi.runtime.policing import policing_effects
from dosadi.runtime.sovereignty import ensure_sovereignty_state, ward_fracture_pressure
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WorldState


def _world_with_polity(seed: int = 7) -> WorldState:
    world = WorldState(seed=seed)
    ensure_sovereignty_state(world).territory.ward_control["ward:1"] = "polity:empire"
    cfg: ConstitutionConfig = world.constitution_cfg
    cfg.enabled = True
    cfg.update_cadence_days = 1
    cfg.adoption_rate_base = 1.0
    return world


def test_deterministic_adoption_and_emergency():
    world_a = _world_with_polity(seed=11)
    world_a.crisis_pressure_by_polity = {"polity:empire": 1.0}
    maybe_update_constitution(world_a, day=0)

    world_b = _world_with_polity(seed=11)
    world_b.crisis_pressure_by_polity = {"polity:empire": 1.0}
    maybe_update_constitution(world_b, day=0)

    state_a = world_a.constitution_by_polity["polity:empire"]
    state_b = world_b.constitution_by_polity["polity:empire"]

    assert state_a.active_settlement_id == state_b.active_settlement_id
    assert state_a.rights_current == state_b.rights_current
    assert state_a.emergency_active == state_b.emergency_active


def test_reform_success_increases_adoption_probability():
    baseline = _world_with_polity(seed=3)
    baseline.constitution_cfg.adoption_rate_base = 0.0
    maybe_update_constitution(baseline, day=0)
    assert not baseline.constitution_by_polity["polity:empire"].active_settlement_id

    reform_world = _world_with_polity(seed=3)
    reform_world.constitution_cfg.adoption_rate_base = 1.0
    reform_world.reforms_by_polity = {"polity:empire": [type("Stub", (), {"status": "SUCCEEDED"})()]}
    maybe_update_constitution(reform_world, day=0)
    assert reform_world.constitution_by_polity["polity:empire"].active_settlement_id


def test_due_process_constrains_policing_terror_share():
    world_high = _world_with_polity(seed=5)
    state_high = ensure_constitution_state(world_high, polities=["polity:empire"])["polity:empire"]
    settlement = Settlement(
        settlement_id="s1",
        polity_id="polity:empire",
        name="High Rights",
        governance_form="REPUBLIC",
        rights={"due_process": 0.8},
        constraints={},
        emergency_power_ease=0.2,
        adopted_day=0,
    )
    world_high.settlements[settlement.settlement_id] = settlement
    state_high.active_settlement_id = settlement.settlement_id
    state_high.rights_current = {"due_process": 0.8}
    state_high.constraints_current = {}
    state_high.last_update_day = 0
    world_high.policing_cfg.enabled = True
    ward_state = world_high.policing_by_ward.setdefault("ward:1", world_high.policing_by_ward.get("ward:1"))
    if ward_state is None:
        from dosadi.runtime.policing import WardPolicingState

        ward_state = WardPolicingState(ward_id="ward:1")
    ward_state.doctrine_mix = {"TERROR": 0.6, "PROCEDURAL": 0.1, "COMMUNITY": 0.2, "MILITARIZED": 0.1}
    ward_state.last_update_day = 0
    world_high.policing_by_ward["ward:1"] = ward_state

    low_rights_world = copy.deepcopy(world_high)
    low_state = low_rights_world.constitution_by_polity["polity:empire"]
    low_state.rights_current = {"due_process": 0.0}

    effects_high = policing_effects(world_high, "ward:1", day=0)
    effects_low = policing_effects(low_rights_world, "ward:1", day=0)

    assert effects_high.suppression_mult < effects_low.suppression_mult


def test_emergency_suspends_rights_and_lifts_caps():
    world = _world_with_polity(seed=9)
    world.crisis_pressure_by_polity = {"polity:empire": 1.0}
    maybe_update_constitution(world, day=0)
    state = world.constitution_by_polity["polity:empire"]
    settlement = world.settlements[state.active_settlement_id]
    settlement.emergency_power_ease = 1.0
    maybe_update_constitution(world, day=0)
    state = world.constitution_by_polity["polity:empire"]
    assert state.emergency_active
    rights = effective_rights(world, "polity:empire", day=0)
    assert rights["speech"] < state.rights_current.get("speech", 0.0) or rights["movement"] < state.rights_current.get("movement", 0.0)
    constraints = policing_constraints_for_polity(world, "polity:empire", day=0)
    assert constraints["terror_cap"] == 1.0


def test_rights_reduce_fracture_pressure():
    world = _world_with_polity(seed=21)
    world.governance_failure_pressure = {"ward:1": 0.6}
    base_pressure = ward_fracture_pressure(world, "ward:1")

    state = world.constitution_by_polity["polity:empire"]
    settlement = Settlement(
        settlement_id="s2",
        polity_id="polity:empire",
        name="Stability",
        governance_form="REPUBLIC",
        rights={key: 0.8 for key in ("due_process", "movement", "speech", "labor_organizing", "property_security", "religious_freedom")},
        constraints={},
        emergency_power_ease=0.2,
        adopted_day=0,
    )
    world.settlements[settlement.settlement_id] = settlement
    state.active_settlement_id = settlement.settlement_id
    state.rights_current = dict(settlement.rights)
    reduced_pressure = ward_fracture_pressure(world, "ward:1")
    assert reduced_pressure < base_pressure


def test_snapshot_roundtrip_preserves_constitution_state():
    world = _world_with_polity(seed=31)
    maybe_update_constitution(world, day=0)
    snapshot = snapshot_world(world, scenario_id="test")
    restored = restore_world(snapshot)
    original_state = world.constitution_by_polity["polity:empire"]
    restored_state = restored.constitution_by_polity["polity:empire"]
    assert restored_state.active_settlement_id == original_state.active_settlement_id
    assert restored_state.rights_current == original_state.rights_current


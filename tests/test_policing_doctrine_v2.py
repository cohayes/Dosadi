from dataclasses import dataclass, field

from dosadi.runtime.policing import (
    PolicingConfig,
    WardPolicingState,
    get_policing_capacity,
    policing_effects,
    update_policing_doctrine,
)
from dosadi.runtime.snapshot import from_snapshot_dict, to_snapshot_dict
from dosadi.runtime.workforce import WardWorkforcePools
from dosadi.runtime.comms import CommsModifiers


@dataclass
class FakeWard:
    legitimacy: float = 0.5
    need_index: float = 0.0
    risk_index: float = 0.0


@dataclass
class FakeLaborOrg:
    status: str


@dataclass
class FakeWorld:
    seed: int = 7
    day: int = 0
    policing_cfg: PolicingConfig = field(default_factory=PolicingConfig)
    policing_by_ward: dict[str, WardPolicingState] = field(default_factory=dict)
    wards: dict[str, FakeWard] = field(default_factory=dict)
    labor_orgs_by_ward: dict[str, list[FakeLaborOrg]] = field(default_factory=dict)
    workforce_by_ward: dict[str, WardWorkforcePools] = field(default_factory=dict)
    comms_mod_by_ward: dict[str, CommsModifiers] = field(default_factory=dict)
    counterintel_by_ward: dict[str, float] = field(default_factory=dict)
    raid_pressure_by_ward: dict[str, float] = field(default_factory=dict)
    governance_failure_by_ward: dict[str, float] = field(default_factory=dict)
    leadership_authoritarian_bias: float = 0.0


WARD_ID = "ward:alpha"


def _baseline_world() -> FakeWorld:
    world = FakeWorld()
    world.policing_cfg.enabled = True
    world.wards[WARD_ID] = FakeWard()
    pools = WardWorkforcePools(ward_id=WARD_ID)
    pools.pools = {"GUARD": 10.0, "ADMIN": 4.0, "BUILDER": 6.0}
    world.workforce_by_ward[WARD_ID] = pools
    return world


def test_determinism_same_inputs() -> None:
    world = _baseline_world()
    world.raid_pressure_by_ward[WARD_ID] = 0.5
    mix1 = update_policing_doctrine(world, WARD_ID, day=7).doctrine_mix
    mix2 = update_policing_doctrine(world, WARD_ID, day=7).doctrine_mix
    assert mix1 == mix2

    effects1 = policing_effects(world, WARD_ID, day=7)

    replay = _baseline_world()
    replay.raid_pressure_by_ward[WARD_ID] = 0.5
    update_policing_doctrine(replay, WARD_ID, day=7)
    effects2 = policing_effects(replay, WARD_ID, day=7)
    assert effects1 == effects2


def test_raid_pressure_increases_militarized_share() -> None:
    world_calm = _baseline_world()
    mix_calm = update_policing_doctrine(world_calm, WARD_ID, day=7).doctrine_mix

    world_hot = _baseline_world()
    world_hot.raid_pressure_by_ward[WARD_ID] = 1.0
    mix_hot = update_policing_doctrine(world_hot, WARD_ID, day=7).doctrine_mix

    assert mix_hot.get("MILITARIZED", 0.0) > mix_calm.get("MILITARIZED", 0.0)


def test_terror_doctrine_harms_legitimacy_and_raises_backlash() -> None:
    world = _baseline_world()
    state = world.policing_by_ward.setdefault(WARD_ID, WardPolicingState(ward_id=WARD_ID))
    state.doctrine_mix = {"TERROR": 0.7, "MILITARIZED": 0.3}
    state.force_threshold = 0.9
    effects = policing_effects(world, WARD_ID, day=14)
    assert effects.legitimacy_delta < 0.0
    assert effects.backlash > 0.0


def test_procedural_reduces_corruption_drift() -> None:
    world_proc = _baseline_world()
    state_proc = world_proc.policing_by_ward.setdefault(WARD_ID, WardPolicingState(ward_id=WARD_ID))
    state_proc.doctrine_mix = {"PROCEDURAL": 0.8, "COMMUNITY": 0.2}
    effects_proc = policing_effects(world_proc, WARD_ID, day=7)

    world_loose = _baseline_world()
    state_loose = world_loose.policing_by_ward.setdefault(WARD_ID, WardPolicingState(ward_id=WARD_ID))
    state_loose.doctrine_mix = {"PROCEDURAL": 0.1, "TERROR": 0.4, "MILITARIZED": 0.5}
    effects_loose = policing_effects(world_loose, WARD_ID, day=7)

    assert effects_proc.corruption_delta < effects_loose.corruption_delta


def test_comms_failure_reduces_effectiveness() -> None:
    world_ok = _baseline_world()
    effects_ok = policing_effects(world_ok, WARD_ID, day=7)

    world_outage = _baseline_world()
    world_outage.comms_mod_by_ward[WARD_ID] = CommsModifiers(loss_mult=3.0)
    effects_outage = policing_effects(world_outage, WARD_ID, day=7)

    assert effects_outage.detection_mult < effects_ok.detection_mult
    assert get_policing_capacity(world_outage, WARD_ID, 7) < get_policing_capacity(world_ok, WARD_ID, 7)


def test_snapshot_roundtrip_preserves_doctrine_and_corruption() -> None:
    world = _baseline_world()
    state = world.policing_by_ward.setdefault(WARD_ID, WardPolicingState(ward_id=WARD_ID))
    state.doctrine_mix = {"COMMUNITY": 0.4, "PROCEDURAL": 0.6}
    state.corruption = 0.2
    world.policing_cfg.effect_scale = 0.3

    payload = to_snapshot_dict(world)
    restored = from_snapshot_dict(payload)
    restored_state = restored.policing_by_ward[WARD_ID]
    assert restored_state.doctrine_mix == state.doctrine_mix
    assert restored_state.corruption == state.corruption
    assert restored.policing_cfg.effect_scale == world.policing_cfg.effect_scale

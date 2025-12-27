from types import SimpleNamespace

from dosadi.runtime.reform import (
    ReformAction,
    ReformCampaign,
    ReformConfig,
    ensure_reform_config,
    ensure_reform_ledgers,
    load_reform_seed,
    run_reform_update,
    export_reform_seed,
    _stable_rand01,
    _success_prob,
)
from dosadi.runtime.shadow_state import CorruptionIndex
from dosadi.runtime.policing import ensure_policing_state
from dosadi.runtime.leadership import ensure_leadership_state
from dosadi.runtime.sovereignty import ensure_sovereignty_state
from dosadi.runtime.snapshot import snapshot_world, restore_world


class DummyWard:
    def __init__(self, need_index: float = 0.2):
        self.need_index = need_index


def _base_world(capture: float = 0.4, shadow: float = 0.3, procedural_share: float = 0.4, *, need: float = 0.3):
    world = SimpleNamespace(seed=7, day=0)
    world.wards = {"ward:1": DummyWard(need_index=need)}
    world.corruption_by_ward = {"ward:1": CorruptionIndex(ward_id="ward:1", capture=capture, shadow_state=shadow)}
    ensure_sovereignty_state(world, ward_ids=["ward:1"])
    p_state = ensure_policing_state(world, "ward:1")
    p_state.doctrine_mix = {"PROCEDURAL": procedural_share, "TERROR": max(0.0, 1.0 - procedural_share)}
    ensure_leadership_state(world, polities=["polity:empire"])
    cfg: ReformConfig = ensure_reform_config(world)
    cfg.enabled = True
    cfg.update_cadence_days = 0
    cfg.emergence_rate_base = 0.0
    cfg.success_scale = 0.7
    return world


def test_determinism_same_seed_same_actions():
    w1 = _base_world(capture=0.7, shadow=0.7, procedural_share=0.6)
    w2 = _base_world(capture=0.7, shadow=0.7, procedural_share=0.6)
    run_reform_update(w1, day=0)
    run_reform_update(w2, day=0)
    assert export_reform_seed(w1) == export_reform_seed(w2)


def test_high_corruption_increases_reform_pressure():
    low = _base_world(capture=0.1, shadow=0.1)
    high = _base_world(capture=0.9, shadow=0.9)
    high.reform_cfg.emergence_rate_base = 2.0
    run_reform_update(low, day=0)
    run_reform_update(high, day=0)
    low_count = len(low.reforms_by_polity.get("polity:empire", []))
    high_count = len(high.reforms_by_polity.get("polity:empire", []))
    assert high_count > low_count


def test_procedural_policing_improves_success_probability():
    base_campaign = ReformCampaign(
        reform_id="reform:polity:empire:0:0",
        polity_id="polity:empire",
        kind="PROCEDURAL",
        sponsors=[],
        targets=[{"ward_id": "ward:1", "domain": "COURTS", "priority": 1.0}],
        intensity=0.6,
        legitimacy_push=0.5,
        risk_tolerance=0.3,
        start_day=0,
        last_update_day=-1,
    )

    low = _base_world(capture=0.3, shadow=0.2, procedural_share=0.1)
    high = _base_world(capture=0.3, shadow=0.2, procedural_share=0.9)
    ensure_reform_ledgers(low, ["polity:empire"])[0]["polity:empire"] = [base_campaign]
    ensure_reform_ledgers(high, ["polity:empire"])[0]["polity:empire"] = [base_campaign]

    roll = _stable_rand01(low.reform_cfg.deterministic_salt, base_campaign.reform_id, "ward:1", 0, 0)
    prob_low = _success_prob(
        campaign=base_campaign,
        procedural_share=0.1,
        shadow_strength=0.2,
        cfg=low.reform_cfg,
    )
    prob_high = _success_prob(
        campaign=base_campaign,
        procedural_share=0.9,
        shadow_strength=0.2,
        cfg=high.reform_cfg,
    )
    assert prob_high > prob_low
    assert prob_high > roll >= prob_low

    run_reform_update(low, day=0)
    run_reform_update(high, day=0)
    low_result = low.reform_actions[-1].result
    high_result = high.reform_actions[-1].result
    assert low_result != "SUCCESS"
    assert high_result == "SUCCESS"


def test_purges_reduce_capture_but_increase_backlash():
    campaign = ReformCampaign(
        reform_id="reform:polity:empire:0:1",
        polity_id="polity:empire",
        kind="POPULIST_PURGE",
        sponsors=[],
        targets=[{"ward_id": "ward:1", "domain": "POLICING", "priority": 1.0}],
        intensity=0.8,
        legitimacy_push=0.5,
        risk_tolerance=0.7,
        start_day=0,
        last_update_day=-1,
    )
    procedural = ReformCampaign(
        reform_id="reform:polity:empire:0:2",
        polity_id="polity:empire",
        kind="PROCEDURAL",
        sponsors=[],
        targets=[{"ward_id": "ward:1", "domain": "POLICING", "priority": 1.0}],
        intensity=0.5,
        legitimacy_push=0.4,
        risk_tolerance=0.4,
        start_day=0,
        last_update_day=-1,
    )

    purge_world = _base_world(capture=0.6, shadow=0.1, procedural_share=0.9)
    procedural_world = _base_world(capture=0.6, shadow=0.1, procedural_share=0.9)
    purge_world.reform_cfg.success_scale = 0.9
    procedural_world.reform_cfg.success_scale = 0.9
    ensure_reform_ledgers(purge_world, ["polity:empire"])[0]["polity:empire"] = [campaign]
    ensure_reform_ledgers(procedural_world, ["polity:empire"])[0]["polity:empire"] = [procedural]

    start_capture = purge_world.corruption_by_ward["ward:1"].capture
    run_reform_update(purge_world, day=0)
    run_reform_update(procedural_world, day=0)
    purge_capture = purge_world.corruption_by_ward["ward:1"].capture
    procedural_capture = procedural_world.corruption_by_ward["ward:1"].capture

    assert purge_capture < procedural_capture < start_capture
    assert purge_world.reforms_by_polity["polity:empire"][0].backlash >= procedural_world.reforms_by_polity["polity:empire"][0].backlash


def test_high_shadow_increases_retaliation():
    campaign = ReformCampaign(
        reform_id="reform:polity:empire:1:0",
        polity_id="polity:empire",
        kind="PROCEDURAL",
        sponsors=[],
        targets=[{"ward_id": "ward:1", "domain": "MEDIA", "priority": 1.0}],
        intensity=0.4,
        legitimacy_push=0.4,
        risk_tolerance=0.4,
        start_day=0,
        last_update_day=-1,
    )

    low_shadow = _base_world(capture=0.2, shadow=0.05, procedural_share=0.5)
    high_shadow = _base_world(capture=0.8, shadow=0.9, procedural_share=0.5)
    ensure_reform_ledgers(low_shadow, ["polity:empire"])[0]["polity:empire"] = [campaign]
    ensure_reform_ledgers(high_shadow, ["polity:empire"])[0]["polity:empire"] = [campaign]

    run_reform_update(low_shadow, day=0)
    run_reform_update(high_shadow, day=0)

    low_sabotaged = any(action.result == "SABOTAGED" for action in low_shadow.reform_actions)
    high_sabotaged = any(action.result == "SABOTAGED" for action in high_shadow.reform_actions)
    assert high_sabotaged
    assert not low_sabotaged


def test_snapshot_roundtrip_persists_reforms():
    world = _base_world(capture=0.7, shadow=0.5)
    world.reform_cfg.emergence_rate_base = 2.0
    world.reform_cfg.success_scale = 1.0
    run_reform_update(world, day=0)
    snap = snapshot_world(world, scenario_id="test")
    restored = restore_world(snap)
    assert export_reform_seed(restored) == export_reform_seed(world)
    assert isinstance(restored.reform_actions[0], ReformAction)



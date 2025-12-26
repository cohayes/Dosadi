from __future__ import annotations

from dataclasses import dataclass, field

from dosadi.runtime.crackdown import (
    CrackdownConfig,
    CrackdownTarget,
    border_modifiers,
    ensure_crackdown_config,
    ensure_crackdown_state,
    plan_crackdown,
)
from dosadi.runtime.customs import CustomsConfig, _bribe_success, _effective_inspection_prob
from dosadi.runtime.institutions import InstitutionConfig, ensure_state, _update_state
from dosadi.runtime.telemetry import Metrics
from dosadi.runtime.snapshot import to_snapshot_dict, from_snapshot_dict


@dataclass
class FakeWorld:
    seed: int = 1
    day: int = 0
    metrics: Metrics = field(default_factory=Metrics)
    crackdown_plans: dict[int, object] = field(default_factory=dict)
    crackdown_active: dict[str, CrackdownTarget] = field(default_factory=dict)


def test_deterministic_plan_same_inputs() -> None:
    world = FakeWorld()
    cfg = ensure_crackdown_config(world)
    cfg.enabled = True
    world.customs_signals = {"border:1": {"bribes": 2.0, "seizures": 1.0, "traffic": 1.0}}
    first = plan_crackdown(world, day=3)
    second = plan_crackdown(world, day=3)
    assert first is not None and second is not None
    assert [(t.kind, t.target_id, t.intensity) for t in first.targets] == [
        (t.kind, t.target_id, t.intensity) for t in second.targets
    ]


def test_bounded_targets_respect_topk_and_max() -> None:
    world = FakeWorld()
    cfg = ensure_crackdown_config(world)
    cfg.enabled = True
    cfg.max_targets_per_day = 2
    cfg.border_topk = 2
    world.customs_signals = {
        "b1": {"bribes": 5.0},
        "b2": {"bribes": 4.0},
        "b3": {"bribes": 3.0},
    }
    plan = plan_crackdown(world, day=1)
    assert plan is not None
    assert len(plan.targets) == 2
    selected_ids = {t.target_id for t in plan.targets}
    assert selected_ids.issubset({"b1", "b2"})


def test_cooldown_prevents_immediate_retarget() -> None:
    world = FakeWorld()
    cfg = ensure_crackdown_config(world)
    cfg.enabled = True
    cfg.cooldown_days = 3
    ensure_crackdown_state(world)
    world.crackdown_active["border:hot"] = CrackdownTarget(
        kind="border",
        target_id="hot",
        intensity=1.0,
        start_day=0,
        end_day=2,
        reason="existing",
    )
    world.customs_signals = {"hot": {"bribes": 10.0}, "alt": {"bribes": 9.0}}
    plan = plan_crackdown(world, day=1)
    assert plan is not None
    assert all(t.target_id != "hot" for t in plan.targets)


def test_border_modifiers_affect_customs_probabilities() -> None:
    world = FakeWorld()
    cfg = ensure_crackdown_config(world)
    cfg.enabled = True
    ensure_crackdown_state(world)
    world.crackdown_active["border:edge-1"] = CrackdownTarget(
        kind="border",
        target_id="edge-1",
        intensity=1.0,
        start_day=0,
        end_day=7,
        reason="test",
    )
    policy = ensure_state(world, "ward:x")
    phase = "P1"
    customs_cfg = CustomsConfig(enabled=True)
    base_prob = _effective_inspection_prob(customs_cfg, policy, phase, escorted=False, flags=set())
    modifiers = border_modifiers(world, "edge-1")
    boosted_prob = min(1.0, base_prob * float(modifiers.get("inspection_mult", 1.0)))
    assert boosted_prob > base_prob

    key = "bribe-test"
    base_bribe_success = _bribe_success(customs_cfg, policy, policy.corruption, 0.0, key, phase)
    harder_bribe = _bribe_success(
        customs_cfg,
        policy,
        policy.corruption,
        0.0,
        key,
        phase,
        modifier_mult=float(modifiers.get("bribe_mult", 1.0)),
    )
    if modifiers.get("bribe_mult", 1.0) < 1.0:
        assert base_bribe_success or not harder_bribe


def test_smuggling_adapts_by_rotating_targets_with_cooldown() -> None:
    world = FakeWorld()
    cfg = ensure_crackdown_config(world)
    cfg.enabled = True
    world.customs_signals = {"alpha": {"bribes": 5.0}, "beta": {"bribes": 4.0}}
    first = plan_crackdown(world, day=0)
    assert first is not None
    ensure_crackdown_state(world)
    second = plan_crackdown(world, day=1)
    assert second is not None
    first_ids = {(t.kind, t.target_id) for t in first.targets}
    second_ids = {(t.kind, t.target_id) for t in second.targets}
    assert first_ids != second_ids


def test_political_costs_raise_unrest_and_reduce_legitimacy() -> None:
    world = FakeWorld()
    ensure_crackdown_config(world).enabled = True
    ensure_crackdown_state(world)
    world.crackdown_active["ward_audit:w1"] = CrackdownTarget(
        kind="ward_audit",
        target_id="w1",
        intensity=1.0,
        start_day=0,
        end_day=5,
        reason="audit",
    )
    cfg = InstitutionConfig()
    state = ensure_state(world, "w1", cfg=cfg)
    issues = {"issue:shortage": 0.0, "issue:predation": 0.0, "issue:belief_anger": 0.0, "issue:corruption_opportunity": 0.0}
    baseline = ensure_state(FakeWorld(), "w1", cfg=cfg)
    _update_state(world, state, issues, cfg=cfg)
    _update_state(FakeWorld(), baseline, issues, cfg=cfg)
    assert state.legitimacy < baseline.legitimacy
    assert state.unrest > baseline.unrest


def test_snapshot_roundtrip_preserves_active_targets() -> None:
    world = FakeWorld()
    ensure_crackdown_config(world).enabled = True
    plans, active = ensure_crackdown_state(world)
    active["border:a"] = CrackdownTarget(
        kind="border",
        target_id="a",
        intensity=0.5,
        start_day=0,
        end_day=3,
        reason="persist",
    )
    plans[0] = plan = plan_crackdown(world, day=0) or plan_crackdown(world, day=0)
    snap = to_snapshot_dict(world)
    restored = from_snapshot_dict(snap)
    restored_active = getattr(restored, "crackdown_active", {})
    assert "border:a" in restored_active
    assert getattr(restored_active.get("border:a"), "intensity", 0.0) == 0.5
    assert hasattr(restored, "crackdown_plans")

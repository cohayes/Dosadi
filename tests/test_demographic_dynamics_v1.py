from __future__ import annotations

import copy

import pytest

from dosadi.agents.core import AgentState
from dosadi.runtime.demographics import PolityDemographics, run_demographics_for_day
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WardState, WorldState


def _world_with_population(seed: int = 7, agents: int = 120) -> WorldState:
    world = WorldState(seed=seed)
    world.demographics_cfg.enabled = True
    world.demographics_cfg.update_cadence_days = 30
    world.demographics_cfg.annual_step_days = 120

    world.wards["ward:a"] = WardState(
        id="ward:a",
        name="A",
        ring=1,
        sealed_mode="open",
        need_index=0.2,
        risk_index=0.15,
    )

    for idx in range(agents):
        world.agents[f"agent:{idx}"] = AgentState(agent_id=f"agent:{idx}", name=f"Agent {idx}")

    return world


def test_deterministic_quarterly_updates() -> None:
    world_a = _world_with_population(seed=11, agents=64)
    world_b = copy.deepcopy(world_a)

    for day in range(0, 360, 30):
        run_demographics_for_day(world_a, day=day)
        run_demographics_for_day(world_b, day=day)

    assert world_a.demographics_by_polity.keys() == world_b.demographics_by_polity.keys()
    for polity_id in world_a.demographics_by_polity:
        a_state = world_a.demographics_by_polity[polity_id]
        b_state = world_b.demographics_by_polity[polity_id]
        assert a_state.cohort_pop == pytest.approx(b_state.cohort_pop)
        assert a_state.fertility == pytest.approx(b_state.fertility)
        assert a_state.mortality == pytest.approx(b_state.mortality)


def test_annual_step_applies_births_deaths_and_aging() -> None:
    world = _world_with_population(seed=19, agents=0)
    cfg = world.demographics_cfg
    cfg.enabled = True
    cfg.annual_step_days = 1
    cfg.cohort_years = 5
    cfg.max_age = 15
    cfg.update_cadence_days = 999

    cohorts = [50.0, 40.0, 30.0, 20.0]
    mortality = [0.1, 0.05, 0.02, 0.01]

    state = PolityDemographics(polity_id="polity:central")
    world.demographics_by_polity["polity:central"] = state

    state.cohort_pop = cohorts
    state.mortality = mortality
    state.fertility = 0.05
    state.last_annual_year = 0
    state.last_update_day = 0

    run_demographics_for_day(world, day=1)

    expected = [43.0, 39.4, 31.12, 25.68]
    assert state.cohort_pop == pytest.approx(expected, rel=1e-3)
    assert state.dependency_ratio == pytest.approx((43.0 + 39.4 + 31.12) / 25.68, rel=1e-3)
    assert state.youth_bulge == pytest.approx(25.68 / sum(expected), rel=1e-3)


def test_snapshot_roundtrip_preserves_demographics() -> None:
    world = _world_with_population(seed=23, agents=48)
    world.demographics_cfg.enabled = True

    for day in range(0, 180, 30):
        run_demographics_for_day(world, day=day)

    snap = snapshot_world(world, scenario_id="demo")
    restored = restore_world(snap)

    run_demographics_for_day(restored, day=180)

    assert restored.demographics_by_polity
    state = next(iter(restored.demographics_by_polity.values()))
    assert state.cohort_pop
    assert restored.demographic_events

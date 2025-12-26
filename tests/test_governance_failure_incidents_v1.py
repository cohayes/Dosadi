from types import SimpleNamespace

import pytest

from dosadi.runtime.governance_failures import (
    GovernanceFailureConfig,
    GovernanceIncidentRecord,
    ensure_govfail_config,
    ensure_govfail_state,
    delivery_disruption_prob_for_ward,
    production_multiplier_for_ward,
    run_governance_failure_for_day,
    _record_effects,
)
from dosadi.runtime.production_runtime import ProductionConfig, ProductionState, run_production_for_day
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.world.facilities import Facility, FacilityKind, FacilityLedger
from dosadi.world.incidents import IncidentKind
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, LogisticsLedger, _delivery_should_fail
from dosadi.world.recipes import Recipe, RecipeRegistry
from dosadi.world.survey_map import SurveyMap, SurveyNode


def _baseline_world(seed: int = 1):
    nodes = {
        "n1": SurveyNode(node_id="n1", kind="node", ward_id="ward:a"),
        "n2": SurveyNode(node_id="n2", kind="node", ward_id="ward:b"),
    }
    world = SimpleNamespace(
        seed=seed,
        day=0,
        survey_map=SurveyMap(nodes=nodes, edges={}),
        inst_state_by_ward={
            "ward:a": SimpleNamespace(legitimacy=0.35, discipline=0.35, corruption=0.25, unrest=0.8, audit=0.2),
            "ward:b": SimpleNamespace(legitimacy=0.32, discipline=0.30, corruption=0.2, unrest=0.75, audit=0.1),
        },
        culture_by_ward={
            "ward:a": SimpleNamespace(norms={"norm:anti_state": 0.6, "norm:queue_order": 0.2}),
            "ward:b": SimpleNamespace(norms={"norm:anti_state": 0.55, "norm:queue_order": 0.25}),
        },
        market_shortage_pressure=0.9,
    )
    cfg: GovernanceFailureConfig = ensure_govfail_config(world)
    cfg.enabled = True
    cfg.max_new_incidents_per_day = 2
    return world


def _count_active(world) -> int:
    state = getattr(world, "govfail_state", None)
    if state is None:
        return 0
    return sum(len(v) for v in getattr(state, "active_by_ward", {}).values())


def test_determinism_same_seed_same_incidents():
    world_a = _baseline_world(seed=2)
    world_b = _baseline_world(seed=2)

    run_governance_failure_for_day(world_a, day=0)
    run_governance_failure_for_day(world_b, day=0)

    assert getattr(world_a, "incidents").signature() == getattr(world_b, "incidents").signature()


def test_daily_cap_respected():
    world = _baseline_world(seed=3)
    cfg: GovernanceFailureConfig = ensure_govfail_config(world)
    cfg.max_new_incidents_per_day = 1

    run_governance_failure_for_day(world, day=0)

    assert _count_active(world) <= cfg.max_new_incidents_per_day


def test_cooldown_blocks_repeats():
    world = _baseline_world(seed=4)
    cfg: GovernanceFailureConfig = ensure_govfail_config(world)
    cfg.cooldown_days_by_kind["STRIKE"] = 10
    cfg.base_rates_by_phase["P0"]["STRIKE"] = 1.0
    run_governance_failure_for_day(world, day=0)
    state = world.govfail_state
    initial_strikes = [
        rec
        for rec in state.active_by_ward.get("ward:a", [])
        if rec.kind is IncidentKind.STRIKE
    ]

    run_governance_failure_for_day(world, day=1)
    repeated_strikes = [
        rec
        for rec in state.active_by_ward.get("ward:a", [])
        if rec.kind is IncidentKind.STRIKE
    ]
    assert len(repeated_strikes) == len(initial_strikes)


def _attach_simple_production(world):
    registry = RecipeRegistry(
        recipes=[
            Recipe(
                recipe_id="R1",
                facility_kind=FacilityKind.WORKSHOP.value,
                inputs={},
                outputs={},
                duration_days=1,
            )
        ]
    )
    world.recipe_registry = registry
    world.prod_cfg = ProductionConfig()
    world.prod_state = ProductionState()
    ledger = FacilityLedger(
        facilities={
            "fac-1": Facility(facility_id="fac-1", kind=FacilityKind.WORKSHOP, site_node_id="n1"),
        }
    )
    world.facilities = ledger
    return world


def test_effects_apply_and_revert():
    world = _baseline_world(seed=5)
    world = _attach_simple_production(world)
    cfg: GovernanceFailureConfig = ensure_govfail_config(world)
    cfg.base_rates_by_phase["P0"]["STRIKE"] = 1.0

    world.prod_state.jobs_started_today = 0
    world.prod_state.jobs_started_by_facility.clear()
    run_production_for_day(world, day=0)
    base_started = getattr(world.prod_state, "jobs_started_today", 0)

    world.prod_state.jobs_started_today = 0
    world.prod_state.jobs_started_by_facility.clear()
    run_governance_failure_for_day(world, day=0)
    run_production_for_day(world, day=1)
    reduced_started = getattr(world.prod_state, "jobs_started_today", 0)
    assert reduced_started <= base_started
    assert production_multiplier_for_ward(world, "ward:a") < 1.0

    # Tick through duration to restore
    restored = False
    for step in range(1, 15):
        run_governance_failure_for_day(world, day=step)
        if production_multiplier_for_ward(world, "ward:a") == 1.0:
            restored = True
            break
    assert restored


def test_riot_disrupts_deliveries_then_recovers():
    world = _baseline_world(seed=6)
    ensure_govfail_config(world)
    state = ensure_govfail_state(world)
    state.active_by_ward = {
        "ward:a": [
            GovernanceIncidentRecord(
                incident_id="test-riot",
                kind=IncidentKind.RIOT,
                ward_id="ward:a",
                severity=0.8,
                remaining_days=3,
                duration_days=3,
            )
        ]
    }
    _record_effects(state)

    ledger = LogisticsLedger()
    delivery = DeliveryRequest(
        delivery_id="d1",
        project_id="p1",
        origin_node_id="n1",
        dest_node_id="n2",
        items={"w": 1.0},
        status=DeliveryStatus.IN_TRANSIT,
        created_tick=0,
    )
    ledger.add(delivery)
    world.logistics = ledger

    assert delivery_disruption_prob_for_ward(world, "ward:a") > 0.0

    state.active_by_ward["ward:a"][0].status = "resolved"
    _record_effects(state)

    assert delivery_disruption_prob_for_ward(world, "ward:a") == 0.0


def test_counterplay_reduces_propensity():
    risky_world = _baseline_world(seed=7)
    safe_world = _baseline_world(seed=7)
    safe_state = safe_world.inst_state_by_ward["ward:a"]
    safe_state.legitimacy = 0.9
    safe_state.discipline = 0.8
    safe_state.unrest = 0.2

    run_governance_failure_for_day(risky_world, day=0)
    run_governance_failure_for_day(safe_world, day=0)

    risky_active = _count_active(risky_world)
    safe_active = _count_active(safe_world)
    assert risky_active >= safe_active

    if safe_active and risky_active:
        risky_incident = next(iter(risky_world.incidents.incidents.values()))
        safe_incident = next(iter(safe_world.incidents.incidents.values()))
        assert risky_incident.severity >= safe_incident.severity


def test_snapshot_roundtrip_preserves_active_incidents():
    world = _baseline_world(seed=8)
    run_governance_failure_for_day(world, day=0)
    snap = snapshot_world(world, scenario_id="scn")
    restored = restore_world(snap)

    assert _count_active(restored) == _count_active(world)
    assert restored.govfail_state.effects_by_ward == world.govfail_state.effects_by_ward


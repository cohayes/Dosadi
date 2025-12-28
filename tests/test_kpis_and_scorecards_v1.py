from __future__ import annotations

import copy
from dataclasses import dataclass, field

import pytest

from dosadi.runtime.kpis import SCHEMA, kpi_from_legacy_metrics, update_kpis
from dosadi.runtime.scorecards import compute_scorecard
from dosadi.runtime.telemetry import Metrics
from dosadi.world.facilities import Facility, FacilityKind, FacilityLedger
from dosadi.world.incidents import IncidentLedger


@dataclass
class FakeGroup:
    group_type: str = "COUNCIL"


@dataclass
class FakeContract:
    milestones: list


@dataclass
class FakeMilestone:
    status: str


@dataclass
class FakeWorld:
    tick: int = 0
    day: int = 0
    metrics: Metrics = field(default_factory=Metrics)
    facilities: FacilityLedger = field(default_factory=FacilityLedger)
    routes: dict = field(default_factory=dict)
    infra_edges: dict = field(default_factory=dict)
    groups: list = field(default_factory=list)
    incidents: IncidentLedger = field(default_factory=IncidentLedger)
    agents: dict = field(default_factory=dict)
    active_contract: FakeContract | None = None


def _basic_world() -> FakeWorld:
    world = FakeWorld()
    world.metrics.set_gauge("economy.avg_ration_level", 0.5)
    return world


def test_schema_presence_after_update():
    world = _basic_world()
    store = update_kpis(world, tick=0, mode="run_end")

    assert set(SCHEMA) <= set(store.values)
    for key in SCHEMA:
        assert key in store.values
        assert isinstance(store.values[key].value, float)


def test_deterministic_updates_and_scorecard():
    world_a = _basic_world()
    world_a.metrics.inc("stockpile.deliveries_completed", 2)
    world_a.routes["r1"] = {}

    world_b = copy.deepcopy(world_a)

    update_kpis(world_a, tick=10, mode="run_end")
    update_kpis(world_b, tick=10, mode="run_end")

    score_a = compute_scorecard(world_a)
    score_b = compute_scorecard(world_b)

    assert score_a.score_total == score_b.score_total
    assert score_a.grades == score_b.grades


def test_increment_hooks_from_world_state():
    world = _basic_world()
    world.facilities.add(Facility(facility_id="f1", kind=FacilityKind.DEPOT))
    world.routes["r1"] = {}
    world.infra_edges["c1"] = {}
    world.metrics.inc("stockpile.deliveries_completed", 1)
    world.metrics.inc("incidents_total", 2)

    store = update_kpis(world, tick=5, mode="micro")

    assert store.values["logistics.depots_built"].value == 1
    assert store.values["logistics.routes_active"].value == 1
    assert store.values["logistics.corridors_established"].value == 1
    assert store.values["logistics.deliveries_completed"].value == 1
    assert store.values["safety.incidents_total"].value >= 2


def test_delivery_success_ratio_derivation():
    world = _basic_world()
    world.metrics.inc("stockpile.deliveries_completed", 3)
    world.metrics.inc("stockpile.deliveries_failed", 1)

    store = update_kpis(world, tick=20, mode="day")
    assert store.values["logistics.delivery_success_rate"].value == pytest.approx(0.75)


def test_scorecard_monotonicity():
    base_world = _basic_world()
    improved_world = _basic_world()
    improved_world.active_contract = FakeContract(
        milestones=[FakeMilestone(status="ACHIEVED"), FakeMilestone(status="PENDING")]
    )
    improved_world.metrics.inc("stockpile.deliveries_completed", 5)
    improved_world.routes["r1"] = {}
    improved_world.groups.append(FakeGroup())

    base_score = compute_scorecard(base_world)
    improved_score = compute_scorecard(improved_world)

    assert improved_score.score_total >= base_score.score_total


def test_legacy_adapter_mapping():
    legacy = {
        "depots_built": 2,
        "deliveries_completed": 7,
        "routes_active": 3,
        "corridors_established": 1,
        "incidents_total": 4,
        "injuries_total": 1,
        "deaths_total": 0,
    }
    mapped = kpi_from_legacy_metrics(legacy)

    assert mapped["logistics.depots_built"] == 2
    assert mapped["logistics.deliveries_completed"] == 7
    assert mapped["safety.incidents_total"] == 4

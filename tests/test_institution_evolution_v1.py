import copy
import json
from pathlib import Path

import pytest

from dosadi.agents.core import AgentState, PhysicalState
from dosadi.runtime.corridor_risk import CorridorRiskLedger, EdgeRiskRecord
from dosadi.runtime.institutions import (
    InstitutionConfig,
    WardInstitutionState,
    ensure_state,
    institutions_signature,
    run_institutions_for_day,
)
from dosadi.runtime.law_enforcement import WardSecurityPolicy
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WardState, WorldState
from dosadi.vault.seed_vault import save_seed
from dosadi.world.phases import PhaseState, WorldPhase
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode, edge_key


def _basic_world(*, enabled: bool = True) -> WorldState:
    world = WorldState(seed=99)
    world.inst_cfg = InstitutionConfig(enabled=enabled)
    world.phase_state = PhaseState()

    node_a = SurveyNode(node_id="loc:a", kind="pod", ward_id="ward:a")
    node_b = SurveyNode(node_id="loc:b", kind="pod", ward_id="ward:b")
    edge = SurveyEdge(a=node_a.node_id, b=node_b.node_id, distance_m=10.0, travel_cost=1.0, hazard=0.7)
    world.survey_map = SurveyMap(nodes={node_a.node_id: node_a, node_b.node_id: node_b}, edges={edge.key: edge})

    world.wards["ward:a"] = WardState(
        id="ward:a",
        name="Ward A",
        ring=0,
        sealed_mode="open",
        need_index=0.8,
    )
    world.wards["ward:b"] = WardState(
        id="ward:b",
        name="Ward B",
        ring=1,
        sealed_mode="open",
        need_index=0.2,
    )
    world.wards["ward:a"].infrastructure.maintenance_index = 0.6

    ledger = CorridorRiskLedger()
    ledger.edges[edge.key] = EdgeRiskRecord(edge_key=edge.key, risk=0.9, incidents_lookback=2.0)
    world.risk_ledger = ledger

    world.agents["agent:a"] = AgentState(
        agent_id="agent:a",
        name="Agent A",
        location_id=node_a.node_id,
        physical=PhysicalState(stress_level=0.6),
    )
    world.agents["agent:b"] = AgentState(
        agent_id="agent:b",
        name="Agent B",
        location_id=node_b.node_id,
        physical=PhysicalState(stress_level=0.1),
    )
    world.enf_policy_by_ward["ward:a"] = WardSecurityPolicy(ward_id="ward:a", budget_points=8.0)
    return world


def test_institutions_are_deterministic():
    world_a = _basic_world()
    world_b = copy.deepcopy(world_a)

    run_institutions_for_day(world_a, day=1)
    run_institutions_for_day(world_b, day=1)

    assert world_a.inst_state_by_ward.keys() == world_b.inst_state_by_ward.keys()
    assert institutions_signature(world_a) == institutions_signature(world_b)


def test_delta_caps_respected():
    world = _basic_world()
    cfg = world.inst_cfg
    world.inst_state_by_ward["ward:a"] = WardInstitutionState(
        ward_id="ward:a",
        legitimacy=0.2,
        discipline=0.2,
        corruption=0.6,
        audit=0.1,
    )
    run_institutions_for_day(world, day=1)

    updated = world.inst_state_by_ward["ward:a"]
    for key, cap in cfg.daily_delta_caps.items():
        before = 0.0
        if key == "legitimacy":
            before = 0.2
            after = updated.legitimacy
        elif key == "discipline":
            before = 0.2
            after = updated.discipline
        elif key == "corruption":
            before = 0.6
            after = updated.corruption
        else:
            before = 0.1
            after = updated.audit
        assert abs(after - before) <= cap + 1e-6


def test_phase_defaults_applied():
    world = _basic_world()
    world.phase_state = PhaseState(phase=WorldPhase.PHASE2)
    world.inst_cfg = InstitutionConfig(enabled=True)

    state = ensure_state(world, "ward:a", cfg=world.inst_cfg)
    defaults = world.inst_cfg.phase_defaults["P2"]
    assert state.legitimacy == pytest.approx(defaults["legitimacy"])
    assert state.discipline == pytest.approx(defaults["discipline"])
    assert state.corruption == pytest.approx(defaults["corruption"])
    assert state.audit == pytest.approx(defaults["audit"])


def test_enforcement_budget_coupling():
    world = _basic_world()
    run_institutions_for_day(world, day=2)

    inst_policy = world.inst_policy_by_ward["ward:a"]
    enf_policy = world.enf_policy_by_ward["ward:a"]
    assert enf_policy.budget_points == pytest.approx(inst_policy.enforcement_budget_points)


def test_persistence_and_seed_export(tmp_path: Path):
    world = _basic_world()
    run_institutions_for_day(world, day=3)
    sig_before = institutions_signature(world)

    snap = snapshot_world(world, scenario_id="test")
    restored = restore_world(snap)
    assert institutions_signature(restored) == sig_before

    entry = save_seed(tmp_path, world, seed_id="seed-01", scenario_id="scenario", meta={})
    inst_path = tmp_path / entry["institutions_path"]
    assert inst_path.exists()
    with inst_path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    assert data["schema"] == "institutions_v1"
    ward_ids = [row["ward_id"] for row in data["wards"]]
    assert ward_ids == sorted(ward_ids)

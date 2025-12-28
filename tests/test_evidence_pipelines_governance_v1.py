from __future__ import annotations

import copy

from dosadi.agents.core import AgentState
from dosadi.runtime.evidence import ensure_evidence_buffer
from dosadi.runtime.evidence_producers import run_evidence_update
from dosadi.runtime.protocol_authoring import maybe_author_movement_protocols
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.state import WorldState
from dosadi.runtime.corridor_risk import CorridorRiskLedger, EdgeRiskRecord
from dosadi.runtime.stockpile_policy import DepotPolicyLedger
from dosadi.world.materials import Material, ensure_inventory_registry


def _world_with_risk() -> WorldState:
    world = WorldState(seed=42)
    world.day = 3
    ledger = CorridorRiskLedger()
    rec = EdgeRiskRecord(edge_key="loc:a|loc:b", risk=0.8, incidents_lookback=0.2, last_updated_day=3)
    ledger.edges[rec.edge_key] = rec
    ledger.hot_edges = [rec.edge_key]
    world.risk_ledger = ledger
    return world


def test_determinism_with_same_seed() -> None:
    base = _world_with_risk()
    world_a = copy.deepcopy(base)
    world_b = copy.deepcopy(base)

    run_evidence_update(world_a, day=base.day)
    run_evidence_update(world_b, day=base.day)

    buf_a = ensure_evidence_buffer(world_a, "polity:default")
    buf_b = ensure_evidence_buffer(world_b, "polity:default")

    assert buf_a.signature() == buf_b.signature()


def test_payloads_and_buffer_are_bounded() -> None:
    world = _world_with_risk()
    world.evidence_cfg.max_payload_items = 1
    buffer = ensure_evidence_buffer(world, "polity:default")
    buffer.max_items = 2

    # Force multiple hot edges to exercise payload truncation
    ledger = world.risk_ledger
    assert isinstance(ledger, CorridorRiskLedger)
    ledger.hot_edges = [f"edge:{idx}" for idx in range(5)]
    for edge_key in ledger.hot_edges:
        ledger.edges[edge_key] = EdgeRiskRecord(edge_key=edge_key, risk=0.5, last_updated_day=world.day)

    run_evidence_update(world, day=world.day)

    bounded_buffer = ensure_evidence_buffer(world, "polity:default")
    assert len(bounded_buffer.items) <= 2
    entry = bounded_buffer.items.get("evidence.corridor_risk.topk")
    assert entry is not None
    payload_items = entry.payload.get("items", []) if isinstance(entry.payload, dict) else []
    assert len(payload_items) <= 1


def test_producers_emit_keys_even_when_sparse() -> None:
    world = WorldState(seed=7)
    world.day = 1

    run_evidence_update(world, day=world.day)

    buffer = ensure_evidence_buffer(world, "polity:default")
    expected = {
        "evidence.corridor_risk.topk",
        "evidence.incidents.rate_7d",
        "evidence.protocol_violations.rate_7d",
        "evidence.enforcement.load_7d",
        "evidence.diagnostics.missing_source",
    }
    assert expected <= set(buffer.items.keys())


def test_diagnostics_when_sources_missing() -> None:
    world = WorldState(seed=11)
    world.day = 2
    run_evidence_update(world, day=world.day)

    buffer = ensure_evidence_buffer(world, "polity:default")
    diag = buffer.items.get("evidence.diagnostics.missing_source")
    assert diag is not None
    assert diag.confidence <= 0.2


def test_council_can_author_protocol_from_evidence() -> None:
    world = _world_with_risk()
    world.agents["agent:1"] = AgentState(agent_id="agent:1", name="Agent 1")
    run_evidence_update(world, day=world.day)

    created = maybe_author_movement_protocols(world=world, dangerous_edge_ids=[], tick=0)

    assert created is True
    assert getattr(world, "protocols", None) is not None
    registry = world.protocols
    assert registry.protocols_by_id
    created_proto = next(iter(registry.protocols_by_id.values()))
    assert "loc:a|loc:b" in created_proto.covered_location_ids


def test_snapshot_roundtrip_preserves_evidence() -> None:
    world = _world_with_risk()
    stock_ledger = DepotPolicyLedger()
    world.stock_policies = stock_ledger
    ensure_inventory_registry(world)

    run_evidence_update(world, day=world.day)
    snap = snapshot_world(world, scenario_id="evidence-test")
    restored = restore_world(snap)

    buffer = ensure_evidence_buffer(restored, "polity:default")
    assert buffer.items

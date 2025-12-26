from __future__ import annotations

import copy

from dosadi.runtime.corridor_risk import EdgeRiskRecord
from dosadi.runtime.factions import Opportunity, _apply_outcome, _success_probability, run_real_factions_for_day
from dosadi.runtime.law_enforcement import WardSecurityState, ensure_enforcement_config
from dosadi.simulation.snapshots import serialize_state
from dosadi.state import WorldState
from dosadi.world.factions import Faction, FactionSystemConfig, FactionTerritory, export_factions_seed


def _basic_world() -> WorldState:
    world = WorldState()
    world.faction_cfg.enabled = True
    world.risk_ledger.edges["edge:a"] = EdgeRiskRecord(edge_key="edge:a", risk=0.8)
    world.risk_ledger.edges["edge:b"] = EdgeRiskRecord(edge_key="edge:b", risk=0.3)
    world.factions = {
        "fac:state": Faction(faction_id="fac:state", name="Ward Council", kind="STATE"),
        "fac:raiders": Faction(faction_id="fac:raiders", name="Roving Raiders", kind="RAIDERS"),
    }
    return world


def test_deterministic_actions_across_runs() -> None:
    world_a = _basic_world()
    world_b = copy.deepcopy(world_a)

    run_real_factions_for_day(world_a, day=1)
    run_real_factions_for_day(world_b, day=1)

    assert serialize_state(world_a.faction_territory) == serialize_state(world_b.faction_territory)
    assert serialize_state(world_a.faction_state) == serialize_state(world_b.faction_state)


def test_action_caps_and_claim_caps() -> None:
    world = _basic_world()
    world.faction_cfg.max_actions_per_faction_per_day = 1
    world.faction_cfg.max_claims_per_faction = 1
    world.risk_ledger.edges["edge:c"] = EdgeRiskRecord(edge_key="edge:c", risk=0.9)
    run_real_factions_for_day(world, day=1)

    assert world.faction_state.actions_taken_today["fac:state"] == 1
    territory = world.faction_territory["fac:state"]
    total_claims = len(territory.edges) + len(territory.wards) + len(territory.nodes)
    assert total_claims <= 1


def test_claims_change_on_success_and_failure() -> None:
    cfg = FactionSystemConfig(claim_gain_on_success=0.1, claim_loss_on_failure=0.05)
    faction = Faction(faction_id="fac:test", name="Test", kind="STATE")
    territory = FactionTerritory()
    world = WorldState()
    opp = Opportunity(kind="edge", target_id="edge:z", value=0.7)

    _apply_outcome(
        faction=faction,
        territory=territory,
        opportunity=opp,
        success=True,
        cfg=cfg,
        day=3,
        world=world,
    )
    assert territory.edges["edge:z"] == cfg.claim_gain_on_success

    _apply_outcome(
        faction=faction,
        territory=territory,
        opportunity=opp,
        success=False,
        cfg=cfg,
        day=4,
        world=world,
    )
    assert territory.edges["edge:z"] == cfg.claim_gain_on_success - cfg.claim_loss_on_failure


def test_snapshot_roundtrip_preserves_territory() -> None:
    world = _basic_world()
    run_real_factions_for_day(world, day=1)

    snapshot = serialize_state(world)

    restored = WorldState()
    restored.faction_cfg = FactionSystemConfig(**snapshot["faction_cfg"])
    restored.faction_state = copy.deepcopy(world.faction_state)
    restored.risk_ledger = copy.deepcopy(world.risk_ledger)
    restored.wards = copy.deepcopy(world.wards)
    restored.faction_territory = {
        key: FactionTerritory(
            wards=dict(val.get("wards", {})),
            edges=dict(val.get("edges", {})),
            nodes=dict(val.get("nodes", {})),
            last_claim_day=dict(snapshot.get("faction_territory", {}).get(key, {}).get("last_claim_day", {})),
        )
        for key, val in snapshot.get("faction_territory", {}).items()
    }
    restored.factions = copy.deepcopy(world.factions)

    run_real_factions_for_day(world, day=2)
    run_real_factions_for_day(restored, day=2)

    assert serialize_state(world.faction_territory) == serialize_state(restored.faction_territory)


def test_seed_vault_export_sorted_and_stable() -> None:
    world = WorldState()
    world.factions = {
        "fac:b": Faction(faction_id="fac:b", name="B", kind="STATE"),
        "fac:a": Faction(faction_id="fac:a", name="A", kind="RAIDERS"),
    }
    world.faction_territory = {
        "fac:b": FactionTerritory(edges={"edge:2": 0.3, "edge:1": 0.1}),
        "fac:a": FactionTerritory(wards={"ward:2": 0.5}),
    }

    export = export_factions_seed(world)
    assert [entry["faction_id"] for entry in export] == ["fac:a", "fac:b"]
    assert export[1]["territory"]["edges"] == {"edge:1": 0.1, "edge:2": 0.3}


def test_enforcement_pressure_reduces_raider_success() -> None:
    world = _basic_world()
    world.faction_cfg.deterministic_salt = "enforcement"
    cfg = ensure_enforcement_config(world)
    cfg.enabled = True
    world.enf_state_by_ward = {"": WardSecurityState(ward_id="", patrol_edges={"edge:a": 3})}

    base_prob = _success_probability(world.factions["fac:raiders"], Opportunity(kind="edge", target_id="edge:a", value=0.8), world)
    cfg.enabled = False
    easier_prob = _success_probability(world.factions["fac:raiders"], Opportunity(kind="edge", target_id="edge:a", value=0.8), world)

    assert base_prob < easier_prob

    cfg.enabled = True
    run_real_factions_for_day(world, day=1)
    territory = world.faction_territory["fac:raiders"]
    strong_claim = territory.edges.get("edge:a", 0.0)

    world2 = _basic_world()
    world2.faction_cfg.deterministic_salt = "enforcement"
    run_real_factions_for_day(world2, day=1)
    stronger_claim = world2.faction_territory["fac:raiders"].edges.get("edge:a", 0.0)

    assert strong_claim <= stronger_claim

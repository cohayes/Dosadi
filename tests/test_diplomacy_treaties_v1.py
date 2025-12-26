from types import SimpleNamespace

from dosadi.runtime.corridor_risk import CorridorRiskLedger
from dosadi.runtime.diplomacy_treaties import (
    DiplomacyConfig,
    Treaty,
    ensure_diplomacy_config,
    ensure_diplomacy_ledger,
    run_diplomacy_and_treaties,
)
from dosadi.world.factions import Faction, ensure_faction_territory


def _world_with_factions() -> SimpleNamespace:
    world = SimpleNamespace()
    world.factions = {
        "ward:alpha": Faction(faction_id="ward:alpha", name="Alpha", kind="ward", budget_points=25.0),
        "ward:beta": Faction(faction_id="ward:beta", name="Beta", kind="ward", budget_points=6.0),
    }
    ensure_faction_territory(world, "ward:alpha").edges["edge:alpha:beta"] = 0.4
    ensure_faction_territory(world, "ward:beta").edges["edge:alpha:beta"] = 0.5
    world.risk_cfg = SimpleNamespace(enabled=True)
    ledger = CorridorRiskLedger()
    rec = ledger.record("edge:alpha:beta", hazard_prior=0.2)
    rec.risk = 0.72
    world.risk_ledger = ledger
    return world


def test_corridor_stabilization_treaty_created_when_enabled():
    world = _world_with_factions()
    cfg = ensure_diplomacy_config(world)
    cfg.enabled = True
    cfg.max_active_treaties = 2
    run_diplomacy_and_treaties(world, day=10)

    ledger = ensure_diplomacy_ledger(world)
    assert ledger.active_treaties, "expected at least one active treaty"
    kinds = [(cl.kind, cl.scope) for t in ledger.active_treaties for cl in t.clauses]
    assert ("corridor_stabilization", "edge:alpha:beta") in kinds


def test_resource_sharing_treaty_created_for_budget_gap():
    world = _world_with_factions()
    cfg: DiplomacyConfig = ensure_diplomacy_config(world)
    cfg.enabled = True
    cfg.min_budget_gap_for_sharing = 4.0
    run_diplomacy_and_treaties(world, day=12)

    ledger = ensure_diplomacy_ledger(world)
    kinds = [clause.kind for t in ledger.active_treaties for clause in t.clauses]
    assert "resource_sharing" in kinds


def test_deterministic_signature_with_repeat_runs():
    world = _world_with_factions()
    cfg = ensure_diplomacy_config(world)
    cfg.enabled = True
    run_diplomacy_and_treaties(world, day=5)
    sig1 = ensure_diplomacy_ledger(world).signature()

    # Running again on the same day should not duplicate treaties
    run_diplomacy_and_treaties(world, day=5)
    sig2 = ensure_diplomacy_ledger(world).signature()

    assert sig1 == sig2


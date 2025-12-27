import pytest

from dosadi.runtime import market_signals
from dosadi.runtime.market_signals import MarketSignalsState, run_market_signals_for_day
from dosadi.runtime.trade_federations import (
    CartelAgreement,
    CartelCompliance,
    FederationConfig,
    run_federations_update,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.telemetry import Metrics
from dosadi.state import FactionState, WorldState
from dosadi.world.phases import WorldPhase


def _base_world() -> WorldState:
    world = WorldState(seed=7)
    world.metrics = Metrics()
    world.market_cfg.enabled = True
    world.market_state = MarketSignalsState()
    world.phase_state.phase = WorldPhase.PHASE2
    world.fed_cfg = FederationConfig(
        enabled=True,
        formation_rate_base=0.8,
        cartelization_rate_p2=0.9,
        update_cadence_days=1,
        enforcement_strength=0.4,
        defection_rate_base=0.12,
    )
    world.factions = {
        "fac:a": FactionState(id="fac:a", name="Alpha", archetype="GUILD", home_ward="ward:1", members=["a1", "a2"]),
        "fac:b": FactionState(id="fac:b", name="Beta", archetype="GUILD", home_ward="ward:2", members=["b1", "b2", "b3"]),
    }
    return world


def test_deterministic_formation_and_cartels():
    world_a = _base_world()
    world_b = _base_world()

    run_federations_update(world_a, day=14)
    run_federations_update(world_b, day=14)

    signature_a = (
        sorted(world_a.federations.keys()),
        sorted(world_a.cartels.keys()),
    )
    signature_b = (
        sorted(world_b.federations.keys()),
        sorted(world_b.cartels.keys()),
    )

    assert signature_a == signature_b


def test_cartel_price_floor_increases_market_signal(monkeypatch: pytest.MonkeyPatch):
    world = _base_world()
    world.cartels["cartel:water:1"] = CartelAgreement(
        cartel_id="cartel:water:1",
        fed_id=None,
        goods=["WATER"],
        kind="PRICE_FLOOR",
        members=list(world.factions.keys()),
        target_price_mult=1.8,
        quota_by_member={},
        start_day=0,
        end_day=30,
        status="ACTIVE",
    )

    baseline = _base_world()

    monkeypatch.setattr(market_signals, "_construction_demand", lambda *_args, **_kwargs: {"WATER": 10.0})
    monkeypatch.setattr(market_signals, "_production_supply", lambda *_args, **_kwargs: {"WATER": 10.0})
    monkeypatch.setattr(market_signals, "_stockpile_demand", lambda *_args, **_kwargs: {})

    run_market_signals_for_day(baseline, day=0)
    run_market_signals_for_day(world, day=0)

    base_signal = baseline.market_state.global_signals["WATER"].urgency
    cartel_signal = world.market_state.global_signals["WATER"].urgency
    assert cartel_signal > base_signal


def test_quotas_reduce_supply_and_raise_urgency(monkeypatch: pytest.MonkeyPatch):
    world = _base_world()
    world.cartels["cartel:water:2"] = CartelAgreement(
        cartel_id="cartel:water:2",
        fed_id=None,
        goods=["WATER"],
        kind="QUOTA_ALLOCATION",
        members=list(world.factions.keys()),
        target_price_mult=1.0,
        quota_by_member={"fac:a": 0.2, "fac:b": 0.2},
        hoard_target_days=14,
        start_day=0,
        end_day=30,
        status="ACTIVE",
    )

    baseline = _base_world()

    monkeypatch.setattr(market_signals, "_construction_demand", lambda *_args, **_kwargs: {"WATER": 8.0})
    monkeypatch.setattr(market_signals, "_production_supply", lambda *_args, **_kwargs: {"WATER": 10.0})
    monkeypatch.setattr(market_signals, "_stockpile_demand", lambda *_args, **_kwargs: {})

    run_market_signals_for_day(baseline, day=1)
    run_market_signals_for_day(world, day=1)

    base_signal = baseline.market_state.global_signals["WATER"].urgency
    cartel_signal = world.market_state.global_signals["WATER"].urgency
    assert cartel_signal > base_signal


def test_cheating_breaks_cartel():
    world = _base_world()
    world.fed_cfg.enforcement_strength = 0.05
    world.fed_cfg.defection_rate_base = 0.4
    cartel = CartelAgreement(
        cartel_id="cartel:test:1",
        fed_id=None,
        goods=["WATER"],
        kind="PRICE_FLOOR",
        members=["fac:a"],
        target_price_mult=2.5,
        quota_by_member={"fac:a": 0.1},
        enforcement_mode="SOFT",
        start_day=0,
        end_day=10,
        status="ACTIVE",
    )
    world.cartels[cartel.cartel_id] = cartel

    run_federations_update(world, day=0)
    run_federations_update(world, day=2)
    run_federations_update(world, day=4)

    assert cartel.status == "BROKEN"


def test_stronger_enforcement_reduces_cheating():
    weak = _base_world()
    strong = _base_world()
    weak.fed_cfg.enforcement_strength = 0.1
    strong.fed_cfg.enforcement_strength = 0.9
    for target in (weak, strong):
        target.fed_cfg.defection_rate_base = 0.25
        target.cartels["cartel:test:2"] = CartelAgreement(
            cartel_id="cartel:test:2",
            fed_id=None,
            goods=["WATER"],
            kind="PRICE_FLOOR",
            members=["fac:a"],
            target_price_mult=1.6,
            quota_by_member={"fac:a": 0.2},
            enforcement_mode="CUSTOMS",
            start_day=0,
            end_day=12,
            status="ACTIVE",
        )
        run_federations_update(target, day=0)
        run_federations_update(target, day=1)

    weak_entry: CartelCompliance | None = weak.cartel_compliance.get(("cartel:test:2", "fac:a"))
    strong_entry: CartelCompliance | None = strong.cartel_compliance.get(("cartel:test:2", "fac:a"))

    assert weak_entry is not None and strong_entry is not None
    assert strong_entry.cheat_score < weak_entry.cheat_score


def test_snapshot_roundtrip_preserves_trade_state():
    world = _base_world()
    run_federations_update(world, day=2)
    world.cartels["cartel:snapshot:1"] = CartelAgreement(
        cartel_id="cartel:snapshot:1",
        fed_id=None,
        goods=["WATER"],
        kind="STOCKPILE_HOARDING",
        members=list(world.factions.keys()),
        target_price_mult=1.2,
        quota_by_member={"fac:a": 0.3, "fac:b": 0.3},
        hoard_target_days=21,
        start_day=2,
        end_day=14,
        status="ACTIVE",
    )

    snapshot = snapshot_world(world, scenario_id="test")
    restored = restore_world(snapshot)

    assert set(restored.federations.keys()) == set(world.federations.keys())
    assert set(restored.cartels.keys()) == set(world.cartels.keys())


import statistics

import pytest

from dosadi.worldgen import WorldgenConfig, generate_world


@pytest.mark.doc("D-WORLD-0004")
def test_ring_distribution_and_policy_matches_design():
    world = generate_world(WorldgenConfig())
    ring_counts = {label: 0 for label in ("inner", "middle", "outer")}
    for ward in world.wards.values():
        ring_counts[ward.ring_label] += 1
    assert ring_counts == {"inner": 6, "middle": 12, "outer": 18}
    assert world.policy["tax_rate"] == pytest.approx(0.10)
    assert world.policy["min_rotation_floor_pct"] == pytest.approx(0.005)
    assert world.policy["well_location"] == "center-valley"

    stress_by_ring = {
        ring: statistics.mean(
            world.wards[ward.id].environment.stress for ward in wards
        )
        for ring, wards in (
            ("inner", [w for w in world.wards.values() if w.ring_label == "inner"]),
            ("middle", [w for w in world.wards.values() if w.ring_label == "middle"]),
            ("outer", [w for w in world.wards.values() if w.ring_label == "outer"]),
        )
    }
    assert stress_by_ring["inner"] < stress_by_ring["middle"] < stress_by_ring["outer"]


@pytest.mark.doc("D-WORLD-0004")
def test_route_network_contains_royal_spokes_and_smuggle_tunnels():
    cfg = WorldgenConfig()
    world = generate_world(cfg)
    smuggle_routes = [r for r in world.routes.values() if r.route_type == "SMUGGLE"]
    assert len(smuggle_routes) == cfg.smuggle_tunnels * 2
    royal_routes = [r for r in world.routes.values() if r.route_type == "ROYAL" and r.origin == "ward:1"]
    inner_and_middle = [w.id for w in world.wards.values() if w.ring_label in {"inner", "middle"}]
    assert {r.destination for r in royal_routes} >= set(inner_and_middle) - {"ward:1"}


@pytest.mark.doc("D-WORLD-0004")
def test_faction_specialisations_cover_food_power_and_repair():
    world = generate_world(WorldgenConfig(seed=8128))
    required = {"food", "power", "suit"}
    for ward in world.wards.values():
        specs = set(ward.specialisations)
        assert required <= specs
        assert world.factions[ward.governor_faction].archetype == "GOVERNOR"

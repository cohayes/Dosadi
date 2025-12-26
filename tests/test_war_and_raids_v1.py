from __future__ import annotations

import copy
import random
from types import SimpleNamespace

from dosadi.runtime.crackdown import CrackdownTarget
from dosadi.runtime.ledger import get_or_create_account
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.runtime.war import (
    RaidPlan,
    WarConfig,
    deterministic_roll,
    run_war_for_day,
    success_probability,
)
from dosadi.simulation.snapshots import serialize_state
from dosadi.state import WardState, WorldState
from dosadi.world.factions import Faction
from dosadi.world.routing import compute_route
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode, edge_key


def _basic_world() -> WorldState:
    world = WorldState()
    world.seed = 7
    world.rng = random.Random(world.seed)
    world.debug_cfg.level = "standard"
    world.war_cfg = WarConfig(enabled=True, deterministic_salt="war-test")

    nodes = {
        "node:a": SurveyNode(node_id="node:a", kind="corridor", ward_id="ward:a"),
        "node:b": SurveyNode(node_id="node:b", kind="corridor", ward_id="ward:a"),
        "node:c": SurveyNode(node_id="node:c", kind="corridor", ward_id="ward:b"),
        "node:d": SurveyNode(node_id="node:d", kind="corridor", ward_id="ward:a"),
    }
    edges = {
        "edge:ab": SurveyEdge(a="node:a", b="node:b", distance_m=1.0, travel_cost=1.0, hazard=0.1),
        "edge:bc": SurveyEdge(a="node:b", b="node:c", distance_m=1.0, travel_cost=1.0, hazard=0.2),
        "edge:ad": SurveyEdge(a="node:a", b="node:d", distance_m=2.0, travel_cost=2.0, hazard=0.05),
        "edge:dc": SurveyEdge(a="node:d", b="node:c", distance_m=2.0, travel_cost=2.0, hazard=0.05),
    }
    world.survey_map = SurveyMap(nodes=nodes, edges={edge.key: edge for edge in edges.values()})
    world.wards = {
        "ward:a": WardState(id="ward:a", name="A", ring=0, sealed_mode="open", legitimacy=0.4),
        "ward:b": WardState(id="ward:b", name="B", ring=0, sealed_mode="open", legitimacy=0.4),
    }
    world.factions = {
        "fac:state": Faction(faction_id="fac:state", name="State", kind="STATE"),
        "fac:raiders": Faction(faction_id="fac:raiders", name="Raiders", kind="RAIDERS"),
    }
    return world


def _guarantee_success(plan: RaidPlan, world: WorldState, day: int) -> RaidPlan:
    attempts = 0
    plan.intensity = min(1.0, plan.intensity)
    while attempts < 64:
        if deterministic_roll(world, plan, day) <= success_probability(world, plan):
            return plan
        attempts += 1
        if attempts == 32:
            plan.intensity = 1.0
        plan.op_id = f"{plan.op_id}:{attempts}"
    return plan


def _single_plan(target_key: str, *, day: int = 0, intensity: float = 1.0) -> RaidPlan:
    return RaidPlan(
        op_id="raid:test",
        aggressor_faction="fac:raiders",
        target_kind="corridor",
        target_id=target_key,
        start_day=day,
        end_day=day,
        intensity=intensity,
        objective="disrupt",
    )


def test_determinism_between_runs() -> None:
    world_a = _basic_world()
    world_b = copy.deepcopy(world_a)

    run_war_for_day(world_a, day=1)
    run_war_for_day(world_b, day=1)

    fields = [
        serialize_state(world_a.raid_history),
        serialize_state(world_a.corridor_stress),
        serialize_state(world_a.collapsed_corridors),
    ]
    fields_b = [
        serialize_state(world_b.raid_history),
        serialize_state(world_b.corridor_stress),
        serialize_state(world_b.collapsed_corridors),
    ]
    assert fields == fields_b


def test_corridor_stress_triggers_collapse() -> None:
    world = _basic_world()
    world.war_cfg.collapse_threshold = 0.1
    world.war_cfg.raid_stress_per_success = 0.2
    target = world.survey_map.edges[edge_key("node:a", "node:b")].key
    plan = _guarantee_success(_single_plan(target), world, day=0)
    world.raid_active = {plan.op_id: plan}

    run_war_for_day(world, day=0)

    assert world.raid_history[-1].status == "succeeded"
    assert world.corridor_stress[target] >= world.war_cfg.collapse_threshold
    assert target in world.collapsed_corridors
    assert world.survey_map.edges[target].closed_until_day is not None


def test_collapsed_corridor_is_rerouted() -> None:
    world = _basic_world()
    primary = world.survey_map.edges[edge_key("node:a", "node:b")].key
    route_before = compute_route(world, from_node="node:a", to_node="node:c")
    assert primary in route_before.edge_keys

    world.war_cfg.collapse_threshold = 0.1
    world.war_cfg.raid_stress_per_success = 0.2
    plan = _guarantee_success(_single_plan(primary), world, day=0)
    world.raid_active = {plan.op_id: plan}
    run_war_for_day(world, day=0)

    assert world.raid_history[-1].status == "succeeded"
    world.day = 1
    route_after = compute_route(world, from_node="node:a", to_node="node:c")
    assert primary not in route_after.edge_keys


def test_crackdown_reduces_success_probability() -> None:
    world = _basic_world()
    target = edge_key("node:a", "node:b")
    plan = _single_plan(target, intensity=0.6)
    base_prob = success_probability(world, plan)
    world.crackdown_active = {
        "cd:1": CrackdownTarget(
            kind="corridor", target_id=target, intensity=1.0, start_day=0, end_day=5, reason="test"
        )
    }
    reduced_prob = success_probability(world, plan)
    assert reduced_prob < base_prob


def test_treaty_breach_event_emitted() -> None:
    world = _basic_world()
    target = edge_key("node:a", "node:b")
    plan = _single_plan(target, intensity=0.7)
    base_prob = success_probability(world, plan)
    world.treaties = {"t1": SimpleNamespace(status="active", protected_edges={target})}
    penalized = success_probability(world, plan)
    assert penalized < base_prob

    plan = _guarantee_success(plan, world, day=0)
    world.raid_active = {plan.op_id: plan}
    run_war_for_day(world, day=0)

    events = getattr(world.event_ring, "events", [])
    assert any(evt.get("type") == "TREATY_BREACH" for evt in events)


def test_ledger_loot_transfers() -> None:
    world = _basic_world()
    world.ledger_cfg.enabled = True
    payer = get_or_create_account(world, "acct:ward:ward:a")
    payer.balance = 50.0
    receiver = get_or_create_account(world, "acct:fac:fac:raiders")
    receiver.balance = 0.0

    target = edge_key("node:a", "node:b")
    plan = _guarantee_success(_single_plan(target, intensity=1.0), world, day=0)
    plan.expected_loot = {"credits": 15.0}
    world.raid_active = {plan.op_id: plan}

    run_war_for_day(world, day=0)

    assert world.raid_history[-1].status == "succeeded"
    assert receiver.balance > 0.0
    assert payer.balance < 50.0


def test_snapshot_roundtrip_preserves_war_state() -> None:
    world = _basic_world()
    plan = _guarantee_success(_single_plan(edge_key("node:a", "node:b")), world, day=0)
    world.raid_active = {plan.op_id: plan}
    run_war_for_day(world, day=0)

    snapshot = snapshot_world(world, scenario_id="war-test")
    restored = restore_world(snapshot)

    run_war_for_day(world, day=1)
    run_war_for_day(restored, day=1)

    assert serialize_state(world.corridor_stress) == serialize_state(restored.corridor_stress)
    assert serialize_state(world.raid_history) == serialize_state(restored.raid_history)

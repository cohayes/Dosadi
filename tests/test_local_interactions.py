from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field

from dosadi.agent.memory_crumbs import CrumbStore
from dosadi.runtime.event_to_memory_router import RouterConfig, RouterState, run_router_for_day
from dosadi.runtime.local_interactions import (
    InteractionConfig,
    InteractionOpportunity,
    InteractionState,
    resolve_candidates,
    run_interactions_for_day,
)
from dosadi.runtime.snapshot import restore_world, snapshot_world
from dosadi.world.construction import ProjectLedger
from dosadi.world.events import WorldEventLog
from dosadi.world.facilities import FacilityLedger
from dosadi.world.logistics import DeliveryRequest, DeliveryStatus, LogisticsLedger
from dosadi.world.survey_map import SurveyEdge, SurveyMap
from dosadi.world.workforce import Assignment, AssignmentKind, WorkforceLedger, ensure_workforce


@dataclass
class StubAgent:
    agent_id: str
    location_id: str | None = None
    crumbs: CrumbStore = field(default_factory=CrumbStore)


@dataclass
class StubWorld:
    seed: int = 1
    tick: int = 0
    day: int = 0
    rng: random.Random = field(default_factory=lambda: random.Random(1))
    agents: dict[str, StubAgent] = field(default_factory=dict)
    workforce: WorkforceLedger = field(default_factory=WorkforceLedger)
    logistics: LogisticsLedger = field(default_factory=LogisticsLedger)
    delivery_due_queue: list[tuple[int, str]] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    event_log: WorldEventLog = field(default_factory=lambda: WorldEventLog(max_len=100))
    router_config: RouterConfig = field(default_factory=RouterConfig)
    router_state: RouterState = field(default_factory=RouterState)
    survey_map: SurveyMap = field(default_factory=SurveyMap)
    interaction_cfg: InteractionConfig = field(default_factory=InteractionConfig)
    interaction_state: InteractionState = field(default_factory=InteractionState)
    interaction_queue: list = field(default_factory=list)
    projects: ProjectLedger = field(default_factory=ProjectLedger)
    facilities: FacilityLedger = field(default_factory=FacilityLedger)


def _add_delivery(world: StubWorld, delivery_id: str = "delivery:test") -> DeliveryRequest:
    delivery = DeliveryRequest(
        delivery_id=delivery_id,
        project_id="project:1",
        origin_node_id="n1",
        dest_node_id="n2",
        items={"water": 5.0},
        status=DeliveryStatus.IN_TRANSIT,
        created_tick=0,
    )
    delivery.remaining_edge_ticks = 10
    delivery.next_edge_complete_tick = 50
    delivery.deliver_tick = 100
    delivery.route_nodes = ["n1", "n2"]
    delivery.route_edge_keys = ["n1|n2"]
    world.logistics.add(delivery)
    world.delivery_due_queue.append((delivery.next_edge_complete_tick, delivery.delivery_id))
    return delivery


def test_flag_off_no_change() -> None:
    world = StubWorld()
    world.interaction_cfg.enabled = False
    delivery = _add_delivery(world)
    opp = InteractionOpportunity(
        day=0,
        tick=0,
        kind="courier_edge",
        node_id="n2",
        edge_key="n1|n2",
        primary_agent_id=None,
        subject_id=delivery.delivery_id,
    )
    world.interaction_queue.append(opp)

    run_interactions_for_day(world, day=0)

    assert world.event_log.events == []
    assert world.delivery_due_queue[0][0] == 50
    assert world.logistics.deliveries[delivery.delivery_id].status is DeliveryStatus.IN_TRANSIT


def test_deterministic_outcomes() -> None:
    world = StubWorld()
    world.interaction_cfg.enabled = True
    delivery = _add_delivery(world)
    opp = InteractionOpportunity(
        day=0,
        tick=10,
        kind="courier_edge",
        node_id="n2",
        edge_key="n1|n2",
        primary_agent_id="agent:1",
        subject_id=delivery.delivery_id,
    )
    world.interaction_queue.append(opp)

    world_copy = copy.deepcopy(world)

    run_interactions_for_day(world, day=0)
    run_interactions_for_day(world_copy, day=0)

    payloads = [evt.payload for evt in world.event_log.events]
    payloads_copy = [evt.payload for evt in world_copy.event_log.events]
    assert payloads == payloads_copy


def test_bounded_candidates() -> None:
    world = StubWorld()
    world.interaction_cfg.enabled = True
    world.interaction_cfg.max_candidates_per_opportunity = 3
    for idx in range(6):
        world.agents[f"agent:{idx}"] = StubAgent(agent_id=f"agent:{idx}", location_id="loc:1")
    opp = InteractionOpportunity(
        day=0,
        tick=0,
        kind="project_site",
        node_id="loc:1",
        edge_key=None,
        primary_agent_id=None,
        subject_id="proj:1",
    )

    candidates = resolve_candidates(world, opp, world.interaction_cfg)

    assert len(candidates) == world.interaction_cfg.max_candidates_per_opportunity
    assert candidates == sorted(candidates)


def test_delay_application_updates_queue() -> None:
    world = StubWorld()
    delivery = _add_delivery(world, "delivery:delay")

    from dosadi.runtime.local_interactions import _apply_delivery_delay

    _apply_delivery_delay(world, delivery.delivery_id, 25)

    updated = world.logistics.deliveries[delivery.delivery_id]
    assert updated.next_edge_complete_tick == 75
    assert (75, delivery.delivery_id) in world.delivery_due_queue
    assert updated.deliver_tick == 125


def test_failure_releases_courier() -> None:
    world = StubWorld()
    world.interaction_cfg.enabled = True
    delivery = _add_delivery(world, "delivery:fail")
    carrier_id = "agent:fail"
    delivery.assigned_carrier_id = carrier_id
    ledger = ensure_workforce(world)
    ledger.assign(
        Assignment(
            agent_id=carrier_id,
            kind=AssignmentKind.LOGISTICS_COURIER,
            target_id=delivery.delivery_id,
            start_day=0,
        )
    )
    world.delivery_due_queue.append((delivery.next_edge_complete_tick or 0, delivery.delivery_id))

    from dosadi.runtime.local_interactions import _fail_delivery

    _fail_delivery(world, delivery.delivery_id, tick=0, reason="interaction")

    assert ledger.is_idle(carrier_id)
    assert not world.delivery_due_queue
    assert world.logistics.deliveries[delivery.delivery_id].status is DeliveryStatus.FAILED


def test_router_integration_creates_route_risk_crumbs(monkeypatch) -> None:
    world = StubWorld()
    world.interaction_cfg.enabled = True
    world.router_config.enabled = True
    delivery = _add_delivery(world, "delivery:router")
    delivery.assigned_carrier_id = "agent:router"
    world.agents["agent:router"] = StubAgent(agent_id="agent:router", location_id="n1")
    ledger = ensure_workforce(world)
    ledger.assign(
        Assignment(
            agent_id="agent:router",
            kind=AssignmentKind.LOGISTICS_COURIER,
            target_id=delivery.delivery_id,
            start_day=0,
        )
    )

    def _fixed_draw(*_: str) -> float:
        return 0.05

    monkeypatch.setattr("dosadi.runtime.local_interactions.hashed_unit_float", _fixed_draw)

    opp = InteractionOpportunity(
        day=0,
        tick=0,
        kind="courier_edge",
        node_id="n2",
        edge_key="n1|n2",
        primary_agent_id=delivery.assigned_carrier_id,
        subject_id=delivery.delivery_id,
    )
    world.interaction_queue.append(opp)
    world.survey_map.edges["n1|n2"] = SurveyEdge(a="n1", b="n2", distance_m=1.0, travel_cost=1.0, hazard=0.2)

    run_interactions_for_day(world, day=0)
    assert world.event_log.events
    assert world.event_log.events[-1].payload.get("interaction_kind") == "SABOTAGE"
    run_router_for_day(world, day=0)

    crumbs = world.agents["agent:router"].crumbs
    assert "route-risk:n1|n2" in crumbs.tags
    assert "delivery-fail:delivery:router" in crumbs.tags


def test_snapshot_roundtrip_preserves_opportunities() -> None:
    world = StubWorld()
    world.interaction_cfg.enabled = True
    _add_delivery(world, "delivery:snapshot")
    opp = InteractionOpportunity(
        day=0,
        tick=5,
        kind="courier_edge",
        node_id="n2",
        edge_key="n1|n2",
        primary_agent_id=None,
        subject_id="delivery:snapshot",
    )
    world.interaction_queue.append(opp)

    snapshot = snapshot_world(world, scenario_id="test")
    restored = restore_world(snapshot)

    run_interactions_for_day(world, day=0)
    run_interactions_for_day(restored, day=0)

    original_payloads = [evt.payload for evt in getattr(world, "event_log", WorldEventLog(10)).events]
    restored_payloads = [evt.payload for evt in getattr(restored, "event_log", WorldEventLog(10)).events]
    assert original_payloads == restored_payloads

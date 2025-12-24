from __future__ import annotations

import random
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Sequence

from dosadi.agents.core import AgentState
from dosadi.runtime.scouting_config import ScoutConfig
from dosadi.world.discovery import DiscoveryConfig, expand_frontier
from dosadi.world.survey_map import SurveyEdge, SurveyMap, SurveyNode, edge_key
from dosadi.world.scout_missions import (
    MissionIntent,
    MissionStatus,
    ScoutMission,
    ScoutMissionLedger,
    ensure_scout_missions,
)


@dataclass(slots=True)
class TravelOutcome:
    next_node_id: str
    created_node: SurveyNode | None
    created_edge: SurveyEdge | None
    discovery: dict[str, object] | None


def rng_for(mission_id: str, day: int, world_seed: int) -> random.Random:
    digest = sha256(f"{world_seed}:{mission_id}:{day}".encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big")
    return random.Random(seed)


def _day_to_tick(world, day: int) -> int:
    ticks_per_day = getattr(world, "ticks_per_day", None)
    if ticks_per_day is None:
        ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", 144_000)
    try:
        ticks_per_day = int(ticks_per_day)
    except (TypeError, ValueError):
        ticks_per_day = 144_000
    return max(0, int(day) * max(1, ticks_per_day))


def _select_party(world, *, day: int, cfg: ScoutConfig) -> list[str]:
    agent_ids = sorted(getattr(world, "agents", {}).keys())
    party: list[str] = []
    for agent_id in agent_ids:
        agent: AgentState = world.agents[agent_id]
        if getattr(agent, "is_on_mission", False):
            continue
        last_day = getattr(agent, "last_scout_day", -cfg.allow_reuse_agent_days)
        if last_day >= 0 and day - last_day < cfg.allow_reuse_agent_days:
            continue
        party.append(agent_id)
        if len(party) >= cfg.party_size:
            break
    return party


def _derive_node_id(mission_id: str, day: int, survey: SurveyMap) -> str:
    salt = 0
    while True:
        base = f"{mission_id}:{day}:{salt}" if salt else f"{mission_id}:{day}"
        digest = sha256(base.encode("utf-8")).hexdigest()
        candidate = f"loc:auto:{digest[:12]}"
        if candidate not in survey.nodes:
            return candidate
        salt += 1


def _choose_neighbor(current_node_id: str, survey: SurveyMap, rng: random.Random) -> str | None:
    neighbors: list[str] = []
    for key, edge in survey.edges.items():
        if current_node_id not in key:
            continue
        if edge.a == current_node_id:
            neighbors.append(edge.b)
        elif edge.b == current_node_id:
            neighbors.append(edge.a)
    if not neighbors:
        return None
    neighbors.sort()
    return neighbors[int(rng.random() * len(neighbors))]


def _create_edge(
    current_node_id: str,
    new_node_id: str,
    rng: random.Random,
    *,
    tick: int,
    cfg: ScoutConfig,
) -> SurveyEdge:
    distance = rng.uniform(50.0, 500.0)
    return SurveyEdge(
        a=current_node_id,
        b=new_node_id,
        distance_m=distance,
        travel_cost=distance,
        hazard=0.0,
        confidence=cfg.confidence_new_node,
        last_seen_tick=tick,
    )


def _advance_mission(
    world,
    mission: ScoutMission,
    survey: SurveyMap,
    *,
    day: int,
    cfg: ScoutConfig,
    rng: random.Random,
    discovery_cfg: DiscoveryConfig,
) -> TravelOutcome:
    tick = _day_to_tick(world, day)
    discovery: dict[str, object] | None = None
    created_node: SurveyNode | None = None
    created_edge: SurveyEdge | None = None
    next_node_id = mission.current_node_id

    if discovery_cfg.enabled:
        node_budget = min(mission.discovery_budget_nodes, discovery_cfg.max_new_nodes_per_day)
        edge_budget = min(mission.discovery_budget_edges, discovery_cfg.max_new_edges_per_day)
        new_nodes = expand_frontier(
            world,
            from_node=mission.current_node_id,
            budget_nodes=node_budget,
            budget_edges=edge_budget,
            day=day,
            mission_id=mission.mission_id,
            cfg=discovery_cfg,
        )
        if new_nodes:
            next_node_id = new_nodes[0]
            created_node = survey.nodes.get(next_node_id)
            created_edge = survey.edges.get(edge_key(mission.current_node_id, next_node_id))
            discovery = {
                "day": day,
                "kind": "DISCOVERY_NODE",
                "node_id": next_node_id,
                "from": mission.current_node_id,
                "confidence": getattr(created_node, "confidence", 0.0),
                "tags": list(getattr(created_node, "resource_tags", ())),
            }
            mission.discovery_budget_nodes = max(0, mission.discovery_budget_nodes - len(new_nodes))
            mission.discovery_budget_edges = max(0, mission.discovery_budget_edges - len(new_nodes))
            mission.discovered_nodes.extend(new_nodes)
            if created_edge:
                mission.discovered_edges.append(created_edge.key)
    else:
        neighbor = _choose_neighbor(mission.current_node_id, survey, rng)
        if neighbor and rng.random() < cfg.new_edge_chance:
            next_node_id = neighbor
        else:
            next_node_id = mission.current_node_id
    return TravelOutcome(
        next_node_id=next_node_id,
        created_node=created_node,
        created_edge=created_edge,
        discovery=discovery,
    )


def _mark_agents(world, mission: ScoutMission, *, on_mission: bool, day: int) -> None:
    for agent_id in mission.party_agent_ids:
        agent: AgentState | None = getattr(world, "agents", {}).get(agent_id)
        if agent is None:
            continue
        agent.is_on_mission = on_mission
        agent.last_scout_day = day


def maybe_create_scout_missions(world, cfg: ScoutConfig | None = None) -> list[str]:
    cfg = cfg or getattr(world, "scout_cfg", None) or ScoutConfig()
    world.scout_cfg = cfg
    discovery_cfg: DiscoveryConfig = getattr(world, "discovery_cfg", None) or DiscoveryConfig()
    world.discovery_cfg = discovery_cfg
    ledger = ensure_scout_missions(world)
    survey: SurveyMap = getattr(world, "survey_map", SurveyMap())
    day = getattr(world, "day", 0)

    if len(ledger.active_ids) >= cfg.max_active_missions:
        return []

    origin_node_id = None
    if "loc:well-core" in survey.nodes:
        origin_node_id = "loc:well-core"
    elif survey.nodes:
        origin_node_id = sorted(survey.nodes.keys())[0]

    if origin_node_id is None:
        return []

    created: list[str] = []
    while len(ledger.active_ids) < cfg.max_active_missions:
        party = _select_party(world, day=day, cfg=cfg)
        if not party:
            break

        world.next_mission_seq = getattr(world, "next_mission_seq", 0) + 1
        mission_id = f"scout:{day}:{world.next_mission_seq}"
        heading = rng_for(mission_id, day, getattr(world, "seed", 0)).uniform(0.0, 360.0)

        mission = ScoutMission(
            mission_id=mission_id,
            status=MissionStatus.EN_ROUTE,
            intent=MissionIntent.RADIAL,
            origin_node_id=origin_node_id,
            current_node_id=origin_node_id,
            target_node_id=None,
            heading_deg=heading,
            max_days=cfg.max_days_per_mission,
            party_agent_ids=list(party),
            supplies={},
            risk_budget=0.5,
            start_day=day,
            last_step_day=day - 1,
            days_elapsed=0,
            discoveries=[],
            discovery_budget_nodes=discovery_cfg.max_frontier_expansions_per_mission,
            discovery_budget_edges=discovery_cfg.max_new_edges_per_day,
        )

        ledger.add(mission)
        _mark_agents(world, mission, on_mission=True, day=day)
        created.append(mission_id)

    return created


def _fail_probability(mission: ScoutMission, survey: SurveyMap, cfg: ScoutConfig) -> float:
    current_node = survey.nodes.get(mission.current_node_id)
    hazard = current_node.hazard if current_node else 0.0
    return cfg.base_fail_chance * (1.0 + cfg.hazard_fail_multiplier * hazard)


def _finalize_mission(
    ledger: ScoutMissionLedger,
    mission: ScoutMission,
    *,
    status: MissionStatus,
    day: int,
    world,
) -> None:
    mission.status = status
    if mission.mission_id in ledger.active_ids:
        ledger.active_ids.remove(mission.mission_id)
    _mark_agents(world, mission, on_mission=False, day=day)


def step_scout_missions_for_day(world, day: int | None = None, cfg: ScoutConfig | None = None) -> None:
    cfg = cfg or getattr(world, "scout_cfg", None) or ScoutConfig()
    world.scout_cfg = cfg
    discovery_cfg: DiscoveryConfig = getattr(world, "discovery_cfg", None) or DiscoveryConfig()
    world.discovery_cfg = discovery_cfg
    ledger = ensure_scout_missions(world)
    survey: SurveyMap = getattr(world, "survey_map", SurveyMap())
    day = getattr(world, "day", 0) if day is None else day

    for mission_id in list(sorted(ledger.active_ids)):
        mission = ledger.missions.get(mission_id)
        if mission is None:
            continue
        if day <= mission.last_step_day:
            continue

        mission.days_elapsed += 1
        mission.last_step_day = day

        rng = rng_for(mission.mission_id, day, getattr(world, "seed", 0))
        outcome = _advance_mission(
            world,
            mission,
            survey,
            day=day,
            cfg=cfg,
            rng=rng,
            discovery_cfg=discovery_cfg,
        )
        mission.current_node_id = outcome.next_node_id
        if outcome.discovery:
            mission.discoveries.append(dict(outcome.discovery))

        fail_probability = _fail_probability(mission, survey, cfg)
        if rng.random() < fail_probability:
            _finalize_mission(ledger, mission, status=MissionStatus.FAILED, day=day, world=world)
            continue

        if mission.days_elapsed >= mission.max_days:
            _finalize_mission(
                ledger,
                mission,
                status=MissionStatus.COMPLETE,
                day=day,
                world=world,
            )


__all__ = [
    "maybe_create_scout_missions",
    "rng_for",
    "step_scout_missions_for_day",
]

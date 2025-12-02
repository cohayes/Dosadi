from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

from dosadi.agents.core import AgentState, PlaceBelief
from dosadi.state import WorldState


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _get_place_belief(agent: AgentState, place_id: str) -> PlaceBelief | None:
    return agent.place_beliefs.get(place_id)


def _estimate_distance_norm(world: WorldState, agent: AgentState, facility_id: str) -> float:
    """
    MVP distance heuristic in [0, 1].

    TODO: replace with real path distance when available.
    """
    facility = world.facilities.get(facility_id) if hasattr(world, "facilities") else None
    if facility is not None and getattr(facility, "location_id", None) == agent.location_id:
        return 0.0

    return 0.5


def choose_facility_for_service(
    agent: AgentState,
    service_type: str,
    world: WorldState,
    rng: random.Random,
) -> Optional[str]:
    """
    Return the facility_id that this agent chooses for the given service_type,
    or None if no facility offers that service.

    Implements D-RUNTIME-0208 Belief_Guided_Facility_Selection_MVP.
    """
    candidates = world.service_facilities.get(service_type, [])
    if not candidates:
        return None

    w_rel = 0.5
    w_fair = 0.4
    w_eff = 0.3
    w_safe = 0.3
    w_cong = 0.2
    w_dist = 0.5

    personality = getattr(agent, "personality", None)
    caution = getattr(personality, "caution_vs_bravery", 0.0) if personality else 0.0
    curiosity = getattr(personality, "curiosity_vs_routine", 0.0) if personality else 0.0

    w_safe_eff = w_safe * (1.0 + 0.2 * caution)
    w_cong_eff = w_cong * (1.0 + 0.2 * caution)

    epsilon_base = 0.1
    epsilon = epsilon_base * (1.0 + 0.5 * curiosity)
    epsilon = max(0.01, min(0.3, epsilon))

    last_by_service = getattr(agent, "last_facility_by_service", None)
    if last_by_service is None:
        agent.last_facility_by_service = {}
        last_by_service = agent.last_facility_by_service
    last_used_for_service = last_by_service.get(service_type)

    scored: List[Tuple[str, float]] = []

    for facility_id in candidates:
        place_id = facility_id

        pb = _get_place_belief(agent, place_id)
        if pb is None:
            fair = eff = safe = cong = rel = 0.0
        else:
            fair = pb.fairness_score
            eff = pb.efficiency_score
            safe = pb.safety_score
            cong = pb.congestion_score
            rel = pb.reliability_score

        U_belief = (
            w_rel * rel
            + w_fair * fair
            + w_eff * eff
            + w_safe_eff * safe
            - w_cong_eff * max(0.0, cong)
        )

        d_norm = _estimate_distance_norm(world, agent, facility_id)
        U_cost = -w_dist * _clamp01(d_norm)

        U = U_belief + U_cost

        if curiosity < 0.0 and last_used_for_service == facility_id:
            U += 0.1

        scored.append((facility_id, U))

    if scored and rng.random() < epsilon:
        max_u = max(u for _, u in scored)
        exp_scores = [math.exp(u - max_u) for _, u in scored]
        total = sum(exp_scores)
        if total <= 0:
            chosen_id = rng.choice([fid for fid, _ in scored])
        else:
            r = rng.random() * total
            acc = 0.0
            chosen_id = scored[-1][0]
            for (fid, _), e in zip(scored, exp_scores):
                acc += e
                if r <= acc:
                    chosen_id = fid
                    break
    else:
        max_u = max(u for _, u in scored)
        best = [fid for fid, u in scored if u == max_u]
        chosen_id = rng.choice(best)

    last_by_service[service_type] = chosen_id
    return chosen_id


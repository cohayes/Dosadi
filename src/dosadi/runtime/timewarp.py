"""Timewarp / MacroStep helpers.

Implements the first Timewarp slice (DayStep v1) described in
D-RUNTIME-0232_Timewarp_MacroStep_Implementation_Checklist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from dosadi.agents.core import AgentState
from dosadi.agents.physiology import (
    SLEEP_BASE_ACCUM_PER_TICK,
    SLEEP_HUNGER_MODIFIER,
    SLEEP_STRESS_MODIFIER,
    compute_needs_pressure,
    update_stress_and_morale,
)
from dosadi.runtime.eating import (
    HUNGER_MAX,
    HUNGER_RATE_PER_TICK,
    HYDRATION_DECAY_PER_TICK,
)
from dosadi.runtime.belief_formation import run_belief_formation_for_day
from dosadi.runtime.event_to_memory_router import run_router_for_day
from dosadi.runtime.scouting import maybe_create_scout_missions, step_scout_missions_for_day
from dosadi.runtime.scouting_config import ScoutConfig
from dosadi.runtime.staffing import StaffingConfig, StaffingState, run_staffing_policy
from dosadi.runtime.maintenance import update_facility_wear
from dosadi.runtime.facility_updates import update_facilities_for_day
from dosadi.runtime.incident_engine import run_incident_engine_for_day
from dosadi.runtime.local_interactions import run_interactions_for_day
from dosadi.runtime.suit_wear import ensure_suit_config, run_suit_wear_for_day, suit_decay_multiplier
from dosadi.world.construction import apply_project_work
from dosadi.world.expansion_planner import (
    ExpansionPlannerConfig,
    ExpansionPlannerState,
    maybe_plan,
)
from dosadi.world.logistics import process_logistics_until

DEFAULT_TICKS_PER_DAY = 144_000


@dataclass(slots=True)
class TimewarpConfig:
    max_awake_agents: int = 200
    physiology_enabled: bool = True
    economy_enabled: bool = False
    memory_enabled: bool = False
    health_enabled: bool = False
    governance_enabled: bool = False


def _get_ticks_per_day(world) -> int:
    ticks_per_day = getattr(world, "ticks_per_day", None)
    if ticks_per_day is None:
        ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", None)
    if ticks_per_day is None:
        ticks_per_day = DEFAULT_TICKS_PER_DAY
    try:
        ticks_per_day = int(ticks_per_day)
    except (TypeError, ValueError):
        ticks_per_day = DEFAULT_TICKS_PER_DAY
    return max(1, ticks_per_day)


def _advance_clock(world, *, elapsed_ticks: int, ticks_per_day: int) -> None:
    world.tick = getattr(world, "tick", 0) + elapsed_ticks
    if hasattr(world, "day"):
        world.day = world.tick // ticks_per_day


def integrate_needs(agent: AgentState, *, elapsed_ticks: int, suit_multiplier: float = 1.0) -> None:
    physical = agent.physical
    physical.hunger_level = min(
        HUNGER_MAX, physical.hunger_level + HUNGER_RATE_PER_TICK * elapsed_ticks
    )

    multiplier = max(1.0, float(suit_multiplier))
    hydration = physical.hydration_level - HYDRATION_DECAY_PER_TICK * elapsed_ticks * multiplier
    if hydration < 0.0:
        hydration = 0.0
    elif hydration > 1.0:
        hydration = 1.0
    physical.hydration_level = hydration


def integrate_physiology(agent: AgentState, *, elapsed_ticks: int, suit_multiplier: float = 1.0) -> None:
    if elapsed_ticks <= 0:
        return

    integrate_needs(agent, elapsed_ticks=elapsed_ticks, suit_multiplier=suit_multiplier)

    physical = agent.physical
    needs_pressure = compute_needs_pressure(physical)
    update_stress_and_morale(physical, needs_pressure)

    # Accumulate sleep pressure using a coarse approximation of the per-tick rule.
    base_sleep = elapsed_ticks * SLEEP_BASE_ACCUM_PER_TICK
    hunger_term = max(0.0, physical.hunger_level) * SLEEP_HUNGER_MODIFIER
    stress_term = max(0.0, physical.stress_level) * SLEEP_STRESS_MODIFIER
    sleep_delta = base_sleep + (hunger_term + stress_term) * SLEEP_BASE_ACCUM_PER_TICK * elapsed_ticks

    physical.sleep_pressure += sleep_delta
    if physical.sleep_pressure > 1.0:
        physical.sleep_pressure = 1.0


def integrate_health(agent: AgentState, *, elapsed_days: int) -> None:
    # Placeholder for future rollups.
    return None


def integrate_memory(agent: AgentState, *, elapsed_days: int) -> None:
    # Placeholder for future rollups.
    return None


def select_awake_set(world, cfg: TimewarpConfig) -> List[str]:
    agent_ids = sorted(getattr(world, "agents", {}).keys())
    if len(agent_ids) <= cfg.max_awake_agents:
        return agent_ids
    return agent_ids[: cfg.max_awake_agents]


def _integrate_agent_over_interval(
    agent: AgentState, *, elapsed_ticks: int, substeps: int, suit_multiplier: float = 1.0
) -> None:
    if elapsed_ticks <= 0:
        return

    step_ticks = max(1, elapsed_ticks // max(1, substeps))
    remaining = elapsed_ticks

    while remaining > 0:
        step = min(step_ticks, remaining)
        integrate_physiology(agent, elapsed_ticks=step, suit_multiplier=suit_multiplier)
        remaining -= step


def step_day(world, *, days: int = 1, cfg: Optional[TimewarpConfig] = None) -> None:
    cfg = cfg or TimewarpConfig()
    ticks_per_day = _get_ticks_per_day(world)
    elapsed_ticks = max(0, int(days)) * ticks_per_day
    total_days = max(1, int(days))

    suit_cfg = ensure_suit_config(world)
    awake_ids = select_awake_set(world, cfg)
    awake_set = set(awake_ids)
    ambient_ids = [
        aid for aid in sorted(getattr(world, "agents", {}).keys()) if aid not in awake_set
    ]

    for agent_id in awake_ids:
        agent = world.agents[agent_id]
        multiplier = 1.0
        if getattr(suit_cfg, "enabled", False) and getattr(suit_cfg, "apply_physio_penalties", False):
            multiplier = suit_decay_multiplier(agent, cfg=suit_cfg)
        if cfg.physiology_enabled:
            _integrate_agent_over_interval(
                agent,
                elapsed_ticks=elapsed_ticks,
                substeps=max(1, days * 24),
                suit_multiplier=multiplier,
            )
        agent.physical.last_physical_update_tick = getattr(world, "tick", 0) + elapsed_ticks

    for agent_id in ambient_ids:
        agent = world.agents[agent_id]
        multiplier = 1.0
        if getattr(suit_cfg, "enabled", False) and getattr(suit_cfg, "apply_physio_penalties", False):
            multiplier = suit_decay_multiplier(agent, cfg=suit_cfg)
        if cfg.physiology_enabled:
            _integrate_agent_over_interval(
                agent, elapsed_ticks=elapsed_ticks, substeps=1, suit_multiplier=multiplier
            )
        agent.physical.last_physical_update_tick = getattr(world, "tick", 0) + elapsed_ticks

    apply_project_work(
        world,
        elapsed_hours=(elapsed_ticks / ticks_per_day) * 24.0,
        tick=getattr(world, "tick", 0) + elapsed_ticks,
    )

    current_day = getattr(world, "day", 0)
    planner_cfg = getattr(world, "expansion_planner_cfg", ExpansionPlannerConfig())
    planner_state = getattr(world, "expansion_planner_state", ExpansionPlannerState(next_plan_day=0))
    world.expansion_planner_cfg = planner_cfg
    world.expansion_planner_state = planner_state
    staffing_cfg = getattr(world, "staffing_cfg", StaffingConfig())
    staffing_state = getattr(world, "staffing_state", StaffingState())
    world.staffing_cfg = staffing_cfg
    world.staffing_state = staffing_state
    scout_cfg = getattr(world, "scout_cfg", None) or ScoutConfig()
    for offset in range(total_days):
        world.day = current_day + offset
        maybe_create_scout_missions(world, cfg=scout_cfg)
        step_scout_missions_for_day(world, day=world.day, cfg=scout_cfg)
        update_facilities_for_day(world, day=world.day, days=1)
        update_facility_wear(world, day=world.day)
        run_suit_wear_for_day(world, day=world.day)
        run_incident_engine_for_day(world, day=world.day)
        run_interactions_for_day(world, day=world.day)
        run_router_for_day(world, day=world.day)
        run_belief_formation_for_day(world, day=world.day)
        maybe_plan(world, cfg=planner_cfg, state=planner_state)
        run_staffing_policy(world, day=world.day, cfg=staffing_cfg, state=staffing_state)

    _advance_clock(world, elapsed_ticks=elapsed_ticks, ticks_per_day=ticks_per_day)


def step_to_day(world, *, target_day: int, cfg: Optional[TimewarpConfig] = None) -> None:
    ticks_per_day = _get_ticks_per_day(world)
    current_day = getattr(world, "tick", 0) // ticks_per_day
    if target_day <= current_day:
        return

    days = target_day - current_day
    step_day(world, days=days, cfg=cfg)

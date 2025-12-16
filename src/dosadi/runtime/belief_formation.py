from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable

from dosadi.agent.beliefs import Belief, BeliefStore


@dataclass(slots=True)
class BeliefConfig:
    enabled: bool = True
    sleep_interval_days: int = 1
    max_beliefs_per_agent: int = 64
    crumb_to_belief_alpha: float = 0.10
    episode_bonus_weight: float = 0.15
    belief_decay_half_life_days: int = 120
    min_weight: float = 0.05
    max_weight: float = 0.95
    phase2_suspicion_bias: float = 0.05


@dataclass(slots=True)
class BeliefState:
    last_run_day: int = -1


def _ensure_config(world: Any) -> BeliefConfig:
    cfg = getattr(world, "belief_config", None)
    if not isinstance(cfg, BeliefConfig):
        cfg = BeliefConfig()
        setattr(world, "belief_config", cfg)
    return cfg


def _ensure_state(world: Any) -> BeliefState:
    state = getattr(world, "belief_state", None)
    if not isinstance(state, BeliefState):
        state = BeliefState()
        setattr(world, "belief_state", state)
    return state


def _ensure_agent_beliefs(agent: Any, *, max_items: int) -> BeliefStore:
    store = getattr(agent, "beliefs", None)
    if not isinstance(store, BeliefStore):
        store = BeliefStore(max_items=max_items)
        setattr(agent, "beliefs", store)
    elif store.max_items != max_items:
        store.max_items = max_items
        store._rebalance()
    return store


def _clamp(lo: float, hi: float, value: float) -> float:
    return max(lo, min(hi, value))


def _crumb_signal(count: int, scale: float = 3.0) -> float:
    return 1.0 - math.exp(-max(0.0, float(count)) / max(scale, 1e-6))


def _map_tag_to_belief_key(tag: str) -> str | None:
    if tag.startswith("delivery-fail:"):
        delivery_id = tag.split(":", 1)[1]
        return f"delivery-risk:{delivery_id}"
    if tag.startswith("facility-down:"):
        facility_id = tag.split(":", 1)[1]
        return f"facility-reliability:{facility_id}"
    if tag.startswith("route-risk:"):
        edge_key = tag.split(":", 1)[1]
        return f"route-risk:{edge_key}"
    if tag.startswith("incident:"):
        _, incident_kind, target_id = tag.split(":", 2)
        return f"incident-risk:{incident_kind}:{target_id}"
    return None


def _signals_from_crumbs(agent: Any) -> Dict[str, float]:
    crumbs = getattr(agent, "crumbs", None)
    if not crumbs or not getattr(crumbs, "tags", None):
        return {}

    signals: Dict[str, float] = {}
    for tag, counter in crumbs.tags.items():
        belief_key = _map_tag_to_belief_key(tag)
        if belief_key is None:
            continue
        signal = _crumb_signal(getattr(counter, "count", 0))
        signals[belief_key] = max(signals.get(belief_key, 0.0), signal)
    return signals


def _episode_bonus(agent: Any, belief_key: str, bonus: float) -> float:
    episodes_daily = getattr(agent, "episodes_daily", None)
    if not episodes_daily:
        return 0.0

    key_prefix = belief_key.split(":", 1)[0]
    for episode in getattr(episodes_daily, "daily", []):
        if episode.kind == "DELIVERY_FAILED" and belief_key.startswith("delivery-risk:"):
            if str(episode.payload.get("subject_id")) in belief_key:
                return bonus
        if episode.kind == "FACILITY_DOWNTIME" and key_prefix == "facility-reliability":
            if str(episode.payload.get("subject_id")) in belief_key:
                return bonus
        if episode.kind == "INCIDENT" and key_prefix == "incident-risk":
            return bonus
    return 0.0


def _apply_decay(store: BeliefStore, *, day: int, half_life: int, min_weight: float) -> None:
    if not store.items:
        return

    for belief in list(store.items.values()):
        if belief.last_day >= day:
            continue
        dt = max(0, day - belief.last_day)
        if half_life <= 0 or dt <= 0:
            continue
        decay_factor = 0.5 ** (dt / float(half_life))
        belief.weight = max(min_weight, belief.weight * decay_factor)
        belief.last_day = day
        store.upsert(belief)


def _maybe_phase2_bias(world: Any, key: str, value: float, bias: float) -> float:
    phase_state = getattr(world, "phase_state", None)
    phase = getattr(phase_state, "phase", None)
    try:
        from dosadi.world.phases import WorldPhase

        is_phase2 = phase is WorldPhase.PHASE2
    except Exception:
        is_phase2 = False
    if is_phase2 and key.startswith("route-risk"):
        return _clamp(0.0, 1.0, value + bias)
    return value


def _process_agent(
    world: Any,
    agent: Any,
    *,
    day: int,
    cfg: BeliefConfig,
) -> None:
    store = _ensure_agent_beliefs(agent, max_items=cfg.max_beliefs_per_agent)
    _apply_decay(
        store,
        day=day,
        half_life=cfg.belief_decay_half_life_days,
        min_weight=cfg.min_weight,
    )

    signals = _signals_from_crumbs(agent)
    if not signals:
        return

    for key, signal in sorted(signals.items()):
        existing = store.get(key)
        if existing is None:
            weight = _clamp(cfg.min_weight, cfg.max_weight, signal)
            belief = Belief(key=key, value=_clamp(0.0, 1.0, signal), weight=weight, last_day=day)
        else:
            value = (1.0 - cfg.crumb_to_belief_alpha) * existing.value + cfg.crumb_to_belief_alpha * signal
            weight = existing.weight + cfg.crumb_to_belief_alpha * (signal - existing.weight)
            weight = _clamp(cfg.min_weight, cfg.max_weight, weight)
            belief = Belief(
                key=key,
                value=_clamp(0.0, 1.0, value),
                weight=weight,
                last_day=day,
            )

        bonus = _episode_bonus(agent, key, cfg.episode_bonus_weight)
        if bonus > 0.0:
            belief.weight = _clamp(cfg.min_weight, cfg.max_weight, belief.weight + bonus)

        belief.value = _maybe_phase2_bias(world, key, belief.value, cfg.phase2_suspicion_bias)
        store.upsert(belief)


def _consume_signaled_agents(world: Any) -> Iterable[str]:
    signaled = getattr(world, "agents_with_new_signals", None)
    if signaled is None:
        return []
    if isinstance(signaled, set):
        agents = list(signaled)
        signaled.clear()
        return agents
    try:
        agents = list(signaled)
    except Exception:
        return []
    if hasattr(signaled, "clear"):
        try:
            signaled.clear()
        except Exception:
            pass
    return agents


def run_belief_formation_for_day(world: Any, *, day: int) -> None:
    cfg = _ensure_config(world)
    if not cfg.enabled:
        return

    state = _ensure_state(world)
    agent_ids = _consume_signaled_agents(world)

    for agent_id in sorted(agent_ids):
        agent = getattr(world, "agents", {}).get(agent_id)
        if agent is None:
            continue
        _process_agent(world, agent, day=day, cfg=cfg)

    state.last_run_day = day
    setattr(world, "belief_state", state)


__all__ = ["BeliefConfig", "BeliefState", "run_belief_formation_for_day"]

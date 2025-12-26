from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from dosadi.runtime.institutions import ensure_policy
from dosadi.runtime.ledger import STATE_TREASURY, get_or_create_account, post_tx
from dosadi.runtime.telemetry import ensure_metrics, record_event
from dosadi.world.survey_map import SurveyMap


@dataclass(slots=True)
class DefenseConfig:
    enabled: bool = False
    militia_train_rate_per_day: float = 0.02
    militia_decay_per_day: float = 0.01
    max_militia_strength: float = 1.0
    deterministic_salt: str = "defense-v1"


@dataclass(slots=True)
class WardDefenseState:
    ward_id: str
    militia_strength: float = 0.0
    militia_ready: float = 1.0
    training_level: int = 0
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


def _clamp(lo: float, hi: float, value: float) -> float:
    return max(lo, min(hi, float(value)))


def _clamp01(value: float) -> float:
    return _clamp(0.0, 1.0, value)


def ensure_defense_config(world: Any) -> DefenseConfig:
    cfg = getattr(world, "defense_cfg", None)
    if not isinstance(cfg, DefenseConfig):
        cfg = DefenseConfig()
        world.defense_cfg = cfg
    return cfg


def ensure_ward_defense(world: Any, ward_id: str) -> WardDefenseState:
    states: dict[str, WardDefenseState] = getattr(world, "ward_defense", {}) or {}
    state = states.get(ward_id)
    if not isinstance(state, WardDefenseState):
        state = WardDefenseState(ward_id=ward_id)
        states[ward_id] = state
    world.ward_defense = states
    return state


def _ward_ids(world: Any) -> list[str]:
    wards = sorted(getattr(world, "wards", {}).keys())
    if wards:
        return wards
    survey_map: SurveyMap | None = getattr(world, "survey_map", None)
    if isinstance(survey_map, SurveyMap):
        ward_ids = {node.ward_id for node in survey_map.nodes.values() if node.ward_id}
        return sorted(ward_ids)
    return []


def _pay_budget(world: Any, ward_id: str, amount: float, *, day: int, reason: str) -> float:
    if amount <= 0:
        return 0.0
    payer = get_or_create_account(world, f"acct:ward:{ward_id}")
    get_or_create_account(world, STATE_TREASURY)
    before = float(getattr(payer, "balance", 0.0) or 0.0)
    posted = post_tx(
        world,
        day=day,
        from_acct=f"acct:ward:{ward_id}",
        to_acct=STATE_TREASURY,
        amount=float(amount),
        reason=reason,
    )
    after = float(getattr(payer, "balance", 0.0) or 0.0)
    if not posted:
        return 0.0
    paid = max(0.0, before - after)
    return paid


def run_defense_for_day(world: Any, *, day: int) -> None:
    cfg = ensure_defense_config(world)
    if not cfg.enabled:
        return

    metrics = ensure_metrics(world)
    wards = _ward_ids(world)
    militia_scores: list[float] = []
    defense_bucket: dict[str, object] = metrics.gauges.setdefault("defense", {})  # type: ignore[arg-type]
    defense_bucket.setdefault("militia_by_ward", {})
    defense_bucket.setdefault("forts_by_type", {})
    upkeep_paid = 0.0
    upkeep_shortfall = 0.0

    for ward_id in wards:
        state = ensure_ward_defense(world, ward_id)
        policy = ensure_policy(world, ward_id)
        target = _clamp01(getattr(policy, "militia_target_strength", 0.0))
        upkeep_budget = max(0.0, float(getattr(policy, "militia_upkeep_budget", 0.0)))
        training_budget = max(0.0, float(getattr(policy, "militia_training_budget", 0.0)))

        paid_upkeep = _pay_budget(world, ward_id, upkeep_budget, day=day, reason="PAY_MILITIA_UPKEEP")
        paid_training = _pay_budget(world, ward_id, training_budget, day=day, reason="PAY_MILITIA_TRAINING")

        if upkeep_budget > 0.0 and paid_upkeep < upkeep_budget:
            upkeep_shortfall += upkeep_budget - paid_upkeep
            record_event(
                world,
                {
                    "type": "DEFENSE_UPKEEP_FAILED",
                    "ward_id": ward_id,
                    "day": day,
                    "paid": round(paid_upkeep, 4),
                    "budget": round(upkeep_budget, 4),
                },
            )
        upkeep_paid += paid_upkeep

        if training_budget > 0.0 and paid_training > 0.0:
            progress = cfg.militia_train_rate_per_day * (paid_training / training_budget)
            delta = progress * (target - state.militia_strength)
            state.militia_strength = _clamp(0.0, cfg.max_militia_strength, state.militia_strength + delta)
            record_event(
                world,
                {
                    "type": "MILITIA_TRAINED",
                    "ward_id": ward_id,
                    "day": day,
                    "delta": round(delta, 4),
                    "target": round(target, 4),
                },
            )
        else:
            state.militia_strength = max(0.0, state.militia_strength - cfg.militia_decay_per_day)

        if paid_upkeep > 0.0:
            state.militia_ready = _clamp01(state.militia_ready + 0.05)
        else:
            state.militia_ready = max(0.0, state.militia_ready - 0.05 - cfg.militia_decay_per_day)

        state.last_update_day = day
        militia_scores.append(state.militia_strength)

        ward_bucket: Mapping[str, float] = defense_bucket.get("militia_by_ward", {})  # type: ignore[assignment]
        ward_bucket = dict(ward_bucket)
        ward_bucket[ward_id] = round(state.militia_strength, 4)
        defense_bucket["militia_by_ward"] = ward_bucket

    if militia_scores:
        defense_bucket["militia_avg"] = sum(militia_scores) / len(militia_scores)
    defense_bucket["upkeep_paid"] = round(upkeep_paid, 4)
    defense_bucket["upkeep_shortfall"] = round(upkeep_shortfall, 4)


__all__ = [
    "DefenseConfig",
    "WardDefenseState",
    "ensure_defense_config",
    "ensure_ward_defense",
    "run_defense_for_day",
]

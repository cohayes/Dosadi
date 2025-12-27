from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable

from dosadi.runtime.telemetry import ensure_metrics, record_event


@dataclass(slots=True)
class EspionageConfig:
    enabled: bool = False
    max_ops_active: int = 20
    candidate_topk: int = 24
    op_duration_days: int = 7
    deterministic_salt: str = "espionage-v1"
    base_detect_rate: float = 0.05
    base_success_rate: float = 0.25
    counterintel_efficiency: float = 0.8


@dataclass(slots=True)
class IntelOpPlan:
    op_id: str
    day_started: int
    day_end: int
    attacker_faction: str
    defender_faction: str | None
    target_kind: str
    target_id: str
    op_type: str
    intensity: float
    budget_cost: float
    reason: str
    score_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class IntelOpOutcome:
    op_id: str
    day: int
    status: str
    effects: dict[str, object] = field(default_factory=dict)
    loot: dict[str, float] = field(default_factory=dict)
    notes: dict[str, object] = field(default_factory=dict)


def ensure_espionage_config(world: Any) -> EspionageConfig:
    cfg = getattr(world, "espionage_cfg", None)
    if not isinstance(cfg, EspionageConfig):
        cfg = EspionageConfig()
        world.espionage_cfg = cfg
    return cfg


def ensure_counterintel(world: Any) -> dict[str, float]:
    coverage = getattr(world, "counterintel_by_ward", None)
    if not isinstance(coverage, dict):
        coverage = {}
        world.counterintel_by_ward = coverage
    return coverage


def ensure_intel_ops_active(world: Any) -> dict[str, IntelOpPlan]:
    active = getattr(world, "intel_ops_active", None)
    if not isinstance(active, dict):
        active = {}
        world.intel_ops_active = active
    return active


def ensure_intel_ops_history(world: Any) -> list[IntelOpOutcome]:
    history = getattr(world, "intel_ops_history", None)
    if not isinstance(history, list):
        history = []
        world.intel_ops_history = history
    return history


def _stable_value(cfg: EspionageConfig, *parts: object, spread: float = 1.0) -> float:
    payload = json.dumps([cfg.deterministic_salt, *parts], sort_keys=True)
    digest = sha256(payload.encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) / 0xFFFFFFFF) * spread


def _stable_topk(items: Iterable[tuple[str, float]], k: int) -> list[tuple[str, float]]:
    scored = [(float(score), key) for key, score in items if float(score) > 0]
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [(key, score) for score, key in scored[: max(0, int(k))]]


def _target_counterintel(world: Any, target_id: str) -> float:
    coverage = ensure_counterintel(world)
    return max(0.0, min(1.0, float(coverage.get(target_id, 0.0))))


def _choose_factions(world: Any) -> tuple[str, str | None]:
    factions = sorted(getattr(world, "factions", {}).keys())
    if not factions:
        return "faction:attacker", None
    if len(factions) == 1:
        return factions[0], None
    return factions[0], factions[-1]


def _corridor_candidates(world: Any) -> list[tuple[str, float]]:
    stress = getattr(world, "corridor_stress", {}) or {}
    return list((str(cid), float(score)) for cid, score in stress.items())


def _ward_candidates(world: Any) -> list[tuple[str, float]]:
    wards = getattr(world, "wards", {}) or {}
    pairs: list[tuple[str, float]] = []
    for wid, ward in wards.items():
        score = 0.0
        score += float(getattr(ward, "need_index", 0.0))
        score += float(getattr(ward, "smuggle_risk", 0.0)) * 0.25
        if score > 0:
            pairs.append((str(wid), score))
    return pairs


def _relay_candidates(world: Any) -> list[tuple[str, float]]:
    stats = getattr(world, "media_stats", {}) or {}
    pairs: list[tuple[str, float]] = []
    for key, value in stats.items():
        if str(key).startswith("relay:"):
            pairs.append((str(key).split("relay:", 1)[-1], float(value)))
    return pairs


def _ledger_candidates(world: Any) -> list[tuple[str, float]]:
    ledger_state = getattr(world, "ledger_state", None)
    if ledger_state and hasattr(ledger_state, "accounts"):
        return [(acct_id, float(acct.balance)) for acct_id, acct in ledger_state.accounts.items()]
    return []


def _pick_candidates(world: Any, cfg: EspionageConfig) -> list[IntelOpPlan]:
    attacker, defender = _choose_factions(world)
    plans: list[IntelOpPlan] = []
    day = getattr(world, "day", 0)
    corridor_targets = _stable_topk(_corridor_candidates(world), cfg.candidate_topk)
    for target, score in corridor_targets:
        op_id = f"op:{target}:bribe"
        plans.append(
            IntelOpPlan(
                op_id=op_id,
                day_started=day,
                day_end=day + cfg.op_duration_days,
                attacker_faction=attacker,
                defender_faction=defender,
                target_kind="CORRIDOR",
                target_id=str(target),
                op_type="BRIBE_COURIER",
                intensity=min(1.0, score),
                budget_cost=max(0.0, score * 5.0),
                reason="High corridor stress",
                score_breakdown={"stress": score},
            )
        )

    ward_targets = _stable_topk(_ward_candidates(world), cfg.candidate_topk)
    for target, score in ward_targets:
        plans.append(
            IntelOpPlan(
                op_id=f"op:{target}:informant",
                day_started=day,
                day_end=day + cfg.op_duration_days,
                attacker_faction=attacker,
                defender_faction=defender,
                target_kind="WARD",
                target_id=str(target),
                op_type="PLANT_INFORMANT",
                intensity=min(1.0, score),
                budget_cost=max(0.0, score * 3.0),
                reason="Ward unrest",
                score_breakdown={"unrest": score},
            )
        )
        plans.append(
            IntelOpPlan(
                op_id=f"op:{target}:falseflag",
                day_started=day,
                day_end=day + cfg.op_duration_days,
                attacker_faction=attacker,
                defender_faction=defender,
                target_kind="WARD",
                target_id=str(target),
                op_type="FALSE_FLAG_PROPAGANDA",
                intensity=min(1.0, score),
                budget_cost=max(0.0, score * 2.0),
                reason="Targeted narrative",
                score_breakdown={"ideology": score},
            )
        )

    relay_targets = _stable_topk(_relay_candidates(world), cfg.candidate_topk)
    for target, score in relay_targets:
        plans.append(
            IntelOpPlan(
                op_id=f"op:{target}:relay",
                day_started=day,
                day_end=day + cfg.op_duration_days,
                attacker_faction=attacker,
                defender_faction=defender,
                target_kind="RELAY",
                target_id=str(target),
                op_type="SABOTAGE_RELAY",
                intensity=min(1.0, score),
                budget_cost=max(0.0, score * 4.0),
                reason="High bandwidth relay",
                score_breakdown={"bandwidth": score},
            )
        )

    ledger_targets = _stable_topk(_ledger_candidates(world), cfg.candidate_topk)
    for target, score in ledger_targets:
        plans.append(
            IntelOpPlan(
                op_id=f"op:{target}:ledger",
                day_started=day,
                day_end=day + cfg.op_duration_days,
                attacker_faction=attacker,
                defender_faction=defender,
                target_kind="FACTION",
                target_id=str(target),
                op_type="STEAL_LEDGER",
                intensity=min(1.0, score / (1.0 + score)),
                budget_cost=max(0.0, score * 0.1),
                reason="Large ledger balance",
                score_breakdown={"balance": score},
            )
        )

    plans.sort(key=lambda plan: (-plan.intensity, plan.op_id))
    return plans


def plan_intel_ops(world: Any, *, day: int | None = None) -> list[IntelOpPlan]:
    cfg = ensure_espionage_config(world)
    if not cfg.enabled:
        return []
    ensure_counterintel(world)
    active = ensure_intel_ops_active(world)
    metrics = ensure_metrics(world)
    if day is not None:
        world.day = day
    candidates = _pick_candidates(world, cfg)
    open_slots = max(0, int(cfg.max_ops_active) - len(active))
    selected = candidates[:open_slots]
    for plan in selected:
        active[plan.op_id] = plan
        metrics.inc("espionage.ops_started", 1)
        record_event(
            world,
            {
                "event": "INTEL_OP_STARTED",
                "day": getattr(world, "day", 0),
                "op_id": plan.op_id,
                "op_type": plan.op_type,
                "target": plan.target_id,
            },
        )
    metrics.set_gauge("espionage.ops_active", len(active))
    return selected


def _append_history(world: Any, outcome: IntelOpOutcome, *, max_len: int = 200) -> None:
    history = ensure_intel_ops_history(world)
    history.append(outcome)
    if len(history) > max_len:
        world.intel_ops_history = history[-max_len:]


def _apply_effects(world: Any, plan: IntelOpPlan, outcome: IntelOpOutcome) -> None:
    metrics = ensure_metrics(world)
    stats = getattr(world, "media_stats", None)
    if not isinstance(stats, dict):
        stats = {}
        world.media_stats = stats
    if plan.op_type == "BRIBE_COURIER":
        key = f"intercept_bonus:{plan.target_id}"
        current = float(stats.get(key, 0.0))
        stats[key] = current + plan.intensity * 0.2
        outcome.effects[key] = current + plan.intensity * 0.2
        metrics.inc("espionage.message_intercepts_delta", plan.intensity * 0.2)
    elif plan.op_type == "SABOTAGE_RELAY":
        key = f"relay_loss:{plan.target_id}"
        current = float(stats.get(key, 0.0))
        stats[key] = current + plan.intensity * 0.3
        outcome.effects[key] = current + plan.intensity * 0.3
        metrics.inc("espionage.relay_sabotaged_days", 1)
    elif plan.op_type == "PLANT_INFORMANT":
        key = f"intel_visibility:{plan.target_id}"
        current = float(stats.get(key, 0.0))
        stats[key] = current + plan.intensity * 0.25
        outcome.effects[key] = current + plan.intensity * 0.25
    elif plan.op_type == "STEAL_LEDGER":
        ledger_state = getattr(world, "ledger_state", None)
        if ledger_state and hasattr(ledger_state, "accounts"):
            account = ledger_state.accounts.get(plan.target_id)
            if account is not None:
                steal_amt = min(account.balance * 0.25, account.balance)
                account.balance = max(0.0, account.balance - steal_amt)
                loot_key = f"loot:{plan.target_id}"
                outcome.loot[loot_key] = steal_amt
    elif plan.op_type == "FALSE_FLAG_PROPAGANDA":
        inbox = getattr(world, "media_inbox_by_ward", None)
        if isinstance(inbox, dict):
            queue = inbox.setdefault(plan.target_id, [])
            message = {
                "sender": "unknown",
                "spoofed": True,
                "target": plan.target_id,
                "intensity": plan.intensity,
            }
            queue.append(message)
            outcome.effects[f"false_flag:{plan.target_id}"] = message


def resolve_intel_ops(world: Any, *, day: int | None = None) -> list[IntelOpOutcome]:
    cfg = ensure_espionage_config(world)
    if not cfg.enabled:
        return []
    if day is not None:
        world.day = day
    active = ensure_intel_ops_active(world)
    ensure_counterintel(world)
    metrics = ensure_metrics(world)
    outcomes: list[IntelOpOutcome] = []
    to_remove: list[str] = []
    for op_id, plan in sorted(active.items()):
        coverage = _target_counterintel(world, plan.target_id)
        detect_prob = min(1.0, cfg.base_detect_rate + coverage * cfg.counterintel_efficiency)
        success_prob = min(1.0, cfg.base_success_rate * (1.0 - coverage) + plan.intensity * 0.25)
        detect_roll = _stable_value(cfg, op_id, world.day, "detect")
        success_roll = _stable_value(cfg, op_id, world.day, "success")
        status = "ACTIVE"
        if coverage >= 1.0:
            status = "DETECTED"
            detect_roll = 0.0
        if detect_roll <= detect_prob:
            status = "DETECTED"
            to_remove.append(op_id)
            metrics.inc("espionage.ops_detected", 1)
        elif success_roll <= success_prob:
            status = "SUCCEEDED"
            to_remove.append(op_id)
            metrics.inc("espionage.ops_succeeded", 1)
        elif world.day >= plan.day_end:
            status = "EXPIRED"
            to_remove.append(op_id)

        outcome = IntelOpOutcome(op_id=op_id, day=world.day, status=status)
        if status == "SUCCEEDED":
            _apply_effects(world, plan, outcome)
        if status == "DETECTED":
            outcome.notes["suspected_attacker"] = plan.attacker_faction
        outcomes.append(outcome)
        if status != "ACTIVE":
            _append_history(world, outcome)
            record_event(
                world,
                {
                    "event": f"INTEL_OP_{status}",
                    "day": world.day,
                    "op_id": op_id,
                    "target": plan.target_id,
                    "op_type": plan.op_type,
                },
            )

    for op_id in to_remove:
        active.pop(op_id, None)
    metrics.set_gauge("espionage.ops_active", len(active))
    return outcomes


__all__ = [
    "EspionageConfig",
    "IntelOpOutcome",
    "IntelOpPlan",
    "ensure_counterintel",
    "ensure_espionage_config",
    "ensure_intel_ops_active",
    "ensure_intel_ops_history",
    "plan_intel_ops",
    "resolve_intel_ops",
]

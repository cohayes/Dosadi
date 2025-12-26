from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from .telemetry import ensure_metrics, record_event


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _day(world: Any) -> int:
    if hasattr(world, "day"):
        try:
            return int(getattr(world, "day"))
        except Exception:
            return 0
    tick = getattr(world, "tick", 0)
    ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", 144_000)
    try:
        ticks_per_day = int(ticks_per_day)
    except Exception:
        ticks_per_day = 144_000
    return int(getattr(world, "tick", 0) // max(1, ticks_per_day))


def _phase_key(world: Any) -> str:
    phase_state = getattr(world, "phase_state", None)
    value = getattr(phase_state, "phase", "P0")
    try:
        intval = int(getattr(value, "value", value))
        return f"P{intval}"
    except Exception:
        return "P0"


@dataclass(slots=True)
class CrackdownConfig:
    enabled: bool = False
    border_topk: int = 24
    ward_topk: int = 16
    max_targets_per_day: int = 6
    deterministic_salt: str = "crackdown-v1"
    intensity_levels: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0)
    cooldown_days: int = 7


@dataclass(slots=True)
class CrackdownTarget:
    kind: str
    target_id: str
    intensity: float
    start_day: int
    end_day: int
    reason: str
    score_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class CrackdownPlan:
    day: int
    targets: list[CrackdownTarget] = field(default_factory=list)
    budget_used: float = 0.0
    notes: dict[str, object] = field(default_factory=dict)


def ensure_crackdown_config(world: Any) -> CrackdownConfig:
    cfg = getattr(world, "crackdown_cfg", None)
    if not isinstance(cfg, CrackdownConfig):
        cfg = CrackdownConfig()
        world.crackdown_cfg = cfg
    return cfg


def ensure_crackdown_state(world: Any) -> tuple[dict[int, CrackdownPlan], dict[str, CrackdownTarget]]:
    plans = getattr(world, "crackdown_plans", None)
    if not isinstance(plans, dict):
        plans = {}
    active = getattr(world, "crackdown_active", None)
    if not isinstance(active, dict):
        active = {}
    world.crackdown_plans = plans
    world.crackdown_active = active
    return plans, active


def _capacity_for_day(world: Any) -> float:
    base = float(getattr(world, "paid_enforcement_points", 10.0) or 0.0)
    base += 0.5 * float(getattr(world, "paid_audit_points", 0.0) or 0.0)
    phase_key = _phase_key(world)
    if phase_key == "P0":
        base *= 0.6
    elif phase_key == "P2":
        base *= 1.25
    return max(0.0, base)


def _stable_rand(world: Any, *parts: object) -> float:
    cfg = ensure_crackdown_config(world)
    key = "|".join(str(p) for p in (cfg.deterministic_salt, *_flatten(parts)))
    digest = sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


def _flatten(items: Iterable[object]) -> list[object]:
    flat: list[object] = []
    for item in items:
        if isinstance(item, (list, tuple)):
            flat.extend(_flatten(item))
        else:
            flat.append(item)
    return flat


def _candidate_score(payload: Mapping[str, float], weights: Mapping[str, float]) -> tuple[float, dict[str, float]]:
    breakdown: dict[str, float] = {}
    score = 0.0
    for key, weight in weights.items():
        val = float(payload.get(key, 0.0) or 0.0)
        component = weight * val
        breakdown[key] = component
        score += component
    return score, breakdown


def _trim_topk(entries: list[tuple[str, float, dict[str, float]]], k: int) -> list[tuple[str, float, dict[str, float]]]:
    entries.sort(key=lambda item: (-round(item[1], 6), item[0]))
    return entries[: max(0, int(k))]


def _candidates_from_signals(world: Any) -> tuple[list[tuple[str, float, dict[str, float]]], list[tuple[str, float, dict[str, float]]], list[tuple[str, float, dict[str, float]]]]:
    cfg = ensure_crackdown_config(world)
    customs_signals: Mapping[str, Mapping[str, float]] = getattr(world, "customs_signals", {}) or {}
    corridor_signals: Mapping[str, Mapping[str, float]] = getattr(world, "corridor_signals", {}) or {}
    ward_signals: Mapping[str, Mapping[str, float]] = getattr(world, "ward_signals", {}) or {}

    borders: list[tuple[str, float, dict[str, float]]] = []
    for border_id, payload in customs_signals.items():
        score, breakdown = _candidate_score(
            payload,
            {
                "bribes": 0.5,
                "seizures": 0.7,
                "traffic": 0.3,
                "political_cost": -0.4,
                "corruption_risk": -0.3,
            },
        )
        borders.append((str(border_id), score, breakdown))

    corridors: list[tuple[str, float, dict[str, float]]] = []
    for corridor_id, payload in corridor_signals.items():
        score, breakdown = _candidate_score(
            payload,
            {
                "risk": 0.6,
                "interdictions": 0.5,
                "throughput": 0.3,
                "political_cost": -0.3,
            },
        )
        corridors.append((str(corridor_id), score, breakdown))

    wards: list[tuple[str, float, dict[str, float]]] = []
    for ward_id, payload in ward_signals.items():
        score, breakdown = _candidate_score(
            payload,
            {
                "corruption": 0.6,
                "smuggling_tolerance": 0.4,
                "unrest": 0.3,
                "legitimacy": -0.3,
            },
        )
        wards.append((str(ward_id), score, breakdown))

    borders = _trim_topk(borders, cfg.border_topk)
    corridors = _trim_topk(corridors, cfg.border_topk)
    wards = _trim_topk(wards, cfg.ward_topk)
    return borders, corridors, wards


def _cooldown_ok(active: Mapping[str, CrackdownTarget], candidate_id: str, *, day: int, cooldown_days: int) -> bool:
    target = active.get(candidate_id)
    if target is None:
        return True
    return day - target.end_day >= cooldown_days


def plan_crackdown(world: Any, *, day: int | None = None) -> CrackdownPlan | None:
    cfg = ensure_crackdown_config(world)
    if not cfg.enabled:
        return None

    plans, active = ensure_crackdown_state(world)
    current_day = _day(world) if day is None else int(day)

    if current_day in plans:
        return plans[current_day]

    expire_crackdowns(world, current_day)

    borders, corridors, wards = _candidates_from_signals(world)
    candidates: list[tuple[str, str, float, dict[str, float]]] = []
    for target_id, score, breakdown in borders:
        candidates.append(("border", target_id, score, breakdown))
    for target_id, score, breakdown in corridors:
        candidates.append(("corridor", target_id, score, breakdown))
    for target_id, score, breakdown in wards:
        candidates.append(("ward_audit", target_id, score, breakdown))

    candidates.sort(key=lambda item: (-round(item[2], 6), item[1]))
    capacity = _capacity_for_day(world)
    remaining = capacity
    targets: list[CrackdownTarget] = []

    def _choose_intensity() -> float:
        for level in sorted(cfg.intensity_levels, reverse=True):
            if remaining >= level:
                return float(level)
        return float(min(cfg.intensity_levels))

    for kind, target_id, score, breakdown in candidates:
        if len(targets) >= cfg.max_targets_per_day:
            break
        if not _cooldown_ok(active, f"{kind}:{target_id}", day=current_day, cooldown_days=cfg.cooldown_days):
            continue
        if score <= 0.0:
            continue
        intensity = _choose_intensity()
        if remaining < min(cfg.intensity_levels):
            break
        remaining -= intensity
        target = CrackdownTarget(
            kind=kind,
            target_id=target_id,
            intensity=_clamp01(intensity),
            start_day=current_day,
            end_day=current_day + cfg.cooldown_days,
            reason=f"score:{round(score, 3)}",
            score_breakdown=dict(breakdown),
        )
        targets.append(target)

    if current_day % 7 == 0 and len(candidates) > len(targets):
        for kind, target_id, score, breakdown in candidates:
            if len(targets) >= cfg.max_targets_per_day:
                break
            if any(t.target_id == target_id and t.kind == kind for t in targets):
                continue
            if not _cooldown_ok(active, f"{kind}:{target_id}", day=current_day, cooldown_days=cfg.cooldown_days):
                continue
            intensity = float(sorted(cfg.intensity_levels)[0])
            targets.append(
                CrackdownTarget(
                    kind=kind,
                    target_id=target_id,
                    intensity=_clamp01(intensity),
                    start_day=current_day,
                    end_day=current_day + cfg.cooldown_days,
                    reason="exploratory",
                    score_breakdown=dict(breakdown),
                )
            )
            break

    plan = CrackdownPlan(day=current_day, targets=targets, budget_used=capacity - remaining)
    plans[current_day] = plan
    _prune_history(plans)
    _activate_targets(world, plan)
    metrics = ensure_metrics(world)
    metrics.set_gauge(
        "crackdown.status",
        {"targets_active": len(getattr(world, "crackdown_active", {}) or {}), "budget_used": plan.budget_used},
    )
    record_event(
        world,
        {
            "kind": "CRACKDOWN_PLAN_CREATED",
            "day": current_day,
            "targets": [f"{t.kind}:{t.target_id}" for t in targets],
        },
    )
    return plan


def _activate_targets(world: Any, plan: CrackdownPlan) -> None:
    _, active = ensure_crackdown_state(world)
    for target in plan.targets:
        key = f"{target.kind}:{target.target_id}"
        active[key] = target
        record_event(
            world,
            {
                "kind": "CRACKDOWN_TARGET_ACTIVATED",
                "day": plan.day,
                "target": key,
                "intensity": target.intensity,
            },
        )


def expire_crackdowns(world: Any, current_day: int | None = None) -> None:
    _, active = ensure_crackdown_state(world)
    day = _day(world) if current_day is None else int(current_day)
    expired = [key for key, tgt in active.items() if getattr(tgt, "end_day", day) < day]
    for key in expired:
        active.pop(key, None)
        record_event(world, {"kind": "CRACKDOWN_TARGET_EXPIRED", "day": day, "target": key})


def _prune_history(plans: dict[int, CrackdownPlan], keep: int = 30) -> None:
    if len(plans) <= keep:
        return
    for day in sorted(plans.keys())[:-keep]:
        plans.pop(day, None)


def border_modifiers(world: Any, border_id: str) -> Mapping[str, float]:
    active: Mapping[str, CrackdownTarget] = getattr(world, "crackdown_active", {}) or {}
    tgt = active.get(f"border:{border_id}")
    if tgt is None:
        return {}
    ins = _clamp01(tgt.intensity)
    return {
        "inspection_mult": 1.0 + 0.6 * ins,
        "detection_mult": 1.0 + 0.5 * ins,
        "bribe_mult": max(0.05, 1.0 - 0.5 * ins),
    }


def corridor_modifiers(world: Any, corridor_id: str) -> Mapping[str, float]:
    active: Mapping[str, CrackdownTarget] = getattr(world, "crackdown_active", {}) or {}
    tgt = active.get(f"corridor:{corridor_id}")
    if tgt is None:
        return {}
    ins = _clamp01(tgt.intensity)
    return {"risk_mult": max(0.1, 1.0 - 0.6 * ins), "escort_bonus": 0.1 * ins}


def ward_audit_modifiers(world: Any, ward_id: str) -> Mapping[str, float]:
    active: Mapping[str, CrackdownTarget] = getattr(world, "crackdown_active", {}) or {}
    tgt = active.get(f"ward_audit:{ward_id}")
    if tgt is None:
        return {}
    ins = _clamp01(tgt.intensity)
    return {
        "audit_bonus": 0.2 * ins,
        "corruption_mult": max(0.25, 1.0 - 0.5 * ins),
        "legitimacy_delta": -0.1 * ins,
        "unrest_delta": 0.2 * ins,
    }


__all__ = [
    "CrackdownConfig",
    "CrackdownPlan",
    "CrackdownTarget",
    "border_modifiers",
    "corridor_modifiers",
    "ensure_crackdown_config",
    "ensure_crackdown_state",
    "expire_crackdowns",
    "plan_crackdown",
    "ward_audit_modifiers",
]

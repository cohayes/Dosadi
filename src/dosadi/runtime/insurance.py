from __future__ import annotations

"""Insurance and risk market primitives (v1).

This module implements a bounded, deterministic approximation of corridor
insurance for logistics flows. Premiums are priced weekly from corridor risk
signals, collected from insured macro flows, and claims are paid against
corridor losses. Shadow protection is modelled as a risk modifier rather than
full contract law.
"""

from dataclasses import dataclass, field
from hashlib import sha256
import random
from typing import Any, Mapping

from dosadi.runtime.corridor_risk import risk_for_edge
from dosadi.runtime.ledger import transfer
from dosadi.runtime.telemetry import ensure_metrics


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _clamp_range(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


@dataclass(slots=True)
class InsuranceConfig:
    enabled: bool = False
    update_cadence_days: int = 7
    deterministic_salt: str = "insurance-v1"
    max_policies_active: int = 2000
    premium_smoothing: float = 0.25
    loss_lookback_weeks: int = 8
    min_premium: float = 0.001
    max_premium: float = 0.20
    shadow_markup: float = 0.25
    insurer_reserve_floor: float = 0.15


@dataclass(slots=True)
class Insurer:
    insurer_id: str
    kind: str
    reserve: float = 0.0
    payout_ratio: float = 0.8
    admin_cost: float = 0.05
    last_update_day: int = -1
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class CorridorPremium:
    corridor_id: str
    insurer_id: str
    premium_rate: float
    loss_rate_est: float
    claims_paid_lookback: float
    premiums_collected_lookback: float
    last_update_day: int = -1

    def signature(self) -> str:
        payload = {
            "corridor": self.corridor_id,
            "insurer": self.insurer_id,
            "premium": round(self.premium_rate, 6),
            "loss": round(self.loss_rate_est, 6),
            "claims": round(self.claims_paid_lookback, 6),
            "premiums": round(self.premiums_collected_lookback, 6),
            "day": int(self.last_update_day),
        }
        digest = sha256(
            str(sorted(payload.items())).encode("utf-8")
        ).hexdigest()
        return digest


@dataclass(slots=True)
class InsuredFlow:
    flow_id: str
    route_key: str
    corridors: list[str]
    insurer_id: str
    weekly_value: float
    status: str = "ACTIVE"
    last_update_day: int = -1


def ensure_insurance_config(world: Any) -> InsuranceConfig:
    cfg = getattr(world, "insurance_cfg", None)
    if not isinstance(cfg, InsuranceConfig):
        cfg = InsuranceConfig()
        world.insurance_cfg = cfg
    return cfg


def _insurers(world: Any) -> dict[str, Insurer]:
    insurers: dict[str, Insurer] = getattr(world, "insurers", {}) or {}
    world.insurers = insurers
    if not insurers:
        insurers["insurer:state"] = Insurer(insurer_id="insurer:state", kind="STATE_MUTUAL", reserve=10.0)
        insurers["insurer:guild"] = Insurer(insurer_id="insurer:guild", kind="GUILD_UNDERWRITER", reserve=5.0)
        insurers["insurer:shadow:0"] = Insurer(insurer_id="insurer:shadow:0", kind="SHADOW_PROTECTION", reserve=3.0)
    return insurers


def _premium_records(world: Any) -> dict[str, CorridorPremium]:
    premiums: dict[str, CorridorPremium] = getattr(world, "premiums_by_corridor", {}) or {}
    world.premiums_by_corridor = premiums
    return premiums


def _insured_flows(world: Any) -> dict[str, InsuredFlow]:
    flows: dict[str, InsuredFlow] = getattr(world, "insured_flows", {}) or {}
    world.insured_flows = flows
    max_active = max(1, int(getattr(getattr(world, "insurance_cfg", None), "max_policies_active", 2000)))
    if len(flows) > max_active:
        victims = sorted(flows.values(), key=lambda fl: (fl.last_update_day, fl.flow_id))[: len(flows) - max_active]
        for victim in victims:
            flows.pop(victim.flow_id, None)
    return flows


def _events(world: Any) -> list[Mapping[str, object]]:
    events: list[Mapping[str, object]] = getattr(world, "insurance_events", []) or []
    world.insurance_events = events[-200:]
    return world.insurance_events


def _bounded_append(world: Any, event: Mapping[str, object]) -> None:
    events = _events(world)
    events.append(dict(event))
    if len(events) > 200:
        overflow = len(events) - 200
        if overflow > 0:
            world.insurance_events = events[overflow:]


def _rng(cfg: InsuranceConfig, world: Any, *, day: int) -> random.Random:
    seed_material = f"{cfg.deterministic_salt}:{getattr(world, 'seed', 0)}:{day}"
    digest = sha256(seed_material.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _corridor_loss_rate(world: Any, corridor_id: str, *, cfg: InsuranceConfig) -> float:
    stress = getattr(world, "corridor_stress", {}) or {}
    return _clamp01(float(stress.get(corridor_id, 0.0)))


def shadow_risk_modifier(world: Any, corridor_id: str, base_risk: float) -> float:
    flows = [flow for flow in _insured_flows(world).values() if corridor_id in flow.corridors and flow.status == "ACTIVE"]
    has_shadow = any(getattr(_insurers(world).get(flow.insurer_id), "kind", "") == "SHADOW_PROTECTION" for flow in flows)
    smuggling_present = bool(getattr(world, "smuggling_by_faction", {}))
    adjusted = base_risk
    if has_shadow:
        adjusted *= 0.8
    elif smuggling_present:
        adjusted = min(1.0, base_risk * 1.2)
    return _clamp01(adjusted)


def _target_premium(
    *,
    cfg: InsuranceConfig,
    insurer: Insurer,
    risk_score: float,
    loss_rate_est: float,
    existing: CorridorPremium | None,
) -> float:
    base = cfg.min_premium + 0.5 * risk_score + 0.5 * loss_rate_est
    stressed = base
    if insurer.reserve < cfg.insurer_reserve_floor:
        stress_factor = 1.0 + (cfg.insurer_reserve_floor - insurer.reserve) / max(cfg.insurer_reserve_floor, 1e-6)
        stressed *= stress_factor
    if insurer.kind == "SHADOW_PROTECTION":
        stressed *= 1.0 + cfg.shadow_markup
    return _clamp_range(stressed, cfg.min_premium, cfg.max_premium)


def _update_metrics(world: Any) -> None:
    metrics = ensure_metrics(world)
    premiums = _premium_records(world)
    flows = _insured_flows(world)
    insurers = _insurers(world)
    metrics.set_gauge("insurance/premium_avg", sum(rec.premium_rate for rec in premiums.values()) / max(1, len(premiums)))
    metrics.set_gauge("insurance/claims_paid", sum(rec.claims_paid_lookback for rec in premiums.values()))
    metrics.set_gauge("insurance/insurer_reserve_total", sum(ins.reserve for ins in insurers.values()))
    active_flows = [flow for flow in flows.values() if flow.status == "ACTIVE"]
    metrics.set_gauge("insurance/flows_insured", len(active_flows))
    if active_flows:
        shadow_count = sum(
            1 for flow in active_flows if _insurers(world).get(flow.insurer_id, Insurer("", "")).kind == "SHADOW_PROTECTION"
        )
        metrics.set_gauge("insurance/shadow_share", shadow_count / max(1, len(active_flows)))
    else:
        metrics.set_gauge("insurance/shadow_share", 0.0)


def run_insurance_week(world: Any, day: int) -> None:
    cfg = ensure_insurance_config(world)
    if not getattr(cfg, "enabled", False):
        return

    insurers = _insurers(world)
    premiums = _premium_records(world)
    flows = _insured_flows(world)

    corridors: set[str] = set()
    risk_ledger = getattr(world, "risk_ledger", None)
    if risk_ledger is not None:
        corridors.update(getattr(risk_ledger, "edges", {}).keys())
    for flow in flows.values():
        corridors.update(flow.corridors)

    for corridor_id in sorted(corridors):
        base_risk = risk_for_edge(world, corridor_id)
        risk_score = shadow_risk_modifier(world, corridor_id, _clamp01(base_risk))
        loss_rate_est = _corridor_loss_rate(world, corridor_id, cfg=cfg)
        for insurer_id, insurer in sorted(insurers.items()):
            key = f"{corridor_id}|{insurer_id}"
            existing = premiums.get(key)
            target = _target_premium(cfg=cfg, insurer=insurer, risk_score=risk_score, loss_rate_est=loss_rate_est, existing=existing)
            if existing is None:
                premium_rate = target
                record = CorridorPremium(
                    corridor_id=corridor_id,
                    insurer_id=insurer_id,
                    premium_rate=premium_rate,
                    loss_rate_est=loss_rate_est,
                    claims_paid_lookback=0.0,
                    premiums_collected_lookback=0.0,
                    last_update_day=day,
                )
            else:
                smooth = _clamp01(cfg.premium_smoothing)
                premium_rate = (1.0 - smooth) * existing.premium_rate + smooth * target
                existing.premium_rate = premium_rate
                existing.loss_rate_est = loss_rate_est
                existing.last_update_day = day
                record = existing
            premiums[key] = record
            _bounded_append(world, {"day": day, "event": "PREMIUM_UPDATED", "corridor": corridor_id, "insurer": insurer_id, "premium": premium_rate})

    collect_premiums(world, day=day)
    _update_metrics(world)


def collect_premiums(world: Any, *, day: int) -> None:
    cfg = ensure_insurance_config(world)
    premiums = _premium_records(world)
    insurers = _insurers(world)
    flows = [flow for flow in _insured_flows(world).values() if flow.status == "ACTIVE"]
    for flow in sorted(flows, key=lambda fl: fl.flow_id):
        insurer = insurers.get(flow.insurer_id)
        if insurer is None:
            continue
        burden = 0.0
        for corridor_id in flow.corridors:
            record = premiums.get(f"{corridor_id}|{flow.insurer_id}")
            rate = record.premium_rate if record else cfg.min_premium
            burden += rate
            if record is not None:
                record.premiums_collected_lookback += rate * flow.weekly_value
        premium_amount = max(0.0, float(flow.weekly_value)) * max(0.0, burden)
        if premium_amount <= 0.0:
            continue
        insurer.reserve = max(0.0, insurer.reserve + premium_amount * (1.0 - insurer.admin_cost))
        transfer(
            world,
            day,
            f"acct:{flow.flow_id}",
            f"acct:{insurer.insurer_id}",
            premium_amount,
            "PAY_INSURANCE_PREMIUM",
            meta={"flow_id": flow.flow_id, "insurer": insurer.insurer_id},
        )
        _bounded_append(
            world,
            {
                "day": day,
                "event": "FLOW_INSURED",
                "flow": flow.flow_id,
                "insurer": insurer.insurer_id,
                "premium": premium_amount,
            },
        )


def pay_claims_for_corridor(world: Any, corridor_id: str, *, loss_value: float, day: int) -> None:
    cfg = ensure_insurance_config(world)
    premiums = _premium_records(world)
    insurers = _insurers(world)
    flows = [flow for flow in _insured_flows(world).values() if flow.status == "ACTIVE" and corridor_id in flow.corridors]
    if not flows or loss_value <= 0:
        return

    total_value = sum(max(0.0, flow.weekly_value) for flow in flows)
    if total_value <= 0:
        total_value = 1.0
    for flow in sorted(flows, key=lambda fl: fl.flow_id):
        insurer = insurers.get(flow.insurer_id)
        if insurer is None:
            continue
        share = max(0.0, flow.weekly_value) / total_value
        payout = max(0.0, loss_value * share * insurer.payout_ratio)
        if payout <= 0:
            continue
        effective = min(payout, insurer.reserve)
        insurer.reserve = max(0.0, insurer.reserve - effective)
        transfer(
            world,
            day,
            f"acct:{insurer.insurer_id}",
            f"acct:{flow.flow_id}",
            effective,
            "INSURANCE_CLAIM_PAYOUT",
            meta={"corridor": corridor_id, "flow_id": flow.flow_id},
        )
        record = premiums.get(f"{corridor_id}|{flow.insurer_id}")
        if record is not None:
            record.claims_paid_lookback += effective
            record.loss_rate_est = _clamp01(record.loss_rate_est + loss_value / max(1.0, cfg.loss_lookback_weeks * 100.0))
        _bounded_append(
            world,
            {
                "day": day,
                "event": "CLAIM_PAID",
                "flow": flow.flow_id,
                "corridor": corridor_id,
                "amount": effective,
            },
        )
    stress = getattr(world, "corridor_stress", {}) or {}
    current = float(stress.get(corridor_id, 0.0))
    stress[corridor_id] = _clamp01(current + loss_value / max(1.0, cfg.loss_lookback_weeks * 50.0))
    world.corridor_stress = stress
    _update_metrics(world)


def insurance_signature(world: Any) -> str:
    premiums = _premium_records(world)
    insurers = _insurers(world)
    flows = _insured_flows(world)
    canonical = {
        "premiums": [rec.signature() for rec in sorted(premiums.values(), key=lambda r: (r.corridor_id, r.insurer_id))],
        "insurers": [
            {
                "id": ins.insurer_id,
                "reserve": round(ins.reserve, 6),
                "kind": ins.kind,
            }
            for ins in sorted(insurers.values(), key=lambda ins: ins.insurer_id)
        ],
        "flows": [
            {
                "id": flow.flow_id,
                "insurer": flow.insurer_id,
                "value": round(flow.weekly_value, 6),
                "status": flow.status,
            }
            for flow in sorted(flows.values(), key=lambda fl: fl.flow_id)
        ],
    }
    payload = str(sorted(canonical.items())).encode("utf-8")
    return sha256(payload).hexdigest()


from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping

from dosadi.runtime.class_system import class_hardship, class_inequality, ensure_class_config, ensure_ward_class_state
from dosadi.runtime.institutions import ensure_policy, ensure_state
from dosadi.runtime.labor import _clamp01 as _clamp01_labor, _ensure_cfg as _ensure_labor_cfg, _ensure_orgs
from dosadi.runtime.ledger import STATE_TREASURY, ensure_ledger_config, ensure_ledger_state, transfer
from dosadi.runtime.telemetry import ensure_metrics, record_event


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class FinanceConfig:
    enabled: bool = False
    update_cadence_days: int = 7
    deterministic_salt: str = "finance-v1"
    max_loans_total: int = 500
    max_loans_per_ward: int = 30
    base_interest_rate: float = 0.01
    predatory_rate_bonus: float = 0.02
    default_threshold: float = 0.35
    seizure_strength: float = 0.4


@dataclass(slots=True)
class Loan:
    loan_id: str
    instrument: str
    issuer_id: str
    borrower_id: str
    ward_id: str
    principal: float
    rate_weekly: float
    term_weeks: int
    weeks_elapsed: int = 0
    outstanding: float = 0.0
    payment_weekly: float = 0.0
    collateral: dict[str, float] = field(default_factory=dict)
    status: str = "ACTIVE"
    notes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class Patronage:
    patron_id: str
    client_id: str
    ward_id: str
    weekly_transfer: float
    loyalty_effect: float
    corruption_effect: float
    status: str = "ACTIVE"


def ensure_finance_config(world: Any) -> FinanceConfig:
    cfg = getattr(world, "finance_cfg", None)
    if not isinstance(cfg, FinanceConfig):
        cfg = FinanceConfig()
        world.finance_cfg = cfg
    return cfg


def _loans(world: Any) -> dict[str, Loan]:
    bucket: dict[str, Loan] = getattr(world, "loans", {}) or {}
    world.loans = bucket
    return bucket


def _patronage(world: Any) -> list[Patronage]:
    contracts: list[Patronage] = getattr(world, "patronage", []) or []
    world.patronage = contracts
    return contracts


def _events(world: Any) -> list[Mapping[str, object]]:
    events: list[Mapping[str, object]] = getattr(world, "finance_events", []) or []
    world.finance_events = events[-200:]
    return world.finance_events


def _rng(cfg: FinanceConfig, world: Any, *, day: int) -> random.Random:
    seed_material = f"{cfg.deterministic_salt}:{getattr(world, 'seed', 0)}:{day}"
    digest = sha256(seed_material.encode("utf-8")).hexdigest()
    seed_int = int(digest[:16], 16)
    return random.Random(seed_int)


def _finance_signature(world: Any) -> str:
    loans = _loans(world)
    patronage = _patronage(world)
    canonical = {
        "loans": [
            {
                "id": loan.loan_id,
                "status": loan.status,
                "outstanding": round(float(loan.outstanding), 6),
                "rate": round(float(loan.rate_weekly), 6),
                "weeks": int(loan.weeks_elapsed),
            }
            for loan in sorted(loans.values(), key=lambda ln: ln.loan_id)
        ],
        "patronage": [
            {
                "patron": p.patron_id,
                "client": p.client_id,
                "ward": p.ward_id,
                "amount": round(float(p.weekly_transfer), 6),
            }
            for p in sorted(patronage, key=lambda pt: (pt.patron_id, pt.client_id))
        ],
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _bounded_append(world: Any, event: Mapping[str, object]) -> None:
    events = _events(world)
    events.append(dict(event))
    if len(events) > 200:
        overflow = len(events) - 200
        if overflow > 0:
            world.finance_events = events[overflow:]


def _score_borrower(world: Any, ward_id: str) -> float:
    hardship = class_hardship(world, ward_id)
    wards = getattr(world, "wards", {}) or {}
    need_index = _clamp01(getattr(wards.get(ward_id), "need_index", 0.0))
    return _clamp01(0.6 * hardship + 0.4 * need_index)


def _issue_loans(world: Any, *, cfg: FinanceConfig, day: int) -> None:
    loans = _loans(world)
    existing_total = len(loans)
    if existing_total >= max(1, int(cfg.max_loans_total)):
        return

    wards = getattr(world, "wards", {}) or {}
    rng = _rng(cfg, world, day=day)
    scores = [
        (ward_id, _score_borrower(world, ward_id)) for ward_id in sorted(wards)
    ]
    scores = [(ward_id, score) for ward_id, score in scores if score > 0.15]
    for ward_id, score in scores:
        per_ward = [loan for loan in loans.values() if loan.ward_id == ward_id and loan.status == "ACTIVE"]
        if len(per_ward) >= max(1, int(cfg.max_loans_per_ward)):
            continue
        if len(loans) >= max(1, int(cfg.max_loans_total)):
            break

        rate = cfg.base_interest_rate + cfg.predatory_rate_bonus * (0.5 if score > 0.65 else 0.0)
        principal = 20.0 + 80.0 * score
        term_weeks = 12
        payment = principal / float(term_weeks)
        loan_id = f"loan:{len(loans):04d}"
        loan = Loan(
            loan_id=loan_id,
            instrument="LOAN_PUBLIC_WORKS",
            issuer_id=STATE_TREASURY,
            borrower_id=f"acct:ward:{ward_id}",
            ward_id=ward_id,
            principal=principal,
            rate_weekly=rate,
            term_weeks=term_weeks,
            outstanding=principal,
            payment_weekly=payment,
            collateral={"toll_rights": round(0.1 + 0.2 * score, 3)},
            notes={"score": score},
        )
        loans[loan_id] = loan
        transfer(world, day, STATE_TREASURY, loan.borrower_id, principal, "LOAN_ISSUED", meta={"loan_id": loan_id})
        _bounded_append(world, {"day": day, "event": "LOAN_ISSUED", "loan_id": loan_id, "ward": ward_id})
        record_event(world, {"kind": "LOAN_ISSUED", "day": day, "loan_id": loan_id})


def _apply_payment(world: Any, loan: Loan, *, day: int, cfg: FinanceConfig) -> None:
    if loan.status not in {"ACTIVE", "RESTRUCTURED"}:
        return
    ensure_ledger_config(world)
    ledger_state = ensure_ledger_state(world)
    payer = ledger_state.accounts.get(loan.borrower_id)
    available = float(getattr(payer, "balance", 0.0)) if payer is not None else 0.0
    planned_payment = loan.payment_weekly or loan.outstanding / max(1, loan.term_weeks - loan.weeks_elapsed + 1)
    effective = min(planned_payment, max(0.0, available))
    success = transfer(
        world,
        day,
        loan.borrower_id,
        loan.issuer_id,
        planned_payment,
        "PAY_DEBT_SERVICE",
        meta={"loan_id": loan.loan_id},
    )
    if success and effective > 0:
        loan.outstanding = max(0.0, loan.outstanding - effective)
        loan.notes["missed_payments"] = max(0, int(loan.notes.get("missed_payments", 0)))
    else:
        loan.notes["missed_payments"] = int(loan.notes.get("missed_payments", 0)) + 1
        _bounded_append(world, {"day": day, "event": "PAYMENT_MISSED", "loan_id": loan.loan_id})


def _accrue_interest(loan: Loan) -> None:
    if loan.status not in {"ACTIVE", "RESTRUCTURED"}:
        return
    loan.outstanding = loan.outstanding * (1.0 + max(0.0, float(loan.rate_weekly)))
    loan.weeks_elapsed += 1


def _apply_seizure(world: Any, loan: Loan, *, day: int, cfg: FinanceConfig) -> None:
    state = ensure_ward_class_state(world, loan.ward_id)
    state.inequality_index = _clamp01(state.inequality_index + 0.1 * cfg.seizure_strength)
    state.hardship_index = _clamp01(state.hardship_index + 0.05 * cfg.seizure_strength)
    inst_state = ensure_state(world, loan.ward_id)
    inst_state.corruption = _clamp01(getattr(inst_state, "corruption", 0.0) + 0.05 * cfg.seizure_strength)
    loan.status = "SEIZED"
    _bounded_append(
        world,
        {
            "day": day,
            "event": "COLLATERAL_SEIZED",
            "loan_id": loan.loan_id,
            "ward": loan.ward_id,
            "collateral": dict(loan.collateral),
        },
    )
    record_event(world, {"kind": "COLLATERAL_SEIZED", "day": day, "loan_id": loan.loan_id})


def _maybe_default(world: Any, loan: Loan, *, day: int, cfg: FinanceConfig) -> None:
    if loan.status not in {"ACTIVE", "RESTRUCTURED"}:
        return
    hardship = class_hardship(world, loan.ward_id)
    inequality = class_inequality(world, loan.ward_id)
    missed = int(loan.notes.get("missed_payments", 0))
    default_risk = 0.6 * hardship + 0.2 * inequality + 0.2 * _clamp01(missed / 4.0)
    early_risk = loan.status == "RESTRUCTURED" and default_risk >= cfg.default_threshold
    if not early_risk and missed <= 0:
        return
    if not early_risk and missed < 2 and default_risk < cfg.default_threshold:
        return

    if loan.status == "RESTRUCTURED":
        _apply_seizure(world, loan, day=day, cfg=cfg)
        return

    loan.status = "DEFAULTED"
    _bounded_append(world, {"day": day, "event": "DEFAULT_TRIGGERED", "loan_id": loan.loan_id})
    record_event(world, {"kind": "DEFAULT_TRIGGERED", "day": day, "loan_id": loan.loan_id})

    loan.term_weeks += 6
    loan.rate_weekly = max(cfg.base_interest_rate * 0.5, loan.rate_weekly * 0.5)
    loan.payment_weekly = loan.outstanding / float(max(1, loan.term_weeks - loan.weeks_elapsed))
    loan.status = "RESTRUCTURED"
    loan.notes["missed_payments"] = 0
    _bounded_append(world, {"day": day, "event": "LOAN_RESTRUCTURED", "loan_id": loan.loan_id})


def _update_metrics(world: Any, *, cfg: FinanceConfig) -> None:
    metrics = ensure_metrics(world)
    gauges = metrics.gauges.setdefault("finance", {}) if hasattr(metrics, "gauges") else {}
    loans = _loans(world)
    active = [ln for ln in loans.values() if ln.status in {"ACTIVE", "RESTRUCTURED"}]
    defaults = [ln for ln in loans.values() if ln.status == "DEFAULTED"]
    seizures = [ln for ln in loans.values() if ln.status == "SEIZED"]
    debt_service = sum(getattr(ln, "payment_weekly", 0.0) for ln in active)
    outstanding = sum(getattr(ln, "outstanding", 0.0) for ln in active)
    gauges["loans_active"] = len(active)
    gauges["debt_outstanding_total"] = outstanding
    gauges["debt_service_weekly"] = debt_service
    gauges["defaults"] = len(defaults)
    gauges["seizures"] = len(seizures)
    patronage_total = sum(p.weekly_transfer for p in _patronage(world) if p.status == "ACTIVE")
    gauges["patronage_total_weekly"] = patronage_total

    for loan in active:
        ward_balance = debt_service / max(1, len(active))
        metrics.topk_add(
            "finance.wards_by_debt",
            loan.ward_id,
            ward_balance,
            payload={"loan_id": loan.loan_id, "outstanding": loan.outstanding},
        )
    metrics.counters["finance.signature"] = _finance_signature(world)


def _patronage_effects(world: Any, contract: Patronage, *, day: int, cfg: FinanceConfig) -> None:
    ensure_class_config(world)
    ensure_state(world, contract.ward_id)
    labor_cfg = _ensure_labor_cfg(world)
    orgs = _ensure_orgs(world, contract.ward_id, cfg=labor_cfg)
    for org in orgs:
        org.militancy = _clamp01_labor(org.militancy - contract.loyalty_effect * 0.1)
        org.corruption = _clamp01_labor(org.corruption + contract.corruption_effect * 0.05)

    class_state = ensure_ward_class_state(world, contract.ward_id)
    class_state.inequality_index = _clamp01(class_state.inequality_index + 0.05 * contract.corruption_effect)
    class_state.hardship_index = _clamp01(class_state.hardship_index + 0.03 * contract.corruption_effect)

    transfer(
        world,
        day,
        contract.patron_id,
        contract.client_id,
        contract.weekly_transfer,
        "PAY_PATRONAGE",
        meta={"ward": contract.ward_id},
    )
    _bounded_append(
        world,
        {
            "day": day,
            "event": "PATRONAGE_PAYMENT",
            "patron": contract.patron_id,
            "client": contract.client_id,
            "ward": contract.ward_id,
        },
    )


def _run_patronage(world: Any, *, day: int, cfg: FinanceConfig) -> None:
    for contract in list(_patronage(world)):
        if contract.status != "ACTIVE":
            continue
        _patronage_effects(world, contract, day=day, cfg=cfg)


def run_finance_week(world: Any, day: int) -> None:
    cfg = ensure_finance_config(world)
    if not getattr(cfg, "enabled", False):
        return
    cadence = max(1, int(cfg.update_cadence_days))
    if day % cadence != 0:
        return
    if getattr(world, "finance_last_run_day", -1) == day:
        return

    loans = _loans(world)
    for loan in sorted(loans.values(), key=lambda ln: ln.loan_id):
        if loan.status not in {"ACTIVE", "RESTRUCTURED"}:
            continue
        _accrue_interest(loan)
        _apply_payment(world, loan, day=day, cfg=cfg)
        if loan.outstanding <= 1e-6:
            loan.status = "PAID"
        else:
            _maybe_default(world, loan, day=day, cfg=cfg)

    _issue_loans(world, cfg=cfg, day=day)
    _run_patronage(world, day=day, cfg=cfg)
    _update_metrics(world, cfg=cfg)
    world.finance_last_run_day = day


def finance_seed_payload(world: Any) -> dict[str, Any] | None:
    cfg = getattr(world, "finance_cfg", None)
    if not isinstance(cfg, FinanceConfig) or not cfg.enabled:
        return None
    loans = _loans(world)
    patronage = _patronage(world)
    return {
        "schema": "finance_v1",
        "loans": [
            {
                "loan_id": loan.loan_id,
                "instrument": loan.instrument,
                "issuer_id": loan.issuer_id,
                "borrower_id": loan.borrower_id,
                "ward_id": loan.ward_id,
                "principal": loan.principal,
                "rate_weekly": loan.rate_weekly,
                "term_weeks": loan.term_weeks,
                "weeks_elapsed": loan.weeks_elapsed,
                "outstanding": loan.outstanding,
                "payment_weekly": loan.payment_weekly,
                "collateral": dict(loan.collateral),
                "status": loan.status,
                "notes": dict(loan.notes),
            }
            for loan in sorted(loans.values(), key=lambda ln: ln.loan_id)
        ],
        "patronage": [
            {
                "patron_id": p.patron_id,
                "client_id": p.client_id,
                "ward_id": p.ward_id,
                "weekly_transfer": p.weekly_transfer,
                "loyalty_effect": p.loyalty_effect,
                "corruption_effect": p.corruption_effect,
                "status": p.status,
            }
            for p in sorted(patronage, key=lambda pt: (pt.patron_id, pt.client_id))
        ],
    }


def save_finance_seed(world: Any, path) -> None:
    payload = finance_seed_payload(world)
    if payload is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True)


__all__ = [
    "FinanceConfig",
    "Loan",
    "Patronage",
    "finance_seed_payload",
    "run_finance_week",
    "save_finance_seed",
]

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from dosadi.runtime.events import EventBus, EventKind


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class SuccessMetric:
    key: str
    target: float
    scope: str = ""


@dataclass(slots=True)
class VerificationSpec:
    telemetry_required: tuple[str, ...] = ()
    inspection_min: int = 0
    ledger_required: tuple[str, ...] = ()


@dataclass(slots=True)
class MandateStakes:
    water_share_delta_if_pass: float = 0.0
    water_share_delta_if_fail: float = 0.0
    sanctions_if_fail: tuple[str, ...] = ()


class MandateStatus:
    ISSUED = "ISSUED"
    ACTIVE = "ACTIVE"
    AUDIT = "AUDIT"
    ADJUDICATED = "ADJUDICATED"
    CLOSED = "CLOSED"


@dataclass(slots=True)
class Mandate:
    mandate_id: str
    issuer: str
    recipient: str
    domain: str
    title: str
    start_day: int
    end_day: int
    success_metrics: tuple[SuccessMetric, ...] = ()
    verification: VerificationSpec = field(default_factory=VerificationSpec)
    stakes: MandateStakes = field(default_factory=MandateStakes)
    reason_codes: tuple[str, ...] = ()
    classification: str = "PUBLIC"
    status: str = MandateStatus.ISSUED
    gap: float = 0.0
    progress_by_metric: dict[str, float] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    last_progress_day: int = -1

    def record_progress(self, *, metric_key: str, value: float, day: int) -> None:
        self.progress_by_metric[metric_key] = float(value)
        self.last_progress_day = max(self.last_progress_day, int(day))

    def score(self) -> float:
        if not self.success_metrics:
            return 1.0
        total = 0.0
        for metric in self.success_metrics:
            target = max(1e-6, float(metric.target))
            value = float(self.progress_by_metric.get(metric.key, 0.0))
            total += min(1.0, value / target)
        return total / len(self.success_metrics)

    def audit_risk(self) -> float:
        if not self.success_metrics:
            return 0.0
        risks = []
        for metric in self.success_metrics:
            target = max(1e-6, float(metric.target))
            value = float(self.progress_by_metric.get(metric.key, 0.0))
            gap_ratio = max(0.0, target - value) / target
            risks.append(gap_ratio)
        return max(risks) if risks else 0.0


@dataclass(slots=True)
class WaterShareContract:
    contract_id: str
    grantor: str
    grantee: str
    W_base_lpd: float
    W_bonus_lpd: float = 0.0
    W_discretion_lpd: float = 0.0
    review_cadence_days: int = 14
    linked_mandates: tuple[str, ...] = ()
    revocation_risk: float = 0.0
    notes: tuple[str, ...] = ()
    current_ratio: float = 1.0

    def adjust_ratio(self, *, delta: float, cfg: "SharePolicy") -> float:
        base_floor = max(0.0, cfg.base_share_floor)
        bonus_cap = max(0.0, cfg.bonus_cap)
        penalty_cap = min(0.0, cfg.punishment_cap)
        updated = self.current_ratio + float(delta)
        updated = max(base_floor, updated)
        updated = min(1.0 + bonus_cap, updated)
        updated = max(1.0 + penalty_cap, updated)
        self.current_ratio = updated
        return self.current_ratio


@dataclass(slots=True)
class ReplacementCase:
    case_id: str
    trigger: str
    target: str
    options: tuple[str, ...]
    decision_tick: int
    chosen: str
    justification: tuple[str, ...]
    evidence_bundle: tuple[str, ...] = ()
    enforcement_chain: tuple[str, ...] = ()


@dataclass(slots=True)
class EvidenceWeight:
    telemetry: float = 0.45
    ledger: float = 0.25
    witness: float = 0.20
    video: float = 0.10


@dataclass(slots=True)
class MandatePolicy:
    cadence_minor_days: int = 7
    cadence_major_days: int = 28
    cadence_campaign_days: int = 180
    gap_default: float = 0.25
    audit_latency_days: int = 7
    audit_escalation_threshold: float = 0.18
    evidence_weight: EvidenceWeight = field(default_factory=EvidenceWeight)
    procedural_legitimacy_bonus: float = 0.12
    scapegoat_bias: float = 0.20


@dataclass(slots=True)
class SharePolicy:
    base_share_floor: float = 0.35
    bonus_cap: float = 0.15
    punishment_cap: float = -0.30
    discretion_ratio: float = 0.05


@dataclass(slots=True)
class ReplacementPolicy:
    fail_window_days: int = 56
    fail_threshold: int = 2
    unrest_threshold: float = 0.65
    coup_signal_threshold: float = 0.40
    leadership_swap_cost: float = 0.12
    full_replace_cost: float = 0.28
    vendetta_escalation_factor: float = 0.30


@dataclass(slots=True)
class MandateSystemConfig:
    enabled: bool = True
    mandates: MandatePolicy = field(default_factory=MandatePolicy)
    shares: SharePolicy = field(default_factory=SharePolicy)
    replacement: ReplacementPolicy = field(default_factory=ReplacementPolicy)


@dataclass(slots=True)
class MandateSystemState:
    mandates: dict[str, Mandate] = field(default_factory=dict)
    share_contracts: dict[str, WaterShareContract] = field(default_factory=dict)
    replacement_cases: dict[str, ReplacementCase] = field(default_factory=dict)
    failure_history: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    last_run_day: int = -1

    def register_failure(self, *, recipient: str, mandate_id: str, day: int, cfg: ReplacementPolicy) -> int:
        entries = self.failure_history.setdefault(recipient, [])
        entries.append((int(day), mandate_id))
        window_start = int(day) - max(0, int(cfg.fail_window_days))
        self.failure_history[recipient] = [
            (d, mid) for d, mid in entries if d >= window_start
        ]
        return len(self.failure_history[recipient])


def ensure_mandate_config(world: Any) -> MandateSystemConfig:
    cfg = getattr(world, "mandate_cfg", None)
    if not isinstance(cfg, MandateSystemConfig):
        cfg = MandateSystemConfig()
        world.mandate_cfg = cfg
    return cfg


def ensure_mandate_state(world: Any) -> MandateSystemState:
    state = getattr(world, "mandate_state", None)
    if not isinstance(state, MandateSystemState):
        state = MandateSystemState()
        world.mandate_state = state
    return state


def record_mandate_progress(
    *, world: Any, mandate_id: str, metric_key: str, value: float, day: int
) -> None:
    state = ensure_mandate_state(world)
    mandate = state.mandates.get(mandate_id)
    if not isinstance(mandate, Mandate):
        return
    mandate.record_progress(metric_key=metric_key, value=value, day=day)
    _emit(
        getattr(world, "event_bus", None),
        kind=EventKind.MANDATE_PROGRESS_UPDATED,
        tick=getattr(world, "tick", 0),
        day=day,
        subject_id=mandate_id,
        payload={"metric": metric_key, "value": round(float(value), 6)},
    )


def issue_mandate(world: Any, mandate: Mandate) -> None:
    state = ensure_mandate_state(world)
    state.mandates[mandate.mandate_id] = mandate


def add_share_contract(world: Any, contract: WaterShareContract) -> None:
    state = ensure_mandate_state(world)
    state.share_contracts[contract.contract_id] = contract


def add_replacement_case(world: Any, case: ReplacementCase) -> None:
    state = ensure_mandate_state(world)
    state.replacement_cases[case.case_id] = case


def _emit(
    event_bus: EventBus | None,
    *,
    kind: str,
    tick: int,
    day: int,
    subject_id: str | None = None,
    actor_id: str | None = None,
    payload: Mapping[str, object] | Iterable[tuple[str, object]] | None = None,
) -> None:
    if isinstance(event_bus, EventBus):
        event_bus.publish(kind=kind, tick=tick, day=day, subject_id=subject_id, actor_id=actor_id, payload=payload)


def _mandate_effective_gap(mandate: Mandate, cfg: MandatePolicy) -> float:
    base_gap = mandate.gap if mandate.gap > 0.0 else cfg.gap_default
    return max(0.0, base_gap)


def _apply_outcome(
    *,
    world: Any,
    mandate: Mandate,
    state: MandateSystemState,
    cfg: MandateSystemConfig,
    passed: bool,
    day: int,
) -> None:
    stakes = mandate.stakes
    delta = stakes.water_share_delta_if_pass if passed else stakes.water_share_delta_if_fail
    subject_contracts = [c for c in state.share_contracts.values() if c.grantee == mandate.recipient]
    for contract in subject_contracts:
        previous_ratio = contract.current_ratio
        updated_ratio = contract.adjust_ratio(delta=delta, cfg=cfg.shares)
        _emit(
            getattr(world, "event_bus", None),
            kind=EventKind.SHARE_ADJUSTED,
            tick=getattr(world, "tick", 0),
            day=day,
            subject_id=contract.contract_id,
            payload={
                "grantee": mandate.recipient,
                "from_ratio": round(previous_ratio, 6),
                "to_ratio": round(updated_ratio, 6),
                "mandate": mandate.mandate_id,
            },
        )
        faction = getattr(world, "factions", {}).get(mandate.recipient)
        if faction is not None:
            faction.water_share_ratio = contract.current_ratio
    if not passed:
        failure_count = state.register_failure(
            recipient=mandate.recipient, mandate_id=mandate.mandate_id, day=day, cfg=cfg.replacement
        )
        _maybe_open_replacement_case(
            world=world,
            state=state,
            cfg=cfg,
            failure_count=failure_count,
            mandate=mandate,
            day=day,
        )
    faction = getattr(world, "factions", {}).get(mandate.recipient)
    if faction is not None:
        shift = 0.05 if passed else -0.08
        faction.performance_index = _clamp01(getattr(faction, "performance_index", 0.5) + shift)
        faction.audit_risk = _clamp01(getattr(faction, "audit_risk", 0.0) + (0.02 if not passed else -0.01))


def _maybe_open_replacement_case(
    *,
    world: Any,
    state: MandateSystemState,
    cfg: MandateSystemConfig,
    failure_count: int,
    mandate: Mandate,
    day: int,
) -> None:
    if failure_count < cfg.replacement.fail_threshold:
        return
    ticks_per_day = getattr(getattr(world, "config", None), "ticks_per_day", getattr(world, "ticks_per_day", 144_000))
    try:
        ticks_per_day = int(ticks_per_day)
    except (TypeError, ValueError):
        ticks_per_day = 144_000
    decision_tick = int(day) * max(1, ticks_per_day)
    target_ward = getattr(getattr(world, "factions", {}).get(mandate.recipient), "home_ward", "")
    ward = getattr(world, "wards", {}).get(target_ward)
    unrest = getattr(ward, "risk_index", 0.0) if ward is not None else 0.0
    options: tuple[str, ...]
    chosen: str
    if unrest >= cfg.replacement.unrest_threshold:
        options = ("WARN", "SANCTION", "LEADERSHIP_SWAP", "FULL_REPLACE")
        chosen = "FULL_REPLACE"
    else:
        options = ("WARN", "SANCTION", "LEADERSHIP_SWAP")
        chosen = "LEADERSHIP_SWAP"
    case_id = f"repl:{mandate.recipient}:{len(state.replacement_cases)}"
    case = ReplacementCase(
        case_id=case_id,
        trigger="MANDATE_FAILURE",
        target=mandate.recipient,
        options=options,
        decision_tick=decision_tick,
        chosen=chosen,
        justification=("MANDATE_FAILURE", "CONTROL_STABILITY" if unrest >= cfg.replacement.unrest_threshold else "PERFORMANCE"),
        evidence_bundle=(mandate.mandate_id,),
    )
    state.replacement_cases[case.case_id] = case
    _emit(
        getattr(world, "event_bus", None),
        kind=EventKind.REPLACEMENT_CONSIDERED,
        tick=getattr(world, "tick", 0),
        day=day,
        subject_id=case.case_id,
        payload={"target": mandate.recipient, "chosen": chosen},
    )
    _emit(
        getattr(world, "event_bus", None),
        kind=EventKind.REPLACEMENT_EXECUTED,
        tick=getattr(world, "tick", 0),
        day=day,
        subject_id=case.case_id,
        payload={"option": chosen, "target": mandate.recipient},
    )


def _adjudicate_mandate(*, world: Any, mandate: Mandate, state: MandateSystemState, cfg: MandateSystemConfig, day: int) -> None:
    score = mandate.score()
    gap_bonus = _mandate_effective_gap(mandate, cfg.mandates)
    passed = score + gap_bonus >= 1.0
    mandate.status = MandateStatus.ADJUDICATED
    findings = []
    if not passed:
        for metric in mandate.success_metrics:
            value = mandate.progress_by_metric.get(metric.key, 0.0)
            if value < metric.target:
                findings.append(f"{metric.key} shortfall {round(metric.target - value, 3)} (target={metric.target})")
    _emit(
        getattr(world, "event_bus", None),
        kind=EventKind.MANDATE_ADJUDICATED,
        tick=getattr(world, "tick", 0),
        day=day,
        subject_id=mandate.mandate_id,
        payload={
            "score": round(score, 6),
            "gap_bonus": round(gap_bonus, 6),
            "passed": passed,
            "findings": findings,
        },
    )
    _apply_outcome(world=world, mandate=mandate, state=state, cfg=cfg, passed=passed, day=day)


def _open_audit(*, world: Any, mandate: Mandate, day: int) -> None:
    mandate.status = MandateStatus.AUDIT
    _emit(
        getattr(world, "event_bus", None),
        kind=EventKind.AUDIT_OPENED,
        tick=getattr(world, "tick", 0),
        day=day,
        subject_id=mandate.mandate_id,
        payload={"recipient": mandate.recipient},
    )


def run_mandate_system_for_day(world: Any, *, day: int) -> None:
    cfg = ensure_mandate_config(world)
    state = ensure_mandate_state(world)
    if not cfg.enabled or state.last_run_day == day:
        return
    state.last_run_day = day

    for mandate_id in sorted(state.mandates.keys()):
        mandate = state.mandates[mandate_id]
        if mandate.status == MandateStatus.ISSUED and day >= mandate.start_day:
            mandate.status = MandateStatus.ACTIVE
            _emit(
                getattr(world, "event_bus", None),
                kind=EventKind.MANDATE_ISSUED,
                tick=getattr(world, "tick", 0),
                day=day,
                subject_id=mandate.mandate_id,
                payload={"recipient": mandate.recipient, "title": mandate.title},
            )
        if mandate.status == MandateStatus.ACTIVE:
            audit_day = mandate.end_day + max(0, cfg.mandates.audit_latency_days)
            if day >= audit_day:
                _open_audit(world=world, mandate=mandate, day=day)
                _adjudicate_mandate(world=world, mandate=mandate, state=state, cfg=cfg, day=day)
                mandate.status = MandateStatus.CLOSED


__all__ = [
    "Mandate",
    "MandatePolicy",
    "MandateStakes",
    "MandateStatus",
    "MandateSystemConfig",
    "MandateSystemState",
    "ReplacementCase",
    "ReplacementPolicy",
    "SharePolicy",
    "SuccessMetric",
    "VerificationSpec",
    "WaterShareContract",
    "add_replacement_case",
    "add_share_contract",
    "ensure_mandate_config",
    "ensure_mandate_state",
    "issue_mandate",
    "record_mandate_progress",
    "run_mandate_system_for_day",
]

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, MutableMapping, Sequence, Tuple

from dosadi.runtime.events import EventBus, EventKind


@dataclass(slots=True)
class WaterAccount:
    """Tracked allocation and redemption state for a ward, facility, or person."""

    account_id: str
    ward_id: str = ""
    branch_id: str = ""
    facility_id: str | None = None
    balance_units: float = 0.0
    allocation_budget_units_per_day: float = 0.0
    reserve_target_units: float = 0.0
    redeemed_units_today: float = 0.0
    last_redeemed_day: int = -1

    def record_redemption(self, *, day: int, units: float) -> None:
        if self.last_redeemed_day != day:
            self.redeemed_units_today = 0.0
            self.last_redeemed_day = day
        self.redeemed_units_today += float(units)


@dataclass(slots=True)
class Entitlement:
    person_id: str
    units_per_day: float
    windows: Tuple[str, ...] = ()
    issuer_org_id: str = ""
    sanction_modifiers: Tuple[str, ...] = ()
    entitlement_id: str | None = None
    active: bool = True

    def signature(self) -> tuple:
        return (
            self.entitlement_id or self.person_id,
            round(float(self.units_per_day), 6),
            tuple(self.windows),
            self.issuer_org_id,
            tuple(self.sanction_modifiers),
            self.active,
        )


@dataclass(slots=True)
class Permit:
    permit_id: str
    holder_id: str
    scope: str
    valid_from: int
    valid_to: int
    issuer_id: str = ""
    issuer_org_id: str = ""
    revoked_at: int | None = None
    revoked_reason: str | None = None

    def is_active(self, *, tick: int, holder_id: str | None = None) -> bool:
        if holder_id is not None and holder_id != self.holder_id:
            return False
        if self.revoked_at is not None and self.revoked_at <= tick:
            return False
        return self.valid_from <= tick <= self.valid_to


@dataclass(slots=True)
class LedgerEntry:
    entry_id: str
    timestamp: int
    actor_id: str
    entry_type: str
    subject_ids: Tuple[str, ...] = ()
    units_delta: float = 0.0
    evidence_refs: Tuple[str, ...] = ()


@dataclass(slots=True)
class AuditEvent:
    audit_id: str
    scope: str
    findings: Tuple[str, ...]
    recommended_actions: Tuple[str, ...] = ()


@dataclass(slots=True)
class WaterAccessConfig:
    reconciliation_tolerance: float = 0.05
    audit_overdraw_units: float = 1.0
    max_audit_events: int = 100


@dataclass(slots=True)
class WaterAccessLedger:
    accounts: MutableMapping[str, WaterAccount] = field(default_factory=dict)
    entitlements: MutableMapping[str, Entitlement] = field(default_factory=dict)
    permits: MutableMapping[str, Permit] = field(default_factory=dict)
    ledger_entries: list[LedgerEntry] = field(default_factory=list)
    audit_events: list[AuditEvent] = field(default_factory=list)
    config: WaterAccessConfig = field(default_factory=WaterAccessConfig)

    def get_or_create_account(
        self,
        account_id: str,
        *,
        ward_id: str | None = None,
        branch_id: str | None = None,
        facility_id: str | None = None,
    ) -> WaterAccount:
        account = self.accounts.get(account_id)
        if isinstance(account, WaterAccount):
            return account
        account = WaterAccount(
            account_id=account_id,
            ward_id=ward_id or "",
            branch_id=branch_id or "",
            facility_id=facility_id,
        )
        self.accounts[account_id] = account
        return account

    def set_allocation(
        self,
        account_id: str,
        *,
        budget_per_day: float,
        reserve_target: float = 0.0,
        ward_id: str | None = None,
        branch_id: str | None = None,
        facility_id: str | None = None,
        tick: int = 0,
        day: int = 0,
        event_bus: EventBus | None = None,
    ) -> WaterAccount:
        account = self.get_or_create_account(
            account_id, ward_id=ward_id, branch_id=branch_id, facility_id=facility_id
        )
        account.allocation_budget_units_per_day = float(budget_per_day)
        account.reserve_target_units = float(reserve_target)
        self._emit(
            event_bus,
            kind=EventKind.WATER_ALLOCATION_SET,
            tick=tick,
            day=day,
            subject_id=account_id,
            payload={
                "budget_per_day": float(budget_per_day),
                "reserve_target": float(reserve_target),
                "ward_id": account.ward_id,
                "branch_id": account.branch_id,
                "facility_id": account.facility_id or "",
            },
        )
        return account

    def record_entitlement(
        self, entitlement: Entitlement, *, tick: int = 0, day: int = 0, event_bus: EventBus | None = None
    ) -> None:
        entitlement_id = entitlement.entitlement_id or entitlement.person_id
        self.entitlements[entitlement_id] = entitlement
        self._emit(
            event_bus,
            kind=EventKind.WATER_ENTITLEMENT_ISSUED,
            tick=tick,
            day=day,
            subject_id=entitlement_id,
            payload={
                "person_id": entitlement.person_id,
                "issuer_org_id": entitlement.issuer_org_id,
                "units_per_day": round(float(entitlement.units_per_day), 6),
                "windows": list(entitlement.windows),
            },
        )

    def record_permit(self, permit: Permit) -> None:
        self.permits[permit.permit_id] = permit

    def verify_permit(
        self,
        permit_id: str,
        *,
        holder_id: str,
        tick: int,
        event_bus: EventBus | None = None,
        day: int | None = None,
    ) -> tuple[bool, str]:
        permit = self.permits.get(permit_id)
        if not isinstance(permit, Permit):
            return False, "unknown_permit"
        if permit.holder_id != holder_id:
            return False, "holder_mismatch"
        if permit.revoked_at is not None and permit.revoked_at <= tick:
            return False, "revoked"
        if not (permit.valid_from <= tick <= permit.valid_to):
            return False, "expired"
        self._emit(
            event_bus,
            kind=EventKind.WATER_PERMIT_VERIFIED,
            tick=tick,
            day=day if day is not None else 0,
            subject_id=permit_id,
            actor_id=holder_id,
            payload={"scope": permit.scope},
        )
        return True, "ok"

    def record_dispensation(
        self,
        account_id: str,
        *,
        units: float,
        tick: int,
        day: int,
        actor_id: str | None = None,
        subject_ids: Sequence[str] | None = None,
        event_bus: EventBus | None = None,
    ) -> LedgerEntry:
        account = self.get_or_create_account(account_id)
        account.record_redemption(day=day, units=units)
        entry = LedgerEntry(
            entry_id=f"led:{day}:{len(self.ledger_entries)}",
            timestamp=tick,
            actor_id=actor_id or "",
            entry_type=EventKind.WATER_UNITS_DISPENSED,
            subject_ids=tuple(subject_ids or (account_id,)),
            units_delta=-float(units),
        )
        self.ledger_entries.append(entry)
        self._emit(
            event_bus,
            kind=EventKind.WATER_UNITS_DISPENSED,
            tick=tick,
            day=day,
            actor_id=actor_id,
            subject_id=account_id,
            payload={"units": round(float(units), 6)},
        )
        return entry

    def reconcile(
        self,
        *,
        tick: int,
        day: int,
        event_bus: EventBus | None = None,
    ) -> list[AuditEvent]:
        ward_budgets: Dict[str, float] = {}
        ward_redeemed: Dict[str, float] = {}
        findings: list[str] = []

        for account_id in sorted(self.accounts):
            account = self.accounts[account_id]
            if account.last_redeemed_day != day:
                account.redeemed_units_today = 0.0
                account.last_redeemed_day = day
            budget = float(account.allocation_budget_units_per_day)
            redeemed = float(account.redeemed_units_today)
            ward_key = account.ward_id or ""
            ward_budgets[ward_key] = ward_budgets.get(ward_key, 0.0) + budget
            ward_redeemed[ward_key] = ward_redeemed.get(ward_key, 0.0) + redeemed

            if self._is_overdrawn(budget=budget, redeemed=redeemed):
                findings.append(
                    f"{account_id} overdrawn by {round(redeemed - budget, 3)} (budget={round(budget, 3)})"
                )

        for ward_id in sorted(ward_budgets):
            budget = ward_budgets[ward_id]
            redeemed = ward_redeemed.get(ward_id, 0.0)
            if self._is_overdrawn(budget=budget, redeemed=redeemed):
                findings.append(
                    f"ward:{ward_id or 'unknown'} redemption exceeds allocation by {round(redeemed - budget, 3)}"
                )

        audit_events: list[AuditEvent] = []
        if findings:
            audit = AuditEvent(
                audit_id=f"audit:{day}:{len(self.audit_events)}",
                scope="water_allocation",
                findings=tuple(findings),
            )
            self.audit_events.append(audit)
            self.audit_events[:] = self.audit_events[-self.config.max_audit_events :]
            audit_events.append(audit)
            self._emit(
                event_bus,
                kind=EventKind.WATER_AUDIT_FINDINGS,
                tick=tick,
                day=day,
                payload={"findings": findings},
            )

        self._emit(
            event_bus,
            kind=EventKind.WATER_LEDGER_RECONCILED,
            tick=tick,
            day=day,
            payload={
                "ward_budgets": {k: round(v, 3) for k, v in sorted(ward_budgets.items())},
                "ward_redeemed": {k: round(v, 3) for k, v in sorted(ward_redeemed.items())},
            },
        )
        return audit_events

    def _is_overdrawn(self, *, budget: float, redeemed: float) -> bool:
        tolerance = max(0.0, self.config.reconciliation_tolerance)
        overdraw_units = redeemed - budget
        if overdraw_units <= 0:
            return False
        allowed = budget * (1.0 + tolerance)
        return redeemed > allowed and overdraw_units >= self.config.audit_overdraw_units

    def _emit(
        self,
        event_bus: EventBus | None,
        *,
        kind: str,
        tick: int,
        day: int,
        subject_id: str | None = None,
        actor_id: str | None = None,
        payload: Mapping[str, object] | Sequence[tuple[str, object]] | None = None,
    ) -> None:
        if isinstance(event_bus, EventBus):
            event_bus.publish(
                kind=kind,
                tick=tick,
                day=day,
                subject_id=subject_id,
                actor_id=actor_id,
                payload=payload,
            )


__all__ = [
    "AuditEvent",
    "Entitlement",
    "LedgerEntry",
    "Permit",
    "WaterAccessConfig",
    "WaterAccessLedger",
    "WaterAccount",
]

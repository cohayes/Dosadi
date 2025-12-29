from dosadi.runtime.events import EventBus, EventBusConfig, EventKind
from dosadi.world.water_access import Permit, WaterAccessLedger


def test_permit_verifier_handles_revocation_and_holder_mismatch():
    ledger = WaterAccessLedger()
    permit = Permit(
        permit_id="permit:1",
        holder_id="person:1",
        scope="facility:hydrator",
        valid_from=0,
        valid_to=10,
    )
    ledger.record_permit(permit)

    ok, reason = ledger.verify_permit("permit:1", holder_id="person:1", tick=5)
    assert ok
    assert reason == "ok"

    ok, reason = ledger.verify_permit("permit:1", holder_id="person:9", tick=5)
    assert not ok
    assert reason == "holder_mismatch"

    permit.revoked_at = 6
    ok, reason = ledger.verify_permit("permit:1", holder_id="person:1", tick=6)
    assert not ok
    assert reason == "revoked"


def test_reconciliation_emits_water_events_and_audit_findings():
    bus = EventBus(EventBusConfig(max_events=50))
    ledger = WaterAccessLedger()

    ledger.set_allocation(
        "facility:1", budget_per_day=10.0, ward_id="ward:1", tick=0, day=0, event_bus=bus
    )
    ledger.record_dispensation(
        "facility:1", units=12.0, tick=1, day=0, actor_id="clerk:1", event_bus=bus
    )

    audits = ledger.reconcile(tick=2, day=0, event_bus=bus)

    assert audits
    events = bus.get_since(0)
    kinds = [event.kind for event in events]
    assert EventKind.WATER_LEDGER_RECONCILED in kinds
    assert EventKind.WATER_AUDIT_FINDINGS in kinds

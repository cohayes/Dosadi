import pytest

from dosadi.runtime.timebase import (
    ACCOUNTING,
    CLEANUP,
    DAILY,
    EVERY_TICK,
    HOURLY,
    INIT,
    PERCEPTION,
    Phase,
    SCHEDULES,
    SOCIAL,
    TICKS_PER_DAY,
    TICKS_PER_HOUR,
    TICKS_PER_MINUTE,
    TICKS_PER_SECOND,
    TRANSIT,
    WEEKLY,
    ticks_for,
)


@pytest.mark.doc("D-RUNTIME-0001")
def test_timebase_derivations_match_spec() -> None:
    assert pytest.approx(TICKS_PER_SECOND, rel=0, abs=1e-9) == 1.67
    assert TICKS_PER_MINUTE == 100
    assert TICKS_PER_HOUR == 6_000
    assert TICKS_PER_DAY == 144_000
    assert WEEKLY == 7 * TICKS_PER_DAY


@pytest.mark.doc("D-RUNTIME-0001")
def test_phase_order_matches_documentation() -> None:
    assert tuple(Phase.ordered()) == (
        INIT,
        PERCEPTION,
        Phase.DECISION,
        SOCIAL,
        TRANSIT,
        ACCOUNTING,
        CLEANUP,
    )


@pytest.mark.doc("D-RUNTIME-0001")
def test_schedule_registry_matches_reference() -> None:
    assert SCHEDULES["hydraulics.issuance"].cadence_ticks == DAILY
    assert SCHEDULES["hydraulics.issuance"].phase is ACCOUNTING
    assert SCHEDULES["rumor.broadcast"].cadence_ticks == EVERY_TICK
    assert SCHEDULES["rumor.broadcast"].phase is SOCIAL
    assert SCHEDULES["governance.update"].cadence_ticks == HOURLY


@pytest.mark.doc("D-RUNTIME-0001")
def test_ticks_for_converts_units() -> None:
    assert ticks_for(days=1) == TICKS_PER_DAY
    assert ticks_for(hours=1) == TICKS_PER_HOUR
    assert ticks_for(minutes=5) == 5 * TICKS_PER_MINUTE
    assert ticks_for(seconds=30) == round(30 * TICKS_PER_SECOND)
    assert ticks_for(days=1, hours=2, minutes=3, seconds=4) == (
        TICKS_PER_DAY
        + 2 * TICKS_PER_HOUR
        + 3 * TICKS_PER_MINUTE
        + round(4 * TICKS_PER_SECOND)
    )

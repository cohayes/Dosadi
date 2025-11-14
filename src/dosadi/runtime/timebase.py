"""Simulation timebase constants and canonical schedules.

Implements the cadence contract described in ``docs/latest/02_runtime/Simulation_Timebase.md``
(D-RUNTIME-0001). All simulation systems should import cadences and the
:class:`Phase` enumeration from this module to avoid divergent magic numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Iterable

# ---------------------------------------------------------------------------
# Primitives (floating point definitions for documentation parity)
# ---------------------------------------------------------------------------
TICKS_PER_SECOND: float = 1.67
SECONDS_PER_MINUTE: int = 60
MINUTES_PER_HOUR: int = 60
HOURS_PER_DAY: int = 24

# ---------------------------------------------------------------------------
# Derived integer cadences
# ---------------------------------------------------------------------------
TICKS_PER_MINUTE: int = round(TICKS_PER_SECOND * SECONDS_PER_MINUTE)
TICKS_PER_HOUR: int = TICKS_PER_MINUTE * MINUTES_PER_HOUR
TICKS_PER_DAY: int = TICKS_PER_HOUR * HOURS_PER_DAY

EVERY_TICK: int = 1
HOURLY: int = TICKS_PER_HOUR
DAILY: int = TICKS_PER_DAY
WEEKLY: int = 7 * TICKS_PER_DAY


class Phase(Enum):
    """Canonical phase taxonomy executed each tick."""

    INIT = auto()
    PERCEPTION = auto()
    DECISION = auto()
    SOCIAL = auto()
    TRANSIT = auto()
    ACCOUNTING = auto()
    CLEANUP = auto()

    @classmethod
    def ordered(cls) -> Iterable["Phase"]:
        """Return phases in the mandated execution order."""

        return (
            cls.INIT,
            cls.PERCEPTION,
            cls.DECISION,
            cls.SOCIAL,
            cls.TRANSIT,
            cls.ACCOUNTING,
            cls.CLEANUP,
        )


@dataclass(frozen=True)
class Schedule:
    """Registry entry describing a named cadence."""

    cadence_ticks: int
    phase: Phase


SCHEDULES: Dict[str, Schedule] = {
    "hydraulics.issuance": Schedule(DAILY, Phase.ACCOUNTING),
    "hydraulics.transit": Schedule(EVERY_TICK, Phase.TRANSIT),
    "rumor.broadcast": Schedule(EVERY_TICK, Phase.SOCIAL),
    "rumor.decay": Schedule(EVERY_TICK, Phase.CLEANUP),
    "economy.royalties": Schedule(DAILY, Phase.ACCOUNTING),
    "governance.update": Schedule(HOURLY, Phase.ACCOUNTING),
}


def ticks_for(*, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0) -> int:
    """Convert wall-clock units into ticks (rounded)."""

    return round(
        days * TICKS_PER_DAY
        + hours * TICKS_PER_HOUR
        + minutes * TICKS_PER_MINUTE
        + seconds * TICKS_PER_SECOND
    )


INIT = Phase.INIT
PERCEPTION = Phase.PERCEPTION
DECISION = Phase.DECISION
SOCIAL = Phase.SOCIAL
TRANSIT = Phase.TRANSIT
ACCOUNTING = Phase.ACCOUNTING
CLEANUP = Phase.CLEANUP


__all__ = [
    "ACCOUNTING",
    "CLEANUP",
    "DAILY",
    "DECISION",
    "EVERY_TICK",
    "HOURLY",
    "INIT",
    "MINUTES_PER_HOUR",
    "PERCEPTION",
    "Phase",
    "Schedule",
    "SECONDS_PER_MINUTE",
    "SCHEDULES",
    "SOCIAL",
    "TICKS_PER_DAY",
    "TICKS_PER_HOUR",
    "TICKS_PER_MINUTE",
    "TICKS_PER_SECOND",
    "TRANSIT",
    "WEEKLY",
    "ticks_for",
]

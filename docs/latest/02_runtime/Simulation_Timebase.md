---
title: Simulation_Timebase
doc_id: D-RUNTIME-0001
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-11
---

# Simulation Timebase (Source of Truth)

**Purpose.** Define global tick cadence and derived scheduling constants for all systems (hydraulics, rumors, economy, governance). No magic numbers anywhere—everything derives from this file.

## Primitives

- **TICKS_PER_SECOND:** `1.67` *(chosen so that one minute = 100 ticks)*
- **SECONDS_PER_MINUTE:** `60`
- **MINUTES_PER_HOUR:** `60`
- **HOURS_PER_DAY:** `24`

> Engines may treat a *tick* as a discrete step and real-time mapping as approximate. Use integer tick counts for schedules; use real time only for UI clocks and profiling.

## Derived constants (integer ticks)

| Quantity           | Value                         | Notes |
|-------------------|-------------------------------:|------|
| `TICKS_PER_MINUTE`| **100**                        | `round(1.67 × 60)` |
| `TICKS_PER_HOUR`  | **6,000**                      | `100 × 60` |
| `TICKS_PER_DAY`   | **144,000**                    | `6,000 × 24` |

> We use integer tick counts for scheduling. If your engine computes `TICKS_PER_MINUTE = round(TICKS_PER_SECOND*60)`, you will get exactly **100** ticks/minute from **1.67** TPS.

## Standard cadences

| Name         | Value (ticks) | Typical Phase   |
|--------------|---------------:|-----------------|
| `EVERY_TICK` | 1              | varies          |
| `HOURLY`     | 6,000          | ACCOUNTING      |
| `DAILY`      | 144,000        | ACCOUNTING      |
| `WEEKLY`     | 1,008,000      | ACCOUNTING      |

## Phase taxonomy

`INIT`, `PERCEPTION`, `DECISION`, `SOCIAL`, `TRANSIT`, `ACCOUNTING`, `CLEANUP`

## Canonical schedules (registry)

All systems should register to **this** cadence table—no inline `% 144000` checks.

```python
# src/dosadi/runtime/timebase.py (reference implementation)

from enum import Enum, auto
from dataclasses import dataclass
from math import floor

# ---- Primitives ----
TICKS_PER_SECOND = 1.67
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24

# ---- Derived (integers) ----
TICKS_PER_MINUTE = round(TICKS_PER_SECOND * SECONDS_PER_MINUTE)  # 100
TICKS_PER_HOUR   = TICKS_PER_MINUTE * MINUTES_PER_HOUR           # 6_000
TICKS_PER_DAY    = TICKS_PER_HOUR * HOURS_PER_DAY                # 144_000

# Standard cadences
EVERY_TICK = 1
HOURLY     = TICKS_PER_HOUR
DAILY      = TICKS_PER_DAY
WEEKLY     = 7 * TICKS_PER_DAY

class Phase(Enum):
    INIT        = auto()
    PERCEPTION  = auto()
    DECISION    = auto()
    SOCIAL      = auto()
    TRANSIT     = auto()
    ACCOUNTING  = auto()
    CLEANUP     = auto()

@dataclass(frozen=True)
class Schedule:
    cadence_ticks: int
    phase: Phase

SCHEDULES = {
    # Hydraulics
    "hydraulics.issuance":   Schedule(DAILY, Phase.ACCOUNTING),
    "hydraulics.transit":    Schedule(EVERY_TICK, Phase.TRANSIT),

    # Rumors
    "rumor.broadcast":       Schedule(EVERY_TICK, Phase.SOCIAL),
    "rumor.decay":           Schedule(EVERY_TICK, Phase.CLEANUP),

    # Economy
    "economy.royalties":     Schedule(DAILY, Phase.ACCOUNTING),

    # Governance / legitimacy
    "governance.update":     Schedule(HOURLY, Phase.ACCOUNTING),
}

def ticks_for(*, days=0, hours=0, minutes=0, seconds=0) -> int:
    """Convert wall time into integer ticks (rounded)."""
    return round(
        days    * TICKS_PER_DAY +
        hours   * TICKS_PER_HOUR +
        minutes * TICKS_PER_MINUTE +
        seconds * TICKS_PER_SECOND
    )
```

## Integration rules

1. **Never** hard-code cadence literals in systems; import from the timebase.
2. When comparing against the current tick, use the registry entries:
   ```python
   if tick % DAILY == 0: issue_barrels()
   ```
3. In tests, tag by document:
   ```python
   @pytest.mark.doc("D-RUNTIME-0001")
   def test_daily_events_align():
       assert SCHEDULES["economy.royalties"].cadence_ticks == TICKS_PER_DAY
   ```

## Open questions
- Do we want an in-sim **calendar** (weeks/months/years) or just day-count?
- Should rumor half-life be expressed as minutes (real-time) or ticks (engine-time)?

## Changelog
- 1.0.0 — Initial timebase spec with **1.67 TPS** ⇒ **100 TPM**.

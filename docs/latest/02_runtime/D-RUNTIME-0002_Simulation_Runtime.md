---
title: Simulation_Runtime
doc_id: D-RUNTIME-0002
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-11
depends_on:
  - D-RUNTIME-0001   # Simulation_Timebase (cadences & phases)
---

# Simulation Runtime (Orchestrator)

> **Purpose.** Define how the simulation advances in discrete ticks, orders phases, schedules systems, and pumps events. **All cadences & phases are imported from `Simulation_Timebase (D-RUNTIME-0001)`**—no magic numbers live here.

---

## 1) Scope & Non‑Goals

**This doc covers**
- Tick advancement & phase order
- Scheduler (cadence gating) and handler registration
- Event queueing (priority, TTL, deferral) and dispatch
- Save/Load boundaries for deterministic replay
- Testing hooks for stepwise execution

**This doc does _not_ define**
- Event payload schemas (see *Event & Message Taxonomy*, doc_id TBA)
- System‑specific logic (Hydraulic_Interfaces, Rumor_Systems, etc.)

---

## 2) Phases

The runtime executes the following phases each tick, in order:

1. **INIT** — one‑time system registration & bootstrap
2. **PERCEPTION** — agents read the world (sensors, queries)
3. **DECISION** — agents select actions (policies, planners)
4. **SOCIAL** — rumor broadcasts, messages, negotiations
5. **TRANSIT** — physical movement, logistics, batch transit
6. **ACCOUNTING** — ledgers, royalties, balances, counters
7. **CLEANUP** — decay, expirations, garbage collection

> Phase identifiers and canonical order are declared in `D-RUNTIME-0001`. Systems **must** register with exactly one phase.

---

## 3) Scheduler

The scheduler runs once per tick, consults cadence constants from the timebase, and invokes handlers whose cadence divides the current tick.

### 3.1 Handler registration API (conceptual)

```python
# Pseudocode — reference implementation may differ slightly

from dataclasses import dataclass
from typing import Callable, Dict, List
from dosadi.runtime.timebase import Phase

@dataclass
class Handler:
    name: str
    cadence_ticks: int
    phase: Phase
    fn: Callable[[int, 'World', 'EventBus'], None]

class Scheduler:
    def __init__(self):
        self.handlers: Dict[Phase, List[Handler]] = {p: [] for p in Phase}

    def register(self, handler: Handler):
        self.handlers[handler.phase].append(handler)

    def tick(self, tick: int, world, bus):
        # Phase-ordered execution
        for phase in Phase:
            # 1) Dispatch scheduled handlers
            for h in self.handlers[phase]:
                if h.cadence_ticks == 1 or tick % h.cadence_ticks == 0:
                    h.fn(tick, world, bus)
            # 2) Pump events targeted to this phase (see §4)
            bus.dispatch_phase(phase, tick, world)
```

### 3.2 Recommended convenience decorator

```python
# dosadi/runtime/schedule.py (optional nicety)
from functools import wraps
from dosadi.runtime.timebase import Phase

_REGISTRY = []

def scheduled(name: str, *, cadence_ticks: int, phase: Phase):
    def deco(fn):
        _REGISTRY.append((name, cadence_ticks, phase, fn))
        @wraps(fn)
        def wrapper(*a, **kw): 
            return fn(*a, **kw)
        return wrapper
    return deco
```

Systems can then do:

```python
from dosadi.runtime.timebase import DAILY, Phase
from dosadi.runtime.schedule import scheduled

@scheduled("hydraulics.issuance", cadence_ticks=DAILY, phase=Phase.ACCOUNTING)
def hydraulics_issue(tick, world, bus):
    ...
```

At boot, the runtime converts `_REGISTRY` entries into `Handler`s and registers them.

---

## 4) Events & Dispatch

The runtime provides a minimal event bus with **priority**, **TTL**, and **phase routing**. Event payload schemas live in *Event & Message Taxonomy* (doc_id TBA).

### 4.1 Event model

| Field     | Type        | Notes                                   |
|-----------|-------------|-----------------------------------------|
| `type`    | enum/str    | e.g., `BarrelCascadeIssued`             |
| `phase`   | Phase       | phase where the event is consumed       |
| `ttl`     | int (ticks) | decremented each tick; drop at zero     |
| `prio`    | int         | lower number = higher priority          |
| `payload` | map         | typed per event schema (see taxonomy)   |

### 4.2 Bus operations (conceptual)

```python
class EventBus:
    def __init__(self):
        self._q = []  # min-heap by (phase, prio, seq)

    def emit(self, event): 
        heapq.heappush(self._q, (event.phase, event.prio, next(_seq), event))

    def dispatch_phase(self, phase, tick, world):
        # 1) decrement TTL for all queued events
        self._q = [(ph, pr, seq, e._replace(ttl=e.ttl-1)) for (ph, pr, seq, e) in self._q if e.ttl > 1]
        # 2) deliver only events targeted to 'phase' in priority order
        batch = []
        while self._q and self._q[0][0] == phase:
            _, _, _, e = heapq.heappop(self._q)
            batch.append(e)
        for e in sorted(batch, key=lambda e: e.prio):
            deliver(e, tick, world)  # routes to system-defined handlers
```

**Deferral.** Systems may re‑emit events with a future phase (or with a countdown encoded in `ttl`).

**Idempotency.** Handlers should be idempotent; events may be replayed during load/replay (see §6).

---

## 5) Determinism & Ordering

- **Phase order** is fixed (see §2).  
- **Within a phase**, handlers are invoked in **registration order** by default. If you need strict ordering, either use priority events or split cadence across phases.  
- **Randomness** (simulation RNG) must be seeded and advanced only in handlers to keep replays deterministic.

---

## 6) Save/Load & Replay

**Save state must include:**
- Current `tick` and `phase` cursor
- World state (entities, inventories, environment)
- Event queue contents (including `ttl` and `prio`)
- Scheduler registry (names only; code is static)

**Deterministic replay:**
- Reinitialize RNG with saved seed
- Rebuild handlers from `_REGISTRY`
- Restore event queue and tick counters
- Step forward; checksums of key aggregates can assert equivalence

---

## 7) Testing hooks

- `step(ticks=N)` — advance `N` ticks
- `advance_to(phase=P)` — run until next occurrence of phase `P`
- `freeze_time()` / `thaw_time()` — pause cadence checks (for isolated handler tests)
- `spy_events(types=[...])` — capture events for assertions

**Recommended pytest markers**
```python
@pytest.mark.doc("D-RUNTIME-0002")
def test_daily_economy_runs_at_accounting_phase(runtime):
    day = runtime.timebase.DAILY
    # Find first ACCOUNTING tick in the next day
    runtime.step(ticks=day)
    assert runtime.metrics["economy.last_run_phase"] == runtime.timebase.Phase.ACCOUNTING
```

---

## 8) Metrics & Telemetry (non-normative)

- `runtime.ticks_per_second_actual` — measured wall‑clock performance
- `runtime.handler_latency_ms{name}` — execution time per handler
- `runtime.event_queue_len{phase}` — queue depth at dispatch
- Optional: histogram of event TTLs at consumption for backpressure insight

---

## 9) Integration rules

1. **Never** reference literal cadence numbers; import from `D-RUNTIME-0001`.
2. Each system registers **one** handler per cadence/phase; avoid giant handlers.
3. Cross‑system communication uses **events** (no direct calls across pillars).
4. Emit **bounded TTL** events; avoid immortal messages.
5. Prefer **idempotent** handlers; design for deterministic replay.

---

## 10) Changelog

- **1.0.0** — Extracted orchestration from legacy “Simulation Runtime” into a slim orchestrator spec. Timebase constants moved to `Simulation_Timebase (D-RUNTIME-0001)`.

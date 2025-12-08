---
title: Supervisor_Reporting_And_Council_Input_MVP
doc_id: D-RUNTIME-0223
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-12-06
depends_on:
  - D-RUNTIME-0200   # Founding_Wakeup_Simulation_Loop_MVP
  - D-RUNTIME-0212   # Initial_Work_Detail_Taxonomy_MVP
  - D-RUNTIME-0213   # Work_Detail_Behaviors_MVP_Scout_And_Inventory
  - D-RUNTIME-0214   # Council_Metrics_And_Staffing_Response_MVP
  - D-RUNTIME-0219   # Needs_Stress_And_Performance_MVP
  - D-RUNTIME-0221   # Work_History_Specialization_And_Proto_Guilds_MVP
  - D-RUNTIME-0222   # Promotion_And_Tier_Evolution_MVP
  - D-AGENT-0020     # Canonical_Agent_Model
  - D-AGENT-0022     # Agent_Core_State_Shapes
  - D-MEMORY-0102    # Episode_Representation
  - D-MEMORY-0200    # Belief_System_Overview
  - D-MEMORY-0300    # Sleep_And_Episode_Consolidation_Design
---

# Supervisor Reporting and Council Input (MVP) — D-RUNTIME-0223

## 1. Purpose & scope

This document specifies a minimal loop where **Tier-2 supervisors** become
the council’s primary **eyes and mouths**:

- Supervisors periodically write **summary reports** about their work area.
- Reports are stored in a simple **admin log / council inbox**.
- The council reads these reports to derive **staffing and strain metrics**,
  reducing its reliance on god-like direct inspection of world state.

Loop (MVP):

1. Tier-1 agents perform work and generate episodes as usual.
2. Tier-2 supervisors (from D-RUNTIME-0222) accumulate work and observation
   episodes.
3. Once per “day” (or similar window), each supervisor writes an **aggregated
   report** summarizing their crew and facilities.
4. Reports go into `world.admin_logs` and are used during council updates to
   adjust staffing and detect strain or issues.

Scope (MVP):

- Reporting is coarse and periodic; no fine-grained log streaming.
- Council still has access to direct metrics if needed, but **trends** and
  “how things feel” come from supervisor reports.
- Only Tier-2 supervisors write reports; Tier-1 agents only generate episodes.


## 2. World-level admin log

### 2.1 AdminLogEntry structure

Define a minimal admin log entry in a new module, e.g.
`dosadi/runtime/admin_log.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from dosadi.runtime.work_details import WorkDetailType


@dataclass
class AdminLogEntry:
    log_id: str

    # Author and context
    author_agent_id: str
    work_type: WorkDetailType
    crew_id: Optional[str]

    tick_start: int
    tick_end: int

    # Aggregated simple metrics for this window
    metrics: Dict[str, float] = field(default_factory=dict)

    # Categorical flags / notes
    # e.g. {"strain_high": 1.0, "queue_chronic": 1.0}
    flags: Dict[str, float] = field(default_factory=dict)

    # Optional short text-ish notes (still structuredish)
    notes: Dict[str, str] = field(default_factory=dict)
```

This is a deliberately small, structured view of what a supervisor thinks
matter for their crew and facilities in a given time window.


### 2.2 WorldState additions

Extend `WorldState`:

```python
from dataclasses import dataclass, field
from typing import Dict

from dosadi.runtime.admin_log import AdminLogEntry


@dataclass
class WorldState:
    ...
    admin_logs: Dict[str, AdminLogEntry] = field(default_factory=dict)
    next_admin_log_seq: int = 0
```

Helper for generating ids:

```python
def create_admin_log_id(world: WorldState) -> str:
    seq = world.next_admin_log_seq
    world.next_admin_log_seq += 1
    return f"admin_log:{seq}"
```


## 3. Supervisor daily reporting cadence

### 3.1 Per-supervisor reporting schedule

We want each supervisor to write **at most one report per day** per work type.

Add fields to `AgentState` (if not already present):

```python
from dataclasses import dataclass, field

@dataclass
class AgentState:
    ...
    last_report_tick: int = 0
```

Runtime constants in a config module:

```python
SUPERVISOR_REPORT_INTERVAL_TICKS: int = 120_000  # ~one "day"
MIN_TICKS_AS_SUPERVISOR_BEFORE_REPORT: int = 40_000
```


### 3.2 Eligibility for report-writing

A Tier-2 supervisor is eligible to write a report if:

- `agent.tier == 2`,
- `agent.supervisor_work_type is not None`,
- `current_tick - agent.last_report_tick >= SUPERVISOR_REPORT_INTERVAL_TICKS`,
- `agent.total_ticks_employed >= MIN_TICKS_AS_SUPERVISOR_BEFORE_REPORT`,
- Needs are not in extreme crisis (optional filter).


### 3.3 Creating a micro-goal: WRITE_REPORT

Add a new goal type for clarity:

```python
from enum import Enum, auto

class GoalType(Enum):
    ...
    WRITE_SUPERVISOR_REPORT = auto()
```

When we detect an eligible supervisor during council or agent update, we
create a small, short-lived goal:

```python
from dosadi.agents.goals import Goal, GoalStatus, GoalType

def maybe_create_supervisor_report_goal(world: WorldState, agent: AgentState) -> None:
    if agent.tier != 2 or agent.supervisor_work_type is None:
        return

    if world.current_tick - agent.last_report_tick < SUPERVISOR_REPORT_INTERVAL_TICKS:
        return

    if agent.total_ticks_employed < MIN_TICKS_AS_SUPERVISOR_BEFORE_REPORT:
        return

    # Avoid reports during acute need crisis
    if agent.physical.hunger_level > 1.2 or agent.physical.hydration_level < 0.2:
        return

    # Only create if no pending/active report goal
    for g in agent.goals:
        if g.goal_type == GoalType.WRITE_SUPERVISOR_REPORT and g.status in (
            GoalStatus.PENDING,
            GoalStatus.ACTIVE,
        ):
            return

    goal = Goal(
        goal_id=f"goal:write_report:{agent.id}:{world.current_tick}",
        goal_type=GoalType.WRITE_SUPERVISOR_REPORT,
        status=GoalStatus.PENDING,
        created_tick=world.current_tick,
        metadata={},
    )
    agent.goals.append(goal)
```

Call `maybe_create_supervisor_report_goal` in the agent update loop,
after other core need-based goals (food, water, rest) have been created.


## 4. Handling WRITE_SUPERVISOR_REPORT goals

### 4.1 Goal handler skeleton

In your goal dispatcher, add:

```python
if goal.goal_type == GoalType.WRITE_SUPERVISOR_REPORT:
    _handle_write_supervisor_report(world, agent, goal, rng)
    return
```

Implementation outline:

```python
from dosadi.runtime.admin_log import AdminLogEntry, create_admin_log_id


def _handle_write_supervisor_report(
    world: WorldState,
    agent: AgentState,
    goal: Goal,
    rng: random.Random,
) -> None:
    if agent.tier != 2 or agent.supervisor_work_type is None:
        goal.status = GoalStatus.FAILED
        return

    work_type = agent.supervisor_work_type
    crew_id = agent.supervisor_crew_id

    # Decide reporting window (MVP: last "day")
    tick_end = world.current_tick
    tick_start = max(0, tick_end - SUPERVISOR_REPORT_INTERVAL_TICKS)

    # Aggregate metrics from episodes + simple state
    metrics, flags, notes = _aggregate_supervisor_report_inputs(
        world=world,
        agent=agent,
        work_type=work_type,
        crew_id=crew_id,
        tick_start=tick_start,
        tick_end=tick_end,
    )

    log_id = create_admin_log_id(world)
    entry = AdminLogEntry(
        log_id=log_id,
        author_agent_id=agent.id,
        work_type=work_type,
        crew_id=crew_id,
        tick_start=tick_start,
        tick_end=tick_end,
        metrics=metrics,
        flags=flags,
        notes=notes,
    )
    world.admin_logs[log_id] = entry

    agent.last_report_tick = world.current_tick

    # Emit episodes for the supervisor and council
    _emit_report_episodes(world, agent, entry)

    goal.status = GoalStatus.COMPLETED
```


### 4.2 Report aggregation helper

MVP aggregation only needs to use:

- simple **world counters** (e.g. total meals served, queues, throughput) if
  already available,
- supervisor’s own **episodes** in `agent.episodes.daily` for the window.

Example:

```python
from typing import Tuple, Dict


def _aggregate_supervisor_report_inputs(
    world: WorldState,
    agent: AgentState,
    work_type: WorkDetailType,
    crew_id: Optional[str],
    tick_start: int,
    tick_end: int,
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, str]]:
    metrics: Dict[str, float] = {}
    flags: Dict[str, float] = {}
    notes: Dict[str, str] = {}

    # Simple MVP: count episodes tagged with work_type and "queue" / "strain" / "incident"
    total_work_eps = 0
    queue_issue_eps = 0
    strain_eps = 0
    incident_eps = 0

    for ep in agent.episodes.daily:
        if ep.tick < tick_start or ep.tick > tick_end:
            continue
        if work_type.name.lower() not in {t.lower() for t in ep.tags}:
            continue

        total_work_eps += 1

        if "queue" in ep.tags:
            queue_issue_eps += 1
        if "strain" in ep.tags or "overworked" in ep.tags:
            strain_eps += 1
        if "incident" in ep.tags or "failure" in ep.tags:
            incident_eps += 1

    metrics["episodes_work_related"] = float(total_work_eps)
    metrics["episodes_queue_issues"] = float(queue_issue_eps)
    metrics["episodes_strain"] = float(strain_eps)
    metrics["episodes_incidents"] = float(incident_eps)

    # Very naive strain flag
    if total_work_eps > 0:
        strain_ratio = strain_eps / total_work_eps
        queue_ratio = queue_issue_eps / total_work_eps
    else:
        strain_ratio = 0.0
        queue_ratio = 0.0

    flags["strain_high"] = 1.0 if strain_ratio > 0.3 else 0.0
    flags["queue_chronic"] = 1.0 if queue_ratio > 0.3 else 0.0

    notes["summary"] = (
        f"Supervisor report for {work_type.name} crew {crew_id or 'none'}; "
        f"work_eps={total_work_eps}, strain_eps={strain_eps}, incidents={incident_eps}."
    )

    return metrics, flags, notes
```

This is intentionally crude; later we can refine tags and metrics as more
episode types come online.


### 4.3 Report-related episodes

Add a new verb in `EpisodeVerb`:

```python
class EpisodeVerb(Enum):
    ...
    SUPERVISOR_REPORT_SUBMITTED = auto()
```

In `EpisodeFactory`:

```python
from dosadi.runtime.admin_log import AdminLogEntry


def create_supervisor_report_episode(
    self,
    owner_agent_id: str,
    tick: int,
    entry: AdminLogEntry,
) -> Episode:
    tags = {"report", "supervisor", entry.work_type.name.lower()}
    if entry.crew_id:
        tags.add("crew")

    return Episode(
        episode_id=self._next_episode_id(),
        owner_agent_id=owner_agent_id,
        tick=tick,
        location_id=None,
        channel=EpisodeChannel.DIRECT,
        target_type=EpisodeTargetType.SELF,
        target_id=owner_agent_id,
        verb=EpisodeVerb.SUPERVISOR_REPORT_SUBMITTED,
        summary_tag="supervisor_report_submitted",
        goal_relation=EpisodeGoalRelation.SUPPORTS,
        goal_relevance=0.3,
        outcome=EpisodeOutcome.SUCCESS,
        emotion=EmotionSnapshot(valence=0.3, arousal=0.2, threat=0.0),
        importance=0.3,
        reliability=0.9,
        tags=tags,
        details={
            "log_id": entry.log_id,
            "work_type": entry.work_type.name,
            "crew_id": entry.crew_id or "",
            "episodes_work_related": entry.metrics.get("episodes_work_related", 0.0),
            "episodes_strain": entry.metrics.get("episodes_strain", 0.0),
            "episodes_incidents": entry.metrics.get("episodes_incidents", 0.0),
        },
    )
```

If you maintain a “council agent” placeholder (e.g. `agent_id="council:founders"`),
you may also emit a mirror episode attached to that agent to represent that
the council “read” the report. For MVP, this is optional.


Helper used in the handler:

```python
def _emit_report_episodes(world: WorldState, agent: AgentState, entry: AdminLogEntry) -> None:
    factory = EpisodeFactory(world=world)
    ep = factory.create_supervisor_report_episode(
        owner_agent_id=agent.id,
        tick=world.current_tick,
        entry=entry,
    )
    agent.record_episode(ep)
```


## 5. Council metrics from reports

### 5.1 Existing metrics

D-RUNTIME-0214 defines council metrics based on direct world inspection
(e.g. queue lengths, throughput). We add a **report-derived layer** that
computes softer metrics like “reported strain” per work type.

### 5.2 Aggregating admin logs

Add helper in council module:

```python
from collections import defaultdict
from typing import Dict

from dosadi.runtime.admin_log import AdminLogEntry


def compute_report_based_metrics(world: WorldState) -> Dict[str, float]:
    # aggregated over some horizon, e.g. last N ticks
    HORIZON = 240_000  # last two "days"
    cutoff_tick = max(0, world.current_tick - HORIZON)

    strain_counts = defaultdict(float)
    strain_weighted_reports = defaultdict(float)
    queue_counts = defaultdict(float)
    queue_weighted_reports = defaultdict(float)

    for entry in world.admin_logs.values():
        if entry.tick_end < cutoff_tick:
            continue
        key = entry.work_type

        strain_flag = entry.flags.get("strain_high", 0.0)
        queue_flag = entry.flags.get("queue_chronic", 0.0)

        strain_counts[key] += 1.0
        strain_weighted_reports[key] += strain_flag

        queue_counts[key] += 1.0
        queue_weighted_reports[key] += queue_flag

    metrics: Dict[str, float] = {}

    for work_type, count in strain_counts.items():
        if count <= 0.0:
            continue
        avg_strain = strain_weighted_reports[work_type] / count
        avg_queue = queue_weighted_reports[work_type] / max(queue_counts[work_type], 1.0)
        metrics[f"report_avg_strain_{work_type.name.lower()}"] = avg_strain
        metrics[f"report_avg_queue_{work_type.name.lower()}"] = avg_queue

    return metrics
```


### 5.3 Using report metrics in staffing decisions

In `update_council_metrics_and_staffing`, after you compute your existing
metrics, call:

```python
report_metrics = compute_report_based_metrics(world)
```

Then, when deciding desired headcounts per work type, you can include
report-based strain:

- If `report_avg_strain_T` is high, try to **increase** staffing for `T`.
- If `report_avg_queue_T` is high, increase staffing or change assignment.

MVP example (pseudo):

```python
for work_type in WorkDetailType:
    base_target = base_staffing[work_type]
    strain_key = f"report_avg_strain_{work_type.name.lower()}"
    strain = report_metrics.get(strain_key, 0.0)

    if strain > 0.5:
        base_target += 1  # small bump

    desired_counts[work_type] = base_target
```

The exact function is tunable; the important part is that **reports** now
affect council decisions, not only raw global stats.


## 6. Integration order & boundaries

### 6.1 Recommended implementation order

1. Introduce `AdminLogEntry`, `world.admin_logs`, and id generation.
2. Add `last_report_tick` to `AgentState`.
3. Add `SUPERVISOR_REPORT_INTERVAL_TICKS`, `MIN_TICKS_AS_SUPERVISOR_BEFORE_REPORT`.
4. Implement `maybe_create_supervisor_report_goal` and wire it into the per-agent goal creation stage.
5. Add `GoalType.WRITE_SUPERVISOR_REPORT` and `_handle_write_supervisor_report`.
6. Implement `_aggregate_supervisor_report_inputs` (even in a minimal form).
7. Add `SUPERVISOR_REPORT_SUBMITTED` episode verb and `create_supervisor_report_episode`.
8. Add `compute_report_based_metrics` and incorporate its output into council staffing heuristics.

### 6.2 Simplifications

- We do not differentiate between types of supervisors (they all report in the same style).
- Reports do not directly change protocols yet; they only bias staffing.
- There is no explicit “ignore” or “punish” for supervisors who under/over-report.

Once D-RUNTIME-0223 is implemented, the simulation will have a clear,
data-carrying channel:
**Tier-1 episodes → Tier-2 summaries → council metrics → staffing decisions**,

laying the groundwork for more complex information politics, misreporting, and
protocol changes in later phases.

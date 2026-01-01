---
title: Reform_Movements_and_Anti_Corruption_Drives
doc_id: D-RUNTIME-0304
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2026-01-01
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0271   # Governance Failure Incidents v1
  - D-RUNTIME-0286   # Media & Information Channels v1
  - D-RUNTIME-0287   # Counterintelligence & Espionage v1
  - D-RUNTIME-0296   # Policing Doctrine v2
  - D-RUNTIME-0299   # Succession & Leadership Legitimacy v1
  - D-RUNTIME-0302   # Shadow State & Deep Corruption v1
  - D-RUNTIME-0303   # Reform Movements & Anti-Corruption Drives v1 — Implementation Checklist
---

# Reform Movements & Anti‑Corruption Drives v1 (D-RUNTIME-0304)

## 0) Design intent

Dosadi does not just *decay*. It also **tries to heal**—and those healing attempts can succeed, stall, or backfire into purges and coups.

This spec adds **legitimacy restoration loops** that emerge naturally from:
- **exposure** (scandals become undeniable),
- **hardship** (the system stops delivering),
- **elite splits** (factions fight over who pays the costs of “cleaning house”),
- **procedural leverage** (audits, courts, record systems, and policing doctrine).

**Tone constraint (Dosadi):** reform is not “goodness.” It is a power move that claims moral clothing.

## 1) Scope and non-goals

### In scope
- How **reform movements** form, persist, and dissolve.
- How **watchdogs** (auditors, clerks, inspectors, clergy, jurists) gain power or get captured.
- How reform attempts interact with **law/courts**, **rumor/media**, **policing doctrine**, **shadow budgets**, and **succession legitimacy**.
- Deterministic runtime update rules + bounded state suitable for snapshots/seeds.

### Out of scope (v1)
- Detailed individual-agent “street activism” simulation.
- Full investigative dialogue trees.
- UI beyond cockpit panels and telemetry already defined in D-RUNTIME-0260.

## 2) Core concepts

### 2.1 Reform movement (RM)
A reform movement is a **coalition of factions and offices** attempting to change:
- enforcement priorities (policing doctrine),
- audit thresholds,
- contract/case consistency expectations,
- anti-smuggling/anti-bribery pressure,
- leadership legitimacy components (more procedural legitimacy, less fear legitimacy).

Reform movements have three practical levers:
1) **Information:** what gets exposed (or buried).
2) **Procedure:** what “counts” as evidence and compliance.
3) **Force:** what gets enforced, and against whom.

### 2.2 Watchdogs
A watchdog is an office or institution with routine access to **records + enforcement pathways**:
- civic auditors, court clerks, high arbiters, inspectorate squads,
- clerical recordkeepers, canon lawyers, doctrinal judges,
- industrial QA/safety boards with shutdown authority.

Watchdogs can be:
- **Independent** (rare), **Sponsored** (common), or **Captured** (frequent).

### 2.3 Backlash
Reform creates losers. Losers respond with:
- **counter-coups**, **purges**, **procedural sabotage** (clerk capture),
- **propaganda** and **delegitimization** campaigns,
- **selective enforcement** that breaks the reform’s credibility.

Backlash is a feature, not a bug.

## 3) Player relevance

Even though v1 is world-sim-first, reforms should be legible to a player as:
- new inspection patterns at checkpoints,
- new audit requests,
- sudden “anti-smuggling weeks,”
- arrests of previously untouchable middle managers,
- rumor churn about “clean hands” vs “witch hunts,”
- opportunities: whistleblowing, couriering evidence, forging, bribing, intimidation, safehouse routing.

## 4) State model

All state is bounded, deterministic, and snapshot-friendly.

### 4.1 Data structures (world state)

```python
@dataclass(slots=True)
class ReformConfig:
    enabled: bool = True
    cadence_days: int = 7  # weekly update
    max_movements: int = 12
    max_watchdogs: int = 24
    max_events: int = 200

    # Formation thresholds
    scandal_exposure_trigger: float = 0.75
    hardship_trigger: float = 0.70
    legitimacy_trigger: float = 0.35

    # Dynamics
    formation_chance_base: float = 0.08
    decay_rate: float = 0.03
    capture_risk_base: float = 0.05
    backlash_base: float = 0.04

    # Effects
    policing_proc_shift_max: float = 0.15   # per movement peak
    capture_reduction_max: float = 0.20     # per scandal cleanup
    fear_legit_penalty: float = 0.10        # when reform pushes transparency
    rumor_amplification: float = 0.25       # reform increases rumor volume
```

```python
@dataclass(slots=True)
class WatchdogInstitution:
    watchdog_id: str
    ward_id: str | None           # some are ward-scoped, some polity-scoped
    kind: str                     # AUDIT|INSPECTORATE|CLERICAL|JUDICIAL|INDUSTRIAL_QA
    sponsor_faction: str | None
    independence: float           # 0..1
    capture: float                # 0..1
    capacity: float               # 0..1 (how much it can process)
    last_update_day: int = -1
```

```python
@dataclass(slots=True)
class ReformMovement:
    movement_id: str
    scope: str                    # WARD|POLITY
    ward_id: str | None
    polity_id: str | None
    sponsor_faction: str | None
    coalition: dict[str, float]   # faction_id -> commitment weight
    agenda: dict[str, float]      # POLICY knobs (audit strictness, policing doctrine, court consistency)
    momentum: float               # 0..1
    legitimacy_claim: float       # 0..1 (how persuasive it is in rumor/media)
    risk_of_backlash: float       # 0..1
    status: str = "ACTIVE"        # ACTIVE|STALLED|SUCCESS|CRUSHED|COOPTED
    start_day: int = 0
    last_update_day: int = -1
```

```python
@dataclass(slots=True)
class ReformEvent:
    day: int
    movement_id: str
    kind: str  # FORMATION|LEAK|PROSECUTION|PURGE|POLICY_SHIFT|STALL|SUCCESS|CRUSH
    payload: dict[str, object]
```

World stores:
- `world.reform_cfg: ReformConfig`
- `world.watchdogs: dict[str, WatchdogInstitution]`
- `world.reform_movements: dict[str, ReformMovement]`
- `world.reform_events: list[ReformEvent]` (bounded ring)

### 4.2 Derived signals used as inputs
Existing systems already compute many of these (names shown conceptually; bind to your actual world fields):
- `avg_hardship(polity|ward)` (hardship/inequality indices)
- `avg_legitimacy(polity leadership)` (D-RUNTIME-0299)
- `capture_index(ward)` and `exposure_risk(ward)` (D-RUNTIME-0302)
- `policing_doctrine(ward/polity)` (D-RUNTIME-0296)
- `court_consistency` / `arbiter_consistency` (Justice/Contracts + telemetry)
- `media_pressure` and `truth_regime` (D-RUNTIME-0286 + truth_regimes)

## 5) Weekly update algorithm (deterministic)

`run_reforms_for_day(world, day)` only does work on cadence days.

### 5.1 Candidate wards/polities
Select top-K “pressure zones” deterministically:
- highest `exposure_risk`,
- highest `capture`,
- lowest `legitimacy`,
- highest `hardship`.

### 5.2 Formation step
For each pressure zone, compute a **formation score**:

```
S = w1*exposure + w2*hardship + w3*(1-legitimacy) + w4*media_pressure
P(form) = clamp01(formation_chance_base + S*0.25 - existing_movement_penalty)
```

If `pseudo_rand01(seed, day, zone_id, "reform_form") < P(form)`:
- create a ReformMovement with:
  - sponsor faction: either “inside reform” (a court/clerical/industrial sponsor) or “rival faction” (weaponized reform),
  - agenda: shift toward procedural policing, higher audit strictness, higher evidence requirements for confiscations, etc.
- spawn/assign a WatchdogInstitution if none exists in that zone.

### 5.3 Movement evolution
For each active movement:
- update momentum:
  - increases if scandals appear, prosecutions succeed, or audits find real theft,
  - decreases if captured, if enforcement fails, or if backlash events occur.
- update coalition weights:
  - factions join if expected value improves (reduce rival’s power, gain legitimacy, seize offices).
  - factions leave if crackdown risk rises or sponsor becomes toxic.

### 5.4 Watchdog evolution
Each watchdog updates:
- **capture drift** (toward capture if surrounded by high influence edges, bribery exposure, low independence),
- **capacity** (can be increased by sponsor funding; decreased by sabotage or purge),
- may trigger event: `LEAK` (if independence high + exposure high).

### 5.5 Effects application (policy knobs)
Movements apply bounded changes to:
- policing doctrine procedural share (increase),
- enforcement selectivity bias (reduce capture effects),
- audit frequency/strictness (increase),
- court evidence threshold (increase consistency, reduce arbitrary confiscations).

All effects should be:
- small per-cadence deltas,
- capped by config,
- reversible over time if movement stalls or is crushed.

### 5.6 Backlash / suppression step
For each movement, compute backlash chance:

```
B = backlash_base + (movement.momentum*0.2) + (threat_to_elites*0.3) + (fear_legit_dependence*0.2)
```

If triggered:
- choose response (deterministic weighted pick):
  - **Co-opt** (offer offices, shift agenda, reduce independence) → status COOPTED
  - **Crush** (purge watchdog, terror policing spike) → status CRUSHED
  - **Counter-coup** (leadership instability event) → interacts with D-RUNTIME-0299
  - **Scapegoat purge** (token arrests; capture unchanged; movement stalls)

## 6) Integration points

### 6.1 Shadow state (D-RUNTIME-0302)
- Successful reforms can reduce `capture` and `shadow_state` indices modestly.
- Co-opted reforms can *increase* capture by legitimizing new “clean” channels for graft.

### 6.2 Law & enforcement (D-RUNTIME-0265, Justice_Contracts)
- Reforms can create “priority dockets” for corruption cases.
- Watchdogs can create evidence packets that feed into case initiation.

### 6.3 Rumor/media/truth regimes (D-RUNTIME-0286 + truth_regimes)
- Reforms increase rumor volume and polarization:
  - “clean hands” narrative vs “witch hunt” narrative.
- Truth regimes determine whether leaked evidence becomes “real” socially.

### 6.4 Policing doctrine (D-RUNTIME-0296)
- Procedural share can rise; terror share can spike during backlash.
- The player experiences this as checkpoint strictness, bribe behavior, and search patterns.

### 6.5 Succession/legitimacy (D-RUNTIME-0299)
- Reform success increases procedural legitimacy.
- Crushing reforms increases fear legitimacy short term, but may reduce ideological/performance legitimacy long term.

## 7) Failure modes (story fuel)

- **Reform-as-weapon:** rival faction sponsors audits to kneecap an opponent; corruption stays, only faces change.
- **Clerk capture counterattack:** records falsified → “reality split” (true events cannot be proven).
- **Purity spiral:** reform movement turns into purge ladder (everyone is suspect).
- **Security backlash:** terror policing rises; smuggling adapts; court dockets overflow.
- **Hero watchdog assassination:** watchdog removed; movement collapses; martyr rumors.

## 8) Telemetry & cockpit

Minimum metrics:
- movements by status (counts)
- watchdog capture vs independence scatter
- per-ward “reform pressure” score
- deltas applied to policing doctrine & audit strictness
- major events log (bounded)

Admin panels (extend existing cockpit):
- “Reform map” (top wards)
- “Movement inspector” (coalition, agenda, momentum)
- “Watchdog inspector” (capture drift, recent leaks, sponsor)

## 9) Definition of Done (v1)

- `pytest` passes.
- With `reform_cfg.enabled=True`:
  - movements form deterministically from exposure/hardship/low-legitimacy conditions,
  - watchdogs exist, drift toward capture, and sometimes leak,
  - reform effects can reduce capture and shift policing doctrine procedurally,
  - backlash can crush or co-opt movements and is reflected in legitimacy components,
  - cockpit explains “why reform rose and why it failed/succeeded.”

## 10) Tests (suggested)

- T1: Deterministic formation given fixed seed/day.
- T2: High exposure + high hardship forms movements more often than low exposure.
- T3: Watchdog capture drift increases when influence edges strengthen.
- T4: Successful reform reduces capture index in a ward.
- T5: Backlash event can crush movement and increases terror policing share.
- T6: Snapshot roundtrip preserves reform state signatures.

---

# Codex implementation instructions (checklist)

**Branch:** `feature/reform-anti-corruption-v1`

1) **State + config**
- Add `src/dosadi/runtime/reforms.py`
- Define dataclasses: `ReformConfig`, `WatchdogInstitution`, `ReformMovement`, `ReformEvent`
- Add world fields with `ensure_*` helpers (mirror patterns in `shadow_state.py`, `culture_wars.py`, etc.)
- Add bounded ring buffer helper for `reform_events`

2) **Runtime update**
- Implement `run_reforms_for_day(world, day)` with `cadence_days` gate
- Deterministic selection of pressure zones (top-K scoring)
- Deterministic weighted picks via `pseudo_rand01(...)`
- Apply effects by modifying:
  - `world.policing_state` / doctrine knobs
  - `world.corruption_by_ward` deltas (bounded)
  - `world.leadership_by_polity` legitimacy component deltas (bounded)

3) **Telemetry**
- Add metrics via `dosadi.runtime.telemetry.record_event`:
  - `REFORM_FORMED`, `REFORM_LEAK`, `REFORM_BACKLASH`, `REFORM_SUCCESS`, `REFORM_CRUSHED`, `REFORM_COOPTED`
- Add `reform_signature()` for snapshot determinism checks

4) **Snapshots/seeds**
- Extend snapshot/restore to include:
  - `reform_cfg`
  - `watchdogs`
  - `reform_movements`
  - bounded `reform_events`
- Add seed export support if you have a “seed payload” pipeline

5) **Cockpit**
- Extend admin views:
  - new panel summarizing top reform pressure wards
  - movement inspector view
  - watchdog inspector view

6) **Tests**
- Add `tests/test_reforms_anti_corruption_v1.py` implementing T1–T6
- Add at least one snapshot roundtrip test for reforms.

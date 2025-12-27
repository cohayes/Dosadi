---
title: Communications_Failure_and_Jamming_v1_Implementation_Checklist
doc_id: D-RUNTIME-0294
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0265   # Law & Enforcement v1
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0268   # Tech Ladder v1
  - D-RUNTIME-0278   # War & Raids v1
  - D-RUNTIME-0286   # Media & Information Channels v1
  - D-RUNTIME-0287   # Counterintelligence & Espionage v1
---

# Communications Failure & Jamming v1 — Implementation Checklist

Branch name: `feature/comms-failure-jamming-v1`

Goal: make the empire blind under stress so that:
- relay networks degrade under sabotage, overload, and environmental shocks,
- factions can jam or spoof signals during conflict,
- institutions operate on stale information and make mistakes,
- communications resilience becomes a strategic investment.

v1 introduces outages and jamming as macro modifiers on Media Channels (0286).

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same outage/jam patterns.
2. **Bounded.** Node-level status + corridor-level modifiers; no packet-level physics.
3. **Composable.** Directly affects message latency/loss/interception (0286).
4. **Strategic levers.** Defense spending and redundancy reduce outages.
5. **Phase-aware.** P2 brings deliberate disruption; P0 mostly accidents.
6. **Tested.** Outage generation, modifiers, persistence, and telemetry.

---

## 1) Concept model

We add a **Comms Reliability Layer** that:
- tracks status of relay and broadcast nodes,
- applies modifiers to media routing and delivery,
- and creates incidents that ripple into governance/war/markets.

Status types:
- `OK`
- `DEGRADED`
- `OUTAGE`
- `JAMMED`
- `SPOOFED` (optional v1: treat as increased distortion)

Modifiers applied to media:
- +latency
- +loss_rate
- +distortion_rate
- +intercept_rate (during spoofed periods)

---

## 2) Data structures

Create `src/dosadi/runtime/comms.py`

### 2.1 Config
- `@dataclass(slots=True) class CommsConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 1`
  - `deterministic_salt: str = "comms-v1"`
  - `base_outage_rate: float = 0.001`
  - `base_degrade_rate: float = 0.003`
  - `jam_rate_war: float = 0.010`
  - `repair_rate: float = 0.15`             # chance/day to recover one step
  - `resilience_spend_effect: float = 0.25`
  - `max_events_per_day: int = 6`

### 2.2 Node state
- `@dataclass(slots=True) class CommsNodeState:`
  - `node_id: str`                  # "relay:<ward_id>" or "broadcast:<ward_id>"
  - `ward_id: str`
  - `kind: str`                     # RELAY|BROADCAST
  - `status: str = "OK"`
  - `status_until_day: int = -1`
  - `health: float = 1.0`           # 0..1 (wear proxy)
  - `jammer_faction: str | None = None`
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

### 2.3 Comms modifiers (cached)
- `@dataclass(slots=True) class CommsModifiers:`
  - `loss_mult: float = 1.0`
  - `latency_add_days: int = 0`
  - `distortion_mult: float = 1.0`
  - `intercept_mult: float = 1.0`

World stores:
- `world.comms_cfg`
- `world.comms_nodes: dict[str, CommsNodeState]`
- `world.comms_mod_by_ward: dict[str, CommsModifiers]`      # ward-level aggregate
- `world.comms_events: list[dict]` (bounded)

Persist node states (and optionally events) in snapshots and seeds.

---

## 3) Creating nodes

When relay/broadcast facilities exist (0286):
- create corresponding CommsNodeState:
  - relay node at ward with RELAY_TOWER
  - broadcast node at ward with BROADCAST_HUB
If facility removed/destroyed:
- node becomes OUTAGE until rebuilt.

---

## 4) Daily update loop

Implement:
- `run_comms_day(world, day)`

Per comms node:
1) Determine hazard pressure:
- environmental hazards (A1) if modeled, else use corridor risk proxy
- war/raids proximity increases jam attempts
- espionage ops (0287) can sabotage nodes (direct hook)

2) Determine defense posture:
- institution dials:
  - `comms_resilience_spend_bias` (-0.5..+0.5)
  - `comms_security_bias` (-0.5..+0.5)
- pay `PAY_COMMS_MAINTENANCE` and `PAY_COMMS_SECURITY` via ledger (0273)
- spend improves node health and reduces outage/jam rates

3) Apply random-but-deterministic transitions:
- OK → DEGRADED (base_degrade_rate * pressure * (1 - defense))
- DEGRADED → OUTAGE (base_outage_rate * pressure)
- OK/DEGRADED → JAMMED during war:
  - jam_rate_war * conflict_pressure * attacker_capability
- JAMMED → DEGRADED after status_until_day or repair chance

4) Repair:
- with maintenance staffing (0290) and budget spend:
  - chance/day to improve status toward OK
- update health up/down based on maintenance.

Cap events per day: max_events_per_day.

---

## 5) Applying modifiers to media routing (0286)

Expose helper:
- `get_comms_modifiers_for_hop(world, from_ward, to_ward, channel) -> CommsModifiers`

Rules:
- If RELAY node at hop is OUTAGE: relay hop cannot be used (force courier fallback).
- If RELAY is DEGRADED: +loss and +latency.
- If JAMMED: large +loss, +latency, +distortion.
- If SPOOFED (optional): +distortion and +intercept.

Apply modifier multiplication/addition to media config:
- loss_rate *= loss_mult
- distortion_rate *= distortion_mult
- intercept_rate *= intercept_mult
- latency += latency_add_days

Also apply to broadcast if implemented.

---

## 6) Jamming and spoofing actors (0287 integration)

During war or active espionage:
- choose jammer factions from local contenders (0266) or active ops (0287)
- if jammer active:
  - set node.jammer_faction
  - create `COMMS_JAMMING` event

If spoofing is enabled:
- certain message kinds (ORDER/ALERT) get higher intercept probability and integrity drops.

Keep v1 minimal: jamming without spoofing is fine.

---

## 7) Incidents driven by comms failure

Use Incident Engine (0242):
- `RELAY_BLACKOUT`
- `BROADCAST_HIJACK` (optional)
- `PANIC_DUE_TO_RUMOR` (if media system emits distorted propaganda)

Effects:
- temporary legitimacy drop
- spike in market volatility (0263)
- increased raid success due to blindness (0278)
- increased governance failure probability (0271)

v1 can just emit events and adjust a couple scalar inputs.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["comms"]["nodes_ok"]`
- `metrics["comms"]["nodes_degraded"]`
- `metrics["comms"]["nodes_outage"]`
- `metrics["comms"]["nodes_jammed"]`
- `metrics["comms"]["relay_fallbacks"]`     # relay → courier fallbacks
- `metrics["comms"]["avg_latency_delta"]`

TopK:
- wards with repeated outages
- jammer factions by jam-days
- worst comms corridors / relay graphs (connectivity loss)

Cockpit:
- comms network view: node status map
- ward comms panel: modifiers and recent events
- message inspector shows comms modifiers per hop (tie into 0286 inspector)

Events:
- `COMMS_DEGRADED`
- `COMMS_OUTAGE`
- `COMMS_JAMMED`
- `COMMS_RECOVERED`
- `COMMS_SPEND`

---

## 9) Persistence / seed vault

Export:
- `seeds/<name>/comms.json` with node states (status, health).

---

## 10) Tests (must-have)

Create `tests/test_comms_failure_jamming_v1.py`.

### T1. Determinism
- same pressures/spend → same node transitions.

### T2. Relay fallback
- relay outage forces courier routing deterministically.

### T3. Jamming increases loss/latency
- JAMMED nodes increase message loss/latency vs OK.

### T4. Maintenance spend improves recovery
- higher maintenance spend increases recovery probability deterministically.

### T5. Espionage sabotage hook
- sabotage op can set node to OUTAGE and impact media delivery.

### T6. Snapshot roundtrip
- node statuses persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add comms module + node state
- Create `src/dosadi/runtime/comms.py` with CommsConfig, CommsNodeState, CommsModifiers
- Create comms nodes when relay/broadcast facilities exist; persist in snapshots + seeds

### Task 2 — Implement daily outage/degradation/jamming loop
- Apply hazard pressure, war pressure, and espionage hooks
- Add comms maintenance/security spending via ledger and apply to health/transition rates

### Task 3 — Integrate with media routing
- Expose hop modifiers and apply to message loss/distortion/latency
- Force relay fallback to courier when nodes are OUTAGE

### Task 4 — Add incidents, telemetry, and cockpit views
- Emit comms events and optional incidents
- Add network status view and message inspector integration

### Task 5 — Tests
- Add `tests/test_comms_failure_jamming_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - relay/broadcast nodes can degrade, outage, and be jammed deterministically,
  - maintenance/security spending reduces failure risk and improves recovery,
  - media system routes around failures with measurable latency and loss impacts,
  - war and espionage can deliberately blind the empire,
  - cockpit explains “why we lost contact,” and seeds preserve comms posture.

---

## 13) Next slice after this

**Sanctions & Embargo Systems v1** — diplomacy gets teeth:
- customs policies, treaty enforcement,
- and economic warfare through controlled corridors.

---
title: Media_and_Information_Channels_v1_Implementation_Checklist
doc_id: D-RUNTIME-0286
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0246   # Agent Courier Logistics v1
  - D-RUNTIME-0248   # Courier MicroPathing v1
  - D-RUNTIME-0257   # Depot Network & Stockpile Policy v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0268   # Tech Ladder v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0274   # Diplomacy & Treaties v1
  - D-RUNTIME-0285   # Ideology & Curriculum Control v1
---

# Media & Information Channels v1 — Implementation Checklist

Branch name: `feature/media-info-channels-v1`

Goal: model how ideas and orders travel across the empire so that:
- information has **latency** and **distortion** (not omniscient),
- institutions and factions can run propaganda and information warfare,
- tech unlocks improve bandwidth (couriers → relays → broadcast),
- culture wars become spatial and networked over corridors.

v1 is macro “message traffic,” not per-agent rumor micro-sim.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same message routing and arrival.
2. **Bounded.** TopK channels per ward; bounded message queues; no global spam.
3. **Latency matters.** Policies take time to propagate; stale info causes mistakes.
4. **Distortion.** Messages can be lost, delayed, altered, intercepted.
5. **Composable.** Plugs into courier logistics, ideology, diplomacy, war, and enforcement.
6. **Tested.** Delivery determinism, queue bounds, interception effects, persistence.

---

## 1) Concept model

The empire has **information channels**:
- Courier routes (physical): slow, reliable-ish, interceptable
- Relay nodes (tech-gated): faster, limited bandwidth, can be jammed
- Broadcast (late tech): wide reach, high propaganda potential, censorship leverage

Messages are macro packets with:
- origin, destination scope, kind, payload summary,
- priority,
- TTL,
- and cryptographic posture (optional later).

Messages update:
- institution “belief” about the world (operational intelligence),
- policy dissemination (orders),
- propaganda narratives that shift ideology axes (0285),
- diplomacy events (0274),
- and war deterrence signaling (0280).

---

## 2) Channel types (v1)

Define 3 channel layers:

### 2.1 COURIER_NET
- Uses existing courier movement (0246/0248)
- Latency: corridor travel time
- Risk: interception on high-risk corridors (0261)
- Bandwidth: bounded by courier capacity

### 2.2 RELAY_NET (tech gated)
- Facilities: `RELAY_TOWER_L2` placed in wards
- Latency: 1–2 day hops between relay-equipped wards
- Risk: jamming or sabotage (optional v1: corridor risk affects relays too)
- Bandwidth: limited messages/day per relay

### 2.3 BROADCAST (late tech)
- Facility: `BROADCAST_HUB_L3`
- Latency: near-instant to connected wards (within “coverage”)
- Risk: censorship and propaganda capture (0285)
- Bandwidth: high for propaganda, medium for operational orders

v1 can implement only COURIER_NET + RELAY_NET if scope tight.

---

## 3) Data structures

Create `src/dosadi/runtime/media.py`

### 3.1 Config
- `@dataclass(slots=True) class MediaConfig:`
  - `enabled: bool = False`
  - `max_messages_in_flight: int = 5000`
  - `max_messages_per_ward_queue: int = 200`
  - `relay_bandwidth_per_day: int = 50`
  - `deterministic_salt: str = "media-v1"`
  - `loss_rate_base: float = 0.01`
  - `distortion_rate_base: float = 0.02`
  - `intercept_rate_base: float = 0.03`

### 3.2 Message model
- `@dataclass(slots=True) class MediaMessage:`
  - `msg_id: str`
  - `day_sent: int`
  - `sender: str`                  # faction/ward/institution id
  - `origin_ward: str`
  - `dest_scope: str`              # "WARD"|"NEIGHBORS"|"FACTION"|"GLOBAL"
  - `dest_id: str`                 # ward_id or faction_id or "*" for global
  - `channel: str`                 # "COURIER"|"RELAY"|"BROADCAST"
  - `kind: str`                    # "ORDER"|"INTEL"|"PROPAGANDA"|"TREATY"|"ALERT"
  - `priority: int`                # 0..3
  - `ttl_days: int`                # drop if expired
  - `payload: dict[str, object]` = field(default_factory=dict)
  - `integrity: float = 1.0`       # 0..1 (distortion/loss proxy)
  - `status: str = "IN_FLIGHT"`    # IN_FLIGHT|DELIVERED|DROPPED|INTERCEPTED
  - `notes: dict[str, object]` = field(default_factory=dict)

### 3.3 Routing / queues
World stores:
- `world.media_cfg`
- `world.media_in_flight: dict[str, MediaMessage]`
- `world.media_inbox_by_ward: dict[str, deque[str]]`      # ward_id -> msg_ids
- `world.media_inbox_by_faction: dict[str, deque[str]]`   # faction_id -> msg_ids
- `world.media_stats: dict[str, int|float]`               # counters

Persist bounded in-flight messages and inbox queues (by msg_id + message store), or store messages inline.

---

## 4) Message sources (who emits messages)

v1 minimum emitters:
- institutions (policies/orders): escort policies, crackdowns, quarantine, zoning
- war module: alerts, deterrence postures, raid reports
- diplomacy: treaty offers/accepts/breaches
- ideology: propaganda campaigns

Provide helper APIs:
- `emit_order(...)`
- `emit_intel(...)`
- `emit_propaganda(...)`

Keep payload small and structured; do not serialize huge objects.

---

## 5) Routing rules (deterministic)

### 5.1 Determine channel
- If RELAY available at origin and destination is relay-connected: use RELAY for priority >=1
- Else COURIER
- BROADCAST used only for propaganda/global notices when hub exists.

### 5.2 Build path
- COURIER: use existing corridor path planner (0248) but at macro level:
  - choose best corridor path deterministically (TopK)
- RELAY: hop through relay wards (graph shortest hops)
Bounded: precompute relay graph per update or cache.

### 5.3 Transit time
- COURIER: sum corridor travel times + delay from escort risk/raids
- RELAY: hop_count days (or 1 day per hop)

### 5.4 Loss, distortion, interception
At each hop/day:
- loss probability depends on:
  - corridor risk (for COURIER),
  - sabotage risk (for RELAY),
  - censorship level (for PROPAGANDA vs ORDER interplay)
- distortion reduces integrity
- interception flips to INTERCEPTED and can create counter-intel message to interceptor faction

Use deterministic pseudo-rand keyed on (salt, msg_id, day, hop_index).

---

## 6) Inbox consumption: turning messages into effects

Delivering a message just queues it.
Consumption occurs by the owning subsystem on cadence:

- Institutions read ORDER/ALERT:
  - update local policy if message is “newer” than last-known version

- Diplomacy reads TREATY:
  - handle proposals/acceptances

- Ideology reads PROPAGANDA:
  - adjust local ideology axes via a “propaganda input” bucket

- War reads INTEL:
  - update perceived threat/target selection (optional v1)

Important: messages can be stale (day_sent too old) → reduced effect.

---

## 7) Propaganda at scale (0285 integration)

Define propaganda payload schema:
- target axis (ORTHODOXY/TECHNICISM/MERCANTILISM/MILITARISM)
- intensity (0..1)
- campaign_id
- desired coverage (neighbors/faction/global)

Consumption:
- ideology module applies campaign effects weighted by message integrity and arrival latency.
Censorship can block hostile propaganda.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["media"]["in_flight"]`
- `metrics["media"]["delivered"]`
- `metrics["media"]["dropped"]`
- `metrics["media"]["intercepted"]`
- `metrics["media"]["avg_latency_days"]`
- `metrics["media"]["avg_integrity"]`

TopK:
- corridors with most interceptions
- wards with largest inbox backlog
- factions with most propaganda throughput

Cockpit:
- message inspector (by msg_id): path, hops, loss/distortion events
- inbox views for wards/factions (recent N)
- “policy staleness” view: which wards are running outdated policies

Events:
- `MSG_SENT`
- `MSG_DELIVERED`
- `MSG_DROPPED`
- `MSG_INTERCEPTED`
- `PROPAGANDA_APPLIED`

---

## 9) Persistence / seed vault

Persist only what’s needed:
- in-flight messages (bounded)
- inbox queues (bounded)
Seeds may omit in-flight and start with empty queues unless you want “living world” continuity.

---

## 10) Tests (must-have)

Create `tests/test_media_information_channels_v1.py`.

### T1. Determinism
- same graph/risk → same delivery day and integrity outcomes.

### T2. Queue bounds
- cannot exceed max per ward; oldest dropped or lowest priority dropped deterministically.

### T3. Relay speedup
- with relays, average latency decreases vs courier-only.

### T4. Interception
- high corridor risk increases interception counts deterministically.

### T5. Staleness
- old orders have reduced/zero effect compared to recent orders.

### T6. Snapshot roundtrip
- in-flight and inbox messages persist across snapshot/load (if enabled).

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add media module + message store and queues
- Create `src/dosadi/runtime/media.py` with MediaConfig and MediaMessage
- Add world.media_in_flight and inbox queues with bounds; persist in snapshots

### Task 2 — Implement routing for COURIER and RELAY
- Deterministic pathing and transit time computation
- Apply loss/distortion/interception with deterministic pseudo-rand
- Deliver to ward/faction inboxes

### Task 3 — Wire message consumption into subsystems
- Institutions consume ORDER/ALERT for policy propagation with staleness handling
- Diplomacy consumes TREATY messages
- Ideology consumes PROPAGANDA campaigns and applies to axes
- Add basic INTEL consumption hooks for war planner (optional)

### Task 4 — Telemetry + cockpit + tests
- Add message inspector and inbox views
- Add `tests/test_media_information_channels_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - orders, intel, and propaganda travel through courier/relay networks with latency and distortion,
  - risk creates interceptions and loss,
  - policies and ideology respond to received messages with staleness,
  - cockpit can inspect message paths and policy staleness,
  - seeds can evolve into distinct “information regimes.”

---

## 13) Next slice after this

**Counterintelligence & Espionage v1** — move from random interceptions to active ops:
- spy cells, courier bribery, relay sabotage,
- information asymmetry as power,
- and smuggling networks carrying secrets, not just goods.

---
title: Dosadi_Runtime_Event_And_Message_Taxonomy
doc_id: D-RUNTIME-0005
version: 1.0.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-RUNTIME-0001
---
# **Event & Message Taxonomy v1 (Dosadi Sim Bus)**

**Purpose.** Define the canonical event bus used by all systems (Temporal, Environment, Economy, Law/Contracts, Governance, Rumor/Perception, Agents, and UI/Telemetry).  
**Tick cadence.** 1 tick = 0.6s. Bus is processed once per tick.

---

## 0) Bus Guarantees & Mechanics

**Addressing & Scope**
- `scope`: `GLOBAL` | `WARD:<id>` | `FACTION:<id>` | `AGENT:<id>`
- `emitter`: `System` | `FactionID` | `AgentID`
- `ttl`: ticks to live (default 300); dropped when expired.

**Delivery & Ordering**
- **Phases per tick:** (1) _Ingress_ (emitters append), (2) _Order_ (priority queue), (3) _Dispatch_ (subscribers consume), (4) _Effects_ (state updates), (5) _Egress_ (derived emits).
- **Priority (high→low):** `SECURITY > LAW > ENVIRONMENT > ECONOMY > GOVERNANCE > RUMOR > SOCIAL > TELEMETRY`.
- **Ward partitioning:** within a ward, events are ordered; cross‑ward order is best‑effort.

**Idempotency & Dedupe**
- Each event has `id` (UUID) and `dedupe_key` (optional). Consumers must be idempotent.
- Retries may occur (e.g., transient subscriber failure).

**Versioning & Compatibility**
- `schema_v`: semantic version; subscribers must accept compatible minor versions.
- Deprecated fields are kept 1 major version with `deprecated: true` notes.

**Audit & Security**
- `audit`: signed header for privileged events; Royal/Arbiter keys for rulings/seizures.
- Access control: subscribers can only see events within their permission scope.

**Event Envelope**
```json
{
  "id":"EventID",
  "type":"String",
  "schema_v":"1.0.0",
  "tick":0,
  "scope":"GLOBAL|WARD:W12|FACTION:F9|AGENT:A42",
  "emitter":"System|FactionID|AgentID",
  "priority":"SECURITY|LAW|ENVIRONMENT|ECONOMY|GOVERNANCE|RUMOR|SOCIAL|TELEMETRY",
  "payload":{},
  "ttl":300,
  "dedupe_key":null,
  "audit":null
}
```
Subscribers are declared as **system channels**: `Temporal`, `Environment`, `Economy`, `Law`, `Governance`, `Rumor`, `Agents`, `Telemetry`.

---

## 1) Temporal & Core Flow

### 1.1 `TickStarted`
- **Emitter:** Temporal (System) — GLOBAL
- **Payload:** `{ "tick": int }`
- **Subscribers:** all (for per‑tick prep)

### 1.2 `MinuteClosed`, `DayClosed`
- **Emitter:** Temporal — GLOBAL
- **Payload:** aggregates `{ "t_min": int, "t_day": int }`
- **Subscribers:** Economy, Governance, Telemetry

---

## 2) Barrel Cascade & Economy

### 2.1 `BarrelCascadePlanned`
- **Emitter:** Governance/Economy — GLOBAL
- **Payload:** `{ "plan_id": "ID", "targets":[{"ward":"WID","quota_L":float,"bias":float}], "tax_rate": float }`
- **Subs:** Law (mandates), Economy, Rumor, Telemetry
- **Effects:** sets `cascade.T` and daily draw intent

### 2.2 `BarrelCascadeIssued`
- **Emitter:** Economy — GLOBAL
- **Payload:** `{ "plan_id":"ID", "draw_L": float }`
- **Subs:** Law (issue contracts), Factions, Rumor

### 2.3 `AllocationDelivered`
- **Emitter:** Economy / Logistics
- **Payload:** `{ "to_faction":"FID","ward":"WID","amount_L":float,"loss_L":float }`
- **Subs:** Economy (stocks), Law (milestones), Rumor, Telemetry
- **Metrics:** updates `econ.R` for carrier and issuer

### 2.4 `MarketPriceUpdated`
- **Emitter:** Economy (market maker)
- **Payload:** `{ "issuer":"FID","credit_rate": float }`
- **Subs:** Agents (bidding), Rumor, Telemetry
- **Metrics:** updates `econ.X`

---

## 3) Contracts & Law

### 3.1 `ContractProposed`
- **Emitter:** Faction/Agent, Civic desk, Black‑market node
- **Payload:** `{ "contract_id":"CID","record_medium":"WITNESSED|TOKENIZED|HYBRID","token":{"escrow_proxy": "FID|FacilityID|null"} }`
- **Subs:** Law (validation), Rumor (public if civic), Economy (risk pricing)

### 3.2 `ContractActivated`
- **Emitter:** Law (after validation)
- **Payload:** contract header snapshot
- **Subs:** Economy (production), Rumor (public civic posting), Agents

### 3.3 `MilestoneReported`
- **Emitter:** Parties / Guild inspectors
- **Payload:** `{ "contract_id":"CID","milestone":"string","ok":bool,"qty":float }`
- **Subs:** Law (progress), Telemetry, Rumor (if publicized)

### 3.4 `ContractFulfilled`
- **Emitter:** Law
- **Payload:** `{ "contract_id":"CID","quality_ok":bool }`
- **Subs:** Economy (release payments), Governance (legitimacy up), Rumor

### 3.5 `ContractLate`
- **Emitter:** Law (deadline pass)
- **Payload:** `{ "contract_id":"CID","lateness_ticks":int }`
- **Subs:** Law (auto‑mediation), Rumor

### 3.6 `ContractDisputed`
- **Emitter:** Any party / Civic observer
- **Payload:** `{ "contract_id":"CID","cause":"QUALITY|NONDELIVERY|FRAUD|FORCE_MAJEURE" }`
- **Subs:** Law (case create), Rumor

### 3.7 `ArbiterAssigned`
- **Emitter:** Arbiters’ Guild
- **Payload:** `{ "case_id":"KID","tier":"JUNIOR|CIRCUIT|HIGH" }`
- **Subs:** Law (case routing), Rumor (credibility boost)

### 3.8 `ArbiterRuling`
- **Emitter:** Arbiters’ Guild
- **Payload:** `{ "case_id":"KID","outcome":"RESTORATIVE|RETRIBUTIVE","orders":{} }`
- **Subs:** Law (apply), Economy (seizures), Governance (L update), Rumor

### 3.9 `EnforcementExecuted`
- **Emitter:** Royal/Feudal/Guild/Civic/Street enforcers
- **Payload:** `{ "case_id":"KID","type":"SEIZURE|IMPRISON|EXECUTION|OUTLAWRY|BLACKLIST","force_level":"idx" }`
- **Subs:** Rumor (high energy), Governance (fear/legitimacy), Telemetry

### 3.10 `TokenMinted` / `TokenTransferred` / `TokenBurned`
- **Emitter:** Law/Economy/Black‑market
- **Payload:** token ledger delta
- **Subs:** Economy (escrow), Telemetry, Rumor (only if civic)

---

## 4) Environment & Infrastructure

### 4.1 `HeatSurge`
- **Emitter:** Environment (ward sensors)
- **Payload:** `{ "ward":"WID","delta_C":float,"duration":int }`
- **Subs:** Agents (behavior), Governance (alerts), Rumor
- **Effects:** increases `env.S`, suit decay

### 4.2 `CondensationFailure`
- **Emitter:** Environment/Infra
- **Payload:** `{ "ward":"WID","capacity_drop": float }`
- **Subs:** Economy (ration cut), Rumor, Law (sabotage?)

### 4.3 `DustIngress`
- **Emitter:** Environment
- **Payload:** `{ "ward":"WID","visibility_drop": float }`
- **Subs:** Agents, Rumor

### 4.4 `PowerBrownout`
- **Emitter:** Environment/Power guild
- **Payload:** `{ "ward":"WID","severity":"LOW|MID|HIGH" }`
- **Subs:** Law (force majeure flags), Economy (throughput), Rumor

### 4.5 `ReclaimerContamination`
- **Emitter:** Reclaimer guild
- **Payload:** `{ "ward":"WID","batch_id":"ID","risk":"idx" }`
- **Subs:** Governance (legitimacy risk), Rumor, Law

### 4.6 `InfrastructureFailure` / `RepairCompleted`
- **Emitter:** Infra stewards
- **Payload:** `{ "ward":"WID","subsystem":"thermal|condensers|...","status":"FAIL|OK" }`
- **Subs:** Environment, Rumor, Telemetry

---

## 5) Governance, Factions & Succession

### 5.1 `SuccessionInitiated`
- **Emitter:** Faction/Civic observers
- **Payload:** `{ "faction":"FID","cause":"DEATH|COUP|RETIREMENT|INCAPACITY" }`
- **Subs:** Law (continuity rules), Rumor

### 5.2 `SuccessionResolved`
- **Emitter:** Arbiters/Civic observers
- **Payload:** `{ "faction":"FID","leader":"AgentID","legitimacy":float }`
- **Subs:** Governance (L recalc), Law (contract migration), Rumor

### 5.3 `LegitimacyUpdated`
- **Emitter:** Governance
- **Payload:** `{ "faction":"FID","delta":float,"reason":"CONSISTENT_RULINGS|CRISIS|BIAS|TRIUMPH" }`
- **Subs:** Economy (risk pricing), Agents (obedience), Rumor

### 5.4 `AuditInitiated` / `AuditResultLogged`
- **Emitter:** Clerks/Arbiters
- **Payload:** `{ "target":"FID|WARD","findings":{"diversion":float,"sanctions":[]}}`
- **Subs:** Governance (C down/up), Economy, Rumor

### 5.5 `FraudDetected`
- **Emitter:** Audit / Market
- **Payload:** `{ "issuer":"FID","pattern":"COUNTERFEIT|DOUBLE_SPEND|LEDGER_TAMPER" }`
- **Subs:** Law (cases), Economy (halt trades), Rumor

---

## 6) Black‑Market & Security

### 6.1 `BountyPosted` / `BountyClaimed`
- **Emitter:** Black‑market / Enforcers
- **Payload:** `{ "target":"AgentID|FactionID","amount_credits":float }`
- **Subs:** Agents (behavior), Rumor

### 6.2 `EscortAmbushed`
- **Emitter:** Security/Military
- **Payload:** `{ "route":"WID→WID","loss_L":float,"casualties":int }`
- **Subs:** Economy (loss), Law (dispute), Rumor (high energy), Governance

### 6.3 `SafehouseBreached`
- **Emitter:** Security
- **Payload:** `{ "facility":"FacilityID","by":"FactionID" }`
- **Subs:** Rumor, Law, Agents

---

## 7) Rumor & Perception

### 7.1 `RumorEmitted`
- **Emitter:** Rumor system / Agents / Civic posting
- **Payload:** `{ "rumor_id":"RID","cred":float,"salience":float,"visibility":{"firsthand":bool,"radius":int} }`
- **Subs:** Agents (belief updates), Telemetry

### 7.2 `MemeFormed`
- **Emitter:** Rumor system
- **Payload:** `{ "key":"string","strength":float }`
- **Subs:** Governance (narrative pressure), Agents (bias)

### 7.3 `BeliefUpdated`
- **Emitter:** Perception engine
- **Payload:** `{ "agent":"AID","rumor":"RID","delta":float }`
- **Subs:** Agents (policy), Telemetry

---

## 8) Telemetry & UI

### 8.1 `LogMetric`
- **Emitter:** Any
- **Payload:** `{ "key":"string","value":number,"tags":{} }`
- **Subs:** Telemetry

### 8.2 `Trace`
- **Emitter:** Any
- **Payload:** `{ "message":"string","context":{} }`
- **Subs:** Telemetry

---

## 9) Mapping Events → Shared Variables

| Event | Primary SVR Impacts |
|---|---|
| BarrelCascadePlanned/Issued | `cascade.T`, `cascade.Q`, `econ.Tax` |
| AllocationDelivered | stocks.water, `econ.R` (carrier & issuer) |
| ContractFulfilled/Late/Disputed | `econ.R`, `law.E`, `law.RR`, `law.RI` |
| ArbiterRuling/EnforcementExecuted | `gov.L`, `social.Fear`, `law.RR/RI`, `law.AC` |
| HeatSurge/CondensationFailure/PowerBrownout | `env.S`, `infra.M` decay, suit decay |
| SuccessionResolved | `gov.L` for faction, contract migration |
| AuditResultLogged/FraudDetected | `gov.C`, `econ.Prem`, `econ.Col` |
| RumorEmitted/MemeFormed | `rumor.Cred`, `mem.Sal`, `meme.M` |

---

## 10) Example Flows

### 10.1 Daily Barrel Cascade
1. `BarrelCascadePlanned` → Law drafts mandates, Rumor primes.  
2. `BarrelCascadeIssued` → Contracts activated.  
3. `AllocationDelivered` → `econ.R` updates; Rumor “water carts seen.”  
4. If ambush: `EscortAmbushed` → Law dispute → `ArbiterAssigned` → `ArbiterRuling`.

### 10.2 Black‑Market Assassination
1. `ContractProposed` (TOKENIZED, proxy escrow) at node.  
2. `ContractActivated` (hidden; civic unsubscribed).  
3. `EnforcementExecuted` if completed (target killed) → high‑energy Rumor.  
4. `TokenBurned` (escrow payout).

### 10.3 Heat Surge
1. `HeatSurge` → Agents reduce outside labor; suit decay ↑.  
2. If condensers fail: `CondensationFailure` → ration cuts → Rumor panic.  
3. Governance may post `LegitimacyUpdated` (down) after crisis mishandled.

### 10.4 Succession After Coup
1. `SuccessionInitiated` (cause: COUP).  
2. `SuccessionResolved` (winner + legitimacy).  
3. Law migrates contracts; Rumor stabilizes or fractures into `MemeFormed` (“Usurper”).

### 10.5 Clerk Capture & Audit Spiral
1. Prices diverge → `FraudDetected`.  
2. `AuditInitiated` → `AuditResultLogged` (diversion high).  
3. `ArbiterRuling` (restorative + monitoring) or retributive if willful.  
4. `LegitimacyUpdated` (contextual).

---

## 11) Testing Hooks

- **Deterministic seeds** for event generation (env/weather, cascade targeting).  
- **Golden traces**: serialized sequences for scenarios above with expected SVR deltas.  
- **Idempotency tests**: replay events; state must not double‑apply.  
- **TTL tests**: ensure expiry prevents zombie side‑effects.

---

## 12) Extensibility

- New event types must declare: `purpose`, `payload schema`, `emitters`, `subscribers`, `SVR impacts`, `priority`.  
- Deprecation path: mark, dual‑emit for one major version, remove after migration.

---

**End — Event & Message Taxonomy v1**

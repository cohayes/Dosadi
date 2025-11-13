---
title: Dosadi_Telemetry_and_Audit_Infrastructure
doc_id: D-INFOSEC-0009
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-13
parent: D-INFOSEC-0001
---
# **Telemetry & Audit Infrastructure v1 (Identity, Sensors, Ledgers, Chain‑of‑Custody)**

**Version:** v1 — 2025‑11‑12  
**Purpose.** Establish trustworthy data flows so evidence, contracts, credits, and decisions have verifiable ground truth. Defines identities & signing, attested sensors, evidence bundles, chain‑of‑custody, checkpoint anchoring, token standards, fraud detection, and Arbiter audit workflows.

Integrates with **Rumor Credibility v1.1**, **Law & Contract Systems v1** (Arbiters, cases), **Succession v1.1**, **Barrel Cascade v1.1**, **Credits & FX v1.1**, **Clinics v1.1**, **Escort/Security v1**, **Production & Fabrication v1**, **Agent Decision v1**, and the **Tick Loop**.

> Timebase: sensor packets **per 10s–60s**; custody updates **on event**; boards **hourly**; audits **daily** or **on trigger**.

---
## 0) Identity & Key Hierarchy

- **Principals & Keys**
  - **Agent** (person): `agent_pub/priv`, optional subkeys for roles.
  - **Faction** (guild, militia, civic body): `faction_key`, managed by officers.
  - **Office** (king, duke, ward lord, arbiter panel): `office_key`, rotation schedule.
  - **Device** (meter, seal, beacon, camera, shop station, clinic monitor): `device_key`, provisioned & revocable.
- **Key Services**
  - **Registry**: append‑only list of active keys `{id, type, owner, valid_from, valid_to, status}`.
  - **Rotation**: scheduled rotation windows; grace period for dual‑sign acceptance.
  - **Revocation**: emergency revoke emits `KeyRevoked`; dependent devices enter **safe mode**.
- **Signatures**
  - All telemetry & tokens use `sign(payload_hash, key)`; envelope stores `{sig, key_id, ts, nonce}`.
  - Acceptable clock skew configurable (see Policy).

---
## 1) Attested Sensors & Packets

- **Devices**: Well meters, barrel seals, convoy beacons (GPS/IMU), gate counters, clinic hygiene monitors, shop stations.
- **Packet Schema**
  ```yaml
  packet:
    device_id: str
    type: METER|SEAL|BEACON|QA|HYGIGIENE|LEDGER_SNAPSHOT
    reading: {...}     # typed fields
    ts: int            # epoch ms
    seq: int
    loc: {ward, x, y}? # optional
    prev_hash: hex?    # rolling link per device
    sig: hex
  ```
- **Seal Trees**: a barrel or lot has a **seal‑tree** (Merkle) over sub‑seals; break/repair events produce new roots with reason codes.
- **Clock Discipline**: device clocks synced to ward beacons; drift beyond limit → `ClockSkewAlert`.

---
## 2) Evidence Object Model

- **Evidence Types**: `SENSOR`, `VIDEO`, `LEDGER`, `WITNESS`, `TOKEN`, `ARBITER_DECREE`.
- **Bundle**
  ```yaml
  evidence_bundle:
    id: claim_id
    type: SENSOR|...
    payload: bytes|hashes
    sources: [device_id|agent_id|office_id]
    anchors: [checkpoint_id]     # where it was published
    custody_link: custody_id
    sigs: [sig]
    redact: rules?               # PII concealment ranges
  ```
- **Verification API**: `verify_bundle()` checks signatures, key status, clock skew, seal‑tree membership, and anchor presence.

---
## 3) Chain‑of‑Custody

- **Custody Record**: `{custody_id, parent?, holder_id, place, ts_in, ts_out?, purpose, sig}` (append‑only).
- **Transitions**: creation → handoff(s) → archive. Missing link ⇒ `CustodyGap` (penalty escalator by context).
- **Dual Control**: sensitive items (barrels, heir tokens) require **two‑man rule** signatures at handoff.
- **Privacy Grades**: public, ward‑sealed, faction‑sealed. Arbiters can unseal under decree.

---
## 4) Ledgers & Checkpoints

- **Local Ledgers**: per entity (clinic, shop, issuer depot) store streams: episodes, steps, packets, bills.
- **Checkpoint Posts**: hourly **anchoring** to ward **Public Boards**:
  - `anchor_checkpoint(ledger_root, stats, sig)` emits `CheckpointAnchored` with `checkpoint_id`.
  - Boards accept: cascade handoffs, clinics hygiene ticks, fabrication QA lots, FX liquidity snapshots.
- **Public Boards**: tamper‑evident feed with retention policy; rumor engine and auditors read from here.

---
## 5) Token Standards

- **Heir Token**: `{office_id, heir_id, mandate_hash, issued_ts, sig_office}`; optional witness set.
- **Oath/Contract Token**: `{parties, obligations, penalties, valid_window, sigs}`; can link to escrow vault.
- **Ration Token**: non‑transferable, `{bearer_id, liters, exp_ts, sig_office}`; clinics & depots redeem.
- **Black‑Board Escrow Token** (anonymous): `{escrow_id, offer, conditions, deposit, exp_ts, sig_market}`; Arbiter may invalidate if criminality proven.
- **Revocation**: `revoke_token(id, reason)` publishes to boards; wallets must observe revocations.

---
## 6) Fraud, Anomalies, and Audits

- **Detectors**
  - **Time/Geo Conflicts**: same barrel seen in two wards simultaneously.
  - **Duplicate Serials**: collisions signal forgery.
  - **Broken Seal Trees**: sub‑components missing; lot tamper.
  - **Meter Curve Oddities**: well output vs cascade receipts discrepancy.
  - **Queue/FX Mismatch**: posted redemption vs WaterBasis gap persistence.
- **Audit Workflow**
  1) Trigger (`DetectorAlert` or complaint).  
  2) `open_audit(entity, scope)` → request bundles & logs.  
  3) Sampling: targeted pull from ledgers and boards.  
  4) Findings: `ARBITER_DECREE` (uphold/retract/sanction/receivership) → broadcast.
- **Sanctions**: fines in king‑credits, issuance caps, receivership, or succession triggers.

---
## 7) Policy Knobs (defaults)

```yaml
telemetry_audit:
  clock_skew_ms: 5000
  key_rotation_days:
    device: 14
    office: 90
    arbiter: 180
  custody_two_man_rule: true
  board_publish_interval_min: 60
  seal_tree_required_for:
    - "barrel"
    - "qa_lot"
  min_evidence_for_decree:
    SENSOR: 1
    LEDGER: 1
    VIDEO: 0
    WITNESS: 1
  privacy_unseal_rules:
    arbiter_order_required: true
    emergency_exceptions: ["mass_casualty","run_on_issuer"]
```

---
## 8) Event & Function Surface (for Codex)

**Functions**  
- `sign_packet(device_id, payload)` → signed packet.  
- `verify_bundle(bundle)` → returns status & reasons.  
- `anchor_checkpoint(ledger_root, stats, board_id)` → posts anchor & returns `checkpoint_id`.  
- `open_audit(entity_id, scope)` → creates audit case.  
- `issue_token(kind, fields)` / `revoke_token(id, reason)` → emits board notices.  
- `record_custody(prev_id, holder_id, place, purpose)` → new custody link.

**Events**  
- `PacketSigned`, `CheckpointAnchored`, `DetectorAlert`, `AuditOpened`, `ArbiterDecree`, `TokenIssued`, `TokenRevoked`, `CustodyUpdated`, `KeyRevoked`.

---
## 9) Pseudocode (Indicative)

```python
def verify_bundle(bundle):
    ok_sig = verify_sigs(bundle.payload, bundle.sigs, registry)
    ok_keys = keys_active(bundle.sigs, registry)
    ok_time = within_skew(bundle.ts, policy.clock_skew_ms)
    ok_anchor = anchors_exist(bundle.anchors)
    ok_chain = custody_chain_valid(bundle.custody_link)
    return all([ok_sig, ok_keys, ok_time, ok_anchor, ok_chain])

def anchor_checkpoint(ledger_root, stats, board):
    cid = new_checkpoint_id()
    post_board(board, {"cid": cid, "root": ledger_root, "stats": stats, "ts": now()})
    emit("CheckpointAnchored", {"cid": cid})
    return cid

def open_audit(entity, scope):
    case = new_case(entity, scope)
    request_logs(entity, scope)
    emit("AuditOpened", {"case": case.id})
    return case
```

---
## 10) Dashboards & Explainability

- **Boards Viewer**: ward boards with anchors (cascade, clinic, FX, QA).  
- **Key Registry**: active keys, rotations, revocations, device health, clock drift map.  
- **Custody Graph**: visualize handoffs for barrels/lots/cases; highlight gaps.  
- **Detector Panel**: alerts with severity & probable cause; link to evidence bundles & decrees.

---
## 11) Test Checklist (Day‑0+)

- Valid bundles with proper anchors pass verification; forged keys or excessive clock skew fail.  
- Seal‑tree tamper on a lot triggers DetectorAlert → audit → decree & sanctions.  
- Redemption board anchors correlate with FX WaterBasis; persistent gaps flag audits.  
- Custody gaps on barrels prevent “clean” cascade credit; convoys with dual‑sign handoffs show continuous chains.  

---
### End of Telemetry & Audit Infrastructure v1

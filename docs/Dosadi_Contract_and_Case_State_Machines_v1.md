# **Contract & Case State Machines v1**

Formal lifecycle for agreements and disputes in Dosadi. Integrates with **Event Bus v1**, **Scoring v1**, **Tick Loop v1**, **Law & Contract Systems v1**, and **Agent Action API v1**.

> **Bias**: restorative-first across most wards; retributive reserved for severe or military breaches.  
> **Timebase**: timers expressed in minutes (100 ticks/min).

---

## 0) Objects & Identifiers

- **Contract** `ContractID`: agreement with parties, terms, witnesses or token escrow.  
- **Case** `CaseID`: dispute or criminal proceeding opened on a contract or offense.  
- **Evidence** `EvidenceID`: signed records, witness attestations, sensor logs.  
- **ArbiterCase**: assignment within the **Arbiters’ Guild** (ranked by ward).

---

## 1) Contract Model (Data Schema)

```json
{
  "contract_id": "c_00123",
  "kind": "CIVIC|COMMERCIAL|SECURITY|BLACK_MARKET",
  "venue": "CIVIC_CENTER|BLACK_NODE|PRIVATE_CHAMBER",
  "parties": ["FactionID|AgentID", "FactionID|AgentID"],
  "third_parties": { "witnesses": ["AgentID"], "escrow_proxy": "AgentID|null" },
  "terms": {
    "obligation": [{"what":"WATER|GOODS|SERVICE","qty":1000,"quality":0.9,"by_min":43200}],
    "consideration": [{"what":"CREDITS|WATER|TOKEN","qty":800,"by_min":43200}],
    "collateral": {"type":"TOKEN|GOODS|CREDITS","qty":200},
    "penalties": {"late_fee_rate":0.02, "breach_bounty":500}
  },
  "visibility": "PUBLIC|RESTRICTED",
  "lawfulness": "LAWFUL|GREY|ILLICIT",
  "state": "DRAFT|ACTIVE|FULFILLED|LATE|DISPUTED|BREACHED|SETTLED|VOID",
  "created_min": 0,
  "due_min": 43200,
  "grace_min": 240,
  "audit_flags": {"risk":0.0,"bias":0.0},
  "ledger": {"delivered":0,"paid":0},
  "reliability_weight": 1.0
}
```

**Notes**  
- **Witness path (CIVIC)** → enforceability via `witnesses`.  
- **Token path (BLACK_MARKET)** → anonymity via `escrow_proxy` and `Token*` events.  
- `lawfulness` steers venue rules and penalties.

---

## 2) Contract State Machine

```
[DRAFT] --RegisterContract--> [ACTIVE]
   |                              |
   |      deliver/pay complete    |  due+grace passed w/ deficit
   | --------Fulfill------------> [FULFILLED] <------ [LATE] <----
   |                                ^   |                |       |
   |                                |   | dispute        |       |
   |                                |   +----RaiseDispute|       |
   |  cancellation before start     |                    v       |
   +--------------Void--------------+                 [DISPUTED] |
   |                                                    |        |
   |    Arbiter orders settlement   breach ruling       |        |
   +---------[SETTLED] <-------------- [BREACHED] <-----+--------+
                                  (retributive path possible)
```

**Transition Triggers**  
- `RegisterContract` → `ACTIVE` (Event: `ContractActivated`).  
- Due time reached with outstanding obligations → `LATE` (Event: `ContractLate`).  
- All obligations/considerations satisfied → `FULFILLED` (Event: `ContractFulfilled`).  
- Filing within dispute window → `DISPUTED` (Event: `ContractDisputed`).  
- Arbiter ruling: restorative → `SETTLED`; retributive → `BREACHED` with enforcement orders.  
- Administrative `VOID` only if *never* activated or illegal ab initio by Arbiter.

**Timers**  
- `due_min` absolute; `grace_min` added before auto‑`LATE`.  
- `dispute_window_min = min(1440, 0.5 * contract_horizon)` unless venue overrides.  
- Scheduler enqueues checks at due and due+grace (see Tick Loop v1 §8).

---

## 3) Case Model (Data Schema)

```json
{
  "case_id": "k_8831",
  "origin": "CONTRACT|CRIME",
  "contract_id": "c_00123|null",
  "opened_by": "AgentID|FactionID|Clerk",
  "respondent": "AgentID|FactionID",
  "venue": "CIVIC_CENTER|BLACK_NODE|ROYAL_COURT",
  "severity": "LOW|MEDIUM|HIGH|EXTREME",
  "state": "OPEN|EVIDENCE|HEARING|RULING|ENFORCEMENT|CLOSED",
  "arbiter_rank": "JUNIOR|SENIOR|ROYAL",
  "timers": {"evidence_due_min": 120, "hearing_min": 240},
  "orders": {},
  "costs": {"filing": 10, "court": 0},
  "visibility": "PUBLIC|RESTRICTED",
  "lawfulness": "LAWFUL|GREY|ILLICIT",
  "audit": {"bias_flag":0,"latency_min":0}
}
```

---

## 4) Case State Machine

```
[OPEN] --> [EVIDENCE] --> [HEARING] --> [RULING] --> [ENFORCEMENT] --> [CLOSED]
   ^             |            |             |               |               |
   |             |            |             |               |               |
   +--(insufficient grounds)  |             |               |               |
         --> [CLOSED] <-------+----(settlement before ruling)--------------+
```

**Transitions**  
- `OPEN → EVIDENCE`: clerk validates standing; evidence timer starts.  
- `EVIDENCE → HEARING`: minimum evidence quorum met or timer elapsed.  
- `HEARING → RULING`: statements recorded; arbiter deliberates.  
- `RULING → ENFORCEMENT`: orders instantiated (see §6).  
- Any time: parties may settle → `CLOSED` (emit `ArbiterRulingIssued` with outcome=RESTORATIVE).

**Timers & Latency** influence **legitimacy** (Scoring v1 §3): long `latency_min` penalizes leadership.

---

## 5) Evidence Model

Evidence entries accumulate on `CaseID`:

```json
{
  "evidence_id": "e_74",
  "kind": "LEDGER|WITNESS|SENSOR|TOKEN|MEDICAL|VIDEO",
  "submitted_by": "AgentID|FactionID|Clerk",
  "cred": 0.0,
  "salience": 0.0,
  "hash": "sha256...",
  "links": ["EventID", "RumorID"]
}
```

Credibility computed from: witness reliability (reputation), sensor provenance, chain-of-custody, venue integrity. `cred` and `salience` feed **Rumor Belief** only if `visibility=PUBLIC`.

---

## 6) Arbiter Rulings & Orders

### 6.1 Restorative Outcomes (default)
- **Specific Performance**: complete obligation by new deadline.  
- **Make-Whole Transfer**: credits/water/materials to compensate deficits + fees.  
- **Fee Allocation**: loser pays filing/court costs, scaled by reliability history.  
- **Monitoring**: assign clerk audits until completion.

### 6.2 Retributive Outcomes (severe/security)
- **Seizure**: `AssetSeized` from respondent stocks.  
- **Bounty**: `BountyPosted` for capture or asset return.  
- **Curfew/Restriction**: `MilitiaDeployed` at venue.  
- **Void/Blacklist**: contract void, respondent flagged; market prices penalize via risk model.

**Emission**: `ArbiterRulingIssued { case_id, contract_id, outcome, orders }` (priority HIGH/CRITICAL).

---

## 7) Integration Hooks

- `ContractActivated`, `ContractLate`, `ContractFulfilled`, `ContractDisputed` → open/advance cases.  
- Rulings adjust **Reliability R** (Scoring v1 §4), **Legitimacy L** (Scoring v1 §3), and market pricing (risk).  
- PUBLIC rulings feed **Rumor** & **Reputation** updates.

---

## 8) Penalties & Reliability Updates

After ruling:

```
if outcome == RESTORATIVE and completed_on_time:
    R += up_weight *  (0.8 + 0.2*cred_evidence_mean)
elif outcome == RESTORATIVE but late:
    R += mid_weight * 0.4
elif outcome == RETRIBUTIVE:
    R += low_weight * 0.1 if compliance else R -= 0.3
elif BREACHED (defiance):
    R -= 0.6
```

Weights drawn from **Scoring v1 §4** (`α_R`) and venue policy.

---

## 9) ASCII State Diagrams (Compact)

**Contract**

```
DRAFT -> ACTIVE -> FULFILLED
            |          ^
         (due)         |
           v        (dispute)
          LATE --------+
            |                         v                       DISPUTED ----> RULING ---> SETTLED | BREACHED
```

**Case**

```
OPEN -> EVIDENCE -> HEARING -> RULING -> ENFORCEMENT -> CLOSED
 ^                              \___________________________/
 |                                     (settlement)
 +--------------- (insufficient grounds/withdraw) -----------+
```

---

## 10) Pseudocode

```python
def contract_tick_minute(c):
    now = minute_now()
    if c.state == "ACTIVE" and now > c.due_min + c.grace_min and not obligations_met(c):
        c.state = "LATE"; emit("ContractLate", c.contract_id)

def open_dispute(c, opened_by):
    if within_window(c):
        case = new_case(c, opened_by)
        emit("ContractDisputed", c.contract_id)
        return case

def arbiter_rule(case, policy):
    orders = compute_orders(case, policy)  # restorative default
    emit("ArbiterRulingIssued", {"case_id": case.id, "contract_id": case.contract_id, "outcome": orders.kind, "orders": orders})
    apply_orders(orders)
    advance_states(case.contract, orders.kind)
```

---

## 11) Configuration (Policy Knobs)

```yaml
law:
  dispute_window_min: 720
  grace_min_default: 240
  restorative_bias: 0.75       # probability mass toward restorative
  retributive_triggers:
    - "SECURITY_ATTACK"
    - "SABOTAGE_CRITICAL_INFRA"
    - "REPEAT_BREACH>=2"
  bounty_default: 500
  seizure_cap_pct: 0.25        # max stock fraction
  hearing_latency_target_min: 180
```

---

## 12) Audit & Anti‑Fraud

- **Cross-ledger checks**: compare `BarrelDelivered` vs reservoir deltas; mismatch raises fraud flag.  
- **Witness consistency**: conflicting testimonies reduce `cred` and may post fines.  
- **Arbiter bias monitor**: if rulings deviate from precedent without reason, flag `bias_flag` (hurts legitimacy).

---

## 13) Venue Differences

- **CIVIC_CENTER**: PUBLIC visibility; strong witness weight; restorative heavy.  
- **BLACK_NODE**: RESTRICTED; token escrow; retributive available via bounties; anonymity preserved.  
- **ROYAL_COURT**: HIGH priority; rulings propagate legitimacy shifts broadly; retributive tools broader.

---

### End of Contract & Case State Machines v1

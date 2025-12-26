---
title: Diplomatic_Deterrence_v1_Implementation_Checklist
doc_id: D-RUNTIME-0280
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-26
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0245   # Decision Hooks v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0261   # Corridor Risk & Escort Policy v2
  - D-RUNTIME-0266   # Real Factions v1
  - D-RUNTIME-0269   # Institution Evolution v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0273   # Empire Balance Sheet v1
  - D-RUNTIME-0274   # Diplomacy & Treaties v1
  - D-RUNTIME-0278   # War & Raids v1
  - D-RUNTIME-0279   # Fortifications & Militia v1
---

# Diplomatic Deterrence v1 — Implementation Checklist

Branch name: `feature/diplomatic-deterrence-v1`

Goal: make defense posture and treaties interact so the empire can achieve
**stability regimes** that prevent escalation:
- mutual defense pacts and deterrence signaling,
- “threat posture” that reduces raid incentives,
- credibility costs for bluffing,
- phase-aware drift from cooperation (P0) to brinkmanship (P2).

v1 is macro deterrence, not negotiated dialogue.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same deterrence posture shifts.
2. **Bounded.** Operate on TopK neighbor relationships (corridor adjacency).
3. **Composable.** War/raids, treaties, ledger, and defense consume the same signals.
4. **Credibility.** Over-promising without capacity causes penalties.
5. **Phase-aware.** Cooperative P0; coercive/corrupt P2.
6. **Tested.** Pact formation, deterrence effects on raid planning, persistence.

---

## 1) Concept model

Deterrence lives in the relationship graph:
- between wards,
- between factions and wards,
- between factions.

A relationship has:
- perceived threat level,
- perceived credibility of defense,
- treaty commitments (0274),
- history of raids and breaches.

Deterrence is applied by:
- signing mutual defense pacts,
- deploying visible fortifications/militia,
- signaling retaliation thresholds,
- increasing escort/patrol intensity on shared borders.

---

## 2) Deterrence pact types (v1)

Build on treaties by adding 2 treaty types (in 0274 module):
1) **MUTUAL_DEFENSE_PACT**
- obligation: if one party is raided on specified corridors/wards, the other provides:
  - escort capacity boost OR
  - enforcement budget subsidy OR
  - militia support (abstract)
- consideration: reciprocal, or paid via ledger

2) **NONAGGRESSION_PACT**
- obligation: parties commit not to raid/interdict each other’s shipments
- penalty: severe legitimacy loss + sanctions when breached

These are “treaties with teeth.”

---

## 3) Data structures

Create `src/dosadi/runtime/deterrence.py`

### 3.1 Config
- `@dataclass(slots=True) class DeterrenceConfig:`
  - `enabled: bool = False`
  - `neighbor_topk: int = 12`
  - `max_new_pacts_per_week: int = 2`
  - `deterministic_salt: str = "deterrence-v1"`
  - `credibility_decay_per_week: float = 0.03`
  - `credibility_gain_per_week: float = 0.02`
  - `bluff_penalty: float = 0.15`

### 3.2 Relationship state
- `@dataclass(slots=True) class RelationshipState:`
  - `a: str`                        # party id
  - `b: str`                        # party id
  - `threat: float = 0.0`           # 0..1
  - `trust: float = 0.5`            # 0..1
  - `credibility_a: float = 0.5`    # how credible A is to B
  - `credibility_b: float = 0.5`
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.deterrence_cfg`
- `world.relationships: dict[str, RelationshipState]`  # key = "a|b" sorted
Persist in snapshots and seeds.

---

## 4) Relationship update loop (weekly)

Implement:
- `run_deterrence_for_week(world, day)`

Update inputs:
- raids against each other (0278): increase threat, decrease trust
- treaty compliance/breaches (0274): adjust trust and credibility
- visible defense capacity (0279): increases credibility
- crackdown harassment and customs friction (0277/0275): can increase threat

Credibility mechanics:
- credibility increases if a party has real capacity (militia + forts + paid enforcement)
- credibility decays slowly otherwise
- bluff penalty: if a party signs pacts requiring aid, but fails to deliver, credibility drops sharply.

---

## 5) Pact proposal generation (bounded)

Use neighbor graph:
- neighbors defined by corridor adjacency + trade volume
For each ward, consider TopK neighbors and propose:
- MUTUAL_DEFENSE_PACT when raids are frequent and both have some capacity
- NONAGGRESSION_PACT when raids are too costly and trust is borderline but recoverable

Acceptance utility:
- reduces expected raids and corridor collapses
- costs: subsidy payments, escort obligations, political constraints
- cultural constraints: anti_state, xenophobia, honor culture, etc. (0270)

Cap new pacts per week: max_new_pacts_per_week.

Implementation option:
- implement pact proposal by reusing treaties module (0274) to store these treaty types.

---

## 6) How deterrence affects war planning (0278)

Modify raid planner:
- when evaluating a target, compute deterrence penalty:
  - penalty = f(target_relationship_trust, target_credibility, pact_presence)
- if MUTUAL_DEFENSE_PACT exists, defending capacity is boosted:
  - effective defense = base defense + allied contributions
- if NONAGGRESSION_PACT exists between aggressor and target:
  - raid utility gets large negative penalty
  - if raid still happens (desperation), apply severe breach penalties (0274 + this slice)

This is the key: deterrence changes the aggressor’s expected value.

---

## 7) Pact execution (aid delivery)

When a raid occurs:
- trigger “aid obligations” for MUTUAL_DEFENSE_PACT:
  - allied escort coverage increases for N days
  - allied enforcement subsidy transfers via ledger
  - optionally spawn “militia support” as a defense modifier

All bounded:
- cap aid per incident
- cap ledger subsidy per day

If aid not delivered due to insolvency or lack of capacity:
- apply bluff_penalty to credibility/trust.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["deterrence"]["pacts_active"]`
- `metrics["deterrence"]["avg_trust"]`
- `metrics["deterrence"]["avg_threat"]`
- `metrics["deterrence"]["avg_credibility"]`

TopK:
- most fragile neighbor relationships (high threat, low trust)
- strongest deterrence pairs
Cockpit:
- relationship matrix for wards (TopK edges)
- per relationship: trust/threat/credibility, treaty list, recent breaches/raids
- “why raids declined” view: deterrence penalty contributions

Events:
- `PACT_SIGNED`
- `PACT_AID_DELIVERED`
- `PACT_AID_FAILED`
- `PACT_BLUFF_PENALIZED`

---

## 9) Tests (must-have)

Create `tests/test_diplomatic_deterrence_v1.py`.

### T1. Determinism
- same inputs → same relationship updates and pact proposals.

### T2. Pact formation
- under sustained raids and sufficient capacity, mutual defense pacts form.

### T3. Raid deterrence effect
- with pacts/credibility, raid planner selects different targets or reduces ops.

### T4. Aid delivery + bluff penalty
- if ally can pay, aid transfers and defense modifiers apply;
- if not, credibility drops via bluff_penalty.

### T5. Persistence
- relationships and pacts persist across snapshot/load and seed export.

---

## 10) Codex Instructions (verbatim)

### Task 1 — Add deterrence module + relationship state
- Create `src/dosadi/runtime/deterrence.py` with DeterrenceConfig and RelationshipState
- Add world.relationships to snapshots + seeds

### Task 2 — Weekly update loop
- Update trust/threat/credibility from raids, treaty breaches, defense capacity, and customs friction
- Apply credibility decay/gain and bluff penalty logic

### Task 3 — Add pact treaty types + proposal logic
- Extend treaties module (0274) with MUTUAL_DEFENSE_PACT and NONAGGRESSION_PACT
- Propose/accept pacts weekly among TopK neighbors, capped by max_new_pacts_per_week

### Task 4 — Wire pacts into war planner and raid resolution
- Add deterrence penalty to raid target scoring (0278)
- Trigger aid delivery on raids and apply bluff penalties on failure

### Task 5 — Telemetry + tests
- Cockpit relationship matrix and pact dashboards
- Add `tests/test_diplomatic_deterrence_v1.py` (T1–T5)

---

## 11) Definition of Done

- `pytest` passes.
- With enabled=True:
  - relationship trust/threat/credibility evolve deterministically,
  - pacts form and deliver real aid or suffer credibility penalties,
  - raids are deterred by credible defense and treaty commitments,
  - system produces stable “peace regimes” or collapses into war by phase,
  - cockpit explains deterrence state and effects.

---

## 12) Next slice after this

**Migration & Refugees v1** — population movement under corridor collapse/war:
- refugees pressure safe wards,
- legitimacy and culture shift,
- and the empire’s spatial topology evolves politically.

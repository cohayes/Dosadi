---
title: Reform_Movements_and_Anti_Corruption_Drives_v1_Implementation_Checklist
doc_id: D-RUNTIME-0303
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
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
---

# Reform Movements & Anti‑Corruption Drives v1 — Implementation Checklist

Branch name: `feature/reform-anti-corruption-v1`

Goal: create legitimacy restoration loops so that:
- reform coalitions can emerge to fight capture,
- watchdog institutions and audits can expose shadow budgets,
- anti-corruption drives can succeed, stall, or backfire into purges/coups,
- reform pressure becomes a strategic lever for preventing late-phase collapse.

v1 is macro reform coalitions and “drives”, not individual activist agents.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same reform emergence and outcomes.
2. **Bounded.** TopK reforms per polity; bounded audit actions; no explosion of cases.
3. **Legible.** Explain why reform happened and why it failed/succeeded.
4. **Composable.** Hooks into shadow state, leadership legitimacy, policing, media, and governance failures.
5. **Phase-aware.** P1 reform possible; P2 reform dangerous (counter-coups).
6. **Tested.** Emergence, audits, edge reductions, backlash, persistence.

---

## 1) Concept model

A reform movement is a coalition with:
- supporters (factions and institutions),
- targets (captured domains/wards),
- tactics (audits, prosecutions, transparency, purges),
- and risk (backlash, retaliation, sabotage).

Reform drives can be:
- **procedural reform** (rule-of-law, courts, auditing)
- **populist purge** (selective prosecution; may be factional)
- **technocratic transparency** (telemetry + open ledgers)
- **religious revival** (moral reform; can become theocracy adjacent)

We treat reforms as macro “campaigns” with a start day and periodic actions.

---

## 2) Data structures

Create `src/dosadi/runtime/reform.py`

### 2.1 Config
- `@dataclass(slots=True) class ReformConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 14`
  - `deterministic_salt: str = "reform-v1"`
  - `max_reforms_per_polity: int = 3`
  - `max_actions_per_update: int = 6`
  - `emergence_rate_base: float = 0.001`
  - `success_scale: float = 0.55`
  - `backlash_scale: float = 0.35`
  - `retaliation_scale: float = 0.30`

### 2.2 Reform campaign
- `@dataclass(slots=True) class ReformCampaign:`
  - `reform_id: str`
  - `polity_id: str`
  - `kind: str`                      # PROCEDURAL|POPULIST_PURGE|TECH_TRANSPARENCY|RELIGIOUS_REVIVAL
  - `sponsors: list[str]`            # faction_ids
  - `targets: list[dict]`            # e.g. [{"ward_id":"ward:12","domain":"CUSTOMS","priority":1.0}]
  - `intensity: float`               # 0..1
  - `legitimacy_push: float`         # 0..1 how much leadership wants it
  - `risk_tolerance: float`          # 0..1
  - `progress: float = 0.0`          # 0..1
  - `backlash: float = 0.0`          # 0..1
  - `status: str = "ACTIVE"`         # ACTIVE|STALLED|SUCCEEDED|FAILED
  - `start_day: int = 0`
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)`

### 2.3 Audit action record (bounded)
- `@dataclass(slots=True) class ReformAction:`
  - `day: int`
  - `reform_id: str`
  - `action_type: str`               # AUDIT|PROSECUTE|DISCLOSE|PURGE|PROTECT_WITNESS
  - `ward_id: str`
  - `domain: str`
  - `result: str`                    # SUCCESS|FAILED|SABOTAGED
  - `effects: dict[str, object] = field(default_factory=dict)`

World stores:
- `world.reform_cfg`
- `world.reforms_by_polity: dict[str, list[ReformCampaign]]`
- `world.reform_actions: list[ReformAction]` (bounded)

Persist in snapshots and seeds.

---

## 3) Emergence of reform campaigns (biweekly)

Compute reform pressure per polity:
- corruption indices (0302) (capture/shadow_state high)
- scandal frequency (0302)
- leadership legitimacy low but “proc_legit appetite” high (0299)
- media independence high (0286)
- policing procedural share high (0296)
- hardship and unrest (0291) (populist energy)

If trigger and slots available:
- choose kind based on dominant drivers:
  - high procedural + media → PROCEDURAL
  - high hardship + low legitimacy → POPULIST_PURGE
  - high telemetry maturity (0260) → TECH_TRANSPARENCY
  - strong sect pressure (0300) → RELIGIOUS_REVIVAL

Choose sponsors:
- factions with incentives to weaken rivals’ capture (0266)
- watchdog institution if present (new “Audit Office” virtual faction)
- technocrats if education/human capital high (0284)

Targets:
- TopK wards/domains with highest capture and high economic value.

---

## 4) Action loop: audits, prosecutions, disclosures

Each update, per active campaign:
- pick up to max_actions_per_update actions weighted by target priority:
  - AUDIT (attempt to reveal shadow accounts/edges)
  - PROSECUTE (reduce edge strength; seize shadow funds)
  - DISCLOSE (increase exposure; legitimacy gain; backlash risk)
  - PURGE (fast reduction; high backlash; coups risk)
  - PROTECT_WITNESS (reduces sabotage chance)

Success chance depends on:
- policing capacity/procedural share (0296)
- counterintel strength (0287)
- comms reliability (0294) (optional)
- shadow state strength and capture in domain (0302)
- sponsor faction strength and leadership support (0299)

Deterministic: compute score and compare to seeded PRNG.

Effects on success:
- reduce targeted influence edge strengths
- reduce capture indices
- confiscate shadow balances (transfer to polity treasury)
- increase proc_legit and reduce corruption drift

Effects on failure/sabotage:
- increase backlash
- increase shadow retaliation (see next section)
- possible scandal suppression

Update campaign progress and status.

---

## 5) Retaliation and counter-coups

Shadow state may retaliate:
- sabotage audits (destroy records)
- intimidate investigators
- media discredit campaigns
- assassination attempts (hook to 0297)
- leadership coup attempt (hook to 0299)

Retaliation probability increases with:
- reform intensity,
- target domain value,
- and shadow_state index.

If retaliation triggers:
- apply negative effects:
  - reduce comms reliability or generate scandal
  - reduce reform progress
  - increase policing terror share (reactionary shift)
  - increase coup probability (0299)

Bound: only one retaliation incident per polity per update.

---

## 6) Integration points

- Shadow state (0302): audits discover edges/accounts; reduce capture
- Leadership legitimacy (0299): successful reform increases proc_legit; purges may increase fear_legit but harm proc_legit later
- Policing doctrine (0296): procedural policing improves reform effectiveness; terror policing undermines it
- Media (0286): disclosures require independent channels; captured media reduces impact
- Governance failures (0271): failed reforms increase collapse risk and fracture pressure (0298)

---

## 7) Incidents

Use Incident Engine (0242):
- `ANTI_CORRUPTION_DRIVE_LAUNCHED`
- `AUDIT_REVEALS_SHADOW_FUNDS`
- `HIGH_PROFILE_CONVICTION`
- `INVESTIGATOR_ASSASSINATED`
- `REFORM_BACKLASH_RIOTS`
- `COUNTER_COUP_ATTEMPT`

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["reform"]["campaigns_active"]`
- `metrics["reform"]["avg_progress"]`
- `metrics["reform"]["audits_success"]`
- `metrics["reform"]["shadow_funds_seized"]`
- `metrics["reform"]["retaliations"]`

TopK:
- wards/domains most audited
- campaigns with highest backlash
- factions most targeted by prosecutions

Cockpit:
- reform dashboard per polity: campaigns, sponsors, targets, progress/backlash
- audit trail view: actions and outcomes
- corruption delta view: before/after indices per ward
- “why reform failed” explainer: shadow strength vs capacity vs media capture

Events:
- `REFORM_CAMPAIGN_STARTED`
- `REFORM_ACTION_SUCCESS`
- `REFORM_ACTION_SABOTAGED`
- `REFORM_SUCCEEDED`
- `REFORM_FAILED`
- `RETALIATION_EVENT`

---

## 9) Persistence / seed vault

Export:
- `seeds/<name>/reform.json` with campaigns and bounded action history.

---

## 10) Tests (must-have)

Create `tests/test_reform_anti_corruption_v1.py`.

### T1. Determinism
- same inputs → same campaign emergence and action outcomes.

### T2. High corruption increases reform pressure
- rising capture/shadow_state increases probability of campaigns.

### T3. Procedural policing increases audit success
- higher procedural share increases audit/prosecution success rates.

### T4. Purges reduce capture faster but increase backlash and coups risk
- POPULIST_PURGE yields quick capture reduction with increased backlash.

### T5. Retaliation triggers under high shadow state
- higher shadow_state increases sabotage/retaliation frequency deterministically.

### T6. Snapshot roundtrip
- campaigns and outcomes persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add reform module + state
- Create `src/dosadi/runtime/reform.py` with ReformConfig, ReformCampaign, ReformAction
- Add world.reforms_by_polity and reform_actions to snapshots + seeds

### Task 2 — Implement campaign emergence
- Compute reform pressure from corruption, scandals, leadership legitimacy appetite, media independence, and policing doctrine
- Create bounded campaigns with sponsors and targets

### Task 3 — Implement reform action loop
- Run bounded audits/prosecutions/disclosures/purges with deterministic scoring
- Apply effects into shadow state edges/accounts and leadership legitimacy

### Task 4 — Implement retaliation hooks
- Shadow state can sabotage audits and trigger counter-coup/assassination events bounded per polity

### Task 5 — Cockpit + tests
- Add reform dashboards and audit trails
- Add `tests/test_reform_anti_corruption_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - corruption can provoke reform campaigns,
  - audits and prosecutions can measurably reduce capture and seize funds,
  - purges can backfire into backlash and coups,
  - reforms become a meaningful long-run stabilizer (or accelerant),
  - cockpit explains “who is trying to clean house, and why it’s dangerous.”

---

## 13) Next slice after this

**Constitutional Settlements & Rights Regimes v1** — stable rule-of-law endings:
- codified rights, courts, and constitutional crises,
- and the possibility of “late-phase recovery” into durable institutions.

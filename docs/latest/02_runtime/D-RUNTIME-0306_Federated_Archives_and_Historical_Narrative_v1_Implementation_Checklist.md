---
title: Federated_Archives_and_Historical_Narrative_v1_Implementation_Checklist
doc_id: D-RUNTIME-0306
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-12-27
depends_on:
  - D-RUNTIME-0241   # Phase Engine v1
  - D-RUNTIME-0242   # Incident Engine v1
  - D-RUNTIME-0260   # Telemetry & Admin Views v2
  - D-RUNTIME-0286   # Media & Information Channels v1
  - D-RUNTIME-0305   # Metrology & Truth Regimes v1
  - D-RUNTIME-0244   # Belief Formation v1
  - D-RUNTIME-0247   # Focus Mode Awake vs Ambient v1
  - D-RUNTIME-0270   # Culture Wars v1
  - D-RUNTIME-0285   # Ideology & Curriculum Control v1
---

# Federated Archives & Historical Narrative v1 — Implementation Checklist

Branch name: `feature/federated-archives-historical-narrative-v1`

Goal: model memory at empire scale so that:
- polities and institutions maintain archives (records + stories),
- “official history” can drift, be revised, or be contested,
- narrative control feeds into population beliefs and cohesion,
- truth regimes and propaganda influence what is remembered vs erased,
- long-run seeds diverge into technocratic archives, cultic myth-states, or fragmented contradictory histories.

v1 is macro archives + narrative indices, not full-text document storage.

Designed to be handed directly to Codex.

---

## 0) Non-negotiables

1. **Deterministic.** Same seed/state → same archive/narrative evolution.
2. **Bounded.** TopK historical “canon events” per polity; no storing every incident forever.
3. **Composable.** Integrates with belief formation, media, ideology/curriculum, and truth regimes.
4. **Legible.** Explain what is “official canon” and what is suppressed.
5. **Phase-aware.** P0 stable record-keeping; P2 revisionism and archive wars.
6. **Tested.** Canon formation, revision, and persistence.

---

## 1) Concept model

We model two layers:

### 1.1 Archives
Institutional record-keeping capacity and integrity, influenced by:
- truth regimes (0305) and telemetry integrity,
- censorship and propaganda (0286),
- curriculum control (0285),
- and fragmentation (0298).

### 1.2 Narrative
A polity-level “story” about itself:
- founding myth, legitimacy claims, enemies, martyrs, golden ages,
- represented as topic weights and stance vectors.

Archives supply narrative raw material; narrative selection filters what gets canonized.

---

## 2) Archive dimensions (v1)

Per polity:
- `archive_capacity` (0..1): ability to store/maintain records
- `archive_integrity` (0..1): whether archives reflect reality (truth regime dependent)
- `censorship_pressure` (0..1): suppression of records
- `revisionism_pressure` (0..1): drive to rewrite
- `pluralism` (0..1): tolerance for multiple narratives

Per ward (optional): smaller indices for local archives.

---

## 3) Data structures

Create `src/dosadi/runtime/archives.py`

### 3.1 Config
- `@dataclass(slots=True) class ArchivesConfig:`
  - `enabled: bool = False`
  - `update_cadence_days: int = 30`
  - `deterministic_salt: str = "archives-v1"`
  - `max_canon_events_per_polity: int = 64`
  - `max_counter_narratives_per_polity: int = 8`
  - `canon_promote_threshold: float = 0.60`
  - `revision_threshold: float = 0.70`
  - `narrative_effect_scale: float = 0.20`

### 3.2 Canon event
- `@dataclass(slots=True) class CanonEvent:`
  - `canon_id: str`
  - `polity_id: str`
  - `day: int`
  - `source_event_id: str | None`      # tie to incident id if available
  - `topic: str`                        # FOUNDING|WAR|MARTYRDOM|REFORM|SCHISM|TECH|DISASTER
  - `stance: dict[str, float]`          # e.g. {"glory":0.7,"shame":0.1,"enemy":0.5}
  - `salience: float`                   # 0..1
  - `truth_weight: float`               # 0..1 (how aligned with truth regime)
  - `status: str = "CANON"`             # CANON|SUPPRESSED|CONTESTED|REVISED
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.3 Narrative state
- `@dataclass(slots=True) class NarrativeState:`
  - `polity_id: str`
  - `topics: dict[str, float] = field(default_factory=dict)  # weights sum ~ 1
  - `stances: dict[str, float] = field(default_factory=dict) # e.g. xenophobia, martyrdom, reformism
  - `cohesion_effect: float = 0.0`
  - `last_update_day: int = -1`
  - `notes: dict[str, object] = field(default_factory=dict)

### 3.4 Archive state
- `@dataclass(slots=True) class ArchiveState:`
  - `polity_id: str`
  - `archive_capacity: float = 0.5`
  - `archive_integrity: float = 0.5`
  - `censorship_pressure: float = 0.0`
  - `revisionism_pressure: float = 0.0`
  - `pluralism: float = 0.5`
  - `last_update_day: int = -1`

### 3.5 Counter-narrative (bounded)
- `@dataclass(slots=True) class CounterNarrative:`
  - `counter_id: str`
  - `polity_id: str`
  - `topic: str`
  - `stance: dict[str, float]`
  - `support: float`                    # 0..1
  - `risk: float`                       # 0..1
  - `status: str = "ACTIVE"`            # ACTIVE|SUPPRESSED|MAINSTREAMED
  - `notes: dict[str, object] = field(default_factory=dict)

World stores:
- `world.archives_cfg`
- `world.archive_by_polity: dict[str, ArchiveState]`
- `world.narrative_by_polity: dict[str, NarrativeState]`
- `world.canon_events: dict[str, list[CanonEvent]]`
- `world.counter_narratives: dict[str, list[CounterNarrative]]`

Persist in snapshots and seeds.

---

## 4) Inputs: harvesting events into candidate canon

Each month:
- gather TopK incidents since last update (0242) and/or key macro events:
  - wars, coups, reforms, schisms, disasters, discoveries
- compute candidate salience from:
  - event severity, casualties, economic impact, leadership involvement
- compute truth_weight from truth regimes (0305) integrity:
  - low integrity lowers truth_weight (more room for myth)

If `salience * archive_capacity` exceeds threshold:
- promote to canon (bounded max events).

If at capacity:
- evict lowest `salience * retention_weight` where retention_weight favors older canon slightly (avoid churn).

---

## 5) Revisionism and suppression

If censorship/revisionism pressures are high (from media, leadership fear, ideology control):
- some canon events get marked:
  - SUPPRESSED (removed from official narrative)
  - REVISED (stance changed)
- probability increases when truth regimes are weak (0305) and pluralism low.

Counter-narratives:
- if suppression high but pluralism not zero, counter narratives can form (bounded).
- support grows with hardship and culture wars (0270/0291).

---

## 6) Narrative update (monthly)

Update narrative topic weights and stance vector based on canon:
- e.g., many MARTYRDOM canon events increases martyr stance and cohesion in short run
- heavy REFORM canon increases procedural legitimacy narrative
- heavy WAR canon increases xenophobia and militarism stance

Compute `cohesion_effect`:
- short-run cohesion increases with a consistent narrative
- but long-run fragility increases if truth_weight is low and pluralism low

Expose narrative output to:
- belief formation biases (0244) at agent level
- institution evolution (0269) and governance stability
- recruitment drivers in insurgency (0297) and sect conflict (0300)

Keep v1 scalar: provide a handful of stance outputs per polity.

---

## 7) Integration hooks (v1)

### 7.1 Belief formation (0244)
Add optional polity-level narrative priors:
- agents in polity gain a slight bias in belief formation toward narrative stances.

### 7.2 Media and curriculum (0286/0285)
- censorship_pressure and revisionism_pressure derive from these modules (or share indices).

### 7.3 Truth regimes (0305)
- archive_integrity is function of telemetry/ledger truth.

---

## 8) Telemetry + cockpit

Metrics:
- `metrics["archives"]["canon_events_total"]`
- `metrics["archives"]["suppressed_events"]`
- `metrics["archives"]["revised_events"]`
- `metrics["archives"]["avg_truth_weight"]`
- `metrics["archives"]["counter_narratives"]`

Cockpit:
- polity archives page:
  - archive capacity/integrity, censorship, revisionism, pluralism
  - list Top canon events (topic + salience + truth_weight + status)
  - counter narratives and risk/support
- narrative stance view: stance vector and changes over time

Events:
- `CANON_EVENT_ADDED`
- `CANON_EVENT_REVISED`
- `CANON_EVENT_SUPPRESSED`
- `COUNTER_NARRATIVE_FORMED`
- `COUNTER_NARRATIVE_MAINSTREAMED`

---

## 9) Persistence / seed vault

Export:
- `seeds/<name>/archives.json` with archive state, narrative state, canon, counter narratives.

---

## 10) Tests (must-have)

Create `tests/test_federated_archives_narrative_v1.py`.

### T1. Determinism
- same incidents → same canon and narrative outcomes.

### T2. Higher archive capacity yields more canon retention
- increasing archive_capacity increases canon events count bounded.

### T3. Weak truth regimes increase revisionism effects
- lower integrity increases revised/suppressed probability.

### T4. Narrative stances respond to canon topics
- injecting martyrdom incidents increases martyr stance weight.

### T5. Counter narratives form under suppression
- high censorship with some pluralism yields counter narratives.

### T6. Snapshot roundtrip
- canon and narrative state persist across snapshot/load and seeds.

---

## 11) Codex Instructions (verbatim)

### Task 1 — Add archives module + state
- Create `src/dosadi/runtime/archives.py` with ArchivesConfig, ArchiveState, CanonEvent, NarrativeState, CounterNarrative
- Add archive/narrative/canon state to snapshots + seeds

### Task 2 — Implement monthly canon harvesting and retention
- Harvest TopK incidents/events; promote to canon based on salience and archive capacity; bound storage and evict least important

### Task 3 — Implement suppression/revisionism and counter narratives
- Based on censorship/revisionism pressures and truth regime integrity, revise/suppress canon; form bounded counter narratives

### Task 4 — Implement narrative stance updates and hooks
- Compute narrative stances from canon; expose as polity-level priors for belief formation and recruitment dynamics

### Task 5 — Cockpit + tests
- Add archives/narrative pages and timelines
- Add `tests/test_federated_archives_narrative_v1.py` (T1–T6)

---

## 12) Definition of Done

- `pytest` passes.
- With enabled=True:
  - incidents become canon history boundedly,
  - censorship and weak truth regimes enable revisionism,
  - counter narratives form under suppression,
  - narrative stances affect cohesion and belief formation,
  - cockpit explains “what the empire thinks happened.”

---

## 13) Next slice after this

**Inter-Generational Social Mobility v1** — class dynamics over centuries:
- education → skills → roles,
- inheritance and patronage,
- and the long-run “ladder” (or trap) structure.

---
title: Office_Precedent_and_Institutional_Memory
doc_id: D-RUNTIME-0106
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-RUNTIME-0001        # Simulation_Timebase
  - D-RUNTIME-0102        # Campaign_Milestone_and_Crisis_Triggers
  - D-RUNTIME-0103        # Scenario_Framing_and_Win_Loss_Conditions
  - D-RUNTIME-0104        # Scenario_Packaging_and_Metadata
  - D-RUNTIME-0105        # AI_Policy_Profiles
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-INFO-0009           # Counterintelligence_Tradecraft_and_Signatures
---

# 02_runtime · Office Precedent & Institutional Memory (D-RUNTIME-0106)

## 1. Purpose

This document defines a **v1 implementation subset** for how Tier-3 offices
(kings, dukes, bishops, MIL command, guild masters, cartel bosses, etc.) in the
Dosadi system learn from **precedent**:

- their own past decisions, and
- the recorded or remembered decisions of their predecessors and peers.

The goal is to:

- make major actors feel like **career predators with institutional memory**,
- give them a small but meaningful set of **signals and training actions**
  to improve their judgement over time, and
- keep the system implementable as a first pass, with clear extension points
  for richer behavior later.

This v1 subset intentionally focuses on:

- Tier-3 actors (and a few Tier-2 specialists) as primary owners of precedent,
- simple, bounded personal libraries of cases,
- explicit **learning actions** that trade off against other activities,
- a basic model of **bias strengthening or weakening** based on exposure
  to diverse or reinforcing sources.

More complex notions (distinct office vs personal histories, multi-role
cross-pollination, full-blown RL on top) are reserved for future extensions.

---

## 2. Core Concepts (v1)

### 2.1 Precedent entry

At the lowest level, a **precedent entry** is a compressed trace of one
decision and its consequences, as seen through some information channel.

In v1 we model it as:

```yaml
PrecedentEntry:
  decision_type: string          # e.g. "campaign_path", "ci_stance", "guild_action"
  role: string                   # role that took the decision (duke_house, esp_branch, mil_command, guild_master, cartel_boss)
  office_tag: string             # lineage/office identifier (e.g. "duchy:river_ring")

  # Context at decision time (already compressed)
  context_vector: list[float]    # e.g. [stress, fragmentation, legitimacy, local_unrest, local_black_market, seat_risk, patron_satisfaction, phase_one_hot...]

  # Choice made
  action: string                 # action label within that decision_type

  # Outcomes over a fixed horizon (v1: short/medium aggregated into one)
  outcome_vector: list[float]    # e.g. [Δstress, Δfragmentation, Δlegitimacy, Δseat_risk, Δfaction_power]

  # Provenance
  source_type: string            # "archive", "rumor", or "mixed"
  source_integrity: float        # [0, 1] – quality/credibility of this record

  timestamp: int                 # tick when decision was taken
```

This schema is deliberately simple: the game engine is responsible for
compressing world state into `context_vector` and `outcome_vector` according to
its own conventions.

### 2.2 Personal precedent library

Each Tier-3 actor (and some Tier-2 specialists) maintains a **personal
precedent library**:

```python
class PersonalPrecedentLibrary:
    entries: list[PrecedentEntry]   # bounded by memory_capacity_current
```

Agents never query a global, omniscient history. They only query the subset of
history they have **personally ingested** via:

- reading archives,
- listening to storytellers/rumor circles,
- or living through events themselves.

---

## 3. Agent Fields (v1 subset)

The following fields are sufficient to get useful behavior in v1.

### 3.1 Access fields (what history they *could* reach)

Per Tier-3 actor:

```yaml
archive_access_level: int          # 0–3
# 0 = no access
# 1 = local / ward archives
# 2 = branch / guild archives
# 3 = royal / central archives

rumor_circle_tags: list[string]    # social circles they actively frequent
# e.g. ["officers_mess", "dockside_tavern", "guild_lodge"]
```

These act as **hard filters** over the global pool of potential PrecedentEntry
records. A duke without royal clearance cannot see sealed royal incident files;
a cartel boss who never leaves the docks will not hear palace salon gossip.

### 3.2 Capacity & training fields

We assume base attributes already exist (e.g. intelligence, charisma,
literacy, social_skill) and are used to derive:

```yaml
archive_literacy_score: float   # f(intelligence, literacy) in [0, 1]
rumor_attunement_score: float   # f(charisma, social_skill) in [0, 1]
```

The memory-related fields:

```yaml
memory_capacity_base: int       # initial number of precedent entries they can hold
memory_capacity_current: int    # current capacity (>= base, bounded by some global max)
memory_training_xp: float       # cumulative "learning effort" spent
```

- `memory_capacity_base` is set by role and attributes.
- `memory_capacity_current` starts at `memory_capacity_base` and can grow via
  training (Section 4).
- `memory_training_xp` measures how much time they have spent studying; it
  drives **diminishing returns** for future capacity growth.

### 3.3 Disposition & bias fields

These determine how much an actor invests in learning, and how strongly their
existing worldview distorts new information.

```yaml
learning_drive: float            # [0, 1] – propensity to allocate time to learning

source_trust_archive: float      # [0, 1] – baseline trust in archive sources
source_trust_rumor: float        # [0, 1] – baseline trust in rumor sources

bias_strength: float             # [0, 1] – 0=open-minded, 1=heavily biased
bias_style: string               # e.g. "zealous", "cynical", "paranoid", "dogmatic", "opportunistic"
```

- High `learning_drive` means the agent is more willing to trade time and
  attention for additional information and capacity.
- `bias_style` describes the **direction** of distortion (e.g., a zealot
  overweights cases that confirm doctrine; a cynic overweights betrayals).
- `bias_strength` is the **magnitude** of distortion, which can **increase or
  decrease** based on what kind of material they consume (Section 4.3).

---

## 4. Learning Actions (v1)

In v1 we define two generic learning actions that Tier-3 actors (and some
Tier-2 specialists) can take. These actions:

- consume some amount of time / attention in the simulation,
- pull new PrecedentEntry records into the personal library (subject to access
  constraints and capacity), and
- update memory capacity and bias.

We assume the engine exposes them as high-level options, not as direct UI
controls.

### 4.1 StudyArchives(level)

**Preconditions**:

- `archive_access_level >= level`

**Effects** (conceptual):

1. **Add entries to library**  
   - Query the global pool of PrecedentEntry records with:
     - `source_type == "archive"` or `"mixed"`,
     - access constraints compatible with the actor's `archive_access_level`,
     - some focus filters (same role, same office_tag, similar phases, etc.).
   - Sample a batch (size influenced by `archive_literacy_score` and time
     budget) and attempt to insert them into `PersonalPrecedentLibrary`:
     - If the library is full, evict lowest-relevance entries first
       (v1: e.g. oldest + least similar to current role).

2. **Increase training XP and capacity**  
   - Increment:
     ```text
     memory_training_xp += XP_ARCHIVE * learning_drive
     ```
   - If `memory_training_xp` exceeds the next threshold:
     - `memory_capacity_current += Δcapacity`
     - Increase the threshold for next capacity gain (diminishing returns).

3. **Update bias_strength (archive channel)**  
   - Compute a **diversity_scalar** for the new entries, in **[-1, +1]**:
     - positive values → exposure to surprising, non-aligned or
       previously unseen situations (“broadening” experience),
     - negative values → strongly reinforcing material
       (propaganda, cult-mandated reading, selectively curated archive).
   - Update:
     ```text
     bias_strength = clamp01(
         bias_strength
         - D_ARCHIVE * learning_drive * diversity_scalar
     )
     ```
     - Note the sign: if `diversity_scalar` is negative, the product is
       positive and **bias_strength increases** (bias is reinforced).
     - If `diversity_scalar` is positive, bias_strength tends to decrease.       Zealous or dogmatic `bias_style` profiles may cap the maximum possible
       decrease.

### 4.2 WorkRumorCircles(circle_tag)

**Preconditions**:

- `circle_tag in rumor_circle_tags`

**Effects**:

1. **Add entries to library**  
   - Query the pool of PrecedentEntry records with:
     - `source_type == "rumor"` or `"mixed"`,
     - `circle_tag` as one of their provenance tags (if modeled at that level).
   - Sample a batch (size influenced by `rumor_attunement_score` and time),
     and insert them with the same capacity/eviction rules as above.

2. **Increase training XP and capacity**  
   - Rumor-based learning is typically noisier but may still train memory:
     ```text
     memory_training_xp += XP_RUMOR * learning_drive
     ```
     - XP_RUMOR may be lower than XP_ARCHIVE or adjusted per role.

   - Capacity thresholds behave as in StudyArchives.

3. **Update bias_strength (rumor channel)**  
   - Compute rumor-specific `diversity_scalar` in **[-1, +1]**:
     - gossip from the same echo chamber or ideological in-group tends to be
       **negative** (reinforcing existing bias),
     - cross-faction or cross-class circles (e.g. a duke listening in a
       dockside tavern) can be **positive**, exposing alien perspectives.
   - Apply the same update rule as in 4.1, scaled by a separate constant
     `D_RUMOR`.

---

## 5. Decision-Time Precedent Query (v1)

When an actor faces a decision of some `decision_type` (e.g. choose campaign
path, select CI stance, call a guild strike), the engine can invoke a simple
precedent-based helper before applying the AiPolicyProfile.

### 5.1 Inputs

- `decision_type: string`
- `current_context_vector: list[float]`
- `library: PersonalPrecedentLibrary`
- `profile: AiPolicyProfile` (from D-RUNTIME-0105)

### 5.2 Algorithm sketch

1. **Filter library entries by decision_type**:
   ```python
   candidates = [e for e in library.entries if e.decision_type == decision_type]
   ```

2. **Compute similarity and weight** each entry:
   - Similarity `sim(e)` between `current_context_vector` and `e.context_vector`
     (v1: cosine similarity or inverse Euclidean distance with a simple clamp).
   - Source weight `w_source(e)`:
     - `source_trust_archive` or `source_trust_rumor` (from the actor) scaled
       by `e.source_integrity`.
   - Combined weight:
     ```python
     weight(e) = sim(e) * w_source(e)
     ```

3. **Aggregate expected outcomes by action**:
   - For each distinct `action` present in `candidates`:
     - gather all entries with that action,
     - compute a weighted average of their `outcome_vector` using `weight(e)`.

4. **Map outcomes to subjective utility** using AiPolicyProfile:
   - From `profile`, pull the relevant weights (e.g., cares about survival,
     legitimacy, control, economy).
   - Combine the expected Δmetrics into a scalar “expected utility” per action.

5. **Return ranked actions**:
   - The decision hook (e.g. `decide_campaign_path`) can:
     - pick the highest-utility action,
     - or sample with some exploration noise,
     - or override in extreme conditions (e.g. existential threats).

V1 does not require any RL; this is **case-based reasoning** guided by
personality and constrained by access/learning history.

---

## 6. Out-of-Scope for v1 (Future Extensions)

The following ideas are acknowledged but explicitly out-of-scope for the v1
implementation subset and may be added in later revisions:

- Distinguishing **office-level institutional memory** from purely personal
  memory (e.g. persistent archive for a duchy vs one duke's library).
- Richer modeling of **who curates archives** (archivists, bards, intelligence
  brokers as agents with their own incentives).
- Fine-grained modeling of:
  - time windows (short vs medium vs long horizon outcome vectors),
  - per-role feature weightings in context/outcome vectors,
  - social penalties/rewards for being “too well-read” in taboo material.
- Dynamic interaction between **player agency** and institutional memory,
  including deliberate falsification of records, propaganda campaigns, and
  memory purges.

This document should be treated as the baseline contract for Codex and engine
implementations; extensions SHOULD preserve the spirit of:

> Access × Capacity × Disposition + Precedent
>
> rather than introducing omniscient or cost-free learning.

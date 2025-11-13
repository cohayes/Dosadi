---
title: Public_Traceability_and_Ward_Boards
doc_id: D-INTERFACE-0002
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-11
dependent_on: [D-RUNTIME-0001]
---

# Intent

Unify **diegetic explainability & public traceability** into a single interface pillar so players (and tests) can see *why* ward states change. This spec defines UI contracts and data schemas; the scheduling and determinism derive from **Simulation Timebase (D-RUNTIME-0001)**.

# Scope

**In**: read-only civic dashboards (ward board, rumor widget, clinic panel) + auditable **Evidence Cards/Chains** + an Observer-Mode **Golden Day** test harness.  
**Out**: new game rules, art/skin, networking.

# Cadence Contract (derived from D-RUNTIME-0001)

Use symbols from the runtime timebase:
- `TPS` (ticks_per_second), `TPM` (ticks_per_minute), `TPH` (ticks_per_hour), `TPD` (ticks_per_day).  
Schedulers MUST gate on integer tick boundaries emitted by Runtime:

- Minute jobs when `(tick % TPM == 0)`  
- Hourly jobs when `(tick % TPH == 0)`  
- Daily jobs when `(tick % TPD == 0)`

> Codex: reference the actual constants exported by Runtime; do not hardcode numbers here.

# Ward Public Board (Composite)

## Purpose
A per-ward “civic status” roll-up summarizing operational quality and legitimacy.

## Inputs (signals)
- **Safety**: `incident_count`, `response_latency_ms`, `patrol_coverage_pct`, `detentions`  
- **Queues**: `avg_wait_{venue}_min`, `max_wait_{venue}_min`, `throughput_{venue}`  
- **Legitimacy**: `tax_compliance_pct`, `contract_honors_pct`, `corruption_flags`, `dispute_resolutions`  
- **Rumor**: `active_rumors`, `volatility_index`, `safe_zones`, `unsafe_zones`  
- **Clinic**: `LWBS_rate`, `D2D_minutes`, `hygiene_incidents`, `capacity_util_pct`  
- *(optional v1.1)* **Water/Economy**: `price_index`, `ration_uptime_pct`, `capture_efficiency_pct`

## Update cadence
- **Minute**: queues, patrol coverage, capacity util, rumor counts  
- **Hour**: legitimacy drift, volatility index, LWBS, D2D  
- **Day**: safety grade, corruption & disputes

## Aggregations (pure logic)
```
safety_grade_hour   = clamp(100 - (w_incidents_hour*α + avg_response_s*β), 0, 100)
queue_score_min     = clamp(100 - norm_wait_min*γ - max_wait_penalty, 0, 100)
legitimacy_hour     = ema(legitimacy_hour_prev, legitimacy_signals, λ=0.7)
rumor_vol_hour      = normalize(stddev(rumor_strength_active), 0..100)      # higher = noisier
clinic_kpi_hour     = f(LWBS_rate, D2D_min, hygiene_incidents, capacity_util_pct)
civic_index_hour    = weighted_mean([safety_grade_hour,
                                     queue_score_hour,
                                     legitimacy_hour,
                                     inverse(rumor_vol_hour),
                                     clinic_kpi_hour], W)
```
> Constants `α, β, γ, W` in **Appendix A**.

## UI Contract
```ts
type WardPublicBoardProps = {
  ward_id: string;
  tick: number;                  // source tick of latest roll-up
  minute_block: number;          // tick // TPM
  hour_block: number;            // tick // TPH
  safety_grade: number;          // 0..100
  queue_score: number;           // 0..100
  legitimacy: number;            // 0..100
  rumor_volatility: number;      // 0..100 (higher=more volatile)
  clinic_kpi: number;            // 0..100
  civic_index: number;           // 0..100
  highlights: HighlightItem[];   // notable shifts with evidence links
  evidence_chain_ids: string[];  // EvidenceCard ids
}
type HighlightItem = {
  label: string;
  delta: number;
  since_hour_block: number;
  evidence_id?: string;
}
```

# Rumor Venue Widget (Per Location)

## Purpose
Make rumor mechanics legible: spread strength, half-life, alignment fit, venue safety.

## Cadence
- **Minute**: active counts, local strength
- **Hour**: half-life updates, alignment fit, stickiness

## Logic
```
local_strength_min = Σ_i rumor[i].strength * exposure_modifier(agent_set_at_venue)
half_life_hours    = base_half_life_h * venue_factor * safety_factor
alignment_fit      = cosine(pop_alignment_vec, rumor_alignment_vec)   // -1..1
stickiness         = sigmoid(a*local_strength_hour + b*alignment_fit - c*safety)
```

## UI Contract
```ts
type RumorVenueWidgetProps = {
  venue_id: string;
  hour_block: number;
  active_count: number;
  local_strength: number;        // 0..1
  half_life_h: number;
  alignment_fit: number;         // -1..1
  stickiness: number;            // 0..1
  safe_zone: boolean;
  evidence_chain_ids: string[];
}
```

# Clinic Quality Panel

## KPIs & cadence
- **Minute**: capacity_util_pct (beds, staff), arrivals, departures  
- **Hour**: LWBS_rate, D2D_minutes, hygiene_incidents, adverse_events  
- **Day**: mortality, readmit_24h, supply_stockouts

## Logic
```
LWBS_rate_hour     = LWBS_count_hour / max(1, arrivals_hour)
D2D_minutes_hour   = median(t_triage - t_arrival)
quality_score_hour = 100 - norm(LWBS_rate_hour, D2D_minutes_hour, hygiene_incidents, adverse_events)
```

## UI Contract
```ts
type ClinicPanelProps = {
  clinic_id: string;
  ward_id: string;
  hour_block: number;
  LWBS_rate: number;
  D2D_minutes: number;
  hygiene_incidents: number;
  capacity_util: number;
  quality_score: number;
  evidence_chain_ids: string[];
}
```

# Evidence (Auditable Explainability)

## EvidenceCard (JSON)
```json
{
  "evidence_id": "evc_{ULID}",
  "kind": "contract|smuggling|justice|clinic|rumor|patrol|queue",
  "ward_id": "w_12",
  "venue_id": "v_foodhall_03",
  "subject_ids": ["agent_123", "agent_989"],
  "time_tick": 123456,
  "summary": "Short player-readable title",
  "detail": "Long-form narrative with key numbers",
  "inputs": {"...": "raw signals used"},
  "outputs": {"...": "decision or state change"},
  "decision_trace": [
    {"rule": "RUMOR_SPREAD_RULE_2", "score": 0.62, "threshold": 0.55},
    {"rule": "VENUE_SAFE_ZONE", "score": -0.12, "threshold": 0.00}
  ],
  "links": {"next": ["evc_..."], "prev": ["evc_..."]}
}
```

## EvidenceChain
```json
{
  "chain_id": "ech_{ULID}",
  "root_evidence_id": "evc_...",
  "topic": "smuggling_case_17",
  "sequence": ["evc_a", "evc_b", "evc_c"],
  "verdict": "open|resolved|dismissed|penalized",
  "score": 0.0
}
```

# Event & Log Schemas (Runtime)

Emit NDJSON with deterministic timestamps (`tick`).

```json
{"type":"RumorSpreadEvent","tick":123400,"ward_id":"w_1","venue_id":"v_7",
  "rumor_id":"r_22","delta_strength":0.08,"agent_ids":["a1","a9"]}

{"type":"ClinicAdmissionEvent","tick":123450,"clinic_id":"c_1","agent_id":"a2",
  "t_arrival":123440,"t_triage":123470,"acuity":"Mild"}

{"type":"ContractDecisionEvent","tick":123500,"ward_id":"w_1","contract_id":"k_77",
  "decision":"penalty","score":0.71,"rules":["K7","K12"]}
```

# Aggregator Pseudocode

```python
def on_tick(tick):
    ingest_events(tick)

    if tick % TPM == 0:   # minute
        for ward in wards:
            m = minute_rollups[ward]
            m.update_from_buffers()
            publish_ward_minute(ward, m)

        for venue in venues:
            rv = rumor_minute[venue]
            rv.update_local_strength()
            publish_rumor_minute(venue, rv)

        for clinic in clinics:
            cp = clinic_minute[clinic]
            cp.update_capacity()
            publish_clinic_minute(clinic, cp)

    if tick % TPH == 0:  # hour
        for ward in wards:
            h = hour_rollups[ward]
            h.safety_grade = calc_safety(h)
            h.legitimacy = calc_legitimacy(h)
            h.queue_score = calc_queue(h)
            h.rumor_volatility = calc_volatility(h)
            h.clinic_kpi = calc_clinic(h)
            h.civic_index = weighted_mean(...)
            emit_board_state(ward, h)        # -> WardPublicBoardProps
            link_evidence(ward, h)

        for venue in venues:
            rvh = rumor_hour[venue]
            rvh.half_life_h = update_half_life(rvh)
            rvh.stickiness = update_stickiness(rvh)
            emit_rumor_widget(venue, rvh)

        for clinic in clinics:
            ch = clinic_hour[clinic]
            ch.LWBS_rate = compute_LWBS(ch)
            ch.D2D_minutes = compute_D2D(ch)
            ch.quality_score = compute_quality(ch)
            emit_clinic_panel(clinic, ch)

    if tick % TPD == 0:  # day
        daily_rollup()
```

# Observer-Mode “Golden Day” (Test Script)

**Goal:** deterministically exercise boards and confirm assertions.

**Steps**
1. Seed PRNG: `seed=0xD0S4D1`  
2. Load fixture wards/venues (≥3), clinic, rumor seeds, patrol routes, queue patterns  
3. Simulate **2 hours** (≥ 2 * TPH ticks). Ensure:
   - 1 rumor spike at a “safe” venue and 1 at an “unsafe” venue
   - 1 clinic surge producing `LWBS_rate > 0`
   - 1 contract resolved with penalty; 1 dispute dismissed
4. Capture hourly board states (H0, H1) and EvidenceChain

**Assertions**
- `civic_index(H1) != civic_index(H0)` when incidents + queue surge occur  
- `stickiness_unsafe > stickiness_safe` given equal strength  
- `LWBS_rate > 0` iff arrivals > capacity for ≥ N minutes  
- EvidenceChain order matches emitted events  
- Rerun with same seed → identical board values

# Storage Keys

- `ward_board:<ward_id>:<hour_block>` → WardPublicBoardProps JSON  
- `rumor_widget:<venue_id>:<hour_block>` → RumorVenueWidgetProps JSON  
- `clinic_panel:<clinic_id>:<hour_block>` → ClinicPanelProps JSON  
- `evidence:<evidence_id>` → EvidenceCard JSON  
- `evidence_chain:<chain_id>` → EvidenceChain JSON

# Internal API

```
GET /ward/{ward_id}/board?hour_block=...
GET /venue/{venue_id}/rumor?hour_block=...
GET /clinic/{clinic_id}/panel?hour_block=...
GET /evidence/{evidence_id}
GET /evidence-chain/{chain_id}
POST /observer/golden-day/run
```

# Appendix A — Constants

```json
{
  "SAFETY_ALPHA": 2.5,
  "RESPONSE_BETA_PER_SEC": 0.02,
  "QUEUE_GAMMA_PER_MIN": 0.8,
  "CIVIC_WEIGHTS": {
    "safety_grade": 0.30,
    "queue_score": 0.20,
    "legitimacy": 0.25,
    "rumor_inverse_volatility": 0.10,
    "clinic_kpi": 0.15
  },
  "RUMOR": {
    "base_half_life_h": 6.0,
    "venue_factor_safe": 0.7,
    "venue_factor_unsafe": 1.3,
    "stickiness": {"a": 4.0, "b": 1.2, "c": 0.8}
  },
  "CLINIC": {
    "capacity_util_softmax_k": 4.0
  }
}
```

# Notes

- All calculations must be pure; no hidden global state  
- Components degrade gracefully if a prop is missing (“—”)  
- Every highlight should link to at least one `evidence_id`

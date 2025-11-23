---
title: Rumor_Systems
doc_id: D-INFO-0010
version: 1.2.0
status: draft
owners: [cohayes]
last_updated: 2025-11-11
depends_on:
  - D-RUNTIME-0001   # Simulation runtime (tick phases, scheduler)
  - D-AGENT-0001     # Agent Core (memory, perception)
---

# Overview
This document consolidates **Rumors_and_Information (v1)**, **Rumor_Credibility_Propagation (v1.1)**, and **Rumor_Stress_Scenarios (v1)** into a single, testable spec for rumor lifecycle, credibility mechanics, and operational stress scenarios.

Rumors are modeled as propagating information objects tracked across agents, venues, and time. The system targets: (1) emergent behavior in social hubs, (2) factional asymmetries, (3) decision pressure on agents under resource scarcity.

## Scope
- Normative specification for data structures, equations, and event flow.
- Interfaces to runtime (tick phases) and to Agent memory/perception.
- Stress scenarios and a test checklist (conformance & regression).

---

## Interfaces (Inputs/Outputs)
### Inputs
- **Agent perception feed**: sightings, overheard events, social cues.
- **Venue modifiers**: audience composition, safety score, faction tilt.
- **Rumor seeds**: origin, claim vector, initial credibility \(c_0\).
- **Governance signals**: legitimacy index, enforcement heat.

### Outputs
- **Events**:
  - `RumorCreated {id, topic, seed_actor, venue, c0, ttl}`
  - `RumorHeard {id, actor, delta_c, time}`
  - `RumorRebroadcast {id, actor, venue, c_out}`
  - `CounterRumorIssued {id, issuer, target_id, weight}`
- **Agent state updates**:
  - Memory entries with `(topic, last_heard, credibility, source)`
  - Task pressure deltas (e.g., investigate, avoid, report).

**Contracts**
- Credibility \(c\in[0,1]\). Sources must identify self or a proxy type.
- Rebroadcast only if \(c\cdot\text{agent\_broadcast\_propensity} > \theta\).

---

## Data & Schemas
### Rumor object
| field | type | notes |
|---|---|---|
| `id` | UUID | unique rumor id |
| `topic` | enum | indexed topic taxonomy |
| `claim` | vector | compact representation of the claim |
| `credibility` | float [0,1] | running credibility |
| `source_confidence` | float [0,1] | confidence in last source |
| `ttl` | ticks | time-to-live (decays) |
| `tags` | set | e.g., {crime, water, leadership} |

### Venue modifiers
- `audience_alignment` \(\in[-1,1]\) per faction
- `safety_zone` \(\in[0,1]\) — probability of sanction-free talk
- `memory_density` \(\ge 0\) — how “sticky” a venue is for rumor retention

---

## Algorithms / Logic
### Lifecycle
1. **Seed** at venue \(v\) with initial \(c_0\).
2. **Hearing** by agent \(i\): update \(c\leftarrow f(c, i, v)\).
3. **Decision** to rebroadcast: threshold over \(c\) and agent trait bundle.
4. **Decay** \(c\leftarrow c\cdot (1-\lambda)\) per tick; decrement `ttl`.
5. **Countering**: issue counter-rumor with weight \(w\) that subtracts from \(c\).

### Credibility update
Let \(E\) be evidence weight (personal experience, trusted contact, venue trust).  
\[
c' = \sigma\big(\alpha\,c + \beta\,E + \gamma\,S + \eta\,L\big)
\]
- \(S\) = source reputation for this agent, \(L\) = local legitimacy signal.  
- \(\sigma\) is a logistic squashing function to keep \(c'\in[0,1]\).  
- Typical defaults: \(\alpha=0.6,\beta=0.25,\gamma=0.1,\eta=0.05\).

### Venue effect
`effective_c = c' * (1 + k_align * audience_alignment) * (1 + k_safe * safety_zone)`

### Rebroadcast policy
Broadcast if `effective_c > theta_b` and `ttl > 0`. On broadcast:  
`c_out = effective_c * (1 - noise)`, where `noise ~ U(0, epsilon)` models distortion.

### Counter-rumor
- Issued by authority or faction.
- Reduces target rumor via convolution over listeners: `c <- c * (1 - w*reach)`.

---

## Runtime Integration
- **Phases**: Perception → Decision → Social Broadcast → Decay.
- **Tick cadence**: see Timebase (D-RUNTIME-0001). Rumor decay runs per tick; broadcasts scheduled in `SOCIAL` phase.
- **Events produced**: `RumorHeard`, `RumorRebroadcast`, optional `CounterRumorIssued`.
- **Metrics**: spread radius, volatility (std of c), half-life (ticks to `c<0.2`).

---

## Examples & Test Notes
- **Seed-and-spread**: seed at a “safe” venue; expect \(+\) spread radius and lower half-life.  
- **Counter-campaign**: inject counter-rumor mid-spread; expect volatility spike then dampening.  
- **Factional asymmetry**: set opposing `audience_alignment`; verify bifurcated belief clusters.

### Test checklist
- ✓ Credibility stays in \([0,1])\) under all paths.  
- ✓ Decay reduces \(c\) monotonically absent new evidence.  
- ✓ Rebroadcast rate increases with venue safety and alignment.  
- ✓ Counter-rumor reduces average \(c\) proportionally to `w*reach`.

---

## Open Questions
- Should `ttl` be scaled by `memory_density` to model urban legends?  
- Do we need agent “confabulation” noise for low-discipline characters?

## Changelog
- 1.2.0 — Merge of Rumors_and_Information (v1), Credibility_Propagation (v1.1), Stress_Scenarios (v1).


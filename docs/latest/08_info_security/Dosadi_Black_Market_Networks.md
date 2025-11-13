---
title: Dosadi_Black_Market_Networks
doc_id: D-INFOSEC-0007
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-13
parent: D-INFOSEC-0001
---
# **Black‑Market Networks v1 (Smugglers, Brokers, Dark Escrow, and Laundering)**

**Version:** v1 — 2025‑11‑13  
**Purpose.** Model the extra‑legal economy: how contraband goods/services, information, and people move across wards; how anonymity, escrow, and reputation work; how enforcement penetrates, and how these flows perturb prices, legitimacy, and risk in the formal system.

Integrates with **Logistics Corridors & Safehouses v1**, **Telemetry & Audit v1**, **Identity/Licensing & Permits v1**, **Law & Contract Systems v1** (tokenized contracts + Arbiters), **Credits & FX v1.1**, **Production & Fabrication v1**, **Clinics v1.1**, **Rumor v1.1**, **Escort & Security v1**, **Financial Ledgers & Taxation v1**, **Barrel Cascade v1.1**, **Agent Decision v1**, and the **Tick Loop**.

> Timebase: listings & bids **per 10 minutes**; meetups & handoffs **per 5 minutes**; reputation updates **hourly**; crackdowns **daily** or **on trigger**.

---
## 0) Entities & State

- **Node (Market/Hub)** `{node_id, ward, type: BACK_ALLEY|TEAHOUSE|REPAIR_DEN|SAFEHOUSE_DARK|MOBILE, capacity, guard_arrangement, hush_level, audit_heat, closures}`  
- **Broker** `{broker_id, network: {nodes[]}, rep_score, cut%, specialties, keys, safe_phrases}`  
- **Operator (Crew/Smuggler)** `{op_id, faction_hint?, lanes: [SMUGGLER|OUTER|MIDDLE], stealth_score, escort_level, cold_chain?, violence_pref, keys}`  
- **Fence** `{fence_id, convert_map: {item->credits_issuer}, haircut%, laundering_paths[]}`  
- **Listing** `{list_id, type: BUY|SELL|HIRE, commodity, qty, min_grade?, route_hint?, reserve_price_L, expires_at, tokenized?: BlackBoardEscrowToken}`  
- **Order** `{order_id, list_id, side, qty, offer_L, escrow_id?, anonymizer, status}`  
- **Reputation** `{entity_id, score, recency_decay, facets: RELIABILITY|DISCRETION|QUALITY|VIOLENCE}`  
- **Contraband Classes**: `weapons_heavy`, `forged_permits`, `black_parts` (ghost gaskets), `narcotics`, `stolen_barrels`, `info/intel`, `passage` (people), `meds_high`, `data_wipes`.

**KPIs**: `FillRate`, `BustRate`, `AvgRiskPremium`, `SettlementLag`, `FenceHaircut%`, `RumorHeat`, `LaunderVolume`.

---
## 1) Trade Topology & Flows

- **Black‑Board**: anonymous listing wall (tokenized); brokers mirror boards across nodes; time‑boxed for deniability.  
- **Meetup Graph**: listings → broker match → route plan (prefers SMUGGLER/OUTER lanes) → staged handoffs → fence/launder → delivery.  
- **Escrow**: **Black‑Board Escrow Token** holds deposit (liters or issuer credits); releases on **dual‑ack** or Arbiter blind‑arbit rule (optional).  
- **Reputation**: EWMA from successful closings; late/partial/fraud events subtract with heavier weight (discretion facet is private to the black network).

---
## 2) Anonymity & Comms

- **One‑time Phrases**: out‑of‑band pass‑phrases rotate; failure increments bust risk.  
- **Dead Drops**: custody links use **faction‑sealed privacy** grade; opens only with matching shard keys.  
- **Handoff Rituals**: precise micro‑timings, coin flips for order of inspection, and **seal‑tree fragment** verification for parts/lots.

---
## 3) Pricing & Risk Premiums

Total price in liters:  
```
price_L = base_market_L * (1 + risk_premium + scarcity_premium - reputation_discount)
```
- **Risk Premium** ∝ lane heat, recent busts, listing class severity, escort mismatch, and **audit_heat** at nodes.  
- **Scarcity Premium** ∝ supply shortfall (FX shocks, cascade throttles, clinic surges).  
- **Reputation Discount** grows with positive rep of *both* counter‑parties and broker.

---
## 4) Detection, Stings & Crackdowns

- **Signals to Enforcement**: telemetry gaps on official lanes, duplicate serials, sudden issuer reserve dips, rumor spikes, clinic anomalies (tainted meds), and pattern detection (repeated meetup geometry).  
- **Sting Mechanics**: Arbiter/guards inject decoy listings with telemetry traps; acceptance → timed sweep.  
- **Crackdown Event**: node closure with seizures; rep splash damages nearby nodes; **BustRate** up, listings migrate.

---
## 5) Laundering & Fences

- **Paths**: contraband → fence → convert to issuer credits (haircut) → shop invoices (fake) → taxes settled (washing) **or** contraband → issuer bribes → legit permits.  
- **Issuer Risk**: accepting tainted flows raises **reserve breach** and audit odds.  
- **Clinic/Workshop Hooks**: black parts may fail QA; warranty claims expose shops; Arbiter uses seal‑trees to trace fakes.

---
## 6) Violence & Protection

- **Enforcement of Deals**: crews rely on direct violence, hostage posting, or broker‑mediated blacklists.  
- **Safehouse_DARK**: private bays with jammer curtains; lower staging throughput; higher **node guard_arrangement** reduces ambush but increases inspection if exposed.  
- **Assassin & Kidnap Listings**: modeled as **HIRE** class; **tokenized contracts** with proxy payers; Arbiter can invalidate tokens post‑hoc with decree if identities proven.

---
## 7) Policy Knobs (defaults)

```yaml
black_market:
  risk_premium_base_by_class:
    weapons_heavy: 0.40
    forged_permits: 0.35
    black_parts: 0.25
    narcotics: 0.20
    stolen_barrels: 0.60
    meds_high: 0.50
    intel: 0.30
    passage: 0.28
    data_wipes: 0.22
  reputation_decay_per_day: 0.06
  escrow_required_classes: ["stolen_barrels","meds_high","assassin","kidnap","intel"]
  escrow_release_rule: "dual_ack_or_timeout"   # else Arbiter blind-arbit
  fence_haircut_default: 0.18
  node_closure_duration_hours: [4, 72]        # random in range
  sting_injection_rate: 0.03
  crackdown_wave_size: 3
  lane_heat_to_risk_mult: 0.5
  broker_cut_pct_default: 0.05
  max_listing_ttl_hours: 24
```

---
## 8) Event & Function Surface (for Codex)

**Functions**  
- `post_listing(node_id, broker_id?, listing)` → returns list_id; posts to mirrored boards.  
- `place_order(list_id, offer_L, escrow?)` → creates order; holds funds in token escrow if required.  
- `route_dark(order_id)` → selects smuggler lanes + Safehouse_DARK sequence; prints pass‑phrases.  
- `perform_handoff(order_id, node_id)` → seal‑tree fragment check; custody update (privacy grade).  
- `settle_dark(order_id)` → release escrow, update reputations, pay broker/fence cuts.  
- `launder(fence_id, instrument)` → convert tainted stock to issuer credits or invoices.  
- `inject_sting(node_id, listing_proto)` → enforcement API to create decoys per policy.  
- `crackdown(node_id)` → close node; confiscate; broadcast decrees.

**Events**  
- `ListingPosted`, `OrderPlaced`, `DarkRoutePlanned`, `HandoffCompleted`, `DarkSettled`, `FenceConverted`, `StingInjected`, `CrackdownExecuted`, `NodeReopened`.

---
## 9) Pseudocode (Indicative)

```python
def price_contraband(listing, context):
    base = base_market_price_L(listing.commodity, context.fx, scarcity=context.scarcity)
    risk = policy.risk_premium_base_by_class[listing.commodity] \
           * (1 + context.lane_heat*policy.lane_heat_to_risk_mult) \
           * (1 + context.node.audit_heat)
    rep = reputation_discount(listing.counterparties)
    return base * (1 + risk + context.scarcity - rep)

def perform_handoff(order, node):
    if not passphrase_ok(order, node): return "spook"
    if not verify_seal_fragments(order): return "tamper"
    custody_priv = make_custody(order.item, privacy="faction-sealed")
    emit("HandoffCompleted", {"order": order.id, "node": node.id})
    return "ok"

def settle_dark(order):
    if escrow_required(order): release_escrow(order.escrow_id)
    update_rep(order.buyer, order.seller, order.broker, outcome="success")
    pay_broker_and_fence(order)
    emit("DarkSettled", {"order": order.id})
```

---
## 10) Dashboards & Explainability

- **Dark Board** (internal sim view): listings by class, fill rates, prices vs risk/heat, escrow outstanding.  
- **Node Heat Map**: per‑ward audit_heat, closures, migration of volume.  
- **Counter‑party Reputation**: histograms by facet; bust‑adjusted decay curves.  
- **Fence Flow**: laundering volumes by instrument and issuer; reserve impact warnings.  
- **Enforcement Panel**: stings injected, arrests, seizures; spillover to rumor & FX spreads.

---
## 11) Test Checklist (Day‑0+)

- Risk premiums rise with lane heat, recent busts, and commodity severity; fall with high reputation.  
- Stings increase **BustRate** and reduce listings at targeted nodes; volume migrates to neighboring nodes.  
- Laundering increases issuer audit probability; reserve breaches spike FX spread until resolved.  
- Black parts create downstream QA/warranty spikes and Arbiter disputes traceable via seal‑trees.  
- Escrow & reputation reduce defaults; disabling escrow increases scams and violence events.

---
### End of Black‑Market Networks v1

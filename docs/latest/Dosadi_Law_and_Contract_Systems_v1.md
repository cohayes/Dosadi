# **Dosadi Law and Contract Systems v1**

---

## 1) Purpose & Scope

**Law** on Dosadi is the **total ecology of enforceable behavior**: royal edicts, guild ordinances, civic customs, street taboos, and the formal contracts that bind factions. It exists to:

- Convert **promises** into **obligations** with predictable outcomes.
- Stabilize production and exchange amid lethal scarcity.
- Provide structured pathways for **conflict resolution** (restorative first) and, where necessary, **retribution**.

**Core Principle:**  
> Law is weaponized bookkeeping and social memory—recycling conflict back into order.

**Simulation Scope Includes:**
- Royal/feudal mandates and taxes
- Guild standards and licenses
- Civic customs and etiquette norms
- Street codes (“no ratting”), smuggler compacts
- Formal contracts and their enforcement
- **Succession legality** and legitimacy transfer

---

## 2) Normative Layers (What “counts” as law)

| Layer | Domain | Examples | Violation → Rumor Signature |
|---|---|---|---|
| **Royal Law** | Citywide | Barrel cascade rules, royal taxes, rebellion decrees | “Treason,” “Royal audit incoming” |
| **Feudal Law** | Ward | Curfews, gate control, militia call-ups | “Lord can’t enforce,” “Gate bribes” |
| **Guild Law** | Trade | Quality standards, maintenance cycles, secrecy | “Shoddy tools,” “Leaking condensers” |
| **Civic Law** | Public order | Queues, permits, dispute etiquette | “Antisocial,” “Line-cutter protected” |
| **Street Code** | Underclass | Don’t rat; safe zones; black-market norms | “Snitch,” “Bounty on informers” |
| **Cult Statutes** | Sect | Rituals, narcotic rites, taboos | “Heretic,” “Unclean rumor” |

All layers generate **enforcement events** and **rumor emissions**; they can overlap or conflict.

---

## 3) Contract Typology (Objects the code will handle)

Most agreements are **witness-based** via civic observers; some are **tokenized** for traceability.

### 3.1 Contract Object

```yaml
Contract:
  id: UUID
  parties: [AgentOrFactionID, ...]
  type: {MANDATE, TRADE, SERVICE, ALLIANCE, TRUCE, LOYALTY_OATH, LICENSE, SURETY}
  obligations:  # machine-readable tasks
    - {what, qty, quality_spec, location, due_tick}
  consideration:  # what is received in return
    - {asset_type: WATER|CREDITS|PROTECTION|STATUS|ACCESS, amount|grade}
  conditions: {start_tick, end_tick, contingencies[]}
  jurisdiction: {ROYAL|FEUDAL|GUILD|CIVIC|CULT|MIXED}
  record_medium: {WITNESSED, TOKENIZED, HYBRID}
  witnesses: [CivicObserverID|ArbiterID|GuildRegistrarID]
  penalty_structure:
    restorative: {make_whole, surcharge, service_hours, public_apology}
    retributive: {fine, seizure, imprisonment, execution, outlawry}
  reputation_impacts: {on_fulfill, on_breach, on_renegotiate}
  audit_hooks: {clerks[], inspection_interval, report_channels[]}
  status: {PENDING, ACTIVE, FULFILLED, LATE, DISPUTED, BREACHED, SETTLED}
  timestamps: {created, activated, last_audit, closed}
```

### 3.2 Tokenized Instruments (Optional)

- **Sigil/Chip** (physical or cryptographic).  
- Encodes: `contract_id`, `amount/quality`, `issuer`, `escrow rules`.  
- Enables **fungible sub-contracts** (e.g., subcontract a quota) and **royal recalls**.

**Black-Market Usage (Default Convention):**
- **Tokenized contracts are preferred** for smuggling, assassination, and other covert work brokered at **black‑market nodes**.  
- Settlement uses **proxy escrow** (trusted third-party or blind drop) to preserve **creator anonymity**.  
- Breach typically triggers **retributive norms** (vigilante enforcement, bounty issuance) rather than civic mediation.

**Above-Table Civic Usage:**
- “Safe to broadcast” deals (permits, service concessions, public works) are **posted at civic centers** for maximum publicity.  
- These are **witness‑based** by default, with public registers and rumor amplification designed to **raise compliance via visibility**.

---

## 4) Witnesses, Civic Record & Rumor Banks

- **Civic Observers** (lawyers/clerks) register contracts, validate milestones, and append outcomes to the **Civic Record**.
- Each faction maintains a **Rumor Bank**:
  - `verified[]`: first-hand or trusted witness entries
  - `unverified[]`: leads/speculation
- Contract lifecycle events automatically generate rumor entries with **source credibility** and **propagation targets**.

---

## 5) Enforcement Hierarchy (with Arbiters’ Guild)

### 5.1 The Arbiters’ Guild (stratified)

- **High Arbiters (Inner Wards):** adjudicate inter-ducal disputes, mint binding rulings, command royal guard detachments as needed.
- **Circuit Arbiters (Middle Wards):** roving judges for multi-guild and inter-ward cases; can bind local militias with writs.
- **Junior Arbiters (Outer Wards):** handle ward-level disputes; rely on civic watchers and guild stewards; vulnerable to coercion.

**Guild Powers:**
- Register/validate contracts; issue **Writs of Specific Performance**; order **Restitution**; escalate to royal force.
- Maintain **Case Ledger** feeding legitimacy/consistency metrics.

### 5.2 Other Enforcers

| Tier | Actor | Powers |
|---|---|---|
| **Royal** | Praetorians + High Arbiters | Inter-lord seizures, rebellion suppression |
| **Feudal** | Lords’ Militia | Gate closure, seizure, curfew |
| **Guild** | Inspectors/Stewards | Blacklist, equipment denial, license revoke |
| **Civic** | Watchers/Advocates | Mediation, restorative boards, public censure |
| **Street/Cult** | Vigilantes/Enforcers | Informal justice, taboo sanction, exile |

**Default resolution path:** **Civic → Guild/Feudal → Arbiter → Royal** (escalate only if lower fails).

---

## 6) Justice Models (Restorative First, Retributive When Required)

### 6.1 Restorative (Default)

- **Make Whole:** deliver shortfall, replace defective goods, perform service.  
- **Surcharge:** water/credits premium.  
- **Reputation Repair:** public acknowledgment, service to harmed party.  
- **Civic Harmony:** mediated truce, future inspection schedule.

### 6.2 Retributive (Triggers)

- Military-military breaches (e.g., escort betrayal)
- Repeated willful fraud/counterfeit
- Acts endangering ward infrastructure (condensers, scrubbers)
- Low-caste lethal deterrence (biomass/water reclamation logic)

**Note:** Retribution generates **high-energy rumors**; brief legitimacy bump if seen as fair, steep loss if seen as arbitrary.

---

## 7) Succession Law & Legal Continuity

**Succession** = lawful transfer of command and the contract portfolio.

### 7.1 Legitimacy Metric (per faction archetype)

- **Feudal:** mandate delivery + enforcement capacity  
- **Military:** command power (trained troops × equipment × readiness)  
- **Industrial Guild:** technical competence × output reliability  
- **Civic Commonwealth:** service network support × compromise skill × law fluency  
- **Cult:** doctrinal authority × ritual control × narcotic supply lines  
- **Bureaucratic/Arbiters:** seniority × case consistency × incorruptibility score

### 7.2 Succession Procedures (archetype defaults)

- **King/Dukes/Lords:** designated heir; if deposed, victor’s leader assumes title; **Arbiters** record continuity.
- **Military:** highest **command power** officer takes lead; Arbiters validate order of battle rolls if disputed.
- **Guilds:** highest competence master; Guild Council + Arbiter witness; licenses reissued.
- **Civic:** candidate with the broadest service-provider backing; public caucus; Arbiter files charter update.
- **Cults:** per internal canon (chosen heir, trials); Arbiter logs external recognition only.
- **Bureaucrats/Arbiters:** seniority with local flavor; High Arbiter confirms.

**Contract continuity rule:**  
> On succession, **obligations persist**; deadlines may be renegotiated within a short lawful grace window.

---

## 8) Contract Lifecycle & State Machine

### 8.1 States

`PENDING → ACTIVE → (FULFILLED | LATE → {FULFILLED|DISPUTED} | DISPUTED → {SETTLED|BREACHED} | BREACHED) → CLOSED`

### 8.2 Transition Hooks (events & side-effects)

- **Activate:** witnesses logged; rumor “deal struck” emitted.  
- **Fulfill:** civic record credit; +reputation; “reliable” meme increment.  
- **Late:** auto-mediation trigger; small surcharge.  
- **Disputed:** Arbiter assigned; discovery period (clerks/guild inspectors).  
- **Settled:** restorative plan; monitoring schedule.  
- **Breached:** penalties applied; seizure/blacklist; strong rumor emission.  
- **Closed:** archive; impacts decay over time into **memes** if high-salience.

---

## 9) Variables, Signals, and Metrics

| Variable | Meaning | Source/Update |
|---|---|---|
| **Legitimacy[L]** | Perceived ability to enforce & deliver | From Governance module; boosted by consistent rulings |
| **Corruption[C]** | Expected diversion rate | From audits; increases when enforcement weak |
| **Reliability[R]_faction** | Contract completion ratio (weighted) | Contract ledger roll-ups |
| **EnforcementLatency[E]** | Avg ticks to resolve disputes | Case ledger + temporal system |
| **RestorativeRatio** | % disputes settled restoratively | Case outcomes |
| **RetributiveIndex** | Severity & frequency of punishments | Case outcomes |
| **RumorImpact** | Emission weight per event | Rumor system callbacks |
| **ArbiterConsistency** | Alignment across similar cases | Case similarity audit |

**Feedbacks:**
- High **R** → better terms & lower collateral requirements.  
- High **C** or **E** → price-in risk, more tokenized deals, rumor of “law failure.”  
- High **ArbiterConsistency** → city-wide rise in respect for adjudication (legitimacy uptick).

---

## 10) Integration Map

| System | Integration Points |
|---|---|
| **Economy** | Contracts carry production mandates; token mint/recall; taxes on official transfers; reclaimers pay water tax. |
| **Governance** | Legitimacy raised by consistent enforcement; corruption reduces effective law. |
| **Perception & Memory** | Witnessed events stored; credibility determines belief strength; disputes spawn high-salience memories. |
| **Rumor Ecology** | Every lifecycle transition emits rumors; credibility shaped by witness rank and Arbiter tier. |
| **Temporal Simulation** | Deadlines, audits, discovery, and enforcement consume ticks; half-life for reputation/rumor decay. |
| **Environment Dynamics** | Tampering with condensers/scrubbers considered aggravated breach; retributive eligible. |
| **Factional Systems** | Large factions add lawyers (civic), stewards (industrial), captains (military); better enforcement leverage. |

---

## 11) Procedural Algorithms (Pseudocode)

### 11.1 Offer/Accept with Risk Pricing
```
price_premium = f(C, 1-R_counterparty, EnforcementLatency, Legitimacy_context)
collateral    = g(counterparty_rank, tokenization, ArbiterConsistency)
accept        = EV(consideration - price_premium - collateral_opportunity) > threshold
```

### 11.2 Dispute Resolution
```
if restorative_possible and harm_quantified:
    plan = compute_make_whole() + surcharge + monitoring
    outcome = SETTLED
else:
    outcome = BREACHED
    apply_penalties()
emit_rumor(outcome, credibility=arbiter_tier_weight)
update_reputation(parties, outcome)
```

### 11.3 Succession Continuity
```
new_leader = argmax(candidate.legitimacy_archetype_weighted)
carry_over = migrate_active_contracts(to=new_leader)
open_window = set_grace_period()
if renegotiation_requested within open_window:
    Arbiter_mediation()
```

---

## 12) Failure Modes & Narrative Cracks

- **Contract Inflation:** too many unenforceable deals → market freezes.  
- **Selective Enforcement:** perceived bias → faction polarization, parallel legal orders (cult courts).  
- **Clerk Capture:** civic records falsified → reality/rumor split, legitimacy collapse.  
- **Arbiter Schism:** junior arbiters coerced → case inconsistency, black markets seek own “judges.”

---

## 13) Future Hooks

- **Quantified Consistency Scoring** for arbiters (training signal for a judge-RL).  
- **Propaganda & Deception Layer** (intentional rumor shaping in trials).  
- **Cross-Jurisdiction Conflict Resolver** (royal vs guild vs cult law precedence).  
- **Smart-Token Extensions** (escrowed sub-contracts, milestone oracles).  
- **Lawful Rebellion Doctrines** (meta-contracts enabling coups when sovereign breaches primal obligations).

---

### End of Law and Contract Systems v1

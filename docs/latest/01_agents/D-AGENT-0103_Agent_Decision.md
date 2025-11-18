---
title: Agent_Decision
doc_id: D-AGENT-0103
version: 1.0.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-AGENT-0001
---
# **Agent Decision v1 (Drive→Technique→Action Loop)**

**Purpose.** Provide a unified decision loop for Dosadi agents that chooses *what to do next* by translating **Drives** into **Techniques** and finally into concrete **Actions**, subject to constraints (safety, legality, contracts), perceived utilities, and resource budgets (time, energy, water, credits).

Integrates with **Agents v1**, **Perception & Memory v1**, **Rumor v1.1**, **Suit–Body–Environment v1**, **Work–Rest v1**, **Law & Contract Systems v1**, **Credits & FX v1.1**, **Barrel Cascade v1.1**, **Clinic & Health v1.1**, **Security/Escort v1**, and the **Tick Loop**.

> Timebase: **per Minute** micro‑decisions; **per 15 Minutes** re‑plan; **per Day** goal update.

“The v1 drive portfolio D_v1 extends D_v0. For agents using only civic drives, treat D_v1 as a projection where the extra components are either 0 or derived from the 7 primaries.”

---
## 0) Agent State for Decisions

- **Drives Portfolio** (weights sum to 1.0): `{Physiological, Survival, Grow, Hoard, Maintenance, Innovation, Dominance, Subservience, Vengeance, ReputationPreservation, Legacy, Conciliation, Paranoia, Destruction, Reclamation, Order, Curiosity, Transcendence}`
- **Constraints**: safety (`T_core`, stamina, hydration, seal), legal (venue law, oaths, active contracts), social (legitimacy of targets), and budget (time, energy, water, credits).
- **Perception Pack**: local beliefs with credibility, meme indices, prices (FX mids), route risks, clinic wait, venue capacities.
- **Capabilities**: affinities/skills, inventory (suit/tools/rations), known contacts, faction privileges, outstanding promises.
- **Scheduling**: current assignment (job/escort/clinic), mandatory rest windows, curfew and venue hours.

---
## 1) Action Lattice

Three layers:

1) **Drive → Technique Candidates**: e.g., *Survival → Rest, Seek Shelter, Clinic; Hoard → Barter, Secure, Thieve; Conciliation → Commune, Seek Patronage; Innovation → Experiment, Fabricate Prototype; Vengeance → Investigate→Track→Ambush (if legal bounds allow)*.
2) **Technique → Action Schemas**: parameterized blueprints with pre‑/post‑conditions and costs, e.g., `REST(sealed_room, 10m)`, `BARTER(guild_x, tool_y)`, `ESCORT(route_r, shift)`, `OBSERVE(node_k, 5m)`.
3) **Action → Atomic Steps** for the tick loop: move, sense, interact, craft, communicate, transact, fight, rest.

Actions carry: `{preconds, expected_time, water_cost, energy_cost, risk_profile (injury, legal, social), payoff_vector, rumor_emission}`.

---
## 2) Utility Model (myopic with look‑ahead)

Per candidate action `a`:

```
U(a) = Σ_d W_d * Gain_d(a)  -  Cost_energy(a) - Cost_water(a) - Cost_time(a)
       - Risk_injury(a) - Risk_legal(a) - Risk_social(a)
       + Bonus_reputation(a) + InfoValue(a)
```

- **Gain_d**: drive‑specific gains (e.g., Survival ↑ via reducing heat/fatigue; Hoard ↑ via assets; Conciliation ↑ via trust).  
- **Costs**: computed from suit/body models (heat, hydration, fatigue) and FX prices for consumables.  
- **Risks**: probability × severity; legal risk includes Arbiter penalties & contract breach.  
- **Reputation Bonus**: updates to known audiences given rumor propagation probabilities.  
- **InfoValue**: expected reduction in decision uncertainty (VoI) from *Observe/Investigate/Interview* actions.

Agents choose **argmax U** subject to hard constraints; use ε‑greedy or softmax for exploration.

---
## 3) Constraints & Guards

- **Safety Guards** (from Work–Rest): if predicted to cross thresholds within horizon, inject `REST/RECOVERY` before any other pick.  
- **Legality Guards** (Law & Contracts): block illegal actions in inner/mid wards unless *intentional crime* module is enabled.  
- **Contract Guards**: service‑level obligations (shift, escort minimums) preempt low‑value personal actions.  
- **Social Guards**: avoid actions that would tank reputation below faction‑specific floors unless drive pressures exceed **override**.

---
## 4) Planning Horizons

- **H0 (Immediate, 1–5 min)**: greedy with safety/queue forecasting.  
- **H1 (Quarter hour)**: pack compatible actions into a *micro‑plan* (e.g., move → trade → hydrate → rest).  
- **H2 (Daily)**: update drive weights and targets (e.g., save X liters, earn Y credits, finish Z contract).

---
## 5) Rumor & Explainability Hooks

- Each action emits a **visibility footprint**; if observed/heard, creates claim with stance & evidence quality.  
- Decision logs keep **why**: top terms in utility; evidence and prices used; expected vs realized outcomes.  
- Agents avoid spreading rumors that contradict their high‑cred beliefs (until propaganda systems are enabled).

---
## 6) Technique Glossary (seed set)

- **REST / RECOVERY**: choose best venue (SEALED>LEAKY>OUTSIDE), hydrate, snack; updates fatigue and hydration.  
- **HYDRATE / FEED**: acquire rations (prices via FX); choose quality vs cost curve.  
- **COMMUNE**: socialize to raise trust; chance to receive vetted tips; emits benign rumors.  
- **BARTER / TRADE**: swap materials/credits; uses posted FX; risk of being short‑changed scales with venue opacity.  
- **SECURE**: hide assets; improves Hoard; risk/benefit shaped by ward transparency and safehouse quality.  
- **OBSERVE / INVESTIGATE**: gather rumors/evidence; boosts InfoValue; low cost but time‑consuming.  
- **SEEK PATRONAGE**: pitch to a superior; raises Conciliation; risk of reputation loss on rejection.  
- **LABOR / CONTRACT**: perform assigned work; steady income; affects reliability metric.  
- **ESCORT**: join convoy; raises pay + risk; affects legitimacy of issuer and reputation of company.  
- **MAINTAIN**: suit/tool service; preserves failure probability; consumes credits/parts.  
- **INNOVATE**: attempt craft upgrade; consumes reagents; success raises Innovation + future income.  
- **THIEVE / VIOLENCE** (gated): illegal; disabled unless explicit scenario enables crime.  
- **CLINIC**: seek treatment; cost via tier and FX; reduces injury/illness risks.
- **TRANSCEND**: narcotics to mute sensations; short‑term relief; long‑term costs to health & reliability.

---
## 7) Policy Knobs (defaults)

```yaml
decision:
  replan_min: 15
  horizon_min: { H0: 5, H1: 15 }
  epsilon_explore: 0.05
  softmax_temp: 0.15
  risk_aversion: 0.8
  legal_guard_enabled: true
  crime_enabled: false
  reputation_floor: 0.2
  voi_multiplier: 0.25
  rumor_visibility:
    commune: 0.3
    barter: 0.4
    escort: 0.6
    thieve: 0.8
```

---
## 8) Event & Function Surface (for Codex)

**Functions**  
- `decide_next(agent_id)` → returns best action schema under guards.  
- `score_action(agent_id, action_schema)` → utility components & rationale.  
- `microplan(agent_id)` → pack 2–4 actions for H1 horizon.  
- `update_drive_weights(agent_id)` → daily adjustment from outcomes (success/failure, scarcity signals).  
- `log_action_outcome(agent_id, action_id, result)` → learn: reliability, success priors, price memory.  
- `inject_guard_action(agent_id, kind)` → force REST/CLINIC/MAINT when thresholds breached.

**Events**  
- `DecisionMade`, `GuardTriggered`, `ActionStarted`, `ActionCompleted`, `ActionFailed`, `DriveWeightsUpdated`.

---
## 9) Pseudocode (Simplified)

```python
def decide_next(agent):
    if safety_violation_pred(agent): 
        return guard_action("REST")

    candidates = enumerate_actions(agent)
    scored = [(a, utility(agent, a)) for a in candidates if legal_ok(agent, a) and budget_ok(agent, a)]
    a_star = pick(scored, epsilon=policy.epsilon_explore, temp=policy.softmax_temp)
    emit("DecisionMade", {"agent": agent.id, "action": a_star.id, "rationale": explain(agent, a_star)})
    return a_star

def utility(agent, a):
    gains = sum(W[d] * gain(agent, a, d) for d in agent.drives)
    costs = energy(a) + water(a) + time(a)
    risks = injury_risk(a) + legal_risk(a) + social_risk(agent, a)
    bonus = reputation_bonus(agent, a) + value_of_information(agent, a)
    return gains - costs - risks + bonus
```

---
## 10) Learning Hooks

- **Reliability Update**: on‑time arrivals & task completion adjust a personal reliability score used by schedulers.  
- **Success Priors**: Beta/Dirichlet over technique success; converge per venue/ward.  
- **Price Memory**: EWMA of recent FX and local price quotes to improve trade timing.  
- **Reputation Feedback**: compare predicted rumor effect vs actual meme shift to calibrate visibility models.

---
## 11) Test Checklist (Day‑0+)

- Safety guard always preempts risky choices before thresholds.  
- Under scarcity, Hoard/Survival actions outrank low‑value socializing; when fed/rested, social/investment rises.  
- FX shocks tilt choices toward cheaper payers/venues; clinic queues deter non‑urgent care.  
- Escort availability and payments draw agents from low‑value labor when risk‑adjusted utility is higher.  
- Reliability metric moves with punctuality; rumor emissions match action visibility settings.

---
### End of Agent Decision v1

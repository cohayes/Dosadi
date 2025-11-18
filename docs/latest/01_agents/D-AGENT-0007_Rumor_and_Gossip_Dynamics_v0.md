---
title: Rumor_and_Gossip_Dynamics_v0
doc_id: D-AGENT-0007
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-AGENT-0001   # Agent_Core_Schema_v0
  - D-AGENT-0002   # Agent_Decision_Rule_v0
  - D-AGENT-0004   # Agent_Action_API_v0
  - D-AGENT-0005   # Perception_and_Memory_v0
  - D-AGENT-0006   # Skills_and_Learning_v0
  - D-RUNTIME-0001 # Simulation_Timebase
---

# 1. Purpose

This document formalizes **Rumor & Gossip Dynamics** for Dosadi agents.

It turns informal talk into a **strategic system** where:

- Rumors are **moves**, not background flavor.
- Agents choose **when, where, and to whom** to speak based on:
  - Long-term self-interest (loyalty = survival).
  - Local space safety (who overhears? who remembers?).
  - Factional alignments and drives (fear, ambition, loyalty, curiosity).
- Rumors:
  - Alter **beliefs** in `agent.memory` (D-AGENT-0005),
  - Trigger **actions** and emergent “quests” (e.g. investigating, hunting, hiding),
  - Re-shape **social graphs** (trust, suspicion, leverage).

This v0 defines:

- A **schema** for rumor content and state.
- The **logic** by which agents decide to share, suppress, distort, or weaponize rumors.
- Integration with skills (`conversation`, `streetwise`, `perception`) and memory.

---

# 2. Core Principles (8-Point Framework)

This system is rooted in the earlier “8-point” framing (slightly tightened for Codex):

1. **Loyalty = long-term self-interest**  
   - Agents are not “good” or “evil” in abstract.  
   - They propagate or suppress rumors when doing so **maximizes expected long-term payoff** for themselves and those they’re committed to.

2. **Rumor is a calculated move**  
   - Gossip is not free: it has **risk** and **opportunity**.  
   - Each potential utterance is evaluated:
     - Does this help me secure food, shelter, status, safety, leverage?

3. **Spaces have alignment & memory**  
   - Locations (soup kitchen, barracks bar, ward office, alley) have:
     - Typical audiences (loyalist, black-market, mixed),
     - Enforcement presence,
     - A “memory” (how often things said there come back to bite you).

4. **Safe vs unsafe rumor zones**  
   - Some spaces are relatively safe to speak **against authority**.  
   - Some are safe to speak **for authority**.  
   - Some are unsafe to speak at all except trivialities.

5. **Agent-level rumor logic**  
   - Each agent has rumor policies derived from:
     - Drives (fear vs ambition vs loyalty),
     - Faction affiliation,
     - Skills (`conversation`, `streetwise`),
     - Local risk estimates (`memory`, `perceived_safety`, `enforcement_level`).

6. **Social territory as law**  
   - Who “owns” a space (factionally) determines:
     - Which rumors are rewarded,
     - Which are punished,
     - Which factions gain intel or targets.

7. **Emergent quests**  
   - Rumors produce hooks like:
     - “They’re cracking down tomorrow,”
     - “A guard can be bribed at the east gate,”
     - “Someone is hunting soup staff informants.”
   - Agent reactions to such hooks generate emergent missions: flee, investigate, betray, reinforce.

8. **Asymmetric leverage**  
   - Not all gossip is equal.
   - Some agents sit at **information crossroads** (clerks, smugglers, guards, soup staff, medics).
   - Their rumor decisions can swing local conditions dramatically.

---

# 3. Data Model: Rumors & Context

This builds directly on `Rumor` from D-AGENT-0005, adding semantic structure.

## 3.1 Rumor payload schema

`Rumor.payload` (D-AGENT-0005) is structured as:

```python
payload = {
    "category": "THREAT" | "OPPORTUNITY" | "STATUS" | "IDENTITY" | "EVENT",
    "subtype":  str,     # e.g. "CRACKDOWN", "FOOD_SHORTAGE", "NEW_JOB", "SNITCH",
    "ward_id":  str | None,
    "location_id": str | None,
    "target_agent_id": str | None,
    "target_facility_id": str | None,
    "timeframe": str | None,  # e.g. "SOON", "TODAY", "THIS_SHIFT",

    "source_evidence": str | None,  # "I SAW", "HEARD", "OFFICIAL_NOTICE", "RUMOR_CHAIN"
    "claimed_confidence": float,    # speaker's claimed 0..1 confidence
    "promised_payoff": float,       # 0..1: how big the benefit is if true
}
```

This can be refined by future docs; v0 just needs **category**, **subtype**, **targets**, and some sense of **confidence/payoff**.

## 3.2 Rumor state in Memory

Recall from D-AGENT-0005:

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Rumor:
    rumor_id: str
    topic_token: str            # e.g. "BANDIT_ATTACK", "INSPECTION_SOON"
    source_agent_id: Optional[str]
    target_agent_id: Optional[str]
    target_facility_id: Optional[str]
    payload: Dict[str, Any]
    first_heard_tick: int
    last_heard_tick: int
    credibility: float          # 0..1
    times_heard: int
```

`credibility` = agent’s belief the rumor is true/useful.  
Later logic decides when to act on a rumor given `credibility` and `promised_payoff`.

## 3.3 Rumor context: space & faction

Each `ConversationEvent` (D-AGENT-0005) carries:

- `tick`, `speaker_id`, `listener_id`
- `topic_token` = `"RUMOR"`
- `payload` (structured above)
- Location & zone are provided by the world when the conversation is processed.

The world or facility definition should expose:

```python
space_profile = {
    "alignment": "PRO_AUTH" | "ANTI_AUTH" | "MIXED",
    "enforcement_level": float,  # 0..1
    "gossip_risk": float,        # 0..1 (probability words travel upward)
    "gossip_density": float,     # 0..1 (how many agents listen/pass on)
}
```

These parameters heavily affect rumor decisions.

---

# 4. Core Loops

Rumor system runs as three interlocking loops:

1. **Generate / Select rumor to tell** (speaker).
2. **Hear & update belief** (listener).
3. **Act and/or forward** (listener, later ticks).

## 4.1 Speaker: “Do I tell this rumor here, to this person?”

For a speaker `A` considering telling rumor `R` to listener `B` in space `S`, we define an **expected value**:

```text
EV_share = ExpectedBenefit_share - ExpectedRisk_share
```

Where:

- `ExpectedBenefit_share` depends on:
  - R’s category:
    - THREAT → might gain favor with authority / allies.
    - OPPORTUNITY → gain cooperation / allies.
    - STATUS / IDENTITY → gain control, humiliation, leverage.
  - Relationship between A & B (`affinity`, `suspicion`, `threat`).
  - Space alignment (PRO_AUTH vs ANTI_AUTH).

- `ExpectedRisk_share` depends on:
  - `space_profile["gossip_risk"]` and `["enforcement_level"]`.
  - `A` and `B`’s faction alignment vs target of rumor.
  - A’s drives (fear vs ambition).

A simple v0 rule (pseudo):

```text
EV_share = w_benefit * benefit_estimate(A, B, R, S)
         - w_risk    * risk_estimate(A, B, R, S)

IF EV_share > threshold AND A is in mood_to_talk:
    share rumor
ELSE:
    stay silent or talk about something trivial
```

`mood_to_talk` can be influenced by:

- `conversation` skill,
- drives like loneliness/connection,
- fear and suspicion (high fear → tighter mouth, except when snitching to authority is high-payoff).

## 4.2 Listener: updating belief & suspicion

When `B` hears rumor `R` from `A`:

1. `Memory.update_from_conversation(event)`:
   - Creates or updates a `Rumor` entry.
   - Updates `credibility` using:
     - Speaker’s perceived trustworthiness (`1 - suspicion(A)`),
     - Speaker’s track record (rumors confirmed true/false historically),
     - `event.perceived_sincerity`,
     - Listener’s `streetwise` (more skeptical) and `perception`.

2. Listener may update beliefs about:
   - `target_agent_id` (trust/suspicion/threat),
   - `target_facility_id` (safety/access),
   - Or upcoming events (e.g. expected crackdown).

3. Speaker’s **credibility** and **suspicion** are updated **later**, once the rumor is confirmed or contradicted by events.

## 4.3 Followup: act on rumor

On subsequent decision ticks, the decision rule:

- Scans `memory.get_high_credibility_rumors(min_credibility)` (D-AGENT-0005).
- Computes **expected payoff** of acting vs ignoring, based on drives.

Examples:

- Threat rumor:
  - “Crackdown at soup kitchen tonight.”
  - High `credibility`, high `promised_payoff` (avoid arrest).
  - Possible actions:
    - Skip soup kitchen,
    - Warn allies,
    - Go early and leave, etc.

- Opportunity rumor:
  - “Industrial ward hiring exo-suit loaders, high pay.”
  - Drives (ambition, need, greed) push agent toward job-seeking actions.

The key: **rumors become input into ordinary decision-making**, not a separate minigame.

---

# 5. Safe / Unsafe Rumor Spaces

We model space types as **rumor safety profiles**.

## 5.1 Example space archetypes

1. **Garrison Bar (Authority Stronghold)**
   - `alignment = "PRO_AUTH"`
   - `enforcement_level` high
   - `gossip_risk` high
   - Safe to:
     - Praise authority,
     - Snitch on suspects / bandits / dissenters.
   - Dangerous to:
     - Spread anti-authority talk,
     - Suggest sympathy for bandits.

2. **Bandit-friendly Backroom / Smuggler’s Alley**
   - `alignment = "ANTI_AUTH"`
   - `enforcement_level` low (on paper)
   - `gossip_risk` medium (someone might sell you out later)
   - Safe to:
     - Share anti-authority opportunities,
     - Plan raids, prep for crackdowns.
   - Dangerous to:
     - Snitch openly to authority,
     - Admit ties to the garrison.

3. **Mixed Queue: Soup Kitchen Line**
   - `alignment = "MIXED"`
   - `enforcement_level` medium (guards patrolling nearby)
   - `gossip_risk` high (lines are porous; people talk)
   - Safe to:
     - Share “harmless” logistics/info,
     - Spread ambiguous rumors carefully.
   - Dangerous to:
     - Openly incite rebellion,
     - Name specific snitches.

4. **Clerical Office / Ward Administration**
   - `alignment = "PRO_AUTH"`
   - Heavy bureaucratic memory: **things get written down**.
   - `gossip_risk` high for anything off-script.
   - Safe to:
     - Provide formal reports / accusations,
     - Ask about official notices.
   - Dangerous to:
     - Admit illegal behavior,
     - Informally “joke” about subversion.

## 5.2 Implementation hook

The world should provide, for any conversation:

```python
def get_space_profile(location_id: str) -> dict:
    # returns alignment, enforcement_level, gossip_risk, gossip_density, etc.
    ...
```

Agents use `space_profile` in their `EV_share` calculations to decide:

- Whether to speak,
- How much to reveal,
- Whether to distort (blame-shift, omit names).

---

# 6. Agent Logic: Rumor Propagation Policy

Each agent maintains **personal rumor policies** derived from:

- Drives (`fear`, `ambition`, `loyalty`, `curiosity`),
- Skills (`conversation`, `streetwise`, `perception`),
- Faction alignment,
- Past outcomes of rumor involvement.

## 6.1 Personal thresholds

For each agent, define thresholds:

```python
agent.rumor_policy = {
    "min_credibility_to_act": float,    # e.g. 0.6
    "min_payoff_to_act": float,         # e.g. 0.3
    "min_credibility_to_forward": float,
    "min_payoff_to_forward": float,
    "risk_tolerance": float,            # from drives
}
```

Higher fear → higher thresholds (more cautious).  
Higher ambition → lower thresholds for **opportunities**.  
High loyalty to authority / faction → thresholds shaped by rumor category (pro- vs anti-faction).

## 6.2 Share / suppress / distort

Given rumor `R` in memory, at decision time:

1. Determine if it’s relevant to current social context (this listener, this space).
2. Compute `EV_share` as in §4.1.
3. Options:
   - **Share faithfully** if EV positive and risk acceptable.
   - **Distort** (change target, soften edges) if direct share is too risky, but partial hint is useful.
   - **Suppress** if:
     - Sharing helps rivals or hurts loyalty focus.
     - Risk dominates.

Distortion is v0-optional; we can represent it as:

- Mutating the payload for the new `ConversationEvent`.
- Potentially creating a **new rumor_id** downstream (branch in rumor tree).

---

# 7. Skills Integration

Rumors interact strongly with skills from D-AGENT-0006.

## 7.1 Conversation (`conversation`)

- Modulates **success** of rumor-based social actions:
  - Getting someone to accept a rumor,
  - Extracting rumors from others.
- Higher `conversation`:
  - Increases `event.perceived_sincerity` for the listener,
  - Increases chance that listener will share something back.

## 7.2 Streetwise (`streetwise`)

- Modulates **evaluation** of rumors:
  - Higher streetwise makes agents:
    - Better at spotting contradictions,
    - More aware of which spaces are “leaky” or “safe”.
- Implementation examples:
  - Reduce `credibility` boost from a rumor if it conflicts with prior knowledge.
  - Increase **skepticism** of rumors heard in mixed/high-risk spaces.

## 7.3 Perception (`perception`)

- Impacts **confirmation** of rumors:
  - Better perception → more likely to notice evidence that confirms or falsifies a rumor.
- Example:
  - Rumor: “Crackdown squads patrol the north gate at night.”
  - Agent with high `perception` on patrol/observation might:
    - Quickly confirm → boost credibility of both the rumor and the speaker.
    - Quickly falsify → reduce both.

## 7.4 Intimidation & Weapon Handling

- Threat-based rumor usage:
  - “Everyone knows the guard captain wants you dead.”
  - Spreading this in certain spaces is effectively an intimidation move.
- High `intimidation` / `weapon_handling` make threat rumors more potent (but also riskier).

---

# 8. Memory, Credibility & Consequences

## 8.1 Credibility evolution

`Rumor.credibility` is updated over time via:

1. **Multiple sources**  
   - Hearing similar rumors from multiple independent speakers increases credibility.
2. **Confirming evidence**  
   - Perception & events that align with rumor predictions.
3. **Contradictions & failures**  
   - When predicted events do not occur, credibility declines.

This is largely implemented in `Memory._update_rumor_credibility(...)` (D-AGENT-0005-SKEL) with additional input from world events.

## 8.2 Speaker trust updates

When a rumor gets **resolved** (world events mark it TRUE or FALSE):

- For listeners who previously heard it from speaker `A`:
  - TRUE:
    - `memory.adjust_suspicion(A, -Δ, reason="RUMOR_CONFIRMED", tick=...)`
    - `memory.adjust_affinity(A, +Δ, reason="HELPFUL_INFO", tick=...)`
  - FALSE (especially malicious):
    - `memory.adjust_suspicion(A, +Δ, reason="MISLEADING_INFO", tick=...)`
    - `memory.adjust_affinity(A, -Δ, reason="BETRAYAL", tick=...)`

Over time, this builds speaker-specific **reputation** as reliable or duplicitous.

---

# 9. Hooks for Codex Implementation

This doc is meant to guide implementation but not dictate exact math.

Recommended modules:

- `rumors.py`:
  - `evaluate_rumor_share(agent, rumor, listener, space_profile) -> float` (EV_share).
  - `speaker_choose_rumor(agent, memory, space_profile, listener) -> Optional[rumor]`.
  - `listener_update_from_rumor(agent, event, space_profile)`.
  - `resolve_rumor_outcomes(world_events, agents)` – optional world-level function.

- Integration points:
  - `TALK_TO_AGENT` (D-AGENT-0004):
    - When `topic_token == "RUMOR"`, call into `rumors.py`.
  - Decision rule (D-AGENT-0002):
    - When planning social actions, use rumor EV estimates to choose whether to gossip or stay silent.

---

# 10. Roadmap & Extensions

Future refinements may include:

1. **Rumor genealogies**
   - Track chains: who heard from whom, which branches mutated.
   - Useful for forensics and advanced play (“Who started this?”).

2. **Factional information warfare**
   - Dedicated agents/factions specializing in:
     - Disinformation,
     - Propaganda,
     - Controlled leaks.

3. **Quantified leverage**
   - Explicit “blackmail tokens” or “favor tokens” derived from rumors.
   - Integrated into economy / law / interfaces pillars.

4. **UI & debug views**
   - Tools to visualize rumor spread and credibility across wards.
   - Useful for design-time balancing and narrative tuning.

This v0 Rumor & Gossip system should be sufficient for:

- Implementing basic gossip mechanics around:
  - Snitches vs bandits vs civilians,
  - Crackdowns and opportunities,
- While leaving room to layer in richer dynamics later without rewriting core agent memory or skill systems.

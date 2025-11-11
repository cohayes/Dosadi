---
title: Dosadi_Rumors_and_Information
doc_id: D-INFO-0001
version: 1.0.0
status: stable
owners: [cohayes]
depends_on: 
includes:
  - D-INFO-0002  # Rumor_Credibility_Propagation
  - D-INFO-0003  # Rumor_Stress_Scenarios
  - D-INFO-0004  # Security_Loop
  - D-INFO-0005  # Smuggling_Loop
  - D-INFO-0006  # Escort_and_Combat
last_updated: 2025-11-11
---
# **Dosadi Rumors and Information Systems v1**

---

## **1. Purpose and Philosophy**

Rumors are the lifeblood of social perception. They carry not just facts, but **beliefs**, **biases**, and **intentions** — shaping how agents and factions act even when the truth is inaccessible.

**Core Principle:**  
> On Dosadi, truth decays faster than water.  
> What matters is not what *is*, but what is *believed*.

Rumor systems convert the world’s data into *subjective perception streams*, influencing loyalty, legitimacy, fear, and ambition. They are the connective tissue linking **environmental events**, **social memory**, and **agent psychology**.

---

## **2. Rumor Ontology: The Structure of Information**

Each rumor is an **object** with identity, credibility, and scope.

| Property | Type | Description |
|-----------|------|-------------|
| **ID** | UUID | Unique identifier |
| **Source** | Agent or Faction | Origin of the rumor |
| **Target** | Agent, Faction, or Location | Subject of the rumor |
| **Type** | Political, Economic, Personal, Mystical, Environmental | Category of information |
| **Content Vector** | Data + sentiment | Fact or statement with bias |
| **Credibility (0–1)** | Probability of truth | Weighted by verification |
| **Propagation Weight (0–1)** | Strength of transmission | Influences spread rate |
| **Decay Rate (per cycle)** | 0.05–0.15 | Credibility loss over time |
| **Visibility Tier** | Private, Faction, Public | Who can perceive it |
| **Intent** | Informative, Manipulative, Defensive | Purpose behind rumor creation |
| **Emotion Vector** | Fear, Pride, Envy, Awe, etc. | Emotional payload |
| **Timestamp** | Epoch | Temporal anchor for simulation clock |

Rumors can be **atomic** (single statement) or **compound** (bundles that merge and mutate during propagation).

---

## **3. Information Sources**

Rumors originate from **five major pathways**:

| Source Type | Example | Reliability |
|--------------|----------|-------------|
| **Witnessed Events** | “The duke’s guards executed three workers.” | High (0.8–1.0) |
| **Secondhand Testimony** | “A friend of a machinist saw it happen.” | Moderate (0.4–0.7) |
| **Faction Broadcasts** | Official proclamations or propaganda. | Variable (0.2–0.9) |
| **Intentional Falsehoods** | Smear campaigns, mystic visions. | Low (0.0–0.5) |
| **Data Artifacts** | Leaked documents, intercepted communications. | High but limited scope |

Each source type also leaves **contextual metadata** — allowing downstream agents to trace or infer origin, depending on skill and memory.

---

## **4. Rumor Lifecycle**

| Stage | Process | Description |
|--------|----------|-------------|
| **1. Generation** | Event → Rumor creation | Triggered by notable environmental, political, or personal events. |
| **2. Propagation** | Spread across agents/factions | Carried by dialogue, trade, digital systems, or narcotic cult networks. |
| **3. Verification** | Evaluation by recipient | Agent decides belief weight using trust, loyalty, and personal bias. |
| **4. Mutation** | Distortion via retelling | Bias and memory noise modify content or sentiment. |
| **5. Institutionalization** | Rumor becomes “common knowledge” | Achieved when credibility > threshold and coverage > faction size. |
| **6. Decay** | Fades into myth | Information loses weight unless reinforced by new evidence. |

This lifecycle operates on **Temporal Simulation ticks**: each cycle advances the rumor’s decay, while interactions refresh or mutate its form.

---

## **5. Propagation Mechanics**

### **5.1 Transmission Probability**
When two agents or factions interact:

\[
P_{transmit} = f(Trust, Interest, Privacy, EmotionalIntensity)
\]

Where:
- **Trust:** Higher = more likely to share truthfully.  
- **Interest:** High if rumor aligns with receiver’s goals.  
- **Privacy:** Lower in public or hostile environments.  
- **EmotionalIntensity:** Amplifies sharing, especially for fear, envy, or outrage.

### **5.2 Mutation and Noise**
Each retelling adds distortion:

\[
Rumor_{t+1} = Rumor_t \times (1 - NoiseFactor) + Bias_{speaker}
\]

Bias derives from caste, faction alignment, and psychological traits (fearful agents exaggerate danger, ambitious agents inflate opportunity).

### **5.3 Reinforcement**
Repeated encounters with similar rumors amplify perceived truth:

\[
Credibility_{new} = Credibility_{old} + (1 - Credibility_{old}) \times ReinforcementRate
\]

When multiple agents verify the same event, it transitions toward “public record.”

---

## **6. Rumor Ecology: Social Networks and Memory**

Rumors move through **social graphs** governed by faction ties, ward proximity, and social caste.

### **6.1 Propagation Networks**
- **Local Loops:** Within a ward or faction — fast spread, high redundancy.  
- **Inter-Ward Smuggler Routes:** Slower but carry critical cross-ward intelligence.  
- **Vertical Channels:** Subordinate → superior → peer → subordinate (hierarchical rumor recursion).  
- **Broadcast Events:** Public speeches or mechanical announcements, high reach but low precision.

### **6.2 Rumor Banks**
Each faction maintains a “rumor bank” — a weighted store of collective knowledge.  
Rumors with sufficient credibility can influence:
- **Faction decisions** (e.g., to rebel, cooperate, or trade).  
- **Legitimacy recalculations** for leaders.  
- **Agent behavior** (fear, opportunism, loyalty shifts).

Rumors too dangerous to share may be **suppressed**, **sold**, or **weaponized** via controlled leaks.

---

## **7. Psychological Integration**

Rumors are not just data — they *rewrite perceptions*. Each agent maps incoming rumors into its internal state:

| Input | Psychological Effect | Notes |
|--------|----------------------|-------|
| **Threatening rumor** | Raises Fear → reduces initiative | May trigger flight or defensive behavior |
| **Reward rumor** | Raises Ambition or Hope | May increase risk-taking |
| **Betrayal rumor** | Lowers Loyalty | Directly undermines legitimacy |
| **Flattering rumor** | Raises Confidence | Increases charisma or dominance display |
| **Mystical rumor** | Raises Awe or Confusion | Can alter rationality or hallucination states |

Narcotic use, sensory fatigue, and caste-based education all alter the *weighting* of rumor influence.

---

## **8. Integration with Governance and Temporal Systems**

- **Temporal Link:** Each simulation tick updates rumor propagation, decay, and reinforcement probabilities.  
- **Governance Link:** Factional legitimacy adjusts based on *rumor density* and *alignment*.  
- **Economic Link:** Rumors about scarcity or surplus alter market demand.  
- **Conflict Link:** Certain rumor combinations act as triggers for rebellion or suppression events.

---

## **9. Quantitative Metrics**

| Metric | Description | Behavior |
|---------|-------------|-----------|
| **Rumor Density** | Active rumors per ward | Indicator of social volatility |
| **Credibility Index** | Mean credibility value | Global trust measure |
| **Noise Factor** | Average mutation rate | Cultural stability measure |
| **Propagation Velocity** | Rumors per tick | Information speed |
| **Faction Rumor Bias** | % of rumors favoring a faction | Political sway index |
| **Rumor Half-Life** | Average persistence in cycles | Memory retention metric |

---

## **10. Future Hooks**

- **Rumor Markets:** Information as trade commodity; factions auction secrets.  
- **Black Archives:** Central rumor repositories accessible only to certain agents.  
- **Cognitive Warfare:** Deliberate manipulation of rumor ecology to destabilize rivals.  
- **Machine Rumors:** Artificial intelligence or Well-monitor whispers shaping events.  
- **Cultural Memory:** Some rumors persist across generations, forming myth and religion.

---

### **End of Rumors and Information Systems v1**

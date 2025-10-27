# Perception and Information – Dosadi

## Overview
Knowledge is the rarest resource on Dosadi.  
The simulation models how incomplete, distorted, or manipulated information governs survival and social control.  
No agent ever sees the full truth — perception is a biased lens shaped by fear, loyalty, and sensory limits.

---

## Sensory Channels

| Sense | Simulation Purpose | Notes |
|--------|---------------------|-------|
| **Sight** | Spatial awareness, recognition of movement and gesture. | Filtered by light, distance, and visibility rules. |
| **Sound** | Communication, threat detection. | Noise masking and overlapping conversations produce uncertainty. |
| **Smell** | Biological cues (sweat, decay, chemical leaks). | Can indicate stress or proximity in closed spaces. |
| **Touch** | Physical feedback, fatigue, temperature regulation. | Provides reliability where vision/sound fail. |
| **Taste** | Symbolic in simulation — used for evaluating food purity or narcotics. | Connects to addiction and loyalty vectors. |

Each sense can be selectively modeled as an input channel in the agent’s observation vector.

---

## Observation Model
Agents do not perceive global state directly.  
Instead, they receive *noisy, partial* data influenced by:
- Environmental `noise` variable.  
- Agent skill and focus.  
- Faction-controlled information networks.  
- Deception or camouflage from others.

### Example (simplified)
```python
def observe(agent, env):
    return {
        "scarcity": env.scarcity + random.uniform(-env.noise, env.noise),
        "danger": env.danger + random.uniform(-env.noise, env.noise),
        "signals": agent.known_facts.sample(k=3)
    }```

---

## Information Ecology
Information itself behaves like a fluid resource:
- Generation: perception, investigation, espionage.
- Propagation: rumor, trade, and surveillance.
- Decay: memory loss, censorship, and deliberate disinformation.
Agents act on belief states, not objective reality.
Two agents may inhabit entirely different “truths” while sharing the same environment.

---

## Rumor and Gossip Dynamics
Social information spreads through conversation and observation.
Each rumor has:
- Origin: who started it and for what motive.
- Propagation Value: perceived usefulness or alignment with goals.
- Distortion: how content changes with each retelling.
- Risk: being caught spreading misinformation.
This mechanic allows emergent social evolution and power shifts.

---

## Surveillance Networks
- Operate as both data collection and psychological control.
- Agents know they are being watched but not by whom.
- Observation alters behavior even when no punishment follows.
- Surveillance failures (blind spots, corrupted records) become opportunities for rebellion.

---

## Cognitive Bias and Interpretation
Perception is filtered through personal bias:
- Fear Bias: danger overestimation under stress.
- Loyalty Bias: information consistent with faction narrative is trusted more.
- Familiarity Bias: repeated signals override accuracy.
Agents can “learn” new biases over time through reinforcement or trauma.

---

## Simulation Notes
- Observation Space: subset of environment variables + interpersonal signals.
- Information Exchange: functions enabling rumor trade, espionage, or deception.
- RL Integration:
	- Each agent’s observation vector defines its state input.
	- Misperception introduces stochasticity, encouraging robust policies.

---

## Design Philosophy
Dosadi’s truth is never absolute — it is a negotiation.
Power belongs to those who can see the pattern beneath the noise.
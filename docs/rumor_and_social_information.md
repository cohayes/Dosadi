# Rumor and Social Information – Dosadi

## Overview
Rumor is Dosadi’s bloodstream.  
Information — true or false — moves faster than water and is traded with greater risk.  
Rumor connects survival, reputation, and control; it transforms private fear into public consequence.

---

## Conceptual Model
Rumor is treated as a **propagating data object** within the simulation, moving through the agent network based on trust, fear, and utility.

Each rumor has:
- **Origin:** the first speaker or event.  
- **Content:** factual or fabricated claim.  
- **Credibility:** perceived likelihood of truth.  
- **Alignment:** whether it benefits or threatens each faction.  
- **Risk Factor:** danger of being associated with its spread.  
- **Mutation Rate:** probability that details distort per transmission.

Agents maintain *belief sets* that evolve through exposure, contradiction, and reinforcement.

---

## Propagation Mechanics

### 1. Creation
Rumors emerge from:
- **Observed events** (e.g., “food shipment arrived late”).  
- **Deliberate manipulation** (propaganda, psychological warfare).  
- **Anomalies** (sensor failures, missing citizens, unexplained noises).  

### 2. Transmission
When two agents interact:
	if trust(a,b) > threshold and rumor.utility(a) > cost(a,b):
	b.receive(modified(rumor))
Each exchange introduces distortion, delay, or emphasis.

### 3. Mutation
Rumors mutate according to:
- Stress level of the speaker.  
- Intentional bias (favoring faction narrative).  
- Audience reaction (confirmation vs rejection).  
- Network density (echo chambers amplify coherence).  

### 4. Decay
If a rumor ceases to be repeated or contradicted by direct experience, it fades:
	rumor.credibility -= decay_rate * time
	
---

## Social Effects
- **Fear Amplification:** false crises trigger hoarding, riots, or purges.  
- **Power Consolidation:** elites seed rumors to test loyalty or discredit rivals.  
- **Trust Networks:** repeated accurate sharing builds long-term alliances.  
- **Factional Drift:** misinformation splits or merges factions over time.  

---

## Agent Logic
Each agent evaluates rumors according to:
1. **Source Reputation:** how reliable is the speaker?  
2. **Risk of Belief:** will repeating it endanger survival?  
3. **Expected Gain:** could it improve standing or safety?  
4. **Verification Cost:** effort to confirm truth.  
5. **Audience Type:** who benefits from knowing?

Decision heuristic:
	share_probability = (trust + gain - risk) * curiosity
	
---

## Emergent Gameplay Potential
- Dynamic **information landscapes** — different groups inhabit different realities.  
- Hidden **quest chains** — missions triggered by false information or propaganda.  
- **Reputation mechanics** — accuracy and timing of rumor spread determine credibility.  
- **Factional manipulation** — players can seed or suppress narratives to steer society.  

---

## Simulation Implementation
Rumors can be implemented as lightweight data objects in memory:
```python
class Rumor:
    def __init__(self, origin, content, alignment, credibility=0.5):
        self.origin = origin
        self.content = content
        self.alignment = alignment
        self.credibility = credibility
        self.history = [origin]
```
Rumor propagation events occur during social interactions inside Agent.step().
Logging rumor lifecycles allows later analysis of narrative diffusion — how society "learns" or collapses under disinformation.

---

## Philosophical Frame

Truth on Dosadi is not moral, it is strategic.
Rumor is the planet’s unconscious — a collective algorithm that predicts and invents power at the same time.
To master rumor is to rewrite reality.
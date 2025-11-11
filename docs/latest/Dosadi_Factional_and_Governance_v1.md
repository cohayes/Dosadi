# **Dosadi Factional and Governance Systems v1**

---

## **1. Purpose**

Factional and Governance Systems define how organized power operates on Dosadi.  
Every ward, guild, cult, and noble lineage acts as both a **political entity** and a **survival strategy**, competing for legitimacy, resources, and loyalty.

Governance is not merely administration — it is the practice of rationing hope.  
Legitimacy, corruption, and loyalty together determine who can command obedience, who will defect, and who will die quietly.

---

## **2. Faction Taxonomy**

| Category | Description | Example |
|-----------|--------------|----------|
| **Feudal Hierarchies** | The king, dukes, counts, and ward lords. Formal rulers, linked through oaths and production mandates. | The Lord of Ward 12, Duke of the Western Aqueduct |
| **Guilds** | Trade, industrial, or service organizations that regulate skill, labor, and maintenance. May span multiple wards. | Machinists Guild, Reclaimers Guild |
| **Mercenary & Militia Orders** | Contracted armed groups who sell violence or security to lords and guilds. | The Iron Barter Militia |
| **Underclass Collectives** | Loosely organized survival groups in destitute wards; scavengers, smugglers, black-market traders. | The Ash Rats |
| **Mystic Cults** | Narcotic or ideological sects providing counterfeit spiritual security and mind control. | The Breath of the Deep |
| **Administrative Clerks** | Bureaucratic networks that track credits, barrels, and taxes; loyal to whoever feeds them best. | The Auditors’ Collegium |

Each faction type operates under a **functional ideology**: a narrative explaining why it deserves water. These ideologies create factional memes — durable collective identities that guide recruitment and obedience.

---

## **3. Governance Pillars**

### **Pillar 1 – Structure and Hierarchy**

Governance forms a **vertical web**:  
The King sits atop, distributing water and mandates through dukes and lords. Each layer acts as both *recipient and gatekeeper*, translating royal edicts into local law.

Below formal authority, guilds, militias, and cults provide horizontal power bases.  
Control exists not only in command chains but in the **networks of dependency**: who maintains whose suit, who trades which tools, who hides whose dead.

---

### **Pillar 2 – Authority and Obedience**

Obedience is not faith — it’s **calculated compliance**.  
Agents follow orders when the *expected punishment for defiance* exceeds the *potential reward for rebellion.*

Obedience flows through:
- **Fear** – of enforcement, starvation, or exposure.  
- **Reward** – access to water, protection, or status.  
- **Habit** – conditioned repetition of social order.

These dynamics are simulated through legitimacy and loyalty feedbacks:  
when leadership is perceived as weak, corruption and factional autonomy increase.

---

### **Pillar 3 – Legitimacy, Corruption, and Loyalty**

| Concept | Definition | Mechanism | Result of High / Low Value |
|----------|-------------|------------|-----------------------------|
| **Legitimacy** | The perceived ability of a leader to command obedience and enforce mandates. | Derived from successful production, consistent law enforcement, and rumor of competence. | High: obedience through respect or fear. Low: splinter factions, rival claimants, civil unrest. |
| **Corruption** | Diversion of collective resources into private hoards or black markets. | Increases with low legitimacy and poor oversight. | High: economic stagnation, rising inequality. Low: stability, but possibly at cost of fear or rigidity. |
| **Loyalty** | The rational alignment of an agent’s long-term self-interest with a superior. | Reinforced by mutual benefit, protection, and reputation for keeping promises. | High: factional cohesion. Low: opportunistic betrayal. |

Corruption grows naturally as legitimacy falls; loyalty realigns toward whoever can deliver survival.  
When a faction rival’s legitimacy surpasses the current lord’s, **power transfer** or **rebellion** becomes inevitable.

---

### **Pillar 4 – Information and Rumor Ecology**

Each faction maintains a **Rumor Bank** — a collection of verified and unverified intelligence items gathered through spies, clerks, and informants.

- **Verified entries** come from first-hand reports or trusted witnesses.  
- **Unverified entries** are speculative but may still influence behavior.  
- **Rumor dissemination** follows internal hierarchies:
  - Lower ranks contribute observations.  
  - Mid ranks filter and prioritize.  
  - High ranks decide what to amplify, conceal, or leak.

Information exchange between factions is risky and often weaponized.  
Some rumors are intentionally **seeded as signals**:  
- Declarations of territory (“The Machinists Guild claims the southern gate”).  
- Advertisements of service (“The Reclaimers accept new contracts”).  
- Propaganda (“The Duke has lost favor at the Well”).  

The value of a rumor depends on:
1. Source credibility.  
2. Propagation distance.  
3. Alignment with pre-existing bias.  
4. Reaction time — stale truth is as useless as fresh lies.

---

### **Pillar 5 – Conflict and Rebellion**

Rebellion arises when **legitimacy differentials** exceed stability thresholds.

**Trigger Conditions:**
1. Rival faction’s legitimacy > current ruler’s legitimacy × local loyalty modifier.  
2. Rumor circulation reaches saturation (belief > 0.7 among local agents).  
3. Adequate material or militia support exists.

**Types of Conflict:**
- **Succession Revolt:** One noble claims right of inheritance.  
- **Ideological Uprising:** Cult or guild declares independence.  
- **Resource Coup:** Mercenaries seize barrels or reservoirs.  

**Resolution Pathways:**
- **Suppression:** Loyal forces restore order, legitimacy rises if swift.  
- **Negotiation:** Power-sharing or vassal swaps occur.  
- **Collapse:** Ward governance disintegrates, creating ungoverned zones.

A rebellion’s outcome feeds back into rumor ecology:  
victories become memes of destiny; failures become cautionary tales.

---

### **Pillar 6 – Environmental Feedback**

Environmental pressure dictates the style of governance that survives.

- **Scarcity and Heat:** Favor authoritarian, tightly monitored systems — control by rationing.  
- **Stability and Comfort:** Breed bureaucratic stagnation and corruption.  
- **Shock Events:** Famine, contamination, or war test legitimacy faster than any audit.

Example cycle:
1. A mystic cult gains legitimacy through narcotic euphoria and emotional cohesion.  
2. Local lord’s authority erodes; corruption spreads as enforcement falters.  
3. The king intervenes, channeling new water allocations and militia reinforcements.  
4. Success restores legitimacy — or failure births a new regime.

---

## **4. Systemic Variables**

| Variable | Description | Typical Range |
|-----------|--------------|----------------|
| **Legitimacy** | Aggregate perceived enforcement competence | 0.0 – 1.0 |
| **Corruption** | Ratio of diverted vs. delivered production | 0.0 – 1.0 |
| **Loyalty** | Weighted trust between subordinate and superior | -1.0 (hostile) → 1.0 (devoted) |
| **Rumor Density** | Volume of circulating faction information | 0 – ∞ |
| **Faction Power** | Combined influence of members, assets, and memes | Dynamic scalar |

These variables evolve per tick within the temporal simulation and influence contract enforcement, resource flow, and conflict triggers.

---

## **5. Governance Agents and Roles**

| Role | Description | Primary Drives |
|------|--------------|----------------|
| **King / Central Sovereign** | Controls the Well; issues mandates and allocates barrels. | Power preservation, legitimacy growth. |
| **Dukes / Counts / Lords** | Manage wards; balance productivity and security. | Stability, reputation, personal wealth. |
| **Arbiters / Clerks** | Track contracts, taxes, and compliance. | Survival through neutrality, hoarding information. |
| **Guild Masters** | Control industry, enforce technical standards. | Profit, prestige, faction survival. |
| **Cult Leaders** | Manipulate belief for control or protection. | Influence, transcendence, survival through ideology. |
| **Mercenary Captains** | Maintain force monopoly for sale. | Credits, loyalty-for-hire, dominance. |

Each role interacts through the shared rumor and law systems, with legitimacy flowing upward and corruption flowing downward through the hierarchy.

---

## **6. System Interactions**

| Connected System | Interaction |
|------------------|-------------|
| **Economic System** | Taxes, contracts, and production mandates flow along faction hierarchies. |
| **Law & Contract System** | Defines formal obligations between factions, including arbitration procedures. |
| **Rumor Ecology** | Distributes updates about legitimacy, corruption, and factional strength. |
| **Temporal Simulation** | Updates legitimacy, loyalty, and corruption on defined tick intervals. |
| **Perception & Memory Systems** | Agents recall and interpret factional events, forming memes of governance. |
| **Environment Dynamics** | Resource scarcity or abundance shifts faction viability and governance style. |

---

## **7. Future Hooks**

- **Factional Evolution Trees:** Track how small collectives become guilds or cults over time.  
- **Parallel Legal Orders:** Simulate overlapping law layers (royal vs. cult vs. guild).  
- **Dynamic Legitimacy Contests:** Competing rulers generating rival mandates.  
- **Factional Memes and Propaganda:** Quantify ideological spread and loyalty conversion.  
- **Inter-Ward Diplomacy Engine:** Enable alliances, trade blocs, and proxy conflicts between wards.  
- **Collapse & Succession Modeling:** Transform failed factions into fragmented power clusters.  

---

### **End of Factional and Governance Systems v1**

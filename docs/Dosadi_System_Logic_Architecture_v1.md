# Dosadi System Logic Architecture v1
### (Foundational Laws of Simulation and World Logic)
**Author:** Conner Hayes  
**Version:** 1.0 — Simulation Constitution  
**Purpose:** Defines the governing logical and mathematical principles underlying all Dosadi simulation layers.  
**Companion Document:** Dosadi v2 Core Systems

---

## 1. Conservation Law — The Law of Closed Causality

### Purpose
Dosadi is a sealed ecosystem: every action must trace back to a finite, measurable resource.  
This law ensures the simulation has no “magic.” All events are consequences of conservation and loss.

### Core Principle
Every conserved quantity \( X \in \{Water, Energy, Information, Biomass\} \) evolves by:
\[
X_{t+1} = X_t + P - C - L + R
\]
Where:
- \(P\): production (extraction, generation, discovery)  
- \(C\): consumption (use, investment)  
- \(L\): loss (decay, theft, inefficiency)  
- \(R\): reclamation (recycling, reuse, entropy recovery)

**Invariant:**  
\[
\sum_{all\ entities} X_{t+1} = constant
\]
except where explicitly reduced by irreversible entropy (e.g., radiation, waste heat).

### Hierarchical Conservation
Each tier (King → Lord → Guild → Citizen) tracks its own conservation balance, which aggregates upward:
\[
X_{King} = \sum X_{Lords}
\]
Losses propagate upward as deficits and downward as austerity measures or coercion.

### Design Implication
This law provides the baseline for balancing: every subsystem (economic, informational, or biological) must show measurable flows.  
Integrity checks verify closure at each tick — the “heartbeat” of Dosadi’s realism.

---

## 2. Recursive Hierarchy — The Fractal Order of Power

### Purpose
Dosadi’s social structure is **self-similar** across scales.  
Each ward, guild, or individual is a smaller copy of the planetary macro-system, bound by the same logic of extraction, retention, and coercion.

### The Fractal Rule
At any scale \( s \), an entity \( e_s \) is defined by:
\[
e_s = (I_s, O_s, L_s)
\]
representing inflows, outflows, and losses.  
Each entity minimizes \( L_s \) by organizing subordinate entities \( e_{s-1} \) beneath it.  
This recursive process creates *nested hierarchies of entropy management.*

### Law of Mimetic Governance
Every subordinate structure imitates its superior’s organization:
- The **King’s Court** → template for all thrones and councils.  
- The **Reclamation Guild** → template for all recycling enterprises.  
- Small crews and families mirror command, tribute, and enforcement.

### Collapse Cascade
When a high-level node collapses (e.g., a Duke’s ward), its sub-nodes lose structural coherence:
\[
\Delta Stability_{child} = k \cdot \Delta Stability_{parent}
\]
with \( k \in (0,1) \) defining dependency.  
Instability propagates downward exponentially, but not instantly — enabling partial resilience and rebellion.

---

## 3. Power Equilibrium Law — The Thermodynamics of Authority

### Purpose
Power on Dosadi is not moral; it is thermodynamic — the ability to delay entropy by organizing resources and information.  
This law governs *why hierarchies exist and why they fail.*

### Power as Energy Potential
Define an entity’s power \( P \) as:
\[
P = \beta_W W + \beta_E E + \beta_I I
\]
Where:
- \(W\): control over water resources  
- \(E\): access to usable energy  
- \(I\): possession of accurate information  
- \(\beta\) coefficients represent contextual importance.

Power must be *spent* to preserve order.  
The **cost of order** \( C \) is the energy needed for social coherence, security, and propaganda.

### Stability Equation
\[
S = P - C
\]
- If \(S > 0\): expansion possible.  
- If \(S = 0\): equilibrium.  
- If \(S < 0\): instability or collapse.

### Equilibrium Feedbacks
- Water scarcity \(W ↓\) reduces \(P\).  
- Propaganda or narcotics can temporarily lower \(C\).  
- Information loss sharply decreases \(I\), triggering “informational implosions.”

This formula ties hydraulic, energetic, and informational systems together under one rule of political physics.

---

## 4. Efficiency as Virtue — The Moral Geometry of Survival

### Purpose
Dosadi’s morality derives not from justice but from *efficiency*.  
Virtue is the minimization of waste.

### Efficiency Metric
Retention ratio \( R \in [0,1] \):  
\[
R = \frac{Output\ Value}{Input\ Value}
\]
High \(R\) → elite status and legitimacy.  
Low \(R\) → waste and moral failure.

### Ascension Gradient
| Tier | Efficiency Range (R) | Social Label |
|------|----------------------|---------------|
| King / Elite | 0.999–1.0 | Perfect |
| High Lord | 0.99–0.999 | Pure |
| Middle Guild | 0.95–0.99 | Competent |
| Lower Class | 0.8–0.95 | Wasteful |
| Outcast | <0.8 | Leaky |

### Efficiency-Entropy Paradox
Perfect efficiency halts change; imperfection drives adaptation.  
\[
Growth = f(R) = -a(R - R^*)^2 + G_{max}
\]
Optimal efficiency \(R^*\) < 1 → maximum vitality.  
This mirrors the “optimal corruption” curve: both describe balance between order and decay.

---

## 5. Transaction Logic — The Grammar of Exchange

### Purpose
All interactions—trade, bribery, loyalty, rumor—are transactions.  
They redistribute resources and reshape the *trust topology* of the world.

### Transaction State Machine
| Phase | Description | Possible Failure Mode |
|-------|--------------|-----------------------|
| Offer | Intent broadcast | Ignored, intercepted |
| Binding | Mutual agreement | False binding, coercion |
| Fulfillment | Transfer executed | Theft, substitution |
| Verification | Outcome checked | Misreporting, delay |

### Trust Function
\[
T_{ij}(t+1) = \alpha T_{ij}(t) + (1 - \alpha) O_{ij}(t)
\]
Where \(O_{ij}\) = success score (0–1).  
\(\alpha\) = memory inertia (0.8–0.95).  

### Network Stability
Mean contract density:
\[
\rho = \frac{2E}{N(N-1)}
\]
If \(\rho\) falls below threshold → economic paralysis.  
Each successful contract reduces entropy; failed ones amplify it.

---

## 6. Rumor Propagation and Uncertainty — The Weather of Information

### Purpose
Information moves faster than water but decays more easily.  
It determines decision quality, fear, and coordination potential.

### Information Field Model
\[
I_x(t+1) = I_x(t)(1 - \sigma_x) + \sum_{y \in N(x)} k_{yx} I_y(t) - \eta_x
\]
- \(\sigma_x\): volatility (chaos, narcotics).  
- \(k_{yx}\): transmission efficiency.  
- \(\eta_x\): noise injection (propaganda).

High \(\sigma\) = rumor storm; low \(\sigma\) = factual calm.

### Rumor Humidity
\[
H_r = \frac{U}{I + U}
\]
High humidity → panic, mob events.  
Low humidity → rational coordination.

### Cognitive Temperature
Agents have temperature \( \theta \): ambiguity tolerance.  
Stress increases \( \theta \), fueling rumor contagion.  
Information fidelity thus couples directly to resource scarcity.

---

## 7. Incentive Inversion Law — The Logic of Corruption

### Purpose
Absolute order is fragile. Controlled instability sustains adaptability.  
Therefore, incentives sometimes invert: corruption becomes functional.

### Inversion Probability
\[
p_{inv} = \gamma \frac{E_a}{P_a + \epsilon}
\]
- \(E_a\): local entropy exposure.  
- \(P_a\): power reserve.  
- \(\gamma\): moral flexibility coefficient.

High entropy, low power → betrayal equilibrium.

### The Reclaimer Paradox
Reclaimers profit from decay yet maintain order—**entropy regulators.**  
They exemplify adaptive corruption maintaining systemic balance.

### Functional Corruption
Some corruption \(C^*\) yields maximum global stability:
\[
Stability = f(C) = -a(C - C^*)^2 + S_{max}
\]
Beyond \(C^*\): collapse. Below \(C^*\): rigidity and revolt.

---

## Summary Table: Systemic Laws

| Law | Core Variable | Systemic Goal | Failure Mode | Analogue |
|------|----------------|----------------|----------------|----------------------|
| Conservation | Resource balance \(X_t\) | Maintain closure | Leak / unsourced gain | Thermodynamics |
| Recursive Hierarchy | Structural depth | Stability by imitation | Cascade collapse | Fractals / Bureaucracy |
| Power Equilibrium | \(S = P - C\) | Maintain surplus of power | Exhaustion / revolt | Energy economics |
| Efficiency as Virtue | Retention \(R\) | Legitimacy through performance | Waste / corruption | Meritocracy entropy |
| Transaction Logic | Trust \(T_{ij}\) | Reduce entropy through cooperation | Betrayal | Network theory |
| Rumor Ecology | Info fidelity \(I_x\) | Maintain clarity | Disinformation storms | Atmospheric physics |
| Incentive Inversion | Corruption rate \(C\) | Adaptive stability | Chaos / stagnation | Thermodynamic metastability |

---

### End of Document
*(This document formalizes the core laws and relationships underlying Dosadi’s simulation logic. All future systems, agents, and behaviors must obey these governing principles.)*

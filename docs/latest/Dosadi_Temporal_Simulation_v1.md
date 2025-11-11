# **Dosadi Temporal Simulation Systems v1**

---

## **1. Purpose and Philosophy**

The Temporal System is the underlying scheduler of Dosadi — the simulation’s *pulse* that determines when and how processes occur.  
Every cycle is both a **world event** (physical and social processes) and a **perceptual event** (what information is observed, remembered, or decayed).

**Core Principle:**  
> Time is not merely passage — it is the rate at which entropy, information, and legitimacy evolve.

---

## **2. Simulation Granularity**

### **2.1 Time Units**
| Level | Duration | Used For | Description |
|--------|-----------|-----------|-------------|
| **Tick** | 0.6 seconds | Continuous simulation | Atomic step: metabolic change, hydration loss, suit function |
| **Turn** | 100 ticks (≈ 1 minute) | Agent actions | Decision/action resolution interval |
| **Cycle** | 144,000 ticks (≈ 1 day) | Ward-level economic and environmental updates |
| **Epoch** | 1 week | Governance and faction-level recalculations |
| **Era** | 1 month or major event | Structural change, rebellion, or crisis |

Each tier encapsulates the next:  
Ticks feed Turns → Turns feed Cycles → Cycles feed Epochs → Epochs feed Eras.

---

## **3. Event Scheduling and Update Order**

Each time step executes in a consistent top-down cascade:

1. **The Well / King Phase** – extraction, mandate generation.  
2. **Ward Governance Phase** – lord interpretation, enforcement, corruption.  
3. **Factional Operations Phase** – guild and collective execution, production, rumor creation.  
4. **Agent Activity Phase** – drives, health, hydration, fatigue, social interactions.  
5. **Environmental Update Phase** – decay, reclamation, pollution.  
6. **Rumor and Information Phase** – verification, propagation, decay.  
7. **Reflection / Summary Phase** – record metrics, trigger major events, advance the clock.

---

## **4. Decay, Cooldown, and Renewal**

Every system has time-dependent decay and renewal constants.  
The following table uses **Typical Decay Rate (per cycle)** to describe fractional loss per simulated day.

| Domain | Decay Variable | Typical Decay Rate (per cycle) | Notes |
|---------|----------------|--------------------------------|-------|
| **Water Storage** | Reservoir loss rate | 0.001–0.01 | Depends on engineering quality |
| **Rumor Credibility** | Credibility decay | 0.05–0.15 | Weakens unless refreshed |
| **Legitimacy** | Trust decay | 0.02–0.10 | Falls if not reinforced by results or fear |
| **Suit Integrity** | Wear rate | 0.005–0.02 | Restored via maintenance |
| **Agent Energy** | Fatigue recovery | -0.1 to -0.3 | Negative = recovery via rest |
| **Production Output** | Efficiency decay | 0.01–0.05 | Must be renewed by resource input |
| **Population Morale** | Stability loss | 0.01–0.08 | Drops in famine or unrest |

Decay ensures that **inactivity equals regression** — an idle faction or agent loses advantage over time.

---

## **5. Asynchronous Systems and Time Dilation**

The simulation allows different wards or factions to operate at different speeds for performance or narrative focus.

- **Foreground Simulation:** Active wards run full fidelity (tick-level).  
- **Background Simulation:** Calm wards compress time to epoch-level approximations.  
- **Time Dilation Coefficient:** Adjusts fidelity, e.g., 1.0 = full speed, 0.1 = 10× compression.

---

## **6. Temporal Dependencies and Causality Chains**

Events follow causal links that define both *direct* and *delayed* consequences.

- Immediate: combat → injury → reclamation.  
- Delayed: corruption → rebellion → death → resource surplus.

Causality can span days to months but operates within a dependency graph.

---

## **7. Temporal Feedback Loops**

| Loop Type | Example | Behavior |
|------------|----------|-----------|
| **Economic** | Overproduction → price collapse → famine → recovery | Damped oscillation |
| **Social** | Rumor surge → panic → suppression → apathy | Chaotic loop |
| **Environmental** | Water scarcity → reclamation → overpopulation → scarcity | Self-reinforcing |
| **Political** | High legitimacy → complacency → corruption → coup → renewal | Cyclical renewal |

Each loop has a unique time constant, governing how quickly stability returns.

---

## **8. Simulation Tick Implementation Concepts**

### **Pseudocode Example**
```python
for tick in world_time:
    time_progression = delta_t * tick_rate  # Δt = 0.6s base unit
    well.extract_water()
    king.issue_mandates()
    for ward in wards:
        ward.execute_governance_cycle()
        for faction in ward.factions:
            faction.update_legitimacy()
            faction.perform_production()
            faction.handle_rumors()
        for agent in ward.agents:
            agent.perform_drive()
            agent.update_health()
    environment.update_conditions()
    rumor_network.propagate()
    log_state()
```

---

## **9. Temporal Metrics**

| Metric | Description |
|---------|-------------|
| **Δt (Tick Rate)** | Base time step (0.6s) |
| **System Load (%)** | Entities processed per cycle |
| **Event Queue Length** | Pending events before overflow |
| **Entropy Index** | Overall disorder level |
| **Time Dilation Map** | Ward update fidelity |
| **Stability Index** | Combined legitimacy × resource × entropy measure |

---

## **10. Future Hooks**

- **Sleep/Awake Cycle Optimization** — RL agents learn predictive rest timing.  
- **Historical Time Compression** — fast-forward peaceful eras.  
- **Localized Time Distortion** — mystic or tech events warp perceived time.  
- **Planetary Cycles** — seasonal entropy and heat variations.  
- **Narrative Anchors** — milestone events tied to specific epochs.

---

### **End of Temporal Simulation Systems v1**

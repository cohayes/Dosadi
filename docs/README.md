# Project Dosadi

### “Survival is compliance, and compliance is an illusion.”

---

## Overview
**Dosadi** is a long-term simulation and game project inspired by Frank Herbert’s *The Dosadi Experiment.*  
It models a closed, resource-scarce world where human and social behavior emerge under systemic pressure.  
Every breath, favor, and betrayal exists within a single economy: the circulation of water, energy, and information.

Dosadi is being developed as both:
- A **simulation framework** for emergent AI behavior under scarcity, and  
- A **real-time strategy / role-playing hybrid** exploring adaptation, power, and social evolution.

---

## Current Goals
- Build a working **simulation loop** where environment and agents interact.  
- Document all systems and lore for modular expansion.  
- Prepare for **reinforcement learning** integration and future Unity visualization.  
- Explore **emergent narrative** through perception, rumor, and survival logic.

---

## Directory Structure

Dosadi/
│
├── env.py # Environment logic (scarcity, events)
├── agents.py # Base agent classes and behaviors
├── simulation.py # Main orchestrator for world ticks
│
└── docs/ # Worldbuilding and design documents
├── overview.md
├── worldbuilding.md
├── agents_and_suits.md
├── governance_and_law.md
├── industry_and_economy.md
├── development_plan.md
├── simulation_architecture.md
├── resources_and_energy.md
├── perception_and_information.md
├── ethics_and_behavioral_economics.md
├── technical_interoperability.md
├── tone_and_theme.md
└── rumor_and_social_information.md


---

## Design Philosophy
Dosadi treats **scarcity as the root law of existence.**  
Its people, systems, and machines all operate under the same mathematical constraint: *entropy wins eventually.*  
Every design choice — from AI decision trees to faction politics — reflects this principle.

- **Scarcity creates behavior.**  
- **Behavior creates systems.**  
- **Systems create belief.**  
- **Belief sustains scarcity.**

---

## Key Simulation Features
- Dynamic environmental model (scarcity, danger, and noise cycles).  
- Multi-agent system with independent motives and imperfect perception.  
- Reinforcement-learning-compatible structure (Gymnasium API).  
- Rumor and information propagation creating emergent social narratives.  
- Factional governance and corruption as stability dynamics.  

---

## Development Roadmap
See [`/docs/development_plan.md`](./docs/development_plan.md) for the full multi-phase roadmap.

### Immediate Goals
1. Refine `env.py`, `agents.py`, and `simulation.py` core loop.  
2. Implement basic social interactions and rumor mechanics.  
3. Establish logging for observation, action, and reward data.  
4. Build the first playable “soup kitchen” prototype.  

---

## Technical Goals
- Wrap environment in Gymnasium-compatible API for ML experimentation.  
- Implement serialization and data replay for long-form simulations.  
- Develop Unity client for visualization and multiplayer testing.  
- Maintain modular, versioned data exchange between systems.

---

## Thematic Intent
Dosadi is not a dystopia — it is a mirror.  
It explores how intelligence adapts when every decision has a cost,  
and how meaning survives in a world where empathy is expensive.

---

## License & Credits
Project Dosadi © Conner Hayes, 2025.  
All narrative and technical material produced within this repository is part of an ongoing experimental simulation design effort.  
Inspired by *The Dosadi Experiment* by Frank Herbert, used here under fair creative reinterpretation.

---

### “On Dosadi, information is oxygen — and everyone is learning to breathe less.”

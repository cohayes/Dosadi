# Simulation Architecture – Dosadi

## Overview
The Dosadi simulation models the flow of perception, decision, and consequence across an evolving environment.  
The architecture is modular, data-driven, and designed for reinforcement learning integration.

---

## System Layers

| Layer | Description | Primary Files |
|--------|--------------|----------------|
| **Environment Layer** | Maintains global conditions such as scarcity, danger, and events. | `env.py` |
| **Agent Layer** | Defines autonomous entities with internal states and perception loops. | `agents.py` |
| **Simulation Orchestrator** | Manages time steps, synchronization, and inter-agent interactions. | `simulation.py` |
| **Event System** | Handles global or local disruptions that alter world parameters. | `env.py`, `simulation.py` |
| **Observation Layer** | Provides filtered state data to agents; injects sensory noise. | `env.py` |
| **Reward/Evaluation Layer** | Computes satisfaction, stress, and survival metrics for RL integration. | `simulation.py` or future `reward.py` |
| **Data Logging Layer** | Records world state, events, and agent metrics for analysis. | future `logger.py` |

---

## Tick Cycle

1. **Environment Step**
   - Update time, fluctuate scarcity/danger.
   - Trigger global events (riots, shipments, breakdowns).
2. **Agent Observation**
   - Each agent receives a noisy snapshot of relevant environment variables.
3. **Decision Phase**
   - Agents decide actions based on internal state, policies, or learned models.
4. **Action Resolution**
   - Environment resolves conflicts (resource claims, violence, cooperation).
5. **Reward Calculation**
   - Agents receive feedback on survival, satisfaction, and loyalty effects.
6. **Logging**
   - All data appended to simulation record for training or replay.

---

## Interactions

| Type | Example | Mechanics |
|-------|----------|------------|
| **Resource Flow** | Water rations, repairs, narcotics | Transactions alter hunger, stress, or loyalty. |
| **Social Interaction** | Bribes, intimidation, cooperation | Modifies reputation and faction metrics. |
| **Physical Interaction** | Queue movement, violence, theft | Impacts injury, fear, and faction response. |

---

## Perception Model (High-Level)
Agents do not access true global state — they sample partial, noisy data:
```python
observed = {
  "scarcity": env.scarcity + random.uniform(-env.noise, env.noise),
  "danger": env.danger + random.uniform(-env.noise, env.noise),
  "local_agents": nearby_entities,
}```

Perception modules will later include sight, sound, and probabilistic inference.

## Reinforcement Learning Integration
	Environment Compatibility: Designed to be wrapped in Gymnasium API (reset(), step()).
	Observation Space: Vectorized environment and social variables.
	Action Space: Movement, speech, trade, aggression, or abstention.
	Reward Functions: Multi-factor — survival + reputation + faction favor.

## Future Expansion
	Multi-threaded agent simulation for scalability.
	Event-driven scheduling system for asynchronous world updates.
	Hooks for Unity or other visualization engines.
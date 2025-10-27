# Technical Interoperability – Dosadi

## Overview
Dosadi is built for modular interoperability — its simulation, learning, and visualization components communicate through stable interfaces.  
This design enables parallel development across Python (simulation), ML frameworks (RL), and game engines (Unity or Godot).

---

## Integration Layers

| Layer | Purpose | Example Implementation |
|--------|----------|------------------------|
| **Simulation Core (Python)** | Core environment, agents, and event logic. | `env.py`, `agents.py`, `simulation.py` |
| **RL Interface** | Reinforcement learning compatibility using Gymnasium API. | `env.step()`, `env.reset()` |
| **Analytics / Logging** | Structured data output for training, replay, or debugging. | `logger.py`, JSON/CSV output |
| **Visualization Layer** | External clients (Unity, Godot) render state transitions. | API or socket-based state stream |
| **Persistence Layer** | Save and resume simulation states for long sessions or multiplayer. | `state_io.py` (planned) |

---

## Data Exchange Standards

### Environment to RL Agent
| Data Type | Format | Description |
|------------|---------|--------------|
| Observation | NumPy / Tensor | Partial state vector (scarcity, danger, social context). |
| Reward | Float | Weighted outcome of agent action. |
| Done | Boolean | Episode termination signal. |
| Info | Dict | Metadata: events, messages, debug info. |

### Simulation to Visualization
| Channel | Protocol | Example |
|----------|-----------|----------|
| State Broadcast | WebSocket / gRPC | Sends agent positions and environment data to Unity. |
| Control Input | REST / gRPC | Player commands or AI overrides. |
| Event Stream | JSON | Narrative or environmental updates (e.g., “riot”, “shipment”). |

---

## Data Logging and Replay
- Each simulation tick produces a log entry:
  ```json
  {
    "time": 12,
    "agents": 48,
    "scarcity": 0.44,
    "danger": 0.21,
    "events": ["riot"]
  }```
  
- Logs support:
	- Statistical replay (RL training dataset).
	- Visualization playback.
	- Anomaly detection and debugging.

---

## Unity Integration Concept
A lightweight bridge translates Python simulation data to a Unity client:
1. Python simulation emits state packets at fixed intervals.
2. Unity visualizer receives packets and updates scene objects.
3. Optional feedback loop: Unity sends player input or AI actions back to Python.

This architecture maintains separation of simulation logic (truth) and visual layer (interpretation).

---

## Multiplayer and Persistence
- Game sessions can serialize world state and agent data to disk.
- Later, asynchronous or distributed simulations will share data over network protocols.
- Event queues ensure deterministic playback when replayed or shared between systems.

---

## Versioning and Compatibility
- Each major build includes:
	- schema_version for JSON/state definitions.
	- protocol_version for communication layers.
- Backward compatibility maintained through converters.
- Documentation in /docs/api_reference/ (planned).

---

## Design Philosophy
Dosadi is modular by necessity: survival, data, and meaning must all persist across imperfect interfaces.
Every boundary — code, network, or mind — is another form of scarcity.
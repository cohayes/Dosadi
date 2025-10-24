# Agent Architecture (Prototype v2)

This folder defines the core agent archetypes for the **Dosadi Simulation**.

Each agent type follows a shared pattern:
1. **Perception** – reads the local “weather” (district/facility conditions).
2. **Mood/State** – internal emotional or cognitive weights derived from perception.
3. **Decision Loop** – selects an action based on current goals and mood.
4. **Action** – placeholder for world interaction; effects applied externally.

### Agent Files
| File | Role | Summary |
|------|------|----------|
| `agent_base.py` | Base agent class | Shared perception, mood, and action loop. |
| `faction_alignment.py` | Faction system | Weighted multi-faction loyalties; supports drift and betrayal. |
| `patron.py` | Civilian visitors | Purchase, bribe, socialize, or exit depending on hunger, fear, greed. |
| `security_guard.py` | Enforces order | Patrols, intervenes, may solicit or resist bribes. |
| `negotiator.py` | Lobby intermediary | Manages vouchers, rumors, and diplomacy. |
| `server.py` | Counter staff | Exchanges food for vouchers; maintains order during rushes. |
| `waiter.py` | Booth service | Delivers food, gathers gossip, can act covertly. |
| `cook.py` | Kitchen worker | Prepares meals, reacts to shortages or corruption. |
| `boss.py` | Site manager | Balances faction loyalty, corruption, and stability. |

All classes are lightweight `dataclasses` intended for early simulation testing.
Future iterations will:
- add perceptual noise and experience modifiers,
- introduce reinforcement-learning hooks,
- and link decision outcomes to a global event log.

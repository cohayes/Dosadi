# src/simulation/agent_manager.py
"""
AgentManager — controls the life-cycle and decision loop of all active agents
in a local simulation zone (e.g., the soup kitchen).

Handles:
- world tick timing
- agent registration
- shared weather / environment updates
- data logging for observation or analysis
"""

import random
from typing import Dict, List
from src.agents.agent_base import Agent
from src.agents.patron import Patron
from src.agents.server import Server
from src.agents.security_guard import SecurityGuard
from src.agents.boss import Boss
from src.agents.cook import Cook
from src.agents.waiter import Waiter
from src.agents.negotiator import Negotiator
from src.agents.faction_alignment import FactionAlignment
from src.simulation.weather_manager import WeatherManager


class AgentManager:
    def __init__(self):
        self.agents: List[Agent] = []
        self.timestep: int = 0
        self.weather = WeatherManager("Soup Kitchen District")
        self.local_weather: Dict[str, float] = self.weather.state
        self.log: List[Dict] = []

    # ------------------------------------------------------------------
    # Agent control
    # ------------------------------------------------------------------

    def add_agent(self, agent: Agent):
        self.agents.append(agent)

    def create_agent(self, agent_type: str, name: str, **kwargs):
        """Convenience factory for new agents."""
        factions = FactionAlignment({
            "count_iron": 0.6,
            "blackmarket": 0.3,
            "guild_workers": 0.1,
        })
        cls_map = {
            "patron": Patron,
            "server": Server,
            "guard": SecurityGuard,
            "boss": Boss,
            "waiter": Waiter,
            "negotiator": Negotiator,
            "cook": Cook,
        }
        cls = cls_map.get(agent_type.lower())
        if cls:
            agent = cls(id=hash(name) % 10000, factions=factions, **kwargs)
            self.add_agent(agent)
            return agent
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")


    # ------------------------------------------------------------------
    # Simulation Loop
    # ------------------------------------------------------------------

    def tick(self):
        """Advance the world one step."""
        self.timestep += 1

        # Environment evolves through WeatherManager, incorporating agent feedback
        self.local_weather = self.weather.tick([a.last_action for a in self.agents])

        print(f"\n=== TICK {self.timestep} ===")
        for agent in self.agents:
            action = agent.tick(self.local_weather)
            entry = {
                "timestep": self.timestep,
                "agent": agent.__class__.__name__,
                "id": agent.id,
                "action": action,
                "fear": agent.mood.fear,
                "trust": agent.mood.trust,
                "loyalty": agent.mood.loyalty,
            }
            self.log.append(entry)
            print(f"{agent.__class__.__name__:>14} -> {action:>22}")

    def run(self, ticks: int = 5):
        """Run simulation for N ticks."""
        for _ in range(ticks):
            self.tick()

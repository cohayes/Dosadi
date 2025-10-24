# src/simulation/weather_manager.py
"""
WeatherManager
--------------
Tracks and evolves the macro-environmental state for a given district.

Acts as the shared context for all AgentManagers in that district.
Encapsulates systemic drift, event shocks, and faction-driven influences.
"""

import random
from typing import Dict

class WeatherManager:
    def __init__(self, name: str = "Unnamed District"):
        self.name = name
        self.tick_count = 0
        self.state: Dict[str, float] = self.initialize_weather()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize_weather(self) -> Dict[str, float]:
        """Baseline environmental conditions (0–1 range)."""
        return {
            "supply_level": 0.6,        # food, water, goods availability
            "service_quality": 0.5,     # cleanliness, efficiency
            "security_intensity": 0.5,  # patrol presence
            "corruption_risk": 0.4,     # normalized systemic corruption
            "gossip_density": 0.4,      # rate of information flow
            "incident_rate": 0.3,       # ongoing minor conflicts or crimes
            "blackmarket_power": 0.4,   # informal economy strength
            "count_iron_power": 0.6,    # formal government/faction power
            "morale": 0.5,              # public morale, worker energy
            "stability": 0.6,           # perceived social order
        }

    # ------------------------------------------------------------------
    # Evolution
    # ------------------------------------------------------------------

    def drift(self):
        """Natural background drift — small stochastic changes."""
        for key, value in self.state.items():
            self.state[key] = max(0.0, min(1.0, value + random.uniform(-0.01, 0.01)))

    def apply_event(self, event: str):
        """Localized shocks or long-term trends."""
        if event == "supply_shortage":
            self.state["supply_level"] = max(0.0, self.state["supply_level"] - 0.2)
            self.state["blackmarket_power"] = min(1.0, self.state["blackmarket_power"] + 0.1)
        elif event == "security_crackdown":
            self.state["security_intensity"] = min(1.0, self.state["security_intensity"] + 0.2)
            self.state["corruption_risk"] = max(0.0, self.state["corruption_risk"] - 0.1)
            self.state["morale"] = max(0.0, self.state["morale"] - 0.05)
        elif event == "corruption_scandal":
            self.state["corruption_risk"] = min(1.0, self.state["corruption_risk"] + 0.2)
            self.state["stability"] = max(0.0, self.state["stability"] - 0.15)
        elif event == "festival":
            self.state["morale"] = min(1.0, self.state["morale"] + 0.2)
            self.state["gossip_density"] = min(1.0, self.state["gossip_density"] + 0.1)
        elif event == "riot":
            self.state["incident_rate"] = min(1.0, self.state["incident_rate"] + 0.3)
            self.state["stability"] = max(0.0, self.state["stability"] - 0.3)

    def feedback_from_agents(self, agent_actions):
        """
        Accepts a list of recent agent actions (strings)
        and adjusts environment slightly in response.
        """
        for action in agent_actions:
            if "bribe" in action:
                self.state["corruption_risk"] = min(1.0, self.state["corruption_risk"] + 0.02)
            elif "serve" in action or "prepare" in action:
                self.state["service_quality"] = min(1.0, self.state["service_quality"] + 0.01)
            elif "intervene" in action:
                self.state["security_intensity"] = min(1.0, self.state["security_intensity"] + 0.02)
            elif "riot" in action or "purge" in action:
                self.state["stability"] = max(0.0, self.state["stability"] - 0.05)
            elif "buy_meal" in action:
                self.state["supply_level"] = max(0.0, self.state["supply_level"] - 0.01)

    # ------------------------------------------------------------------
    # Main Update
    # ------------------------------------------------------------------

    def tick(self, agent_actions=None):
        """Advance district conditions one step."""
        self.tick_count += 1
        self.drift()
        if agent_actions:
            self.feedback_from_agents(agent_actions)

        # occasional random event
        if random.random() < 0.05:
            event = random.choice(["supply_shortage", "festival", "corruption_scandal"])
            self.apply_event(event)
            print(f"⚠️  District Event: {event.upper()}")

        return self.state

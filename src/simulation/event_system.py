# src/simulation/event_system.py
"""
EventSystem
------------
Handles localized facility events within a district.

Each event can:
- temporarily alter facility efficiency or resources
- modify weather conditions
- shift faction power or morale
- persist for multiple ticks (optional future feature)

Author: Project Dosadi
"""

import random
from typing import Dict, Callable, Optional

class EventSystem:
    def __init__(self):
        # Registry maps event names to handler functions
        self.registry: Dict[str, Callable] = {}
        self.register_default_events()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, func: Callable):
        """Add a new event handler."""
        self.registry[name] = func

    def register_default_events(self):
        """Define the default local facility events."""
        self.register("ration_riot", self.ration_riot)
        self.register("supply_shortage", self.supply_shortage)
        self.register("machine_breakdown", self.machine_breakdown)
        self.register("union_strike", self.union_strike)
        self.register("bribery_probe", self.bribery_probe)
        self.register("guard_dispute", self.guard_dispute)
        self.register("sting_operation", self.sting_operation)
        self.register("betrayal", self.betrayal)

    # ------------------------------------------------------------------
    # Triggering
    # ------------------------------------------------------------------

    def maybe_trigger(self, facility, chance: float = 0.05):
        """
        Randomly trigger one of the facility's valid events.
        Returns the name of the triggered event or None.
        """
        if random.random() < chance and facility.profile.event_hooks:
            event_name = random.choice(facility.profile.event_hooks)
            handler = self.registry.get(event_name)
            if handler:
                print(f"⚠️  Event triggered at {facility.profile.name}: {event_name}")
                handler(facility)
                return event_name
        return None

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    def ration_riot(self, facility):
        facility.resources["food_stock"] *= 0.7
        facility.weather.state["stability"] = max(0.0, facility.weather.state["stability"] - 0.1)
        facility.weather.state["incident_rate"] = min(1.0, facility.weather.state["incident_rate"] + 0.2)

    def supply_shortage(self, facility):
        facility.resources["food_stock"] *= 0.5
        facility.weather.state["supply_level"] = max(0.0, facility.weather.state["supply_level"] - 0.2)

    def machine_breakdown(self, facility):
        facility.resources["refined_metal"] *= 0.9
        facility.weather.state["service_quality"] = max(0.0, facility.weather.state["service_quality"] - 0.1)

    def union_strike(self, facility):
        for agent in facility.agents:
            agent.mood.trust *= 0.8
        facility.weather.state["morale"] = max(0.0, facility.weather.state["morale"] - 0.15)

    def bribery_probe(self, facility):
        facility.weather.state["corruption_risk"] = max(0.0, facility.weather.state["corruption_risk"] - 0.2)
        facility.weather.state["security_intensity"] = min(1.0, facility.weather.state["security_intensity"] + 0.2)

    def guard_dispute(self, facility):
        for agent in facility.agents:
            if agent.__class__.__name__ == "SecurityGuard":
                agent.mood.trust *= 0.5
                agent.mood.fear *= 1.2
        facility.weather.state["incident_rate"] = min(1.0, facility.weather.state["incident_rate"] + 0.1)

    def sting_operation(self, facility):
        facility.resources["credits"] *= 0.8
        facility.weather.state["security_intensity"] = min(1.0, facility.weather.state["security_intensity"] + 0.3)
        facility.weather.state["blackmarket_power"] = max(0.0, facility.weather.state["blackmarket_power"] - 0.2)

    def betrayal(self, facility):
        for agent in facility.agents:
            agent.mood.trust *= 0.6
        facility.weather.state["stability"] = max(0.0, facility.weather.state["stability"] - 0.25)

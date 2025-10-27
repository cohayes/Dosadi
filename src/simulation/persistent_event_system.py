# src/simulation/persistent_event_system.py
"""
PersistentEventSystem
---------------------
Extends EventSystem to support multi-tick conditions.

Features:
- Active event registry with durations and decay
- Gradual recovery (morale, stability, supply)
- Integration hooks for FacilityManager and DistrictManager

Author: Project Dosadi
"""

import random
from typing import Dict, Callable, Optional

class PersistentEventSystem:
    def __init__(self):
        # Active events: {event_name: remaining_ticks}
        self.active_events: Dict[str, int] = {}
        # Registry: maps event names to (apply, recover) functions
        self.registry: Dict[str, Dict[str, Callable]] = {}
        self.register_default_events()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, apply_func: Callable, recover_func: Optional[Callable] = None):
        self.registry[name] = {"apply": apply_func, "recover": recover_func}

    def register_default_events(self):
        """Defines a few persistent example events."""
        self.register("strike", self.apply_strike, self.recover_strike)
        self.register("shortage", self.apply_shortage, self.recover_shortage)
        self.register("investigation", self.apply_investigation, self.recover_investigation)
        self.register("riot", self.apply_riot, self.recover_riot)

    # ------------------------------------------------------------------
    # Core Logic
    # ------------------------------------------------------------------

    def maybe_trigger(self, facility, chance: float = 0.05):
        """Chance to begin a new persistent event."""
        if random.random() < chance:
            event_name = random.choice(list(self.registry.keys()))
            if event_name not in self.active_events:
                print(f"⚠️ Persistent Event started at {facility.profile.name}: {event_name}")
                self.active_events[event_name] = random.randint(3, 7)  # duration
                self.registry[event_name]["apply"](facility)

    def tick(self, facility):
        """Advance all active events, decaying them gradually."""
        expired = []
        for event, remaining in self.active_events.items():
            self.active_events[event] -= 1
            if remaining > 0:
                # reapply mild effects each tick
                self.registry[event]["apply"](facility)
            else:
                expired.append(event)

        # Recover from expired events
        for event in expired:
            if self.registry[event]["recover"]:
                self.registry[event]["recover"](facility)
            del self.active_events[event]
            print(f"✅ Event ended: {event}")

    # ------------------------------------------------------------------
    # Event Definitions
    # ------------------------------------------------------------------

    def apply_strike(self, facility):
        facility.weather.state["morale"] = max(0.0, facility.weather.state["morale"] - 0.05)
        facility.weather.state["stability"] = max(0.0, facility.weather.state["stability"] - 0.05)
        for agent in facility.agents:
            agent.mood.trust *= 0.95

    def recover_strike(self, facility):
        facility.weather.state["morale"] = min(1.0, facility.weather.state["morale"] + 0.1)
        print(f"[{facility.profile.name}] Workers return to duties, morale improving.")

    def apply_shortage(self, facility):
        facility.resources["food_stock"] = max(0.0, facility.resources.get("food_stock", 0.0) - 2.0)
        facility.weather.state["supply_level"] = max(0.0, facility.weather.state["supply_level"] - 0.02)

    def recover_shortage(self, facility):
        facility.weather.state["supply_level"] = min(1.0, facility.weather.state["supply_level"] + 0.05)
        print(f"[{facility.profile.name}] Supply levels normalizing.")

    def apply_investigation(self, facility):
        facility.weather.state["corruption_risk"] = max(0.0, facility.weather.state["corruption_risk"] - 0.03)
        facility.weather.state["security_intensity"] = min(1.0, facility.weather.state["security_intensity"] + 0.03)

    def recover_investigation(self, facility):
        facility.weather.state["morale"] = max(0.0, facility.weather.state["morale"] - 0.02)
        print(f"[{facility.profile.name}] Investigation closed; tension fades.")

    def apply_riot(self, facility):
        facility.weather.state["stability"] = max(0.0, facility.weather.state["stability"] - 0.1)
        facility.weather.state["incident_rate"] = min(1.0, facility.weather.state["incident_rate"] + 0.1)
        for agent in facility.agents:
            agent.mood.fear = min(1.0, agent.mood.fear + 0.05)

    def recover_riot(self, facility):
        facility.weather.state["incident_rate"] = max(0.0, facility.weather.state["incident_rate"] - 0.1)
        print(f"[{facility.profile.name}] Order restored after riot.")

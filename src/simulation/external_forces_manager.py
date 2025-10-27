# src/simulation/external_forces_manager.py
"""
ExternalForcesManager
---------------------
Applies macro-level pressures and policy changes to a district.

Handles:
- Political decrees from higher powers (Duke, King)
- Environmental and atmospheric stress
- Trade flux and migration
- Random macro events that shape WeatherManager and faction balance

Author: Project Dosadi
"""

import random
from typing import Dict


class ExternalForcesManager:
    def __init__(self):
        self.global_temperature = 0.6  # normalized planetary dryness/heat
        self.global_trade_flow = 0.5   # normalized inter-district trade strength
        self.policy_pressure = 0.0     # accumulates from Duke decrees or sanctions
        self.active_policies: Dict[str, int] = {}  # policy_name -> remaining duration (ticks)

    # ------------------------------------------------------------------
    # Core External Influences
    # ------------------------------------------------------------------

    def apply_environmental_stress(self, district):
        """Simulate atmospheric or resource scarcity effects."""
        weather = district.weather.state
        base_stress = self.global_temperature + random.uniform(-0.05, 0.05)

        # Heat reduces morale and supply efficiency
        weather["supply_level"] = max(0.0, weather["supply_level"] - base_stress * 0.02)
        weather["morale"] = max(0.0, weather["morale"] - base_stress * 0.015)
        weather["service_quality"] = max(0.0, weather["service_quality"] - base_stress * 0.01)

        # Very high heat increases incident rates (people snap)
        if base_stress > 0.8:
            weather["incident_rate"] = min(1.0, weather["incident_rate"] + 0.1)

    def apply_trade_fluctuations(self, district):
        """Simulate changes in imports/exports that affect supply."""
        weather = district.weather.state
        trade_modifier = random.uniform(-0.1, 0.1)
        self.global_trade_flow = max(0.0, min(1.0, self.global_trade_flow + trade_modifier))

        if self.global_trade_flow < 0.3:
            weather["supply_level"] = max(0.0, weather["supply_level"] - 0.05)
            weather["blackmarket_power"] = min(1.0, weather["blackmarket_power"] + 0.05)
        elif self.global_trade_flow > 0.7:
            weather["supply_level"] = min(1.0, weather["supply_level"] + 0.05)
            weather["blackmarket_power"] = max(0.0, weather["blackmarket_power"] - 0.03)

    def apply_policy_effects(self, district):
        """Apply ongoing policy directives and countdown durations."""
        for policy, duration in list(self.active_policies.items()):
            if policy == "production_increase":
                district.quota_target *= 1.05
                district.weather.state["morale"] = max(0.0, district.weather.state["morale"] - 0.05)
            elif policy == "anti_corruption_sweep":
                district.weather.state["corruption_risk"] = max(0.0, district.weather.state["corruption_risk"] - 0.1)
                district.weather.state["security_intensity"] = min(1.0, district.weather.state["security_intensity"] + 0.1)
            elif policy == "water_rationing":
                district.weather.state["supply_level"] = max(0.0, district.weather.state["supply_level"] - 0.1)
                district.weather.state["morale"] = max(0.0, district.weather.state["morale"] - 0.1)

            # Decrement duration
            self.active_policies[policy] -= 1
            if self.active_policies[policy] <= 0:
                print(f"📜 Policy expired: {policy}")
                del self.active_policies[policy]

    def inject_policy(self, policy_name: str, duration: int = 10):
        """Add a top-down directive from higher powers."""
        print(f"🏛️  New Policy Enacted: {policy_name} ({duration} ticks)")
        self.active_policies[policy_name] = duration

    # ------------------------------------------------------------------
    # Major Events
    # ------------------------------------------------------------------

    def maybe_trigger_global_event(self, district, chance: float = 0.05):
        """Randomly trigger a macro-scale event."""
        if random.random() < chance:
            event = random.choice(["duke_decree", "heatwave", "trade_boom", "famine", "migration_surge"])
            print(f"🌍 Global Event: {event}")
            if event == "duke_decree":
                self.inject_policy(random.choice(["production_increase", "anti_corruption_sweep", "water_rationing"]))
            elif event == "heatwave":
                self.global_temperature = min(1.0, self.global_temperature + 0.1)
            elif event == "trade_boom":
                self.global_trade_flow = min(1.0, self.global_trade_flow + 0.2)
            elif event == "famine":
                district.weather.state["supply_level"] = max(0.0, district.weather.state["supply_level"] - 0.2)
                district.weather.state["morale"] = max(0.0, district.weather.state["morale"] - 0.1)
            elif event == "migration_surge":
                district.weather.state["stability"] = max(0.0, district.weather.state["stability"] - 0.1)
                district.weather.state["morale"] = max(0.0, district.weather.state["morale"] - 0.05)

    # ------------------------------------------------------------------
    # Main Update
    # ------------------------------------------------------------------

    def tick(self, district):
        """Advance macro conditions and apply their effects to the district."""
        self.apply_environmental_stress(district)
        self.apply_trade_fluctuations(district)
        self.apply_policy_effects(district)
        self.maybe_trigger_global_event(district)

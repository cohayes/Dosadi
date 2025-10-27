# src/simulation/district_manager.py
"""
DistrictManager
----------------
Coordinates all simulation systems within a single district (ward).

Responsibilities:
- Holds the district's WeatherManager (environmental state)
- Manages one or more AgentManagers (facilities)
- Tracks district-level economic production and quota obligations
- Mediates factional power balance (Count vs. Black Market, etc.)
- Provides summary reports for governance layers (Duke, King)

Author: Project Dosadi
"""

import random
from typing import Dict, List
from src.simulation.weather_manager import WeatherManager
from src.simulation.agent_manager import AgentManager
from src.simulation.external_forces_manager import ExternalForcesManager


class DistrictManager:
    def __init__(self, name: str, primary_industry: str = "services", quota_target: float = 100.0):
        self.name = name
        self.primary_industry = primary_industry
        self.quota_target = quota_target
        self.production: float = 0.0
        self.faction_power: Dict[str, float] = {
            "count_iron": 0.6,
            "blackmarket": 0.3,
            "guild_workers": 0.1,
        }

        # Subsystems
        self.external_forces = ExternalForcesManager()
        self.weather = WeatherManager(name)
        self.facilities: List[AgentManager] = []
        self.timestep = 0
        self.report_log: List[Dict] = []
        

    # ------------------------------------------------------------------
    # Facility and agent registration
    # ------------------------------------------------------------------

    def add_facility(self, facility: AgentManager):
        """Attach an AgentManager to this district."""
        facility.weather = self.weather
        self.facilities.append(facility)

    def seed_facilities(self, n: int = 1):
        """Populate the district with n generic facilities."""
        for i in range(n):
            fac = AgentManager()
            fac.weather = self.weather
            self.facilities.append(fac)

    # ------------------------------------------------------------------
    # District-level logic
    # ------------------------------------------------------------------

    def calculate_production(self):
        """
        Placeholder: derive production from facility actions.
        Later, we’ll map specific agent actions to productivity rates.
        """
        base_output = random.uniform(5, 15) * len(self.facilities)
        mood_factor = sum(
            sum(a.mood.trust - a.mood.fear for a in fac.agents)
            for fac in self.facilities
        )
        self.production = max(0.0, base_output + mood_factor)
        return self.production

    def assess_quota(self):
        """Compare output to quota and return performance ratio."""
        return self.production / self.quota_target if self.quota_target > 0 else 1.0

    def update_faction_balance(self):
        """Gradually shift power based on conditions."""
        q_ratio = self.assess_quota()
        self.faction_power["count_iron"] = max(0.0, min(1.0, self.faction_power["count_iron"] + (q_ratio - 1.0) * 0.05))
        self.faction_power["blackmarket"] = max(0.0, min(1.0, self.faction_power["blackmarket"] + (1.0 - q_ratio) * 0.03))
        self.faction_power["guild_workers"] = 1.0 - (self.faction_power["count_iron"] + self.faction_power["blackmarket"])
        for k in self.faction_power:
            self.faction_power[k] = max(0.0, min(1.0, self.faction_power[k]))

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def tick(self):
        """Advance all subsystems one step."""
        self.timestep += 1
        print(f"\n===== DISTRICT {self.name.upper()} | TICK {self.timestep} =====")
        
        # Step 0: apply external pressures before local updates
        self.external_forces.tick(self)

        # Step 1: advance weather with agent feedback
        all_actions = []
        for fac in self.facilities:
            fac.tick()
            all_actions.extend(a.last_action for a in fac.agents)
        self.weather.tick(all_actions)

        # Step 2: compute productivity & quota performance
        production = self.calculate_production()
        q_ratio = self.assess_quota()
        self.update_faction_balance()

        print(f"Production: {production:.1f} / {self.quota_target} ({q_ratio*100:.1f}%)")
        print(f"Faction balance: {self.faction_power}")

        # Step 3: record state summary
        self.report_log.append({
            "tick": self.timestep,
            "production": production,
            "quota_ratio": q_ratio,
            "faction_power": self.faction_power.copy(),
            "weather": self.weather.state.copy(),
        })

    def run(self, ticks: int = 10):
        """Run the full district simulation for N ticks."""
        for _ in range(ticks):
            self.tick()

# src/simulation/facility_manager.py
"""
FacilityManager
---------------
Extends AgentManager to include:
- FacilityProfile integration (industry type, IO)
- Resource pools
- Production calculation influenced by agent morale & corruption
"""

from typing import Dict
from src.simulation.agent_manager import AgentManager
from src.simulation.facility_profile import FacilityProfile, FACILITY_TEMPLATES
from src.simulation.event_system import EventSystem


class FacilityManager(AgentManager):
    def __init__(self, profile_name: str = "soup_kitchen"):
        super().__init__()
        if profile_name not in FACILITY_TEMPLATES:
            raise ValueError(f"Unknown facility profile: {profile_name}")

        self.profile: FacilityProfile = FACILITY_TEMPLATES[profile_name]
        self.event_system = EventSystem()
        self.resources: Dict[str, float] = {**self.profile.input_resources, **self.profile.output_resources}
        # initialize resources to moderate stock
        for r in self.resources:
            self.resources[r] = 100.0

        self.last_output: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Resource logic
    # ------------------------------------------------------------------

    def has_inputs(self) -> bool:
        """Check if facility can meet input requirements for one tick."""
        for res, amt in self.profile.input_resources.items():
            if self.resources.get(res, 0.0) < amt:
                return False
        return True

    def consume_inputs(self):
        for res, amt in self.profile.input_resources.items():
            self.resources[res] = max(0.0, self.resources.get(res, 0.0) - amt)

    def produce_outputs(self, efficiency: float):
        self.last_output = {}
        for res, amt in self.profile.output_resources.items():
            produced = amt * efficiency
            self.resources[res] = self.resources.get(res, 0.0) + produced
            self.last_output[res] = produced

    # ------------------------------------------------------------------
    # Productivity model
    # ------------------------------------------------------------------

    def compute_efficiency(self) -> float:
        """Compute efficiency from agent morale and corruption state."""
        if not self.agents:
            return 0.0
        avg_trust = sum(a.mood.trust for a in self.agents) / len(self.agents)
        avg_fear = sum(a.mood.fear for a in self.agents) / len(self.agents)
        corruption = self.weather.state.get("corruption_risk", 0.5)

        morale_factor = (avg_trust - avg_fear) * self.profile.morale_weight
        corruption_factor = (1.0 - corruption) * self.profile.corruption_sensitivity
        efficiency = max(0.0, morale_factor * corruption_factor)
        return efficiency

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self):
        """Advance one tick, producing or idling."""
        self.timestep += 1
        print(f"\n-- Facility Tick {self.timestep}: {self.profile.name} --")

        # Let agents act (same as AgentManager)
        super().tick()

        # Skip production if no inputs
        if not self.has_inputs():
            print(f"[{self.profile.name}] ❌ Missing inputs, production halted.")
            return

        # Consume, produce, log
        self.consume_inputs()
        eff = self.compute_efficiency()
        self.produce_outputs(eff)
        # Random chance to trigger local event
        event_triggered = self.event_system.maybe_trigger(self, chance=0.1)
        if event_triggered:
            print(f"[{self.profile.name}] ⚠️  Event occurred: {event_triggered}")

        print(f"[{self.profile.name}] ✅ Efficiency={eff:.2f}, Output={self.last_output}")

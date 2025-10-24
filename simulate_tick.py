# simulate_tick.py

from src.simulation.district_manager import DistrictManager
from src.simulation.agent_manager import AgentManager

def main():
    # Create a district
    district = DistrictManager("Ward 07", primary_industry="services", quota_target=100)

    # Create a single facility and seed some agents
    facility = AgentManager()
    facility.create_agent("patron", "Marek", credits=3.0, hunger=0.8)
    facility.create_agent("server", "Tessa")
    facility.create_agent("guard", "Loric")
    facility.create_agent("boss", "The Steward")

    district.add_facility(facility)

    # Run simulation
    district.run(ticks=10)

    print("\nSimulation complete.")
    print(f"District '{district.name}' logged {district.timestep} ticks.")

if __name__ == "__main__":
    main()

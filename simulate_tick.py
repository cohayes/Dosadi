# simulate_tick.py

"""
District simulation entry point.
Demonstrates a fully active district with multiple facility types and event persistence.
"""

from src.simulation.district_manager import DistrictManager
from src.simulation.facility_manager import FacilityManager


def populate_facility(facility, name: str):
    """Populate a facility with some agents according to its industry type."""
    if facility.profile.industry == "service":
        facility.create_agent("patron", f"{name}_Patron", credits=3.0, hunger=0.8)
        facility.create_agent("server", f"{name}_Server")
        facility.create_agent("guard", f"{name}_Guard")
        facility.create_agent("boss", f"{name}_Boss")
    elif facility.profile.industry == "manufacturing":
        facility.create_agent("cook", f"{name}_Tech")  # Placeholder for worker type
        facility.create_agent("guard", f"{name}_Enforcer")
        facility.create_agent("boss", f"{name}_Overseer")
    elif facility.profile.industry == "governance":
        facility.create_agent("guard", f"{name}_Patrol")
        facility.create_agent("negotiator", f"{name}_Clerk")
        facility.create_agent("boss", f"{name}_Chief")
    elif facility.profile.industry == "informal":
        facility.create_agent("patron", f"{name}_Fixer")
        facility.create_agent("server", f"{name}_Runner")
        facility.create_agent("boss", f"{name}_Broker")


def main():
    # Initialize district
    district = DistrictManager("Ward 07", primary_industry="services", quota_target=150)

    # Add a few distinct facilities
    facilities = [
        FacilityManager("soup_kitchen"),
        FacilityManager("recycler_plant"),
        FacilityManager("security_office"),
        FacilityManager("blackmarket_den"),
    ]

    # Populate each facility with role-appropriate agents
    for i, f in enumerate(facilities, start=1):
        populate_facility(f, f"Fac{i}")
        district.add_facility(f)

    print("\n=== DOSADI DISTRICT SIMULATION START ===\n")

    # Run simulation
    district.run(ticks=30)

    print("\n=== SIMULATION COMPLETE ===")
    print(f"District '{district.name}' finished after {district.timestep} ticks.")


if __name__ == "__main__":
    main()

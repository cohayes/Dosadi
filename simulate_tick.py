# simulate_tick.py

from src.simulation.facility_manager import FacilityManager

def main():
    facility = FacilityManager("soup_kitchen")
    facility.create_agent("patron", "Marek", credits=3.0, hunger=0.8)
    facility.create_agent("server", "Tessa")
    facility.create_agent("guard", "Loric")
    facility.create_agent("boss", "The Steward")

    for _ in range(20):
        facility.tick()

if __name__ == "__main__":
    main()

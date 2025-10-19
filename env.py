import random

class Environment:
    """World state for the Dosadi simulation."""

    def __init__(self, scarcity=0.3, danger=0.1, noise=0.1, capacity=50):
        # Core conditions
        self.scarcity = scarcity   # affects hunger/thirst growth
        self.danger = danger       # affects fear responses
        self.noise = noise         # background sensory noise
        self.capacity = capacity   # max number of agents

        # Dynamic features
        self.agents = []
        self.time = 0
        self.events = []           # log of world-level events

    # -------------------------------------------------------------
    # Management
    # -------------------------------------------------------------

    def add_agent(self, agent):
        if len(self.agents) < self.capacity:
            self.agents.append(agent)
        else:
            print("⚠️ Environment full — cannot add more agents.")

    def remove_agent(self, agent):
        if agent in self.agents:
            self.agents.remove(agent)

    # -------------------------------------------------------------
    # Environmental updates
    # -------------------------------------------------------------

    def fluctuate_conditions(self):
        """Add slow noise to scarcity/danger to create variation."""
        self.scarcity = max(0, min(1, self.scarcity + random.uniform(-0.05, 0.05)))
        self.danger = max(0, min(1, self.danger + random.uniform(-0.03, 0.03)))

    def trigger_event(self):
        """Occasional global event that modifies conditions."""
        roll = random.random()
        if roll < 0.05:
            event = "food_shipment"
            self.scarcity = max(0, self.scarcity - 0.2)
        elif roll < 0.08:
            event = "riot"
            self.danger = min(1, self.danger + 0.4)
        else:
            event = None

        if event:
            self.events.append((self.time, event))

    # -------------------------------------------------------------
    # Simulation step
    # -------------------------------------------------------------

    def step(self):
        """Advance the world by one tick and update all agents."""
        self.time += 1
        self.fluctuate_conditions()
        self.trigger_event()

        env_state = {
            "scarcity": self.scarcity,
            "danger": self.danger,
            "noise": self.noise
        }

        for agent in self.agents:
            agent.step(env_state)

    # -------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------

    def summary(self):
        """Simple environment printout."""
        avg_hunger = sum(a.hunger for a in self.agents) / len(self.agents)
        avg_stress = sum(a.stress for a in self.agents) / len(self.agents)
        print(f"Time {self.time:03d} | scarcity={self.scarcity:.2f} danger={self.danger:.2f} "
              f"| avg hunger={avg_hunger:.2f} stress={avg_stress:.2f}")

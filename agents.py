import random

class Agent:
    """Base class for all characters in the Dosadi simulation."""

    def __init__(self, id, role="generic", **kwargs):
        # Identification
        self.id = id
        self.role = role

        # --- Core physical state ---
        self.health = kwargs.get("health", 1.0)
        self.energy = kwargs.get("energy", 1.0)
        self.hunger = kwargs.get("hunger", 0.0)
        self.thirst = kwargs.get("thirst", 0.0)

        # --- Psychological state ---
        self.stress = kwargs.get("stress", 0.0)
        self.fear = kwargs.get("fear", 0.0)
        self.ambition = kwargs.get("ambition", random.uniform(0.05, 0.3))
        self.discipline = kwargs.get("discipline", random.uniform(0.3, 0.7))

        # --- Social state ---
        self.loyalty = kwargs.get("loyalty", 0.5)
        self.affiliations = kwargs.get("affiliations", [])
        self.status = kwargs.get("status", 0.0)

        # --- Inventory / possessions ---
        self.inventory = kwargs.get("inventory", [])
        self.credits = kwargs.get("credits", 0)

        # --- Intentions ---
        self.intention = None           # visible action
        self.covert_intention = None    # hidden motive

    # ---------------------------------------------------------------
    # Core behavioral loop
    # ---------------------------------------------------------------

    def perceive(self, env):
        """Update internal states based on environmental factors."""
        scarcity = env.get("scarcity", 0.0)
        danger = env.get("danger", 0.0)

        # hunger and thirst increase with scarcity
        self.hunger = min(1.0, self.hunger + scarcity * 0.1)
        self.thirst = min(1.0, self.thirst + scarcity * 0.15)

        # stress increases with hunger/thirst imbalance
        self.stress = min(1.0, self.stress + 0.05 * (self.hunger + self.thirst))

        # fear scales with environmental danger
        self.fear = min(1.0, self.fear + 0.1 * danger)

    def decide(self):
        """Decide next action based on internal state."""
        if self.hunger > 0.7 or self.thirst > 0.7:
            self.intention = "seek_resources"
        elif self.fear > 0.6 and random.random() > self.discipline:
            self.intention = "hide"
        elif self.ambition > 0.6 and self.energy > 0.5:
            self.intention = "take_risk"
        else:
            self.intention = "idle"

    def act(self, env):
        """Perform the chosen action and update internal state."""
        if self.intention == "seek_resources":
            success = random.random() < (1.0 - env.get("scarcity", 0.5))
            if success:
                self.hunger = max(0.0, self.hunger - 0.4)
                self.thirst = max(0.0, self.thirst - 0.3)
                self.energy = min(1.0, self.energy + 0.2)
            else:
                self.stress += 0.1

        elif self.intention == "hide":
            self.energy -= 0.05
            self.fear = max(0.0, self.fear - 0.2)

        elif self.intention == "take_risk":
            outcome = random.random()
            if outcome > 0.7:
                # success — gain status, resources
                self.status += 0.1
                self.credits += 5
            else:
                # failure — lose energy, increase stress
                self.energy = max(0.0, self.energy - 0.2)
                self.stress = min(1.0, self.stress + 0.2)

        elif self.intention == "idle":
            self.energy = min(1.0, self.energy + 0.05)
            self.stress = max(0.0, self.stress - 0.02)

        # Decay / recovery dynamics
        self.energy = max(0.0, min(1.0, self.energy))
        self.health = max(0.0, min(1.0, self.health - (self.hunger + self.thirst) * 0.02))

    def step(self, env):
        """One full perception–decision–action loop."""
        self.perceive(env)
        self.decide()
        self.act(env)

    def __repr__(self):
        return (f"<Agent {self.id} | role={self.role} | intent={self.intention} | "
                f"H:{self.health:.2f} E:{self.energy:.2f} F:{self.fear:.2f} "
                f"S:{self.stress:.2f} A:{self.ambition:.2f}>")

class Patron(Agent):
    """Specialized Agent representing a patron in the soup kitchen."""
    
    def __init__(self, id, hunger_threshold=0.5, patience=5, **kwargs):
        super().__init__(id, role="patron", **kwargs)
        self.queue_position = None       # Position in line (0 = front)
        self.wait_time = 0
        self.patience = patience         # How long before leaving
        self.hunger_threshold = hunger_threshold
        self.served = False
    
    def perceive(self, env):
        """Patron perceives environment + queue dynamics."""
        super().perceive(env)
        if self.queue_position is not None:
            # Stress grows if waiting too long
            self.stress = min(1.0, self.stress + 0.05 * (self.wait_time / self.patience))
    
    def decide(self):
        """Patron-specific decision logic."""
        if self.served:
            self.intention = "idle"
        elif self.hunger > self.hunger_threshold:
            self.intention = "move_forward" if self.queue_position == 0 else "wait_in_line"
        elif self.wait_time > self.patience:
            self.intention = "leave"
        else:
            self.intention = "wait_in_line"
    
    def act(self, env):
        """Execute action based on queue behavior."""
        if self.intention == "move_forward":
            # Front of the line, gets served
            self.served = True
            self.hunger = max(0.0, self.hunger - 0.5)
            self.stress = max(0.0, self.stress - 0.2)
        elif self.intention == "wait_in_line":
            self.wait_time += 1
        elif self.intention == "leave":
            env.remove_agent(self)
        # Apply base class dynamics (energy, health, fear)
        super().act(env)

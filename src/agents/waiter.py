from dataclasses import dataclass
from .agent_base import Agent

@dataclass
class Waiter(Agent):
    curiosity: float = 0.6
    fear: float = 0.3
    greed: float = 0.4

    def decide_action(self) -> str:
        p = self.perception.values
        if p.get("incident_rate", 0.3) > 0.6:
            return "seek_cover"
        elif p.get("corruption_risk", 0.4) > 0.7 and self.greed > 0.5:
            return "accept_poison_bribe"
        elif p.get("gossip_density", 0.5) > 0.6 and self.curiosity > 0.5:
            return "eavesdrop"
        else:
            return "deliver_meals"

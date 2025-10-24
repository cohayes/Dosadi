from dataclasses import dataclass
from .agent_base import Agent

@dataclass
class Server(Agent):
    integrity: float = 0.7
    greed: float = 0.3
    morale: float = 0.5

    def decide_action(self) -> str:
        p = self.perception.values
        if p.get("supply_level", 0.5) < 0.3:
            return "ration_food"
        elif p.get("corruption_risk", 0.3) > 0.6 and self.integrity < 0.5:
            return "accept_bribe"
        elif p.get("crowd_density", 0.5) > 0.8:
            return "rush_service"
        else:
            return "serve_normally"

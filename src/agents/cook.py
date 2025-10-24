from dataclasses import dataclass
from .agent_base import Agent

@dataclass
class Cook(Agent):
    focus: float = 0.7
    exhaustion: float = 0.3

    def decide_action(self) -> str:
        p = self.perception.values
        if p.get("supply_level", 0.5) < 0.3:
            return "stretch_ingredients"
        elif p.get("morale", 0.5) < 0.4:
            return "complain_to_boss"
        elif p.get("corruption_risk", 0.3) > 0.7:
            return "underreport_stock"
        else:
            return "prepare_meal"

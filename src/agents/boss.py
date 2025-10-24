from dataclasses import dataclass
from .agent_base import Agent

@dataclass
class Boss(Agent):
    authority: float = 0.7
    paranoia: float = 0.4
    greed: float = 0.5

    def decide_action(self) -> str:
        p = self.perception.values
        if p.get("stability", 0.5) < 0.3:
            return "increase_security"
        elif p.get("corruption_risk", 0.4) > 0.7 and self.greed > 0.6:
            return "negotiate_bribe"
        elif p.get("power_balance", 0.5) < 0.4 and self.paranoia > 0.6:
            return "purge_disloyal_staff"
        else:
            return "maintain_operations"

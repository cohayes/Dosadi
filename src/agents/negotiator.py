from dataclasses import dataclass, field
from typing import List
from .agent_base import Agent

@dataclass
class Negotiator(Agent):
    charisma: float = 0.7
    greed: float = 0.4
    rumor_pool: List[str] = field(default_factory=list)

    def decide_action(self) -> str:
        p = self.perception.values
        if p.get("gossip_density", 0.5) > 0.7:
            return "spread_rumor"
        elif p.get("corruption_risk", 0.3) > 0.6 and self.greed > 0.5:
            return "broker_bribe"
        elif p.get("morale", 0.5) < 0.4:
            return "deliver_reassurance"
        else:
            return "maintain_order"

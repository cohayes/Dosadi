from dataclasses import dataclass
from .agent_base import Agent

@dataclass
class SecurityGuard(Agent):
    fatigue: float = 0.0
    corruption_tendency: float = 0.3

    def decide_action(self) -> str:
        p = self.perception.values
        if p.get("incident_rate", 0) > 0.6:
            return "intervene_incident"
        elif p.get("corruption_risk", 0) > 0.7 and self.corruption_tendency < 0.5:
            return "report_corruption"
        elif self.corruption_tendency > 0.6 and p.get("corruption_risk", 0) < 0.5:
            return "solicit_bribe"
        elif self.fatigue > 0.7:
            return "rest"
        elif p.get("security_intensity", 0.5) < 0.3:
            return "increase_patrol"
        else:
            return "maintain_patrol"

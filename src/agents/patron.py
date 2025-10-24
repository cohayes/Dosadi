from dataclasses import dataclass
from .agent_base import Agent

@dataclass
class Patron(Agent):
    hunger: float = 1.0

    def decide_action(self) -> str:
        m = self.mood
        if self.hunger > 0.7:
            if m.fear < 0.5 and self.credits >= 1:
                return "buy_meal"
            elif m.greed > 0.6:
                return "attempt_bribe"
            else:
                return "scavenge"
        elif m.fear > 0.7:
            return "exit_area"
        elif m.greed > 0.5:
            return "seek_black_market"
        else:
            return "socialize"

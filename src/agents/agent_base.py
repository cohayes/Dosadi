from dataclasses import dataclass, field
from typing import Dict
import random
from .faction_alignment import FactionAlignment

@dataclass
class Mood:
    fear: float = 0.0
    trust: float = 0.5
    greed: float = 0.5
    loyalty: float = 0.5

@dataclass
class Perception:
    values: Dict[str, float] = field(default_factory=dict)

    def update(self, local_weather: Dict[str, float], noise: float = 0.0, experience: float = 1.0):
        """Optional perceptual noise for naive agents."""
        for key, val in local_weather.items():
            if random.random() > experience:
                noisy_val = val + random.gauss(0, noise)
                self.values[key] = max(0.0, min(1.0, noisy_val))
            else:
                self.values[key] = val

@dataclass
class Agent:
    id: int
    factions: FactionAlignment = field(default_factory=FactionAlignment)
    state: str = "idle"
    reputation: float = 0.5
    credits: float = 0.0
    perception: Perception = field(default_factory=Perception)
    mood: Mood = field(default_factory=Mood)
    last_action: str = ""

    def update_perception(self, local_weather: Dict[str, float]):
        self.perception.update(local_weather)

    def evaluate_mood(self):
        p = self.perception.values
        self.mood.fear = (p.get("incident_rate", 0.5) + (1 - p.get("security_intensity", 0.5))) / 2
        self.mood.trust = (p.get("service_quality", 0.5) + (1 - p.get("corruption_risk", 0.5))) / 2
        self.mood.greed = (1 - p.get("supply_level", 0.5)) * 0.6 + (p.get("corruption_risk", 0.5) * 0.4)
        self.mood.loyalty = self.factions.weighted_loyalty(p)

    def decide_action(self) -> str:
        return "idle"  # override in subclasses

    def act(self, action: str):
        self.last_action = action

    def tick(self, local_weather: Dict[str, float]):
        self.update_perception(local_weather)
        self.evaluate_mood()
        action = self.decide_action()
        self.act(action)
        return action

from dataclasses import dataclass, field
from typing import Dict

@dataclass
class FactionAlignment:
    allegiance: Dict[str, float] = field(default_factory=dict)
    """
    Maps faction_id -> loyalty strength (0–1).
    Represents perceived long-term benefit from maintaining allegiance.
    """

    def dominant(self) -> str:
        """Return faction with highest loyalty weight."""
        if not self.allegiance:
            return "neutral"
        return max(self.allegiance, key=self.allegiance.get)

    def adjust(self, faction_id: str, delta: float):
        """Modify loyalty toward a faction."""
        self.allegiance[faction_id] = max(
            0.0, min(1.0, self.allegiance.get(faction_id, 0.5) + delta)
        )

    def decay(self, rate: float = 0.01):
        """Slow loyalty decay (natural drift)."""
        for f in self.allegiance:
            self.allegiance[f] = max(0.0, self.allegiance[f] - rate)

    def normalize(self):
        """Normalize total loyalty to 1.0."""
        total = sum(self.allegiance.values())
        if total > 0:
            for k in self.allegiance:
                self.allegiance[k] /= total

    def weighted_loyalty(self, power_map: Dict[str, float]) -> float:
        """Compute perceived world stability based on faction powers."""
        if not self.allegiance:
            return 0.5
        score = sum(
            w * power_map.get(f"{f}_power", 0.5)
            for f, w in self.allegiance.items()
        )
        return min(1.0, max(0.0, score))

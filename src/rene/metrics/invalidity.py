"""Endpoint-sampled active-agreement invalidity, accumulated across recoveries."""

from dataclasses import dataclass


@dataclass
class InvalidityLedger:
    total_s: float = 0.0
    streak_s: float = 0.0

    def observe(self, invalid: bool, dt_s: float, persistence_s: float) -> float:
        """Return newly accrued duration beyond persistence, for reward accounting."""
        if not invalid:
            self.streak_s = 0.0
            return 0.0
        before = max(0.0, self.streak_s - persistence_s)
        self.total_s += dt_s
        self.streak_s += dt_s
        return max(0.0, self.streak_s - persistence_s) - before

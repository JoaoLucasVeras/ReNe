"""Seeded disturbance schedule."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class DisturbanceState:
    disturbance_type: str = "none"
    trigger_s: float = 5.0
    severity: str = "moderate"
    delay_ms: float = 0
    packet_loss: float = 0.0
    triggered: bool = False

    def update(self, time_s: float, rng: np.random.Generator) -> None:
        # Delivery is handled by agreements.communication, not this schedule.
        self.triggered = self.disturbance_type != "none" and time_s >= self.trigger_s

    @property
    def severity_scale(self) -> float:
        return {"mild": 0.6, "moderate": 1.0, "hard": 1.5}.get(self.severity, 1.0)

"""Prescribed unconnected cut-in, present in the adjacent lane from reset."""

from dataclasses import dataclass

from rene.envs.geometry import VehicleBody


@dataclass(frozen=True, slots=True)
class CutInTrajectory:
    initial_x_m: float
    speed_mps: float
    trigger_s: float
    duration_s: float
    lane_width_m: float
    length_m: float
    width_m: float

    def body_at(self, time_s: float) -> VehicleBody:
        fraction = min(1.0, max(0.0, (time_s - self.trigger_s) / self.duration_s))
        return VehicleBody(
            self.initial_x_m + self.speed_mps * time_s,
            -self.lane_width_m * (1.0 - fraction),
            self.length_m,
            self.width_m,
        )

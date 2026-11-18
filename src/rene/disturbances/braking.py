"""Exact piecewise constant-acceleration front-vehicle disturbance.

The prescribed pulse is independent of the manager, not a car-following model.
Acceleration changes at phase boundaries are not jerk limited.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BrakingPulse:
    trigger_s: float
    brake_s: float
    hold_s: float
    decel_mps2: float
    recovery_mps2: float
    cruise_mps: float
    floor_mps: float

    def accel_at(self, time_s: float, speed: float) -> float:
        """Current commanded acceleration, matching the phases integrated by advance."""
        brake_end = self.trigger_s + self.brake_s
        if self.trigger_s <= time_s < brake_end:
            return -self.decel_mps2 if speed > self.floor_mps + 1e-9 else 0.0
        if time_s >= brake_end + self.hold_s:
            return self.recovery_mps2 if speed < self.cruise_mps - 1e-9 else 0.0
        return 0.0

    def advance(self, x: float, speed: float, start: float, duration: float):
        """Integrate exactly, including off-grid phase boundaries and speed caps."""
        end = start + duration
        brake_end = self.trigger_s + self.brake_s
        hold_end = brake_end + self.hold_s
        boundaries = sorted(
            {start, end, *(t for t in (self.trigger_s, brake_end, hold_end) if start < t < end)}
        )
        for left, right in zip(boundaries, boundaries[1:], strict=False):
            dt = right - left
            if self.trigger_s <= left < brake_end:
                accel = -self.decel_mps2
                moving = min(dt, max(0.0, (speed - self.floor_mps) / -accel))
            elif left >= hold_end:
                accel = self.recovery_mps2
                moving = min(dt, max(0.0, (self.cruise_mps - speed) / accel))
            else:
                accel, moving = 0.0, dt
            x += speed * moving + 0.5 * accel * moving**2
            speed += accel * moving
            x += speed * (dt - moving)
        return x, speed

"""Axis-aligned vehicle geometry for the simplified two-lane simulator.

All coordinates are vehicle centers in meters. Vehicles do not rotate. Swept
collision checks assume linear motion between consecutive integration samples.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import inf


@dataclass(frozen=True, slots=True)
class VehicleBody:
    x: float
    y: float
    length: float
    width: float


def lateral_overlap(first: VehicleBody, second: VehicleBody) -> bool:
    """Contact counts as overlap, with a small floating-point tolerance."""
    return abs(first.y - second.y) <= (first.width + second.width) / 2 + 1e-9


def bodies_overlap(first: VehicleBody, second: VehicleBody) -> bool:
    return lateral_overlap(first, second) and (
        abs(first.x - second.x) <= (first.length + second.length) / 2 + 1e-9
    )


def bumper_clearance(follower: VehicleBody, leader: VehicleBody) -> float:
    """Signed longitudinal clearance, independent of lane applicability."""
    return leader.x - follower.x - (leader.length + follower.length) / 2


def longitudinal_ttc(
    first: VehicleBody, first_speed: float, second: VehicleBody, second_speed: float
) -> float:
    """Constant-speed longitudinal TTC when bodies currently overlap laterally.

    Infinity means non-closing or non-applicable, not a measured safe duration.
    This is not a prediction of a future lane change or a curved trajectory.
    """
    if not lateral_overlap(first, second):
        return inf
    if bodies_overlap(first, second):
        return 0.0
    if first.x < second.x:
        clearance = bumper_clearance(first, second)
        closing_speed = first_speed - second_speed
    else:
        clearance = bumper_clearance(second, first)
        closing_speed = second_speed - first_speed
    return clearance / closing_speed if closing_speed > 0 else inf


def swept_overlap(
    first_before: VehicleBody,
    first_after: VehicleBody,
    second_before: VehicleBody,
    second_after: VehicleBody,
) -> bool:
    """Detect contact anywhere in one linear integration segment, not just its end."""
    entry, exit_ = 0.0, 1.0
    for axis, extent in (
        ("x", (first_before.length + second_before.length) / 2),
        ("y", (first_before.width + second_before.width) / 2),
    ):
        start = getattr(first_before, axis) - getattr(second_before, axis)
        end = getattr(first_after, axis) - getattr(second_after, axis)
        delta = end - start
        if abs(delta) < 1e-12:
            if abs(start) > extent + 1e-9:
                return False
            continue
        lower, upper = sorted(((-extent - start) / delta, (extent - start) / delta))
        entry, exit_ = max(entry, lower), min(exit_, upper)
        if entry > exit_ + 1e-9:
            return False
    return True

"""Shared deterministic agreement feasibility checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeasibilityResult:
    feasible: bool
    reason: str


def time_to_collision(distance_m: float, closing_speed_mps: float) -> float:
    if closing_speed_mps <= 0:
        return float("inf")
    return max(distance_m, 0.0) / closing_speed_mps


def evaluate_feasibility(
    *,
    gap_m: float,
    ttc_s: float,
    headway_s: float,
    distance_to_merge_m: float,
    speed_mps: float,
    min_gap_m: float,
    min_ttc_s: float,
    min_headway_s: float,
    ramp_end_margin_m: float = 5.0,
) -> FeasibilityResult:
    if gap_m < min_gap_m:
        return FeasibilityResult(False, "gap_below_minimum")
    if ttc_s < min_ttc_s:
        return FeasibilityResult(False, "ttc_below_minimum")
    if headway_s < min_headway_s:
        return FeasibilityResult(False, "headway_below_minimum")
    if distance_to_merge_m < -ramp_end_margin_m:
        return FeasibilityResult(False, "merge_point_missed")
    if speed_mps <= 0.1:
        return FeasibilityResult(False, "vehicle_stopped")
    return FeasibilityResult(True, "feasible")

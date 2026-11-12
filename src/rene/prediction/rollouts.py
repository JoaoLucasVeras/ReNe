"""Reuse the common physical controller in a synthetic CV prediction world.

Only decoded policy inputs and fixed shared configuration enter this module.
No live environment, RNG, future disturbance, or hidden state is cloned.
"""

from dataclasses import dataclass
from itertools import combinations

from rene.agreements.state import AgreementState
from rene.disturbances.cut_in import CutInTrajectory
from rene.envs.geometry import swept_overlap


@dataclass(frozen=True)
class Prediction:
    status: str
    completion_s: float | None
    reason: str
    horizon_s: float
    min_gap_margin_m: float = 0.0


def predict(
    values: dict,
    config: dict,
    *,
    fallback: bool = False,
    plan_delta_s: float = 0,
    horizon_s: float | None = None,
) -> Prediction:
    # Lazy import avoids a cycle when the environment offers candidate predictions.
    from rene.envs.merge_lifecycle_env import MergeLifecycleEnv

    now = values["time_s"]
    horizon = (
        min(config["duration_s"] - now, max(5.0, values["remaining_plan_s"] + 3.0))
        if horizon_s is None
        else horizon_s
    )
    horizon = max(0.0, horizon)
    if values["front_received"] < 0.5 or values["rear_received"] < 0.5:
        return Prediction("UNKNOWN", None, "missing_peer_state", horizon)
    if max(values["front_message_age_s"], values["rear_message_age_s"]) > 1.0:
        return Prediction("UNKNOWN", None, "stale_peer_state", horizon)
    sim = MergeLifecycleEnv(
        {**config, "disturbance_type": "none", "packet_loss": 0, "_prediction_replica": True}
    )
    sim.reset(seed=0)
    sim.time_s = now
    sim.ramp_x_m = config["merge_point_m"] - values["distance_to_merge_m"]
    sim.ramp_speed_mps = values["ego_speed_mps"]
    sim.ramp_y_m = values["ego_lateral_m"]
    sim.ramp_accel_mps2 = values["ego_accel_mps2"]
    sim._last_accel = sim.ramp_accel_mps2
    sim.front_x_m = sim.ramp_x_m + values["front_relative_m"]
    sim.rear_x_m = sim.ramp_x_m - values["rear_relative_m"]
    sim.front_speed_mps = values["front_speed_mps"]
    sim.rear_speed_mps = values["rear_speed_mps"]
    sim.agreement.planned_merge_time_s = now + values["remaining_plan_s"] + plan_delta_s
    sim._lane_change_started = 1e-6 < sim.ramp_y_m < config["lane_width_m"] - 1e-6
    sim.fallback_active = fallback
    if fallback:
        sim.agreement.transition(AgreementState.CANCELED, now)
    if values["intruder_detected"] > 0.5:
        speed = values["intruder_speed_mps"]
        sim.cut_in_trajectory = CutInTrajectory(
            sim.ramp_x_m + values["intruder_relative_m"] - speed * now,
            speed,
            1e20,
            1,
            -values["intruder_lateral_m"],
            config["vehicle_length_m"],
            config["vehicle_width_m"],
        )  # Hold observed lateral position; never copy the true future lane change.
    end = now + horizon
    margin = float("inf")
    while sim.time_s < end - 1e-8:
        dt = min(config["dt_s"], end - sim.time_s)
        before = sim._traffic_bodies()
        sim._advance_vehicles(dt)
        sim.time_s += dt
        after = sim._traffic_bodies()
        if any(
            swept_overlap(before[i], after[i], before[j], after[j])
            for i, j in combinations(range(len(before)), 2)
        ):
            return Prediction("INFEASIBLE", None, "predicted_collision", horizon, margin)
        margin = min(
            margin,
            sim.front_clearance_m - config["min_gap_m"],
            sim.rear_clearance_m - config["min_gap_m"],
        )
        if (
            sim.ramp_y_m > 1e-6
            and sim.ramp_x_m + config["vehicle_length_m"] / 2 > config["ramp_end_m"]
        ):
            return Prediction("INFEASIBLE", None, "predicted_ramp_end_violation", horizon, margin)
        sim._update_completion()
        if sim.completed:
            return Prediction(
                "SAFE_COMPLETION", sim.time_s - now, "stabilized_merge", horizon, margin
            )
    return Prediction("UNKNOWN", None, "horizon_without_completion", horizon, margin)

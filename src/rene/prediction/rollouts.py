"""Reuse the common physical controller in a synthetic CV prediction world.

Only decoded policy inputs and fixed shared configuration enter this module.
No live environment, RNG, future disturbance, or hidden state is cloned.
"""

from dataclasses import dataclass
from itertools import combinations

from rene.agreements.state import AgreementState
from rene.disturbances.braking import BrakingPulse
from rene.disturbances.cut_in import CutInTrajectory
from rene.envs.geometry import swept_overlap

STATUS_CODES = {"UNKNOWN": 0, "INFEASIBLE": 1, "SAFE_COMPLETION": 2, "NO_COMPLETION": 3}
STATUS_NAMES = {code: name for name, code in STATUS_CODES.items()}
FALLBACK_HORIZON_S = 10.0
# Declared prediction assumptions (ReNe choices, not from the source paper).
PEER_ACCEL_HOLD_S = 2.0
ACCEL_DEADBAND_MPS2 = 0.1
LATERAL_DEADBAND_MPS = 0.05


def _cannot_complete_before_ramp_end(sim, config) -> bool:
    """Demonstrated inability to start/finish a lane change on the usable ramp.

    True only for an ego still fully on the ramp (no lane change in progress) that
    has stopped, or whose remaining lateral move at current speed cannot fit before
    the ramp end. The ego cannot reverse, so this cannot recover later in the rollout.
    """
    if sim._lane_change_started or sim.ramp_y_m <= 1e-6:
        return False
    if sim.ramp_speed_mps <= 0.1:
        return True
    lateral_s = sim.ramp_y_m / (config["lane_width_m"] / config["lane_change_duration_s"])
    usable_end = config["ramp_end_m"] - config["vehicle_length_m"] / 2
    return sim.ramp_x_m + sim.ramp_speed_mps * lateral_s > usable_end + 1e-8


def predicted_intruder(values: dict, config: dict, ego_x_m: float) -> CutInTrajectory:
    """Sensed intruder motion continued at constant speed and lateral rate.

    With sensed lateral motion toward the mainline, the maneuver continues at that
    rate until the intruder is centered in the lane; otherwise its lateral position
    is held. Never uses the true trigger time or duration.
    """
    now = values["time_s"]
    speed = values["intruder_speed_mps"]
    origin = ego_x_m + values["intruder_relative_m"] - speed * now
    lateral = values["intruder_lateral_m"]
    lateral_speed = values["intruder_lateral_speed_mps"]
    length, width = config["vehicle_length_m"], config["vehicle_width_m"]
    if lateral_speed > LATERAL_DEADBAND_MPS and lateral < 0:
        lane = config["lane_width_m"]
        duration = lane / lateral_speed
        started = now - (1.0 - min(-lateral, lane) / lane) * duration
        return CutInTrajectory(origin, speed, started, duration, lane, length, width)
    return CutInTrajectory(origin, speed, 1e20, 1, -lateral, length, width)


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
    # A canceled plan has no planned time; the fallback branch gets enough horizon
    # to slow down and line up with the next gap (declared ReNe choice).
    default_horizon = max(5.0, values["remaining_plan_s"] + 3.0)
    if fallback and config.get("fallback_next_gap", False):
        default_horizon = max(default_horizon, FALLBACK_HORIZON_S)
    horizon = min(config["duration_s"] - now, default_horizon) if horizon_s is None else horizon_s
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
    if sim.follower_x_m is not None:
        if values["follower_detected"] > 0.5:
            sim.follower_x_m = sim.ramp_x_m - values["follower_relative_m"]
            sim.follower_speed_mps = values["follower_speed_mps"]
        else:
            # Unseen: assume the closest position consistent with non-detection,
            # just beyond sensor range and at least one safe spacing behind the rear.
            spacing = config["vehicle_length_m"] + max(
                config["min_gap_m"], config["min_headway_s"] * config["desired_speed_mps"]
            )
            sim.follower_x_m = min(
                sim.ramp_x_m - config["rear_sensor_range_m"] - 0.1, sim.rear_x_m - spacing
            )
            sim.follower_speed_mps = config["desired_speed_mps"]
    sim.agreement.planned_merge_time_s = now + values["remaining_plan_s"] + plan_delta_s
    sim._lane_change_started = 1e-6 < sim.ramp_y_m < config["lane_width_m"] - 1e-6
    sim.fallback_active = fallback
    if fallback:
        sim.agreement.transition(AgreementState.CANCELED, now)
    accel = values["front_accel_mps2"]
    if abs(accel) > ACCEL_DEADBAND_MPS2:
        # Received front acceleration persists for a declared hold, then constant
        # speed (decel) or up to the desired speed (accel). Not the true pulse.
        if accel < 0:
            sim.braking_pulse = BrakingPulse(
                now, PEER_ACCEL_HOLD_S, 1e9, -accel, 0.0, config["desired_speed_mps"], 0.0
            )
        else:
            sim.braking_pulse = BrakingPulse(
                now - 1.0, 0.0, 0.0, 0.0, accel, config["desired_speed_mps"], 0.0
            )
    if values["intruder_detected"] > 0.5:
        sim.cut_in_trajectory = predicted_intruder(values, config, sim.ramp_x_m)
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
        if _cannot_complete_before_ramp_end(sim, config):
            # Safe so far, but the spec's "demonstrated inability to complete before
            # the usable ramp ends". Kept distinct from INFEASIBLE (a predicted
            # constraint violation) and from UNKNOWN (horizon or data insufficient).
            return Prediction(
                "NO_COMPLETION", None, "predicted_no_completion_before_ramp_end", horizon, margin
            )
    return Prediction("UNKNOWN", None, "horizon_without_completion", horizon, margin)

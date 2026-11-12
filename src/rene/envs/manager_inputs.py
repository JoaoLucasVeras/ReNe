"""Versioned common information contract for rules and PPO.

Rules receive the same clipped, float32-quantized values encoded for PPO, not
additional unbounded truth fields. Changing features invalidates old checkpoints.
"""

from __future__ import annotations

import numpy as np

INPUT_VERSION = "lifecycle-prediction-v4"
FEATURES = (
    ("ego_speed_mps", 0, 40),
    ("ego_accel_mps2", -5, 5),
    ("ego_lateral_m", 0, 6),
    ("distance_to_merge_m", -100, 250),
    ("distance_to_ramp_end_m", -100, 300),
    ("front_speed_mps", 0, 40),
    ("rear_speed_mps", 0, 40),
    ("front_relative_m", -250, 250),
    ("rear_relative_m", -250, 250),
    ("front_clearance_m", -250, 250),
    ("rear_clearance_m", -250, 250),
    ("gap_m", -250, 250),
    ("ttc_s", 0, 20),
    ("ttc_finite", 0, 1),
    ("headway_s", 0, 5),
    ("message_age_s", 0, 60),
    ("front_message_age_s", 0, 60),
    ("rear_message_age_s", 0, 60),
    ("front_received", 0, 1),
    ("rear_received", 0, 1),
    ("remaining_plan_s", -20, 20),
    ("agreement_age_s", 0, 60),
    ("revision", 0, 10),
    ("renegotiation_count", 0, 10),
    ("prior_action", 0, 5),
    ("merge_order", 0, 1),
    ("target_gap_id", 0, 10),
    ("cancel_pending", 0, 1),
    ("cancel_confirmed", 0, 1),
    ("cancel_timed_out", 0, 1),
    ("cancel_ack_count", 0, 2),
    ("alternative_gap_feasible", 0, 1),
    ("local_canceled", 0, 1),
    ("time_s", 0, 60),
    ("local_agreement_state", 0, 6),
    ("intruder_detected", 0, 1),
    ("intruder_relative_m", -250, 250),
    ("intruder_speed_mps", 0, 40),
    ("intruder_lateral_m", -6, 6),
    ("slot_occupied", 0, 1),
    ("front_intent_received", 0, 1),
    ("front_intent_position_error_m", -250, 250),
    ("front_intent_speed_error_mps", -20, 20),
    ("front_intent_age_s", 0, 60),
    ("keep_status", 0, 2),
    ("keep_completion_s", 0, 30),
    ("fallback_status", 0, 2),
    ("fallback_completion_s", 0, 30),
    ("advance_feasible", 0, 1),
    ("advance_completion_s", 0, 30),
    ("delay_feasible", 0, 1),
    ("delay_completion_s", 0, 30),
    ("proposal_pending", 0, 1),
)


def encode(values: dict) -> np.ndarray:
    return np.array(
        [
            2 * (np.clip(values[name], low, high) - low) / (high - low) - 1
            for name, low, high in FEATURES
        ],
        dtype=np.float32,
    )


def decode(observation: np.ndarray) -> dict[str, float]:
    return {
        name: float((float(value) + 1) * (high - low) / 2 + low)
        for value, (name, low, high) in zip(observation, FEATURES, strict=True)
    }

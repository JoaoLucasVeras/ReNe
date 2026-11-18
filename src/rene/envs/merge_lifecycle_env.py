"""Seeded post-acceptance cooperative-merge lifecycle environment.

This lightweight environment models lifecycle decisions rather than low-level
driving. It follows the Gymnasium API and is intended for rapid research runs.
HighwayEnv remains the visual/reference simulator and can be used for later
cross-validation.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from rene.agreements.communication import PEERS, CommunicationModel
from rene.agreements.feasibility import FeasibilityResult, evaluate_feasibility
from rene.agreements.protocol import create_accepted_agreement
from rene.agreements.revision import RevisionSession
from rene.agreements.state import AgreementState, ManagerAction
from rene.disturbances.base import DisturbanceState
from rene.disturbances.braking import BrakingPulse
from rene.disturbances.cut_in import CutInTrajectory
from rene.envs.geometry import (
    VehicleBody,
    bumper_clearance,
    lateral_overlap,
    longitudinal_ttc,
    swept_overlap,
)
from rene.envs.manager_inputs import FEATURES, INPUT_VERSION, decode, encode
from rene.metrics.episode_metrics import EpisodeMetrics
from rene.metrics.invalidity import InvalidityLedger
from rene.safety.shield import ShieldDecision, apply_shield

DEFAULT_CONFIG: dict[str, Any] = {
    "duration_s": 20.0,
    "dt_s": 0.2,
    "decision_interval_s": 1.0,
    "merge_point_m": 200.0,
    "ramp_end_m": 240.0,
    "desired_speed_mps": 25.0,
    "initial_gap_m": 60.0,
    "vehicle_length_m": 4.5,
    "vehicle_width_m": 1.8,
    "lane_width_m": 3.6,
    # Earliest lane-change start for the nominal plan (merge point minus half a
    # lane change at 25 m/s), so the accepted plan is already the earliest feasible
    # timing and "advance" is not a free improvement (Nov 18 B3 review).
    "merge_start_m": 175.0,
    "lane_change_duration_s": 2.0,
    "merge_stabilization_s": 1.0,
    "min_gap_m": 12.0,
    "min_ttc_s": 2.0,
    "min_headway_s": 0.8,
    "max_accel_mps2": 2.5,
    "max_decel_mps2": 4.0,
    "invalidation_persistence_s": 0.6,
    "oracle_horizon_s": 3.0,
    "max_renegotiations": 1,
    "enable_timing_revisions": True,
    "fallback_next_gap": True,
    "fallback_gap_gain_per_s": 0.5,
    "render_width": 800,
    "render_height": 240,
    "disturbance_type": "cut_in",
    "disturbance_trigger_s": 5.0,
    "disturbance_severity": "moderate",
    "braking_duration_s": 2.0,
    "braking_hold_s": 1.0,
    "braking_decel_mps2": 3.0,
    "front_max_decel_mps2": 4.0,
    "braking_recovery_mps2": 2.0,
    "braking_min_speed_mps": 8.0,
    "intent_decel_mps2": 1.5,
    "cut_in_duration_s": 2.0,
    "cut_in_offset_fraction": 0.4,
    "local_sensor_range_m": 60.0,
    # Rearward range (rear radar class); bodies behind the ego use this range.
    "rear_sensor_range_m": 120.0,
    "communication_delay_ms": 100,
    "packet_loss": 0.05,
    "beacon_interval_s": 0.1,
    "cancel_retry_s": 0.1,
    "cancel_timeout_s": 3.0,
    "traffic_density": "medium",
}


class MergeLifecycleEnv(gym.Env[np.ndarray, int]):
    """A compact high-level agreement lifecycle environment."""

    metadata = {"render_modes": ["rgb_array"], "render_fps": 5}

    def __init__(self, config: dict[str, Any] | None = None, render_mode: str | None = None):
        super().__init__()
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        for key in (
            "dt_s",
            "decision_interval_s",
            "duration_s",
            "vehicle_length_m",
            "vehicle_width_m",
            "lane_width_m",
            "lane_change_duration_s",
            "merge_stabilization_s",
            "max_decel_mps2",
            "max_accel_mps2",
            "desired_speed_mps",
            "min_gap_m",
            "min_ttc_s",
            "min_headway_s",
            "braking_duration_s",
            "braking_decel_mps2",
            "front_max_decel_mps2",
            "braking_recovery_mps2",
            "intent_decel_mps2",
            "cut_in_duration_s",
            "local_sensor_range_m",
            "rear_sensor_range_m",
        ):
            if not np.isfinite(self.config[key]) or self.config[key] <= 0:
                raise ValueError(f"{key} must be finite and positive")
        for key in ("braking_hold_s", "braking_min_speed_mps"):
            if not np.isfinite(self.config[key]) or self.config[key] < 0:
                raise ValueError(f"{key} must be finite and nonnegative")
        if self.config["braking_min_speed_mps"] > self.config["desired_speed_mps"]:
            raise ValueError("braking minimum speed must not exceed desired speed")
        if not 0 < self.config["cut_in_offset_fraction"] < 0.6:
            raise ValueError("cut-in offset fraction must be between 0 and 0.6")
        if self.config["vehicle_width_m"] >= self.config["lane_width_m"]:
            raise ValueError("vehicle width must be smaller than lane width")
        if (
            not self.config["merge_start_m"]
            < self.config["merge_point_m"]
            < self.config["ramp_end_m"]
        ):
            raise ValueError("require merge_start < merge_point < ramp_end")
        ratio = self.config["decision_interval_s"] / self.config["dt_s"]
        if not np.isclose(ratio, round(ratio)) or ratio < 1:
            raise ValueError("decision interval must be an integer multiple of dt")
        self.render_mode = render_mode
        if render_mode not in {None, "rgb_array"}:
            raise ValueError("supported render modes are None and 'rgb_array'")
        self.action_space = spaces.Discrete(len(ManagerAction))
        self.observation_space = spaces.Box(-1.0, 1.0, shape=(len(FEATURES),), dtype=np.float32)
        self._episode_seed = 0
        self._episode_id = ""
        self.follower_x_m = None
        self.follower_speed_mps = 0.0
        self._invalid_since_s: float | None = None
        self._last_accel = 0.0
        self._intent_position_error_m = 0.0
        self._intent_speed_error_mps = 0.0
        self._intent_inconsistency_count = 0
        self._decision_log: list[dict[str, Any]] = []

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        options = options or {}
        if seed is None:
            seed = int(self.np_random.integers(0, 2**31 - 1))
        self._episode_seed = int(seed)
        self._episode_id = options.get("episode_id", f"episode-{seed}")
        # Ramp length is a per-episode scenario factor (training/evaluation protocol).
        # Everything downstream, including the shared predictor, reads self.config.
        if not hasattr(self, "_base_ramp_end_m"):
            self._base_ramp_end_m = float(self.config["ramp_end_m"])
        ramp_end = float(options.get("ramp_end_m", self._base_ramp_end_m))
        if not np.isfinite(ramp_end) or ramp_end <= self.config["merge_point_m"]:
            raise ValueError("ramp_end_m must be finite and beyond the merge point")
        self.config["ramp_end_m"] = ramp_end
        density = options.get("traffic_density", self.config["traffic_density"])
        density_factor = {"low": 1.2, "medium": 1.0, "high": 5 / 6}.get(density, 1.0)
        density_gap = float(self.config["initial_gap_m"]) * density_factor
        initial_gap = float(options.get("initial_gap_m", density_gap))
        if not np.isfinite(initial_gap) or initial_gap <= 0:
            raise ValueError("initial gap must be finite and positive")
        jitter = float(self.np_random.uniform(-1.0, 1.0))

        self.time_s = 0.0
        self.ramp_x_m = 20.0 + jitter
        self.ramp_speed_mps = float(self.config["desired_speed_mps"])
        self.ramp_accel_mps2 = 0.0
        # initial_gap is the free opening between the two mainline bumpers.
        # Equal initial speeds keep this moving slot aligned with the ego.
        center_span = initial_gap + self.config["vehicle_length_m"]
        self.front_x_m = self.ramp_x_m + center_span / 2
        self.front_speed_mps = self.ramp_speed_mps
        self._front_intent_origin_x_m = self.front_x_m
        self._front_intent_speed_mps = self.ramp_speed_mps
        self.rear_x_m = self.ramp_x_m - center_span / 2
        self.rear_speed_mps = self.ramp_speed_mps
        # Non-connected mainline follower one density gap behind the rear peer. It
        # bounds the next gap available to the perception fallback after cancellation.
        if self.config["fallback_next_gap"]:
            self.follower_x_m = self.rear_x_m - center_span
            self.follower_speed_mps = self.ramp_speed_mps
        else:
            self.follower_x_m = None
            self.follower_speed_mps = 0.0
        self.ramp_y_m = float(self.config["lane_width_m"])
        self._lane_change_started = False
        self._stable_since_s: float | None = None
        self.physical_merge_time_s: float | None = None
        self.low_level_interventions = 0
        self.synthetic_gap_bonus_m = 0.0
        self.canceled = False
        self.fallback_active = False
        self.completed = False
        self.collision = False
        self.ramp_end_violation = False
        self._invalid_since_s = None
        self._last_accel = 0.0
        self._intent_position_error_m = 0.0
        self._intent_speed_error_mps = 0.0
        self._intent_inconsistency_count = 0
        self._decision_log = []
        self._invalidity = InvalidityLedger()
        self._assessment_cache = None

        self.disturbance = DisturbanceState(
            disturbance_type=options.get("disturbance_type", self.config["disturbance_type"]),
            trigger_s=float(
                options.get("disturbance_trigger_s", self.config["disturbance_trigger_s"])
            ),
            severity=options.get("disturbance_severity", self.config["disturbance_severity"]),
            delay_ms=float(
                options.get("communication_delay_ms", self.config["communication_delay_ms"])
            ),
            packet_loss=float(options.get("packet_loss", self.config["packet_loss"])),
        )
        self.braking_pulse = None
        self.cut_in_trajectory = None
        if self.disturbance.disturbance_type == "cut_in":
            if not np.isfinite(self.disturbance.trigger_s) or self.disturbance.trigger_s < 0:
                raise ValueError("cut-in trigger must be finite and nonnegative")
            if self.disturbance.severity not in {"mild", "moderate", "hard"}:
                raise ValueError("unknown cut-in severity")
            offset = (
                center_span
                / 2
                * self.config["cut_in_offset_fraction"]
                / self.disturbance.severity_scale
            )
            if offset <= 0 or center_span / 2 - offset <= self.config["vehicle_length_m"]:
                raise ValueError("cut-in trajectory must fit between the named mainline bodies")
            self.cut_in_trajectory = CutInTrajectory(
                self.ramp_x_m + offset,
                self.ramp_speed_mps,
                self.disturbance.trigger_s,
                self.config["cut_in_duration_s"],
                self.config["lane_width_m"],
                self.config["vehicle_length_m"],
                self.config["vehicle_width_m"],
            )
        if self.disturbance.disturbance_type in {"braking", "intent_mismatch"}:
            if not np.isfinite(self.disturbance.trigger_s) or self.disturbance.trigger_s < 0:
                raise ValueError("braking trigger must be finite and nonnegative")
            if self.disturbance.severity not in {"mild", "moderate", "hard"}:
                raise ValueError("unknown braking severity")
            self.braking_pulse = BrakingPulse(
                self.disturbance.trigger_s,
                self.config["braking_duration_s"],
                self.config["braking_hold_s"],
                min(
                    self.config[
                        "intent_decel_mps2"
                        if self.disturbance.disturbance_type == "intent_mismatch"
                        else "braking_decel_mps2"
                    ]
                    * self.disturbance.severity_scale,
                    self.config["front_max_decel_mps2"],
                ),
                self.config["braking_recovery_mps2"],
                self.config["desired_speed_mps"],
                self.config["braking_min_speed_mps"],
            )
        planned_time = (self.config["merge_point_m"] - self.ramp_x_m) / self.ramp_speed_mps
        lateral_distance = self.ramp_speed_mps * self.config["lane_change_duration_s"] / 2
        # Allow a full integration-step margin for discrete start-time rounding.
        if (
            self.config["merge_point_m"] - lateral_distance < self.config["merge_start_m"]
            or self.config["merge_point_m"]
            + lateral_distance
            + self.ramp_speed_mps * self.config["dt_s"]
            > self.config["ramp_end_m"] - self.config["vehicle_length_m"] / 2
        ):
            raise ValueError("initial lane-change plan does not fit the merge corridor")
        self.agreement = create_accepted_agreement(
            self._episode_id,
            planned_merge_time_s=float(planned_time),
            agreement_id=f"{self._episode_id}-agreement-0",
        )
        self.agreement.transition(AgreementState.EXECUTING, self.time_s)
        self.metrics = EpisodeMetrics(episode_id=self._episode_id, seed=self._episode_seed)
        if not self._slot_safe_for(planned_time + self.config["merge_stabilization_s"]):
            raise ValueError("initial accepted agreement does not have a safe moving target gap")
        self.agreement.feasible = self._feasibility().feasible
        self.agreement.feasibility_reason = self._feasibility().reason
        self.communication = CommunicationModel(
            self._episode_seed,
            self.agreement.agreement_id,
            self.disturbance.delay_ms / 1000.0,
            self.disturbance.packet_loss,
            self.config["beacon_interval_s"],
            self.config["cancel_retry_s"],
            self.config["cancel_timeout_s"],
        )
        self.communication.bootstrap(self._beacon_payloads())
        self.revision_session = RevisionSession(self.communication.bus, self.agreement.agreement_id)
        self.communication.revision_session = self.revision_session
        self.revision_session.accept_peer = self._peer_timing_admission
        self.agreement.message_count = 0  # Initial negotiation is an assumed fixture.
        observation = self._observation()
        return observation, self._info()

    @property
    def gap_m(self) -> float:
        return self.front_x_m - self.rear_x_m - self.config["vehicle_length_m"]

    def _bodies(self) -> tuple[VehicleBody, VehicleBody, VehicleBody]:
        length = self.config["vehicle_length_m"]
        width = self.config["vehicle_width_m"]
        return (
            VehicleBody(self.ramp_x_m, self.ramp_y_m, length, width),
            VehicleBody(self.front_x_m, 0.0, length, width),
            VehicleBody(self.rear_x_m, 0.0, length, width),
        )

    @property
    def front_clearance_m(self) -> float:
        ego, front, _ = self._bodies()
        return bumper_clearance(ego, front)

    def _follower_body(self) -> VehicleBody | None:
        if self.follower_x_m is None:
            return None
        return VehicleBody(
            self.follower_x_m, 0.0, self.config["vehicle_length_m"], self.config["vehicle_width_m"]
        )

    def _traffic_bodies(self) -> tuple[VehicleBody, ...]:
        bodies = self._bodies()
        if self.follower_x_m is not None:
            bodies += (self._follower_body(),)
        if self.cut_in_trajectory is not None:
            bodies += (self.cut_in_trajectory.body_at(self.time_s),)
        return bodies

    def _traffic_speeds(self) -> tuple[float, ...]:
        speeds = (self.ramp_speed_mps, self.front_speed_mps, self.rear_speed_mps)
        if self.follower_x_m is not None:
            speeds += (self.follower_speed_mps,)
        if self.cut_in_trajectory is not None:
            speeds += (self.cut_in_trajectory.speed_mps,)
        return speeds

    def _slot_occupied(self, intruder: VehicleBody | None, rear_x: float, front_x: float) -> bool:
        """The original named-pair agreement cannot ignore an intervening body."""
        if intruder is None:
            return False
        lane = VehicleBody(intruder.x, 0.0, intruder.length, intruder.width)
        return lateral_overlap(intruder, lane) and rear_x < intruder.x < front_x

    def _true_slot_occupied(self) -> bool:
        intruder = self.cut_in_trajectory.body_at(self.time_s) if self.cut_in_trajectory else None
        return self._slot_occupied(intruder, self.rear_x_m, self.front_x_m)

    def _observed_intruder(self) -> VehicleBody | None:
        """Ideal, instantaneous local detection; no remembered out-of-range track."""
        if self.cut_in_trajectory is None:
            return None
        body = self.cut_in_trajectory.body_at(self.time_s)
        return body if self._within_sensor_range(body) else None

    def _within_sensor_range(self, body: VehicleBody) -> bool:
        """Ideal local sensing: forward range ahead of the ego, rear range behind it."""
        offset = body.x - self.ramp_x_m
        limit = (
            self.config["local_sensor_range_m"]
            if offset >= 0
            else self.config["rear_sensor_range_m"]
        )
        return abs(offset) <= limit

    def _observed_intruder_lateral_speed(self, window_s: float = 0.1) -> float:
        """Lateral speed from a backward difference of two sensed positions.

        Positive means moving toward the mainline. Zero at the exact onset of a
        maneuver: a sensor needs measurable displacement before reporting motion.
        """
        if self._observed_intruder() is None:
            return 0.0
        now = self.cut_in_trajectory.body_at(self.time_s).y
        before = self.cut_in_trajectory.body_at(max(0.0, self.time_s - window_s)).y
        return (now - before) / window_s

    def _observed_follower(self) -> VehicleBody | None:
        """Ideal local detection of the non-connected follower within sensor range."""
        body = self._follower_body()
        if body is None or not self._within_sensor_range(body):
            return None
        return body

    @property
    def rear_clearance_m(self) -> float:
        ego, _, rear = self._bodies()
        return bumper_clearance(rear, ego)

    @property
    def distance_to_merge_m(self) -> float:
        return self.config["merge_point_m"] - self.ramp_x_m

    @property
    def ttc_s(self) -> float:
        bodies = self._traffic_bodies()
        speeds = self._traffic_speeds()
        return min(
            longitudinal_ttc(bodies[i], speeds[i], bodies[j], speeds[j])
            for i, j in combinations(range(len(bodies)), 2)
        )

    @property
    def target_slot_ttc_s(self) -> float:
        """Prospective longitudinal TTC if the ego occupied the target lane now."""
        ego, front, rear = self._bodies()
        projected = VehicleBody(ego.x, 0.0, ego.length, ego.width)
        return min(
            longitudinal_ttc(projected, self.ramp_speed_mps, front, self.front_speed_mps),
            longitudinal_ttc(rear, self.rear_speed_mps, projected, self.ramp_speed_mps),
        )

    @property
    def headway_s(self) -> float:
        # Prospective ego/front and rear/ego headways, not the whole gap / rear speed.
        front = (
            max(self.front_clearance_m, 0.0) / self.ramp_speed_mps
            if self.ramp_speed_mps > 0.1
            else float("inf")
        )
        rear = (
            max(self.rear_clearance_m, 0.0) / self.rear_speed_mps
            if self.rear_speed_mps > 0.1
            else float("inf")
        )
        return min(front, rear)

    @property
    def actual_headway_s(self) -> float:
        """Minimum headway only among bodies currently sharing lateral space."""
        bodies = self._traffic_bodies()
        speeds = self._traffic_speeds()
        values = []
        for i, j in combinations(range(len(bodies)), 2):
            if not lateral_overlap(bodies[i], bodies[j]):
                continue
            follower, leader = (i, j) if bodies[i].x <= bodies[j].x else (j, i)
            if speeds[follower] > 0.1:
                values.append(
                    max(bumper_clearance(bodies[follower], bodies[leader]), 0.0) / speeds[follower]
                )
        return min(values, default=float("inf"))

    def _slot_safe_for(self, horizon_s: float) -> bool:
        """Conservative constant-speed entry check; not a formal safety guarantee."""
        if self._true_slot_occupied():
            return False
        front_min = min(
            self.front_clearance_m,
            self.front_clearance_m + (self.front_speed_mps - self.ramp_speed_mps) * horizon_s,
        )
        rear_min = min(
            self.rear_clearance_m,
            self.rear_clearance_m + (self.ramp_speed_mps - self.rear_speed_mps) * horizon_s,
        )
        return (
            front_min
            >= max(self.config["min_gap_m"], self.config["min_headway_s"] * self.ramp_speed_mps)
            and rear_min
            >= max(self.config["min_gap_m"], self.config["min_headway_s"] * self.rear_speed_mps)
            and self.target_slot_ttc_s >= self.config["min_ttc_s"]
        )

    def _update_completion(self) -> None:
        # Fully in the target lane, inside the actual named pair, safely stabilized.
        safe = self._fallback_slot_safe() if self.fallback_active else self._slot_safe_for(0.0)
        valid = abs(self.ramp_y_m) < 1e-9 and safe
        if not valid:
            self._stable_since_s = None
            return
        if self._stable_since_s is None:
            self._stable_since_s = self.time_s
        if self.time_s - self._stable_since_s + 1e-9 >= self.config["merge_stabilization_s"]:
            self.completed = True
            self.physical_merge_time_s = self.time_s

    def _fallback_slot_safe(self):
        """Perception fallback may stabilize in a real opening, not revive an agreement."""
        ego = self._bodies()[0]
        for body, speed in zip(self._traffic_bodies()[1:], self._traffic_speeds()[1:], strict=True):
            if not lateral_overlap(ego, body):
                continue
            clearance = abs(body.x - ego.x) - (body.length + ego.length) / 2
            follower_speed = self.ramp_speed_mps if ego.x < body.x else speed
            if clearance < max(
                self.config["min_gap_m"], self.config["min_headway_s"] * follower_speed
            ):
                return False
            if longitudinal_ttc(ego, self.ramp_speed_mps, body, speed) < self.config["min_ttc_s"]:
                return False
        return True

    def _rear_following_accel(self, dt):
        return self._following_accel(self.rear_x_m, self.rear_speed_mps, dt)

    def _following_accel(self, x_m, speed_mps, dt):
        """Bounded car following for a mainline vehicle (rear peer or follower)."""
        me = VehicleBody(x_m, 0.0, self.config["vehicle_length_m"], self.config["vehicle_width_m"])
        leaders = [
            (body, speed)
            for body, speed in zip(self._traffic_bodies(), self._traffic_speeds(), strict=True)
            if body.x > me.x and lateral_overlap(body, me)
        ]
        target = self.config["desired_speed_mps"]
        cap = float("inf")
        if leaders:
            leader, speed = min(leaders, key=lambda item: item[0].x)
            desired_gap = max(self.config["min_gap_m"], self.config["min_headway_s"] * speed_mps)
            cap = np.sqrt(
                max(
                    0.0,
                    speed**2
                    + 2
                    * self.config["max_decel_mps2"]
                    * (bumper_clearance(me, leader) - desired_gap),
                )
            )
            target = min(target, cap)
        return float(
            np.clip(
                min((target - speed_mps) * 0.5, (cap - speed_mps) / dt),
                -self.config["max_decel_mps2"],
                self.config["max_accel_mps2"],
            )
        )

    def _lane_traffic(self) -> list[tuple[VehicleBody, float]]:
        """Bodies (excluding the ego) touching the mainline lane, ordered front to back.

        A partially cut-in vehicle counts as present, which is conservative.
        """
        width = self.config["vehicle_width_m"]
        items = [
            (body, speed)
            for body, speed in zip(
                self._traffic_bodies()[1:], self._traffic_speeds()[1:], strict=True
            )
            if lateral_overlap(body, VehicleBody(body.x, 0.0, body.length, width))
        ]
        return sorted(items, key=lambda item: -item[0].x)

    def _required_spacing(self, follower_speed_mps: float) -> float:
        return max(self.config["min_gap_m"], self.config["min_headway_s"] * follower_speed_mps)

    def _opening_safe_for(self, horizon_s: float) -> bool:
        """Perception fallback entry check into a bounded opening at the ego's position.

        Requires a real mainline vehicle both ahead and behind (never open road past
        the last modeled vehicle), with the same gap/headway/TTC limits and the same
        constant-speed projection used for the agreement slot.
        """
        length = self.config["vehicle_length_m"]
        ego = VehicleBody(self.ramp_x_m, 0.0, length, self.config["vehicle_width_m"])
        lane = self._lane_traffic()
        ahead = [item for item in lane if item[0].x > ego.x]
        behind = [item for item in lane if item[0].x <= ego.x]
        if not ahead or not behind:
            return False
        (leader, lead_speed), (follower, follow_speed) = ahead[-1], behind[0]
        front = bumper_clearance(ego, leader)
        rear = bumper_clearance(follower, ego)
        front_min = min(front, front + (lead_speed - self.ramp_speed_mps) * horizon_s)
        rear_min = min(rear, rear + (self.ramp_speed_mps - follow_speed) * horizon_s)
        return (
            front_min >= self._required_spacing(self.ramp_speed_mps)
            and rear_min >= self._required_spacing(follow_speed)
            and longitudinal_ttc(ego, self.ramp_speed_mps, leader, lead_speed)
            >= self.config["min_ttc_s"]
            and longitudinal_ttc(follower, follow_speed, ego, self.ramp_speed_mps)
            >= self.config["min_ttc_s"]
        )

    def _target_gap(self):
        """Nearest bounded mainline gap large enough at its follower's speed.

        Returns ((lead_body, lead_speed), (back_body, back_speed)) or None.
        """
        length = self.config["vehicle_length_m"]
        lane = self._lane_traffic()
        # A gap must stay usable over the same entry window the opening check uses.
        window_s = self.config["lane_change_duration_s"] + self.config["merge_stabilization_s"]
        best = None
        for lead, back in zip(lane, lane[1:], strict=False):
            free = lead[0].x - back[0].x - lead[0].length / 2 - back[0].length / 2
            projected = free + min(0.0, (lead[1] - back[1]) * window_s)
            if projected < length + 2 * self._required_spacing(back[1]):
                continue
            distance = abs((lead[0].x + back[0].x) / 2 - self.ramp_x_m)
            if best is None or distance < best[0]:
                best = (distance, lead, back)
        return None if best is None else (best[1], best[2])

    def _gap_alignment_speed(self) -> float | None:
        """Fallback speed target that steers the ego toward the nearest usable gap.

        Returns None when no bounded gap between consecutive mainline vehicles is
        large enough at its current speed; callers keep the legacy fallback speed.
        """
        target = self._target_gap()
        if target is None:
            return None
        (lead, lead_speed), (back, back_speed) = target
        gap_speed = (lead_speed + back_speed) / 2  # the gap center's speed
        error = (lead.x + back.x) / 2 - self.ramp_x_m
        # Relative speed toward the gap center, bounded so the ego can still null it
        # with its comfortable limit on arrival (accelerate back up when the gap is
        # behind, brake when it is ahead). A pure proportional law overshoots.
        recover = self.config["max_accel_mps2"] if error < 0 else self.config["max_decel_mps2"]
        relative = min(
            self.config["fallback_gap_gain_per_s"] * abs(error),
            np.sqrt(2 * 0.8 * recover * abs(error)),
        )
        return float(
            np.clip(
                gap_speed + np.sign(error) * relative, 0.0, self.config["desired_speed_mps"]
            )
        )

    def _feasibility(self):
        if self._true_slot_occupied():
            return FeasibilityResult(False, "target_slot_occupied")
        return evaluate_feasibility(
            gap_m=min(self.front_clearance_m, self.rear_clearance_m),
            ttc_s=self.target_slot_ttc_s,
            headway_s=self.headway_s,
            distance_to_merge_m=(
                self.config["ramp_end_m"] - self.ramp_x_m if self.ramp_y_m > 0.0 else 0.0
            ),
            speed_mps=self.ramp_speed_mps,
            min_gap_m=self.config["min_gap_m"],
            min_ttc_s=self.config["min_ttc_s"],
            min_headway_s=self.config["min_headway_s"],
        )

    def _renegotiation_feasible(self, action: ManagerAction) -> bool:
        if action.family != "renegotiate":
            return True
        if (
            not self.config["enable_timing_revisions"]
            or self.agreement.renegotiation_count >= self.config["max_renegotiations"]
            or self.revision_session.state == "pending"
            or self.canceled
        ):
            return False
        values = decode(self._observation())
        field = {
            ManagerAction.RENEGOTIATE_ADVANCE: "advance_feasible",
            ManagerAction.RENEGOTIATE_DELAY: "delay_feasible",
        }.get(action)
        return field is not None and values[field] > 0.5

    def action_masks(self) -> np.ndarray:
        """Actions a learned manager may request now (MaskablePPO convention).

        Continue and cancel are always allowed; timing revisions only when the shared
        candidate check says they are feasible; next-gap and order-swap never (not
        modeled). Rules use the same feasibility flags, so masking adds no information.
        """
        mask = np.zeros(len(ManagerAction), dtype=bool)
        mask[ManagerAction.CONTINUE] = True
        mask[ManagerAction.CANCEL] = True
        for action in (ManagerAction.RENEGOTIATE_DELAY, ManagerAction.RENEGOTIATE_ADVANCE):
            mask[action] = self._renegotiation_feasible(action)
        return mask

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        requested = ManagerAction(int(action))
        decision_time_s = self.time_s
        decision_inputs = decode(self._observation())
        feasibility = self._feasibility()
        if self.agreement.state == AgreementState.CANCELED:
            shield = ShieldDecision(
                requested,
                ManagerAction.CANCEL,
                False,
                "agreement_already_canceled",
            )
        else:
            renegotiation_feasible = self._renegotiation_feasible(requested)
            shield = apply_shield(
                requested, feasibility, renegotiation_feasible=renegotiation_feasible
            )
        applied = shield.applied
        self.agreement.last_requested_action = requested
        self.agreement.last_applied_action = applied
        if shield.overridden:
            self.metrics.shield_overrides += 1

        self._interval_sent_before = self.communication.counts()["sent"]
        self._apply_lifecycle_action(applied)
        reward_components = self._simulate_interval()
        reward = float(sum(reward_components.values()))
        self.metrics.total_reward += reward

        terminated = self.completed or self.collision or self.ramp_end_violation
        truncated = self.time_s >= self.config["duration_s"] - 1e-9 and not terminated
        if truncated and self.agreement.state not in {
            AgreementState.CANCELED,
            AgreementState.COMPLETED,
        }:
            self.agreement.transition(AgreementState.FAILED, self.time_s)

        self._decision_log.append(
            {
                "time_s": self.time_s,
                "decision_time_s": decision_time_s,
                "manager_inputs": decision_inputs,
                "requested_action": requested.name,
                "applied_action": applied.name,
                "overridden": shield.overridden,
                "override_reason": shield.reason,
                "feasible": feasibility.feasible,
                "feasibility_reason": feasibility.reason,
                "gap_m": self.gap_m,
                "ttc_s": self.ttc_s,
                "message_age_s": max(self.communication.ages(self.time_s).values()),
                **{f"reward_{k}": v for k, v in reward_components.items()},
            }
        )
        info = self._info()
        if terminated or truncated:
            self._finalize_metrics()
            info["episode_metrics"] = self.metrics.as_dict()
            info["decision_log"] = list(self._decision_log)
            info["communication_log"] = list(self.communication.bus.events)
        return self._observation(), reward, terminated, truncated, info

    def _apply_lifecycle_action(self, action: ManagerAction) -> None:
        if self.agreement.state in {
            AgreementState.CANCELED,
            AgreementState.COMPLETED,
            AgreementState.FAILED,
        }:
            return
        if action == ManagerAction.CANCEL:
            if self.agreement.state in {
                AgreementState.ACCEPTED,
                AgreementState.EXECUTING,
                AgreementState.RENEGOTIATING,
            }:
                self.agreement.transition(AgreementState.CANCELED, self.time_s)
            self.revision_session.abort(self.time_s)
            self.canceled = True
            self.fallback_active = True
            self.metrics.canceled = True
            self.communication.session.request(self.time_s)
            self.communication.advance(self.time_s, lambda at: self._beacon_payloads())
            return
        if action.family != "renegotiate":
            return
        if not self._renegotiation_feasible(action):
            return
        delta = 1.0 if action == ManagerAction.RENEGOTIATE_DELAY else -1.0
        self.agreement.transition(AgreementState.RENEGOTIATING, self.time_s)
        self.agreement.renegotiation_count += 1
        self.metrics.renegotiation_attempts += 1
        self.revision_session.request(
            self.time_s, self.agreement.revision + 1, self.agreement.planned_merge_time_s + delta
        )
        self.communication.advance(self.time_s, lambda at: self._beacon_payloads())
        self._update_revision()

    def _update_revision(self):
        session = self.revision_session
        if self.agreement.state != AgreementState.RENEGOTIATING or session.state == "pending":
            return
        if session.state == "accepted":
            # Safety remains common and truth-based; acceptance is not permission
            # to execute an unsafe or already-missed physical plan.
            valid = (
                not self._lane_change_started
                and self._feasibility().feasible
                and session.planned_at_s - self.config["lane_change_duration_s"] / 2 > self.time_s
            )
            if valid:
                self.agreement.planned_merge_time_s = session.planned_at_s
                self.agreement.revision = session.revision
                self.communication.session.revision = session.revision
                self.communication.bus.log(
                    "revision_activated",
                    self.time_s,
                    revision=session.revision,
                    planned_at_s=session.planned_at_s,
                )
            else:
                session.state = "activation_rejected"
                self.communication.bus.log("revision_activation_rejected", self.time_s)
        self.agreement.transition(AgreementState.EXECUTING, self.time_s)

    def _peer_timing_admission(self, peer, payload, at_s):
        """Static cruising peers reserve ego timing only; no peer motion is revised."""
        return (
            peer in PEERS
            and peer not in self.communication.session.remote_released_at_s
            and payload["planned_at_s"] - self.config["lane_change_duration_s"] / 2 > at_s
            and abs(payload["planned_at_s"] - self.agreement.planned_merge_time_s) <= 1.0 + 1e-8
        )

    def _simulate_interval(self) -> dict[str, float]:
        sent_before = getattr(self, "_interval_sent_before", self.communication.counts()["sent"])
        cancel_before = self.metrics.cancel_requested_at_s
        components = {
            "progress": 0.0,
            "success": 0.0,
            "collision": 0.0,
            "near_collision": 0.0,
            "failed_time": 0.0,
            "cancel": 0.0,
            "message": 0.0,
            "override": 0.0,
            "comfort": 0.0,
        }
        substeps = max(1, round(self.config["decision_interval_s"] / self.config["dt_s"]))
        for _ in range(substeps):
            if self.time_s >= self.config["duration_s"] - 1e-9:
                break
            dt = min(self.config["dt_s"], self.config["duration_s"] - self.time_s)
            before = self._traffic_bodies()
            before_time = self.time_s
            self.disturbance.update(self.time_s, self.np_random)
            self._apply_disturbance()
            payloads_before = self._beacon_payloads()
            self._advance_vehicles(dt)
            self.time_s += dt
            payloads_after = self._beacon_payloads()

            def sample(
                at_s,
                before_time=before_time,
                payloads_before=payloads_before,
                payloads_after=payloads_after,
                dt=dt,
                pulse=self.braking_pulse,
            ):
                fraction = float(np.clip((at_s - before_time) / dt, 0, 1))
                payloads = {
                    peer: {
                        **payloads_before[peer],
                        "x_m": payloads_before[peer]["x_m"]
                        + payloads_before[peer]["speed_mps"] * fraction * dt
                        + 0.5
                        * (payloads_after[peer]["speed_mps"] - payloads_before[peer]["speed_mps"])
                        * fraction**2
                        * dt,
                        "speed_mps": payloads_before[peer]["speed_mps"]
                        + fraction
                        * (payloads_after[peer]["speed_mps"] - payloads_before[peer]["speed_mps"]),
                    }
                    for peer in PEERS
                }
                if pulse is not None:
                    x, speed = pulse.advance(
                        payloads_before[PEERS[0]]["x_m"],
                        payloads_before[PEERS[0]]["speed_mps"],
                        before_time,
                        fraction * dt,
                    )
                    payloads[PEERS[0]].update(
                        x_m=x, speed_mps=speed, accel_mps2=pulse.accel_at(at_s, speed)
                    )
                return payloads

            self.communication.advance(self.time_s, sample)
            self._update_revision()
            self.agreement.message_count = self.communication.counts()["sent"]

            feasibility = self._feasibility()
            self.agreement.feasible = feasibility.feasible
            self.agreement.feasibility_reason = feasibility.reason
            active = self.agreement.state in {
                AgreementState.ACCEPTED,
                AgreementState.EXECUTING,
                AgreementState.RENEGOTIATING,
            }
            persistent_invalid_dt = self._invalidity.observe(
                active and not feasibility.feasible, dt, self.config["invalidation_persistence_s"]
            )
            self.metrics.failed_agreement_duration_s = self._invalidity.total_s
            if not feasibility.feasible and self._invalid_since_s is None:
                self._invalid_since_s = self.time_s
            elif feasibility.feasible:
                self._invalid_since_s = None

            self.metrics.min_ttc_s = min(self.metrics.min_ttc_s, self.ttc_s)
            self.metrics.min_headway_s = min(self.metrics.min_headway_s, self.actual_headway_s)
            if self.ttc_s < self.config["min_ttc_s"]:
                self.metrics.near_collision = True
                components["near_collision"] -= 0.5 * dt
            components["failed_time"] -= 0.2 * persistent_invalid_dt

            after = self._traffic_bodies()
            if (
                self.ramp_y_m > 1e-6
                and self.ramp_x_m + self.config["vehicle_length_m"] / 2
                > self.config["ramp_end_m"] + 1e-8
            ):
                self.ramp_end_violation = True
                self.metrics.ramp_end_violation = True
                components["failed_time"] -= 100.0
                if self.agreement.state in {AgreementState.EXECUTING, AgreementState.RENEGOTIATING}:
                    self.agreement.transition(AgreementState.FAILED, self.time_s)
                break
            if any(
                swept_overlap(before[i], after[i], before[j], after[j])
                for i, j in combinations(range(len(before)), 2)
            ):
                self.collision = True
                self.metrics.collision = True
                components["collision"] -= 100.0
                break
            self._update_completion()
            if self.completed:
                self.metrics.completed_merge = True
                components["success"] += 20.0
                if self.agreement.state == AgreementState.EXECUTING:
                    self.agreement.transition(
                        AgreementState.FAILED if self.fallback_active else AgreementState.COMPLETED,
                        self.time_s,
                    )
                self.metrics.completion_mode = "fallback" if self.fallback_active else "agreement"
                if self.agreement.revision > 0 and not self.canceled and not self.fallback_active:
                    self.metrics.renegotiation_successes = 1
                break
            components["progress"] += 0.02 * dt
        if self.canceled and cancel_before is None:
            components["cancel"] -= 0.1
            self.metrics.cancel_requested_at_s = self.communication.session.requested_at_s
        components["message"] -= 0.01 * (self.communication.counts()["sent"] - sent_before)
        components["comfort"] -= 0.01 * abs(self.ramp_accel_mps2)
        return components

    def _apply_disturbance(self) -> None:
        # Physical profiles are integrated by _advance_vehicles/absolute trajectory.
        # Retained evaluator diagnostics are measured, never injected policy labels.
        expected = self._front_intent_origin_x_m + self._front_intent_speed_mps * self.time_s
        self._intent_position_error_m = self.front_x_m - expected
        self._intent_speed_error_mps = self.front_speed_mps - self._front_intent_speed_mps

    def _advance_vehicles(self, dt_s: float | None = None) -> None:
        dt = self.config["dt_s"] if dt_s is None else dt_s
        rear_accel = self._rear_following_accel(dt)
        follower_accel = (
            self._following_accel(self.follower_x_m, self.follower_speed_mps, dt)
            if self.follower_x_m is not None
            else 0.0
        )
        next_gap = self.fallback_active and self.config["fallback_next_gap"]
        target_speed = self.config["desired_speed_mps"]
        aligned = self._gap_alignment_speed() if next_gap else None
        if self.fallback_active:
            target_speed = 18.0 if aligned is None else aligned
        # Without next-gap fallback, a canceled ego may merge only if the same
        # physical pair remains safe. With it, the ego may use any bounded,
        # currently safe opening between mainline vehicles (perception fallback).
        # Otherwise it stays/returns to the ramp and stops at its end.
        remaining_lateral_s = self.ramp_y_m / (
            self.config["lane_width_m"] / self.config["lane_change_duration_s"]
        )
        entry_horizon_s = remaining_lateral_s + self.config["merge_stabilization_s"]
        safe_slot = (
            self._opening_safe_for(entry_horizon_s)
            if next_gap
            else self._slot_safe_for(entry_horizon_s)
        )
        # A canceled agreement no longer binds the ego to its planned *timing*, but the
        # fallback keeps the same nominal merge *location* (a lane change centered on
        # the merge point), so gap choice is the only advantage it can gain.
        fallback_entry_x = (
            self.config["merge_point_m"]
            - self.ramp_speed_mps * self.config["lane_change_duration_s"] / 2
        )
        planned_wait_s = (
            (fallback_entry_x - self.ramp_x_m) / max(self.ramp_speed_mps, 0.1)
            if next_gap
            else self.agreement.planned_merge_time_s
            - self.config["lane_change_duration_s"] / 2
            - self.time_s
        )
        wait_s = max(
            planned_wait_s,
            (self.config["merge_start_m"] - self.ramp_x_m) / max(self.ramp_speed_mps, 0.1),
            0.0,
        )
        expected_entry = (
            safe_slot
            and self.ramp_x_m + self.ramp_speed_mps * (wait_s + remaining_lateral_s)
            <= self.config["ramp_end_m"] - self.config["vehicle_length_m"] / 2
        )
        safety_speed_cap = float("inf")
        eligible = (
            self.ramp_x_m >= self.config["merge_start_m"]
            and self.revision_session.state != "pending"
            and (
                self.ramp_x_m >= fallback_entry_x - 1e-9
                if next_gap
                else self.time_s
                >= self.agreement.planned_merge_time_s - self.config["lane_change_duration_s"] / 2
            )
            and self.ramp_x_m + self.ramp_speed_mps * remaining_lateral_s
            <= self.config["ramp_end_m"] - self.config["vehicle_length_m"] / 2
        )
        if safe_slot and (self._lane_change_started or eligible):
            self._lane_change_started = True
            self.ramp_y_m = max(
                0.0,
                self.ramp_y_m
                - dt * self.config["lane_width_m"] / self.config["lane_change_duration_s"],
            )
        elif self.ramp_y_m > 0.0 and self._lane_change_started:
            self.low_level_interventions += 1
            remaining = (
                self.config["ramp_end_m"] - self.config["vehicle_length_m"] / 2 - self.ramp_x_m
            )
            stop_need = (
                self.ramp_speed_mps**2 / (2 * self.config["max_decel_mps2"])
                + dt * self.ramp_speed_mps
            )
            if remaining < stop_need:
                # Returning would violate the ramp boundary. Finish the physical
                # transition under perception fallback; this does not validate the agreement.
                self.fallback_active = True
                self.ramp_y_m = max(
                    0.0,
                    self.ramp_y_m
                    - dt * self.config["lane_width_m"] / self.config["lane_change_duration_s"],
                )
            else:
                self.ramp_y_m = min(
                    self.config["lane_width_m"],
                    self.ramp_y_m
                    + dt * self.config["lane_width_m"] / self.config["lane_change_duration_s"],
                )
            if np.isclose(self.ramp_y_m, self.config["lane_width_m"]):
                self._lane_change_started = False
        # Preserve an abort/stopping option while a locally detected adjacent car
        # may interfere. This uses current perception, not its future cut-in time.
        uncertain_adjacent_traffic = self._observed_intruder() is not None
        slowing_peer = self.front_speed_mps < self.config["desired_speed_mps"] - 0.05
        target = self._target_gap() if next_gap else None
        if target is not None:
            # After cancellation the named pair no longer matters: scope both triggers
            # to the gap actually targeted. An intruder already in the lane is one of
            # the gap's bounding vehicles and is handled by gap selection.
            (lead, lead_speed), (back, _) = target
            slowing_peer = lead_speed < self.config["desired_speed_mps"] - 0.05
            intruder = self._observed_intruder()
            margin = self.config["vehicle_length_m"]
            uncertain_adjacent_traffic = (
                intruder is not None
                and not lateral_overlap(
                    intruder, VehicleBody(intruder.x, 0.0, intruder.length, intruder.width)
                )
                and back.x - margin <= intruder.x <= lead.x + margin
            )
        if (
            self.ramp_y_m > 0.0
            and not self._lane_change_started
            and (not expected_entry or uncertain_adjacent_traffic or slowing_peer)
        ):
            stopping_distance = max(
                self.config["ramp_end_m"]
                - self.config["vehicle_length_m"] / 2
                - self.ramp_x_m
                - 1.0,
                0.0,
            )
            # Discrete-time stopping-speed bound including the upcoming reaction step.
            decel = self.config["max_decel_mps2"]
            stop_speed = max(
                0.0, np.sqrt((decel * dt) ** 2 + 2 * decel * stopping_distance) - decel * dt
            )
            # Even a fallback target below stop_speed may approach it too slowly
            # to preserve stopping distance. Enforce the next-step cap itself.
            safety_speed_cap = min(safety_speed_cap, stop_speed)
            if target_speed > stop_speed or self.ramp_speed_mps > stop_speed:
                self.low_level_interventions += 1
            target_speed = min(target_speed, stop_speed)
        if self._lane_change_started and self.ramp_y_m > 1e-6:
            # Eligibility assumed the current speed for the rest of the lateral move.
            # Never accelerate past what still lets that move finish on the ramp.
            rate = self.config["lane_width_m"] / self.config["lane_change_duration_s"]
            usable = (
                self.config["ramp_end_m"] - self.config["vehicle_length_m"] / 2 - self.ramp_x_m
            )
            finish_cap = max(0.0, usable) / (self.ramp_y_m / rate + dt)
            if finish_cap < max(target_speed, self.ramp_speed_mps):
                self.low_level_interventions += 1
            safety_speed_cap = min(safety_speed_cap, max(finish_cap, 0.0))
            target_speed = min(target_speed, finish_cap)
        ego = self._bodies()[0]
        for front, front_speed in zip(
            self._traffic_bodies()[1:], self._traffic_speeds()[1:], strict=True
        ):
            if front.x <= ego.x or not lateral_overlap(ego, front):
                continue
            front_bound = np.sqrt(
                max(
                    0.0,
                    front_speed**2
                    + 2
                    * self.config["max_decel_mps2"]
                    * (
                        bumper_clearance(ego, front)
                        - max(
                            self.config["min_gap_m"],
                            self.config["min_headway_s"] * self.ramp_speed_mps,
                        )
                    ),
                )
            )
            if target_speed > front_bound:
                target_speed = front_bound
                safety_speed_cap = min(safety_speed_cap, front_bound)
                self.low_level_interventions += 1
        # Gap tracking needs a stiffer speed loop than cruising, or the ego lags the
        # moving gap and loses it; acceleration limits are unchanged.
        tracking_gain = 1.5 if next_gap and aligned is not None else 0.5
        desired_accel = np.clip(
            min(
                (target_speed - self.ramp_speed_mps) * tracking_gain,
                (safety_speed_cap - self.ramp_speed_mps) / dt,
            ),
            -self.config["max_decel_mps2"],
            self.config["max_accel_mps2"],
        )
        self.ramp_accel_mps2 = float(desired_accel)
        jerk = (self.ramp_accel_mps2 - self._last_accel) / dt
        self.metrics.peak_abs_jerk_mps3 = max(self.metrics.peak_abs_jerk_mps3, abs(jerk))
        self.metrics.peak_abs_accel_mps2 = max(
            self.metrics.peak_abs_accel_mps2, abs(self.ramp_accel_mps2)
        )
        self._last_accel = self.ramp_accel_mps2
        self.ramp_speed_mps = max(0.0, self.ramp_speed_mps + self.ramp_accel_mps2 * dt)
        self.ramp_x_m += self.ramp_speed_mps * dt
        if self.braking_pulse is None:
            self.front_x_m += self.front_speed_mps * dt
        else:
            self.front_x_m, self.front_speed_mps = self.braking_pulse.advance(
                self.front_x_m, self.front_speed_mps, self.time_s, dt
            )
        rear_before = self.rear_speed_mps
        self.rear_speed_mps = max(0.0, rear_before + rear_accel * dt)
        self.rear_x_m += (rear_before + self.rear_speed_mps) * dt / 2
        if self.follower_x_m is not None:
            follower_before = self.follower_speed_mps
            self.follower_speed_mps = max(0.0, follower_before + follower_accel * dt)
            self.follower_x_m += (follower_before + self.follower_speed_mps) * dt / 2

    def _observation(self) -> np.ndarray:
        return encode(self._manager_values())

    def _beacon_payloads(self) -> dict[str, dict]:
        return {
            PEERS[0]: {
                "x_m": self.front_x_m,
                "speed_mps": self.front_speed_mps,
                # Honest current longitudinal acceleration, as in cooperative awareness messages.
                "accel_mps2": (
                    self.braking_pulse.accel_at(self.time_s, self.front_speed_mps)
                    if self.braking_pulse is not None
                    else 0.0
                ),
                "intent_origin_x_m": self._front_intent_origin_x_m,
                "intent_speed_mps": self._front_intent_speed_mps,
                "intent_at_s": 0.0,
            },
            PEERS[1]: {"x_m": self.rear_x_m, "speed_mps": self.rear_speed_mps},
        }

    def _manager_values(self) -> dict:
        ages = self.communication.ages(self.time_s)
        cache = self.communication.cache
        # Constant-speed extrapolation uses ONLY last delivered payload + its age.
        # Do not use simulator neighbor motion to correct the received estimate.
        estimated = {}
        for peer in PEERS:
            message = cache.get(peer)
            estimated[peer] = (
                (
                    message.payload["x_m"] + message.payload["speed_mps"] * ages[peer],
                    message.payload["speed_mps"],
                )
                if message
                else (self.ramp_x_m, 0.0)
            )
        front_x, front_speed = estimated[PEERS[0]]
        rear_x, rear_speed = estimated[PEERS[1]]
        length = self.config["vehicle_length_m"]
        width = self.config["vehicle_width_m"]
        ego = VehicleBody(self.ramp_x_m, 0.0, length, width)
        front = VehicleBody(front_x, 0.0, length, width)
        rear = VehicleBody(rear_x, 0.0, length, width)
        front_clearance = bumper_clearance(ego, front)
        rear_clearance = bumper_clearance(rear, ego)
        ttc = min(
            longitudinal_ttc(ego, self.ramp_speed_mps, front, front_speed),
            longitudinal_ttc(rear, rear_speed, ego, self.ramp_speed_mps),
        )
        headway = min(
            max(front_clearance, 0.0) / max(self.ramp_speed_mps, 0.1),
            max(rear_clearance, 0.0) / max(rear_speed, 0.1),
        )
        session = self.communication.session
        intruder = self._observed_intruder()
        follower = self._observed_follower()
        front_message = cache.get(PEERS[0])
        intent = front_message.payload if front_message else {}
        has_intent = all(
            k in intent for k in ("intent_origin_x_m", "intent_speed_mps", "intent_at_s")
        )
        values = {
            "ego_speed_mps": self.ramp_speed_mps,
            "ego_accel_mps2": self.ramp_accel_mps2,
            "ego_lateral_m": self.ramp_y_m,
            "distance_to_merge_m": self.distance_to_merge_m,
            "distance_to_ramp_end_m": self.config["ramp_end_m"] - self.ramp_x_m,
            "front_speed_mps": front_speed,
            "rear_speed_mps": rear_speed,
            "front_relative_m": front_x - self.ramp_x_m,
            "rear_relative_m": self.ramp_x_m - rear_x,
            "front_clearance_m": front_clearance,
            "rear_clearance_m": rear_clearance,
            "gap_m": front_x - rear_x - length,
            "ttc_s": min(ttc, 20.0),
            "ttc_finite": float(np.isfinite(ttc)),
            "headway_s": headway,
            "message_age_s": max(ages.values()),
            "front_message_age_s": ages[PEERS[0]],
            "rear_message_age_s": ages[PEERS[1]],
            "front_received": float(PEERS[0] in cache),
            "rear_received": float(PEERS[1] in cache),
            "remaining_plan_s": self.agreement.planned_merge_time_s - self.time_s,
            "agreement_age_s": self.time_s - self.agreement.accepted_at_s,
            "revision": self.agreement.revision,
            "renegotiation_count": self.agreement.renegotiation_count,
            "prior_action": float(self.agreement.last_applied_action),
            "merge_order": self.agreement.merge_order,
            "target_gap_id": self.agreement.target_gap_id,
            "cancel_pending": float(session.state == "cancel_pending"),
            "cancel_confirmed": float(session.state == "cancel_confirmed"),
            "cancel_timed_out": float(session.state == "timed_out"),
            "cancel_ack_count": len(session.acknowledged),
            "alternative_gap_feasible": 0.0,
            "local_canceled": float(self.canceled),
            "time_s": self.time_s,
            "local_agreement_state": list(AgreementState).index(self.agreement.state),
            "intruder_detected": float(intruder is not None),
            "intruder_relative_m": intruder.x - self.ramp_x_m if intruder else 0.0,
            "intruder_speed_mps": self.cut_in_trajectory.speed_mps if intruder else 0.0,
            "intruder_lateral_m": intruder.y if intruder else 0.0,
            "intruder_lateral_speed_mps": self._observed_intruder_lateral_speed(),
            "front_accel_mps2": (
                front_message.payload.get("accel_mps2", 0.0) if front_message else 0.0
            ),
            "follower_detected": float(follower is not None),
            "follower_relative_m": self.ramp_x_m - follower.x if follower else 0.0,
            "follower_speed_mps": self.follower_speed_mps if follower else 0.0,
            "slot_occupied": float(self._slot_occupied(intruder, rear_x, front_x)),
            "front_intent_received": float(has_intent),
            "front_intent_position_error_m": (
                intent["x_m"]
                - intent["intent_origin_x_m"]
                - intent["intent_speed_mps"] * (front_message.sent_at_s - intent["intent_at_s"])
                if has_intent
                else 0.0
            ),
            "front_intent_speed_error_mps": (
                intent["speed_mps"] - intent["intent_speed_mps"] if has_intent else 0.0
            ),
            "front_intent_age_s": self.time_s - intent["intent_at_s"] if has_intent else 0.0,
            "keep_status": 0.0,
            "keep_completion_s": 0.0,
            "fallback_status": 0.0,
            "fallback_completion_s": 0.0,
            "advance_feasible": 0.0,
            "advance_completion_s": 0.0,
            "delay_feasible": 0.0,
            "delay_completion_s": 0.0,
            "proposal_pending": float(self.revision_session.state == "pending"),
        }
        if not self.config.get("_prediction_replica", False):
            from rene.agreements.candidates import timing_candidates
            from rene.prediction.rollouts import STATUS_CODES, predict

            snapshot = decode(encode(values))
            # Predictions see exactly the same clipping/float32 precision as PPO.
            key = tuple(snapshot.values())
            if self._assessment_cache is None or self._assessment_cache[0] != key:
                keep = predict(snapshot, self.config)
                fallback = predict(snapshot, self.config, fallback=True)
                candidates = timing_candidates(snapshot, self.config)
                fields = {
                    "keep_status": STATUS_CODES[keep.status],
                    "keep_completion_s": keep.completion_s or 0,
                    "fallback_status": STATUS_CODES[fallback.status],
                    "fallback_completion_s": fallback.completion_s or 0,
                }
                for candidate in candidates:
                    prefix = "advance" if candidate.delta_s < 0 else "delay"
                    fields[f"{prefix}_feasible"] = 1.0
                    fields[f"{prefix}_completion_s"] = candidate.prediction.completion_s
                self._assessment_cache = (key, fields)
            values.update(self._assessment_cache[1])
        return values

    def _info(self) -> dict[str, Any]:
        values = decode(self._observation())
        estimated = evaluate_feasibility(
            gap_m=min(values["front_clearance_m"], values["rear_clearance_m"]),
            ttc_s=values["ttc_s"],
            headway_s=values["headway_s"],
            distance_to_merge_m=values["distance_to_ramp_end_m"],
            speed_mps=values["ego_speed_mps"],
            min_gap_m=self.config["min_gap_m"],
            min_ttc_s=self.config["min_ttc_s"],
            min_headway_s=self.config["min_headway_s"],
        )
        if values["slot_occupied"] > 0.5:
            estimated = FeasibilityResult(False, "target_slot_occupied")
        return {
            "episode_id": self._episode_id,
            "time_s": self.time_s,
            "manager_inputs": values,
            "input_version": INPUT_VERSION,
            "physics_version": "step3c6-timing-execution-v1",
            "agreement_state": self.agreement.state.value,
            "agreement_feasible": estimated.feasible,  # Received-data estimate, not truth.
            "feasibility_reason": estimated.reason,
            "cancel_protocol_state": self.communication.session.state,
        }

    def _finalize_metrics(self) -> None:
        counts = self.communication.counts()
        self.metrics.message_count = counts["sent"]
        self.metrics.messages_delivered = counts["delivered"]
        self.metrics.messages_dropped = counts["dropped"]
        self.metrics.messages_in_flight = counts["sent"] - counts["delivered"] - counts["dropped"]
        self.metrics.cancel_protocol_state = self.communication.session.state
        self.metrics.beacons_sent = self.communication.bus.kind_counts[("sent", "beacon")]
        self.metrics.control_messages_sent = self.metrics.message_count - self.metrics.beacons_sent
        session = self.communication.session
        self.metrics.cancel_requested_at_s = session.requested_at_s
        self.metrics.cancel_confirmed_at_s = session.confirmed_at_s
        self.metrics.cancel_timed_out_at_s = session.timed_out_at_s
        self.communication.bus.log("episode_terminal", self.time_s, protocol_state=session.state)
        self.metrics.merge_completion_time_s = self.time_s if self.completed else 0.0
        self.metrics.failed_agreement_duration_s = self._invalidity.total_s
        # No end-of-episode feasibility proxy: a decision-time counterfactual is required.

    def render(self) -> np.ndarray | None:
        if self.render_mode != "rgb_array":
            return None
        width = int(self.config["render_width"])
        height = int(self.config["render_height"])
        image = np.full((height, width, 3), 245, dtype=np.uint8)
        # World-coordinate view: all vehicles share the same road/lane geometry.
        # Follow the ego with an isotropic meters-to-pixels scale. This preserves
        # body proportions rather than stretching car widths across the lanes.
        x_min = self.ramp_x_m - 60.0
        x_max = self.ramp_x_m + 60.0
        x_scale = width / (x_max - x_min)
        y_scale = x_scale
        # Leave a clear caption band above the added adjacent freeway lane.
        main_y = height / 2 + 24

        def road_y(y_m: float) -> int:
            return int(main_y + y_m * y_scale)

        half_lane = self.config["lane_width_m"] / 2
        image[road_y(-half_lane) : road_y(half_lane), :, :] = (70, 70, 75)
        if self.cut_in_trajectory is not None:
            image[road_y(-3 * half_lane) : road_y(-half_lane), :, :] = (70, 70, 75)
            image[road_y(-half_lane) - 1 : road_y(-half_lane) + 1, :, :] = 220
        ramp_end = int(np.clip((self.config["ramp_end_m"] - x_min) * x_scale, 0, width))
        image[road_y(half_lane) : road_y(3 * half_lane), :ramp_end, :] = (85, 85, 90)
        boundary_y = road_y(half_lane)
        merge_start = int(np.clip((self.config["merge_start_m"] - x_min) * x_scale, 0, width))
        image[boundary_y - 1 : boundary_y + 1, :merge_start, :] = 220
        for x in range(merge_start, min(ramp_end, width), 20):
            image[boundary_y - 1 : boundary_y + 1, x : x + 10, :] = 220

        def vehicle(body: VehicleBody, color: tuple[int, int, int]) -> None:
            left = max(0, int((body.x - body.length / 2 - x_min) * x_scale))
            right = min(width, int((body.x + body.length / 2 - x_min) * x_scale))
            top = max(0, road_y(body.y - body.width / 2))
            bottom = min(height, road_y(body.y + body.width / 2))
            if right > left:
                image[top:bottom, left:right, :] = color

        ego, front, rear = self._bodies()
        vehicle(front, (40, 120, 220))
        vehicle(rear, (40, 120, 220))
        if self.follower_x_m is not None:
            vehicle(self._follower_body(), (120, 120, 130))
        vehicle(ego, (220, 90, 40))
        if self.cut_in_trajectory is not None:
            vehicle(self.cut_in_trajectory.body_at(self.time_s), (160, 70, 190))
        return image

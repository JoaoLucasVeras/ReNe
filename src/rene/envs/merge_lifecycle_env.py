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
from rene.agreements.feasibility import evaluate_feasibility
from rene.agreements.protocol import create_accepted_agreement
from rene.agreements.state import AgreementState, ManagerAction
from rene.disturbances.base import DisturbanceState
from rene.envs.geometry import (
    VehicleBody,
    bumper_clearance,
    lateral_overlap,
    longitudinal_ttc,
    swept_overlap,
)
from rene.envs.manager_inputs import FEATURES, INPUT_VERSION, decode, encode
from rene.metrics.episode_metrics import EpisodeMetrics
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
    "merge_start_m": 140.0,
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
    "render_width": 800,
    "render_height": 240,
    "disturbance_type": "cut_in",
    "disturbance_trigger_s": 5.0,
    "disturbance_severity": "moderate",
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
        ):
            if not np.isfinite(self.config[key]) or self.config[key] <= 0:
                raise ValueError(f"{key} must be finite and positive")
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
        self.rear_x_m = self.ramp_x_m - center_span / 2
        self.rear_speed_mps = self.ramp_speed_mps
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
        self._invalid_since_s = None
        self._last_accel = 0.0
        self._intent_position_error_m = 0.0
        self._intent_speed_error_mps = 0.0
        self._intent_inconsistency_count = 0
        self._decision_log = []

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

    @property
    def rear_clearance_m(self) -> float:
        ego, _, rear = self._bodies()
        return bumper_clearance(rear, ego)

    @property
    def distance_to_merge_m(self) -> float:
        return self.config["merge_point_m"] - self.ramp_x_m

    @property
    def ttc_s(self) -> float:
        bodies = self._bodies()
        speeds = (self.ramp_speed_mps, self.front_speed_mps, self.rear_speed_mps)
        return min(
            longitudinal_ttc(bodies[i], speeds[i], bodies[j], speeds[j])
            for i, j in combinations(range(3), 2)
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
        bodies = self._bodies()
        speeds = (self.ramp_speed_mps, self.front_speed_mps, self.rear_speed_mps)
        values = []
        for i, j in combinations(range(3), 2):
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
        valid = abs(self.ramp_y_m) < 1e-9 and self._slot_safe_for(0.0)
        if not valid:
            self._stable_since_s = None
            return
        if self._stable_since_s is None:
            self._stable_since_s = self.time_s
        if self.time_s - self._stable_since_s + 1e-9 >= self.config["merge_stabilization_s"]:
            self.completed = True
            self.physical_merge_time_s = self.time_s

    def _feasibility(self):
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
        # All revisions await a physical acceptance executor in Step 3C.
        return action.family != "renegotiate"

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

        self._apply_lifecycle_action(applied)
        reward_components = self._simulate_interval()
        reward = float(sum(reward_components.values()))
        self.metrics.total_reward += reward

        terminated = self.completed or self.collision
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
            if self.agreement.state in {AgreementState.ACCEPTED, AgreementState.EXECUTING}:
                self.agreement.transition(AgreementState.CANCELED, self.time_s)
            self.canceled = True
            self.fallback_active = True
            self.metrics.canceled = True
            self.communication.session.request(self.time_s)
            self.communication.advance(self.time_s, lambda at: self._beacon_payloads())
            return
        if action.family != "renegotiate":
            return
        self.agreement.revise(action, self.time_s)
        if action == ManagerAction.RENEGOTIATE_DELAY:
            self.agreement.planned_merge_time_s += 1.0
        elif action == ManagerAction.RENEGOTIATE_ADVANCE:
            self.agreement.planned_merge_time_s = max(
                self.agreement.planned_merge_time_s - 1.0, self.time_s + 0.5
            )
        self.agreement.transition(AgreementState.EXECUTING, self.time_s)
        self.metrics.renegotiation_attempts += 1

    def _simulate_interval(self) -> dict[str, float]:
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
            before = self._bodies()
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
            ):
                fraction = float(np.clip((at_s - before_time) / dt, 0, 1))
                return {
                    peer: {
                        "x_m": payloads_before[peer]["x_m"]
                        + fraction * (payloads_after[peer]["x_m"] - payloads_before[peer]["x_m"]),
                        "speed_mps": payloads_before[peer]["speed_mps"],
                    }
                    for peer in PEERS
                }

            self.communication.advance(self.time_s, sample)
            self.agreement.message_count = self.communication.counts()["sent"]

            feasibility = self._feasibility()
            self.agreement.feasible = feasibility.feasible
            self.agreement.feasibility_reason = feasibility.reason
            if not feasibility.feasible and self._invalid_since_s is None:
                self._invalid_since_s = self.time_s
            elif feasibility.feasible:
                self._invalid_since_s = None

            self.metrics.min_ttc_s = min(self.metrics.min_ttc_s, self.ttc_s)
            self.metrics.min_headway_s = min(self.metrics.min_headway_s, self.actual_headway_s)
            if self.ttc_s < self.config["min_ttc_s"]:
                self.metrics.near_collision = True
                components["near_collision"] -= 0.5 * dt
            if self._invalid_since_s is not None:
                invalid_duration = self.time_s - self._invalid_since_s
                if invalid_duration >= self.config["invalidation_persistence_s"]:
                    components["failed_time"] -= 0.2 * dt

            after = self._bodies()
            if any(
                swept_overlap(before[i], after[i], before[j], after[j])
                for i, j in combinations(range(3), 2)
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
                    self.agreement.transition(AgreementState.COMPLETED, self.time_s)
                if self.agreement.revision > 0:
                    self.metrics.renegotiation_successes = 1
                break
            components["progress"] += 0.02 * dt
        if self.canceled:
            components["cancel"] -= 0.1
        components["message"] -= 0.01 * self.agreement.message_count
        components["comfort"] -= 0.01 * abs(self.ramp_accel_mps2)
        return components

    def _apply_disturbance(self) -> None:
        if not self.disturbance.triggered:
            return
        scale = self.disturbance.severity_scale
        kind = self.disturbance.disturbance_type
        if kind == "cut_in":
            # Legacy diagnostic only: does not change physical geometry. Step 3C
            # must replace this with an actual vehicle; do not evaluate it as a cut-in.
            self.synthetic_gap_bonus_m = min(self.synthetic_gap_bonus_m, -20.0 * scale)
        elif kind == "braking":
            self.front_speed_mps = max(8.0, 24.0 - 6.0 * scale)
        elif kind == "intent_mismatch":
            self._intent_position_error_m = 6.0 * scale
            self._intent_speed_error_mps = 3.0 * scale
            self._intent_inconsistency_count += 1

    def _advance_vehicles(self, dt_s: float | None = None) -> None:
        dt = self.config["dt_s"] if dt_s is None else dt_s
        target_speed = 18.0 if self.fallback_active else self.config["desired_speed_mps"]
        # A canceled ego may merge under fallback only if the same physical pair
        # remains safe. Otherwise it stays/returns to the ramp and stops at its end.
        remaining_lateral_s = self.ramp_y_m / (
            self.config["lane_width_m"] / self.config["lane_change_duration_s"]
        )
        safe_slot = self._slot_safe_for(remaining_lateral_s + self.config["merge_stabilization_s"])
        wait_s = max(
            self.agreement.planned_merge_time_s
            - self.config["lane_change_duration_s"] / 2
            - self.time_s,
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
            and self.time_s
            >= self.agreement.planned_merge_time_s - self.config["lane_change_duration_s"] / 2
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
            self.ramp_y_m = min(
                self.config["lane_width_m"],
                self.ramp_y_m
                + dt * self.config["lane_width_m"] / self.config["lane_change_duration_s"],
            )
            if np.isclose(self.ramp_y_m, self.config["lane_width_m"]):
                self._lane_change_started = False
        if self.ramp_y_m > 0.0 and not self._lane_change_started and not expected_entry:
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
            if target_speed > stop_speed:
                target_speed = stop_speed
                safety_speed_cap = stop_speed
                self.low_level_interventions += 1
        ego, front, _ = self._bodies()
        if lateral_overlap(ego, front):
            front_bound = np.sqrt(
                self.front_speed_mps**2
                + 2
                * self.config["max_decel_mps2"]
                * max(self.front_clearance_m - self.config["min_gap_m"], 0.0)
            )
            if target_speed > front_bound:
                target_speed = front_bound
                safety_speed_cap = min(safety_speed_cap, front_bound)
                self.low_level_interventions += 1
        desired_accel = np.clip(
            min(
                (target_speed - self.ramp_speed_mps) * 0.5,
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
        self.front_x_m += self.front_speed_mps * dt
        self.rear_x_m += self.rear_speed_mps * dt

    def _observation(self) -> np.ndarray:
        return encode(self._manager_values())

    def _beacon_payloads(self) -> dict[str, dict]:
        return {
            PEERS[0]: {"x_m": self.front_x_m, "speed_mps": self.front_speed_mps},
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
        return {
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
        }

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
        return {
            "episode_id": self._episode_id,
            "time_s": self.time_s,
            "manager_inputs": values,
            "input_version": INPUT_VERSION,
            "physics_version": "step3a-axis-aligned-v1",
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
        if self._invalid_since_s is not None:
            self.metrics.failed_agreement_duration_s = max(0.0, self.time_s - self._invalid_since_s)
        self.metrics.unnecessary_cancellation = bool(self.canceled and self._feasibility().feasible)

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
        main_y = height / 2

        def road_y(y_m: float) -> int:
            return int(main_y + y_m * y_scale)

        half_lane = self.config["lane_width_m"] / 2
        image[road_y(-half_lane) : road_y(half_lane), :, :] = (70, 70, 75)
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
        vehicle(ego, (220, 90, 40))
        return image

"""Seeded post-acceptance cooperative-merge lifecycle environment.

This lightweight environment models lifecycle decisions rather than low-level
driving. It follows the Gymnasium API and is intended for rapid research runs.
HighwayEnv remains the visual/reference simulator and can be used for later
cross-validation.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from rene.agreements.feasibility import evaluate_feasibility
from rene.agreements.protocol import create_accepted_agreement
from rene.agreements.state import AgreementState, ManagerAction
from rene.disturbances.base import DisturbanceState
from rene.metrics.episode_metrics import EpisodeMetrics
from rene.safety.shield import ShieldDecision, apply_shield

DEFAULT_CONFIG: dict[str, Any] = {
    "duration_s": 20.0,
    "dt_s": 0.2,
    "decision_interval_s": 1.0,
    "merge_point_m": 200.0,
    "ramp_end_m": 240.0,
    "desired_speed_mps": 25.0,
    "initial_gap_m": 30.0,
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
    "traffic_density": "medium",
}


class MergeLifecycleEnv(gym.Env[np.ndarray, int]):
    """A compact high-level agreement lifecycle environment."""

    metadata = {"render_modes": ["rgb_array"], "render_fps": 5}

    def __init__(self, config: dict[str, Any] | None = None, render_mode: str | None = None):
        super().__init__()
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.render_mode = render_mode
        if render_mode not in {None, "rgb_array"}:
            raise ValueError("supported render modes are None and 'rgb_array'")
        self.action_space = spaces.Discrete(len(ManagerAction))
        self.observation_space = spaces.Box(-1.0, 1.0, shape=(22,), dtype=np.float32)
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
        density_gap = {"low": 38.0, "medium": 30.0, "high": 22.0}.get(density, 30.0)
        initial_gap = float(options.get("initial_gap_m", density_gap))
        jitter = float(self.np_random.uniform(-1.0, 1.0))

        self.time_s = 0.0
        self.ramp_x_m = 20.0 + jitter
        self.ramp_speed_mps = 22.0
        self.ramp_accel_mps2 = 0.0
        self.front_x_m = self.config["merge_point_m"] + initial_gap / 2
        self.front_speed_mps = 24.0
        self.rear_x_m = self.config["merge_point_m"] - initial_gap / 2
        self.rear_speed_mps = 23.0
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
            delay_ms=int(
                options.get("communication_delay_ms", self.config["communication_delay_ms"])
            ),
            packet_loss=float(options.get("packet_loss", self.config["packet_loss"])),
        )
        planned_time = (self.config["merge_point_m"] - self.ramp_x_m) / self.ramp_speed_mps
        self.agreement = create_accepted_agreement(
            self._episode_id, planned_merge_time_s=float(planned_time)
        )
        self.agreement.transition(AgreementState.EXECUTING, self.time_s)
        self.metrics = EpisodeMetrics(episode_id=self._episode_id, seed=self._episode_seed)
        observation = self._observation()
        return observation, self._info()

    @property
    def gap_m(self) -> float:
        return max(self.front_x_m - self.rear_x_m + self.synthetic_gap_bonus_m, 0.0)

    @property
    def distance_to_merge_m(self) -> float:
        return self.config["merge_point_m"] - self.ramp_x_m

    @property
    def ttc_s(self) -> float:
        ramp_eta = max(self.distance_to_merge_m, 0.0) / max(self.ramp_speed_mps, 0.1)

        def temporal_separation(vehicle_x: float, vehicle_speed: float) -> float:
            if vehicle_x >= self.config["merge_point_m"]:
                return 99.0
            vehicle_eta = (self.config["merge_point_m"] - vehicle_x) / max(vehicle_speed, 0.1)
            return abs(ramp_eta - vehicle_eta)

        return min(
            temporal_separation(self.front_x_m, self.front_speed_mps),
            temporal_separation(self.rear_x_m, self.rear_speed_mps),
            99.0,
        )

    @property
    def headway_s(self) -> float:
        return min(self.gap_m / max(self.rear_speed_mps, 0.1), 99.0)

    def _feasibility(self):
        return evaluate_feasibility(
            gap_m=self.gap_m,
            ttc_s=self.ttc_s,
            headway_s=self.headway_s,
            distance_to_merge_m=self.distance_to_merge_m,
            speed_mps=self.ramp_speed_mps,
            min_gap_m=self.config["min_gap_m"],
            min_ttc_s=self.config["min_ttc_s"],
            min_headway_s=self.config["min_headway_s"],
        )

    def _renegotiation_feasible(self, action: ManagerAction) -> bool:
        if self.agreement.renegotiation_count >= self.config["max_renegotiations"]:
            return False
        if action == ManagerAction.RENEGOTIATE_NEXT_GAP:
            return self.distance_to_merge_m > 25.0
        if action == ManagerAction.RENEGOTIATE_DELAY:
            return self.distance_to_merge_m > 15.0
        if action == ManagerAction.RENEGOTIATE_ADVANCE:
            return self.gap_m >= self.config["min_gap_m"] * 0.9
        if action == ManagerAction.RENEGOTIATE_SWAP_ORDER:
            return self.distance_to_merge_m > 20.0 and self.ttc_s > 1.0
        return True

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        requested = ManagerAction(int(action))
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
        truncated = self.time_s >= self.config["duration_s"] and not terminated
        if truncated and self.agreement.state not in {
            AgreementState.CANCELED,
            AgreementState.COMPLETED,
        }:
            self.agreement.transition(AgreementState.FAILED, self.time_s)

        self._decision_log.append(
            {
                "time_s": self.time_s,
                "requested_action": requested.name,
                "applied_action": applied.name,
                "overridden": shield.overridden,
                "override_reason": shield.reason,
                "feasible": feasibility.feasible,
                "feasibility_reason": feasibility.reason,
                "gap_m": self.gap_m,
                "ttc_s": self.ttc_s,
                "message_age_s": self.disturbance.message_age_s,
                **{f"reward_{k}": v for k, v in reward_components.items()},
            }
        )
        info = self._info()
        if terminated or truncated:
            self._finalize_metrics()
            info["episode_metrics"] = self.metrics.as_dict()
            info["decision_log"] = list(self._decision_log)
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
            self.agreement.message_count += 1
            return
        if action.family != "renegotiate":
            return
        self.agreement.revise(action, self.time_s)
        if action == ManagerAction.RENEGOTIATE_DELAY:
            self.agreement.planned_merge_time_s += 1.0
            self.ramp_speed_mps = max(self.ramp_speed_mps - 1.0, 12.0)
        elif action == ManagerAction.RENEGOTIATE_ADVANCE:
            self.agreement.planned_merge_time_s = max(
                self.agreement.planned_merge_time_s - 1.0, self.time_s + 0.5
            )
            self.ramp_speed_mps = min(self.ramp_speed_mps + 1.0, 30.0)
        elif action == ManagerAction.RENEGOTIATE_NEXT_GAP:
            self.agreement.target_gap_id += 1
            self.synthetic_gap_bonus_m += 10.0
        elif action == ManagerAction.RENEGOTIATE_SWAP_ORDER:
            self.agreement.merge_order = 1 - self.agreement.merge_order
            self.synthetic_gap_bonus_m += 6.0
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
            self.disturbance.update(self.time_s, self.np_random)
            self._apply_disturbance()
            self._advance_vehicles()
            self.time_s += self.config["dt_s"]

            feasibility = self._feasibility()
            self.agreement.feasible = feasibility.feasible
            self.agreement.feasibility_reason = feasibility.reason
            if not feasibility.feasible and self._invalid_since_s is None:
                self._invalid_since_s = self.time_s
            elif feasibility.feasible:
                self._invalid_since_s = None

            self.metrics.min_ttc_s = min(self.metrics.min_ttc_s, self.ttc_s)
            self.metrics.min_headway_s = min(self.metrics.min_headway_s, self.headway_s)
            if self.ttc_s < self.config["min_ttc_s"]:
                self.metrics.near_collision = True
                components["near_collision"] -= 0.5 * self.config["dt_s"]
            if self._invalid_since_s is not None:
                invalid_duration = self.time_s - self._invalid_since_s
                if invalid_duration >= self.config["invalidation_persistence_s"]:
                    components["failed_time"] -= 0.2 * self.config["dt_s"]

            if self.gap_m < 2.0 and abs(self.ramp_x_m - self.config["merge_point_m"]) < 10:
                self.collision = True
                self.metrics.collision = True
                components["collision"] -= 100.0
                break
            if self.ramp_x_m >= self.config["merge_point_m"]:
                self.completed = True
                self.metrics.completed_merge = True
                components["success"] += 20.0
                if self.agreement.state == AgreementState.EXECUTING:
                    self.agreement.transition(AgreementState.COMPLETED, self.time_s)
                if self.agreement.revision > 0:
                    self.metrics.renegotiation_successes = 1
                break
            components["progress"] += 0.02 * self.config["dt_s"]
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
            self.synthetic_gap_bonus_m = min(self.synthetic_gap_bonus_m, -20.0 * scale)
        elif kind == "braking":
            self.front_speed_mps = max(8.0, 24.0 - 6.0 * scale)
        elif kind == "intent_mismatch":
            self._intent_position_error_m = 6.0 * scale
            self._intent_speed_error_mps = 3.0 * scale
            self._intent_inconsistency_count += 1

    def _advance_vehicles(self) -> None:
        dt = self.config["dt_s"]
        target_speed = 18.0 if self.fallback_active else self.config["desired_speed_mps"]
        desired_accel = np.clip(
            (target_speed - self.ramp_speed_mps) * 0.5,
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
        prior = float(self.agreement.last_applied_action) / max(len(ManagerAction) - 1, 1)
        raw = np.array(
            [
                self.ramp_speed_mps / 40.0,
                self.ramp_accel_mps2 / 5.0,
                self.front_speed_mps / 40.0,
                self.rear_speed_mps / 40.0,
                (self.front_x_m - self.ramp_x_m) / 200.0,
                (self.ramp_x_m - self.rear_x_m) / 200.0,
                self.gap_m / 60.0,
                self.distance_to_merge_m / 250.0,
                self.ttc_s / 20.0,
                self.headway_s / 5.0,
                self.agreement.merge_order,
                self.agreement.target_gap_id / 5.0,
                (self.agreement.planned_merge_time_s - self.time_s) / 20.0,
                (self.time_s - self.agreement.accepted_at_s) / 20.0,
                np.clip(self.ramp_x_m / self.config["merge_point_m"], 0.0, 1.0),
                self.agreement.revision / 3.0,
                prior,
                self.disturbance.message_age_s / 2.0,
                self.disturbance.packet_loss,
                self._intent_position_error_m / 20.0,
                self._intent_speed_error_mps / 10.0,
                self._intent_inconsistency_count / 10.0,
            ],
            dtype=np.float32,
        )
        return np.clip(raw * 2.0 - 1.0, -1.0, 1.0).astype(np.float32)

    def _info(self) -> dict[str, Any]:
        return {
            "episode_id": self._episode_id,
            "time_s": self.time_s,
            "gap_m": self.gap_m,
            "ttc_s": self.ttc_s,
            "headway_s": self.headway_s,
            "message_age_s": self.disturbance.message_age_s,
            "agreement_state": self.agreement.state.value,
            "agreement_feasible": self.agreement.feasible,
            "feasibility_reason": self.agreement.feasibility_reason,
            "renegotiation_count": self.agreement.renegotiation_count,
            "alternative_gap_feasible": self.distance_to_merge_m > 25.0,
            "disturbance": asdict(self.disturbance),
        }

    def _finalize_metrics(self) -> None:
        self.metrics.message_count = self.agreement.message_count
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
        image[80:150, :, :] = np.array([70, 70, 75], dtype=np.uint8)
        image[155:160, : int(width * 0.78), :] = 120
        image[160:220, : int(width * 0.78), :] = np.array([85, 85, 90], dtype=np.uint8)
        scale = width / max(self.config["ramp_end_m"] + 80.0, 1.0)

        def vehicle(x_m: float, y: int, color: tuple[int, int, int]) -> None:
            x = int(np.clip(x_m * scale, 0, width - 22))
            image[y : y + 14, x : x + 22, :] = color

        vehicle(self.front_x_m, 96, (40, 120, 220))
        vehicle(self.rear_x_m, 118, (40, 120, 220))
        vehicle(self.ramp_x_m, 180, (220, 90, 40))
        return image

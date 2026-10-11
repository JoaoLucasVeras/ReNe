"""Step 3A fixtures with independently calculable geometry and motion."""

from math import inf

import pytest

from rene.agreements.state import ManagerAction
from rene.envs.geometry import (
    VehicleBody,
    bodies_overlap,
    bumper_clearance,
    longitudinal_ttc,
    swept_overlap,
)
from rene.envs.merge_lifecycle_env import MergeLifecycleEnv


def body(x: float, y: float = 0.0) -> VehicleBody:
    return VehicleBody(x, y, 4.0, 2.0)


def make_env(**config) -> MergeLifecycleEnv:
    env = MergeLifecycleEnv(config={"disturbance_type": "none", "packet_loss": 0.0, **config})
    env.reset(seed=42)
    return env


def finish(env: MergeLifecycleEnv, action: ManagerAction = ManagerAction.CONTINUE):
    while True:
        _, _, terminated, truncated, info = env.step(int(action))
        if terminated or truncated:
            return info


def test_bumper_clearance_and_contact_boundary():
    assert bumper_clearance(body(0), body(14)) == 10.0
    assert not bodies_overlap(body(0), body(4.01))
    assert bodies_overlap(body(0), body(4))
    assert bodies_overlap(body(0), body(3))


def test_separate_lanes_do_not_collide():
    assert not bodies_overlap(body(0, 0), body(0, 3.6))
    assert longitudinal_ttc(body(0, 0), 25, body(14, 3.6), 20) == inf


def test_closing_and_nonclosing_ttc():
    assert longitudinal_ttc(body(0), 25, body(14), 20) == 2.0
    assert longitudinal_ttc(body(14), 20, body(0), 25) == 2.0
    assert longitudinal_ttc(body(0), 20, body(14), 25) == inf
    assert longitudinal_ttc(body(0), 20, body(3), 25) == 0.0


def test_swept_collision_detects_between_sample_crossing():
    assert not bodies_overlap(body(-10), body(0))
    assert not bodies_overlap(body(10), body(0))
    assert swept_overlap(body(-10), body(10), body(0), body(0))
    assert not swept_overlap(body(-10, 3.6), body(10, 3.6), body(0), body(0))


def test_swept_lateral_collision():
    assert swept_overlap(body(0, 3.6), body(0, -3.6), body(0), body(0))


def test_swept_two_axis_near_miss_is_not_collision():
    # Longitudinal contact would occur near segment end, after lateral separation.
    assert not swept_overlap(body(-10, 0), body(0, 10), body(0), body(0))


@pytest.mark.parametrize("density,gap", [("low", 72.0), ("medium", 60.0), ("high", 50.0)])
def test_reset_has_safe_aligned_moving_gap(density, gap):
    env = make_env()
    _, info = env.reset(seed=42, options={"traffic_density": density})
    assert env.gap_m == pytest.approx(gap)
    assert env.front_clearance_m == pytest.approx((gap - 4.5) / 2)
    assert env.rear_clearance_m == pytest.approx((gap - 4.5) / 2)
    assert info["agreement_feasible"]
    assert env._slot_safe_for(10.0)
    result = finish(env)
    assert result["episode_metrics"]["completed_merge"]
    assert not result["episode_metrics"]["collision"]


def test_initial_gap_config_and_options_are_honored():
    env = make_env(initial_gap_m=70)
    assert env.gap_m == pytest.approx(70)
    env.reset(seed=42, options={"initial_gap_m": 80})
    assert env.gap_m == pytest.approx(80)
    with pytest.raises(ValueError, match="safe moving target gap"):
        env.reset(seed=42, options={"initial_gap_m": 10})


def test_no_disturbance_merge_requires_lateral_motion_and_stabilization():
    env = make_env()
    initial_x = env.ramp_x_m
    positions = []
    while not env.completed:
        _, _, terminated, truncated, _ = env.step(0)
        positions.append(env.ramp_y_m)
        assert not truncated
        if terminated:
            break
    assert any(0 < y < 3.6 for y in positions)
    assert env.ramp_y_m == pytest.approx(0)
    assert env.ramp_x_m == pytest.approx(initial_x + 25 * env.time_s)
    assert env.front_clearance_m == pytest.approx(27.75)
    assert env.rear_clearance_m == pytest.approx(27.75)
    assert env.time_s - env._stable_since_s >= 1.0 - 1e-9
    assert not env.collision


def test_crossing_old_merge_point_on_ramp_is_not_success():
    env = make_env()
    env.ramp_x_m = 201.0
    env._update_completion()
    assert not env.completed


def test_target_lane_without_gap_is_not_success():
    env = make_env()
    env.ramp_y_m = 0.0
    env.ramp_x_m = env.front_x_m + 20
    for _ in range(10):
        env.time_s += 0.2
        env._update_completion()
    assert not env.completed
    assert env._stable_since_s is None


def test_unsafe_gap_blocks_lateral_entry():
    env = make_env()
    env.front_x_m = env.ramp_x_m + 10
    env.rear_x_m = env.ramp_x_m - 10
    env.agreement.planned_merge_time_s = 0.0
    env.config["merge_start_m"] = 0.0
    env._advance_vehicles()
    assert env.ramp_y_m == pytest.approx(3.6)
    assert not env._lane_change_started


def test_physical_overlap_terminates_with_collision():
    env = make_env()
    env.ramp_y_m = 0.0
    env.ramp_x_m = env.front_x_m
    _, _, terminated, truncated, info = env.step(0)
    assert terminated and not truncated
    assert info["episode_metrics"]["collision"]
    assert not info["episode_metrics"]["completed_merge"]


def test_pairwise_headway_uses_bumpers_and_follower_speed():
    env = make_env()
    env.front_x_m = env.ramp_x_m + 24.5
    env.rear_x_m = env.ramp_x_m - 29.5
    assert env.front_clearance_m == pytest.approx(20)
    assert env.rear_clearance_m == pytest.approx(25)
    assert env.headway_s == pytest.approx(0.8)
    assert env.actual_headway_s == pytest.approx(49.5 / 25)
    env.ramp_y_m = 0.0
    assert env.actual_headway_s == pytest.approx(0.8)


def test_synthetic_bonuses_do_not_change_physical_clearance():
    env = make_env()
    before = env.gap_m
    env.synthetic_gap_bonus_m = 1000
    assert env.gap_m == before
    assert not env._renegotiation_feasible(ManagerAction.RENEGOTIATE_NEXT_GAP)
    assert not env._renegotiation_feasible(ManagerAction.RENEGOTIATE_SWAP_ORDER)


def test_timing_revision_does_not_instantly_change_speed():
    env = make_env()
    speed = env.ramp_speed_mps
    env._apply_lifecycle_action(ManagerAction.RENEGOTIATE_DELAY)
    assert env.ramp_speed_mps == speed


def test_cancellation_is_separate_from_physical_completion():
    env = make_env()
    while env.ramp_y_m > 1e-9:
        env.step(0)
    result = finish(env, ManagerAction.CANCEL)
    assert result["episode_metrics"]["canceled"]
    assert result["episode_metrics"]["completed_merge"]
    assert result["agreement_state"] == "canceled"


def test_missed_gap_does_not_become_success():
    env = make_env()
    env.front_x_m += 300
    env.rear_x_m += 300
    result = finish(env)
    assert not result["episode_metrics"]["completed_merge"]
    assert not result["episode_metrics"]["collision"]
    assert env.ramp_y_m == pytest.approx(3.6)
    assert env.ramp_x_m + env.config["vehicle_length_m"] / 2 <= env.config["ramp_end_m"]


def test_stabilization_restarts_after_invalid_slot():
    env = make_env()
    env.ramp_y_m = 0.0
    env._update_completion()
    env.time_s = 0.6
    front = env.front_x_m
    env.front_x_m = env.ramp_x_m + 5
    env._update_completion()
    env.front_x_m = front
    env.time_s = 1.0
    env._update_completion()
    assert not env.completed
    env.time_s = 2.0
    env._update_completion()
    assert env.completed


@pytest.mark.parametrize("dt", [0.1, 0.2, 0.25])
def test_valid_merge_at_multiple_integration_steps(dt):
    env = make_env(dt_s=dt)
    result = finish(env)
    assert result["episode_metrics"]["completed_merge"]
    assert not result["episode_metrics"]["collision"]
    assert env.front_clearance_m == pytest.approx(27.75)
    assert env.rear_clearance_m == pytest.approx(27.75)
    assert env.ramp_y_m == pytest.approx(0)


def test_accepted_lane_change_must_fit_ramp_corridor():
    with pytest.raises(ValueError, match="merge corridor"):
        make_env(lane_change_duration_s=10.0)


@pytest.mark.parametrize("config", [{"dt_s": 0}, {"dt_s": 0.3}, {"vehicle_width_m": 4}])
def test_invalid_geometry_or_timing_config_is_rejected(config):
    with pytest.raises(ValueError):
        MergeLifecycleEnv(config=config)

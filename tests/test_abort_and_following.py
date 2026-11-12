import pytest

from rene.envs.merge_lifecycle_env import MergeLifecycleEnv


def env():
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    sim.reset(seed=42)
    return sim


def test_slowing_peer_preserves_stopping_reserve_before_lane_commit():
    sim = env()
    sim.time_s = 5.8
    sim.ramp_x_m = 170
    sim.front_x_m = 202.25
    sim.rear_x_m = 137.75
    sim.front_speed_mps = 24
    sim._advance_vehicles(0.2)
    assert sim.ramp_speed_mps < 25
    assert -4 <= sim.ramp_accel_mps2 < 0


def test_partial_merge_does_not_return_to_a_ramp_without_stopping_distance():
    sim = env()
    sim.ramp_x_m = 200
    sim.front_x_m = 210
    sim.rear_x_m = 160
    sim.ramp_y_m = 1.8
    sim._lane_change_started = True
    sim._advance_vehicles(0.2)
    assert sim.fallback_active
    assert sim.ramp_y_m < 1.8


def test_rear_following_brakes_with_bounded_acceleration():
    sim = env()
    sim.ramp_x_m = -100
    sim.front_x_m = 20
    sim.rear_x_m = 0
    sim.front_speed_mps = 10
    sim._advance_vehicles(0.2)
    assert sim.rear_speed_mps == pytest.approx(24.2)
    assert sim.rear_x_m == pytest.approx(4.92)


def test_perception_fallback_checks_real_neighbor_clearance():
    sim = env()
    sim.ramp_y_m = 0
    assert sim._fallback_slot_safe()
    sim.front_x_m = sim.ramp_x_m + 5
    assert not sim._fallback_slot_safe()

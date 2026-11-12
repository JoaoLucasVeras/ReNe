"""Physical braking and timestamped received-state fixtures (not research results)."""

import numpy as np
import pytest

from rene.disturbances.braking import BrakingPulse
from rene.envs.merge_lifecycle_env import MergeLifecycleEnv


def env(**config):
    sim = MergeLifecycleEnv(
        {"disturbance_type": "braking", "disturbance_trigger_s": 1.15, "packet_loss": 0, **config}
    )
    sim.reset(seed=42)
    return sim


def test_exact_pulse_position_and_recovery():
    pulse = BrakingPulse(1.15, 2, 1, 3, 2, 25, 8)
    # Cruise 1.15s; brake 2s (44m); hold 1s (19m); recover 3s (66m).
    assert pulse.advance(0, 25, 0, 7.15) == pytest.approx((157.75, 25))
    assert pulse.advance(0, 25, 0, 3.15) == pytest.approx((72.75, 19))


@pytest.mark.parametrize("dt", [0.1, 0.2, 0.25])
def test_off_grid_boundaries_are_timestep_independent(dt):
    sim = env(dt_s=dt)
    initial_x = sim.front_x_m
    for _ in range(4):
        sim.step(0)
    expected = sim.braking_pulse.advance(initial_x, 25, 0, 4)
    assert (sim.front_x_m, sim.front_speed_mps) == pytest.approx(expected)


@pytest.mark.parametrize("severity,decel", [("mild", 1.8), ("moderate", 3), ("hard", 4)])
def test_severity_acceleration_is_bounded(severity, decel):
    sim = env(disturbance_severity=severity, disturbance_trigger_s=0)
    before = sim.front_speed_mps
    sim.disturbance.update(0, sim.np_random)
    sim._apply_disturbance()
    assert sim.front_speed_mps == before  # No instantaneous speed jump.
    sim._advance_vehicles(0.2)
    assert sim.front_speed_mps == pytest.approx(before - decel * 0.2)


def test_speed_floor_and_recovery_cap():
    pulse = BrakingPulse(0, 10, 1, 4, 2, 25, 8)
    x, speed = pulse.advance(0, 25, 0, 10)
    assert speed == 8
    assert x == pytest.approx((25 + 8) / 2 * 4.25 + 8 * 5.75)
    assert pulse.advance(x, speed, 10, 30)[1] == 25


@pytest.mark.parametrize("delay", [0, 0.8, 1.2])
def test_beacon_matches_truth_at_generation_not_delivery(delay):
    sim = env(communication_delay_ms=delay * 1000)
    initial_x = sim.front_x_m
    for _ in range(4):
        sim.step(0)
        message = sim.communication.cache["mainline_front"]
        expected = sim.braking_pulse.advance(initial_x, 25, 0, message.sent_at_s)
        assert (message.payload["x_m"], message.payload["speed_mps"]) == pytest.approx(expected)
        if message.sequence > 0:  # Accepted t=0 state is an assumed bootstrap fixture.
            assert message.sent_at_s <= sim.time_s - delay + 1e-8


def test_partial_final_step_and_profile_reset():
    sim = env(duration_s=4.05)
    initial_x = sim.front_x_m
    for _ in range(5):
        _, _, terminated, truncated, _ = sim.step(0)
    assert truncated and not terminated
    assert sim.time_s == pytest.approx(4.05)
    assert (sim.front_x_m, sim.front_speed_mps) == pytest.approx(
        sim.braking_pulse.advance(initial_x, 25, 0, 4.05)
    )
    sim.reset(seed=42, options={"disturbance_type": "none"})
    assert sim.braking_pulse is None
    assert sim.front_speed_mps == 25


def test_outage_does_not_reveal_braking():
    sim = env(packet_loss=1)
    for _ in range(4):
        obs, _, _, _, info = sim.step(0)
    assert sim.front_speed_mps == pytest.approx(19)
    assert info["manager_inputs"]["front_speed_mps"] == pytest.approx(25)
    assert sim.observation_space.contains(obs)


def test_no_disturbance_maintains_cruise():
    sim = env(disturbance_type="none")
    initial_x = sim.front_x_m
    for _ in range(4):
        sim.step(0)
    assert (sim.front_x_m, sim.front_speed_mps) == pytest.approx((initial_x + 100, 25))


@pytest.mark.parametrize(
    "config",
    [
        {"braking_duration_s": 0},
        {"braking_decel_mps2": -1},
        {"front_max_decel_mps2": np.inf},
        {"braking_hold_s": -1},
        {"braking_min_speed_mps": 26},
        {"braking_recovery_mps2": 0},
        {"disturbance_trigger_s": -1},
        {"disturbance_severity": "unknown"},
    ],
)
def test_invalid_profile_is_rejected(config):
    with pytest.raises(ValueError):
        env(**config)

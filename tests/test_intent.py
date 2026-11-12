"""Intent evidence comes from delivered plan/state, not disturbance labels."""

from dataclasses import replace

import numpy as np
import pytest

from rene.envs.manager_inputs import decode
from rene.envs.merge_lifecycle_env import MergeLifecycleEnv


def make(**config):
    sim = MergeLifecycleEnv(
        {
            "disturbance_type": "intent_mismatch",
            "disturbance_trigger_s": 1.15,
            "packet_loss": 0,
            **config,
        }
    )
    sim.reset(seed=42)
    return sim


@pytest.mark.parametrize("delay", [0, 100, 800, 1200])
def test_residuals_match_delivered_generation_state(delay):
    sim = make(communication_delay_ms=delay)
    for _ in range(4):
        obs, _, _, _, _ = sim.step(0)
        message = sim.communication.cache["mainline_front"]
        expected_x, expected_speed = sim.braking_pulse.advance(
            sim._front_intent_origin_x_m, 25, 0, message.sent_at_s
        )
        assert message.payload["x_m"] == pytest.approx(expected_x)
        assert message.payload["speed_mps"] == pytest.approx(expected_speed)
        values = decode(obs)
        assert values["front_intent_position_error_m"] == pytest.approx(
            expected_x - sim._front_intent_origin_x_m - 25 * message.sent_at_s, abs=2e-5
        )
        assert values["front_intent_speed_error_mps"] == pytest.approx(
            expected_speed - 25, abs=2e-5
        )


def test_outage_hides_new_mismatch_and_retains_received_plan():
    sim = make(packet_loss=1)
    for _ in range(4):
        obs, _, _, _, _ = sim.step(0)
    values = decode(obs)
    assert sim.front_speed_mps == pytest.approx(22)
    assert values["front_speed_mps"] == pytest.approx(25)
    assert values["front_intent_received"] == 1
    assert values["front_intent_position_error_m"] == pytest.approx(0, abs=2e-5)
    assert values["front_intent_speed_error_mps"] == pytest.approx(0, abs=2e-5)
    assert values["front_intent_age_s"] == pytest.approx(4, abs=2e-5)


def test_residual_is_not_a_privileged_injected_diagnostic():
    sim = make(packet_loss=1)
    before = sim._observation()
    sim._intent_position_error_m = 1000
    sim._intent_speed_error_mps = -999
    sim.front_x_m += 50
    sim.front_speed_mps = 8
    assert np.array_equal(before, sim._observation())


def test_missing_received_plan_has_explicit_mask():
    sim = make()
    msg = sim.communication.cache["mainline_front"]
    sim.communication.cache["mainline_front"] = replace(
        msg, payload={"x_m": msg.payload["x_m"], "speed_mps": 25}
    )
    values = decode(sim._observation())
    assert values["front_intent_received"] == 0
    assert values["front_intent_position_error_m"] == pytest.approx(0, abs=2e-5)


@pytest.mark.parametrize("severity,decel", [("mild", 0.9), ("moderate", 1.5), ("hard", 2.25)])
def test_mismatch_motion_is_bounded_and_not_teleported(severity, decel):
    sim = make(disturbance_trigger_s=0, disturbance_severity=severity)
    initial_x = sim.front_x_m
    sim._apply_disturbance()
    assert sim.front_speed_mps == 25
    sim._advance_vehicles(0.2)
    assert sim.front_speed_mps == pytest.approx(25 - decel * 0.2)
    assert sim.front_x_m == pytest.approx(initial_x + 5 - 0.5 * decel * 0.2**2)


def test_unperturbed_received_plan_has_no_error():
    sim = make(disturbance_type="none")
    for _ in range(4):
        obs, _, _, _, _ = sim.step(0)
    values = decode(obs)
    assert values["front_intent_position_error_m"] == pytest.approx(0, abs=2e-5)
    assert values["front_intent_speed_error_mps"] == pytest.approx(0, abs=2e-5)

import numpy as np
import pytest

from rene.agreements.candidates import timing_candidates
from rene.agreements.state import ManagerAction
from rene.envs.manager_inputs import decode
from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
from rene.policies.literature_cancellation import adapted_decision, reference_incentive
from rene.policies.rule_based import make_manager
from rene.prediction.rollouts import Prediction, predict


@pytest.mark.parametrize(
    "current,target,incentive", [(20, 27, 7), (27, 20, -7), (25, 25, 0), (31, 40, 0)]
)
def test_source_operationalization_reference_fixtures(current, target, incentive):
    assert reference_incentive(30, current, target) == incentive


@pytest.mark.parametrize("value", [-1, np.inf, np.nan])
def test_reference_rejects_invalid_estimates(value):
    with pytest.raises(ValueError):
        reference_incentive(30, 20, value)


@pytest.mark.parametrize(
    "keep,fallback,action",
    [
        (("SAFE_COMPLETION", 4), ("SAFE_COMPLETION", 6), ManagerAction.CONTINUE),
        (("SAFE_COMPLETION", 7), ("SAFE_COMPLETION", 5), ManagerAction.CANCEL),
        (("SAFE_COMPLETION", 5), ("SAFE_COMPLETION", 5), ManagerAction.CONTINUE),
        (("INFEASIBLE", None), ("SAFE_COMPLETION", 5), ManagerAction.CANCEL),
        (("SAFE_COMPLETION", 5), ("INFEASIBLE", None), ManagerAction.CONTINUE),
        (("UNKNOWN", None), ("UNKNOWN", None), ManagerAction.CONTINUE),
        (("NO_COMPLETION", None), ("SAFE_COMPLETION", 5), ManagerAction.CANCEL),
        (("SAFE_COMPLETION", 5), ("NO_COMPLETION", None), ManagerAction.CONTINUE),
        (("NO_COMPLETION", None), ("NO_COMPLETION", None), ManagerAction.CONTINUE),
        (("NO_COMPLETION", None), ("UNKNOWN", None), ManagerAction.CONTINUE),
        (("UNKNOWN", None), ("SAFE_COMPLETION", 5), ManagerAction.CONTINUE),
    ],
)
def test_adapted_decision_table(keep, fallback, action):
    first, second = (Prediction(*item, "fixture", 5) for item in (keep, fallback))
    assert adapted_decision(first, second)[0] == action


def test_short_horizon_is_unknown_not_infeasible():
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    obs, _ = sim.reset(seed=42)
    assert predict(decode(obs), sim.config, horizon_s=1).status == "UNKNOWN"


def _late_ramp_values(lateral_m):
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    obs, _ = sim.reset(seed=42)
    values = decode(obs)
    # Ego near the ramp end at low speed: a full lane change can no longer fit.
    values.update(distance_to_merge_m=-36.0, ego_speed_mps=3.0, ego_lateral_m=lateral_m)
    return values, sim.config


def test_ego_that_cannot_fit_lane_change_is_no_completion():
    values, config = _late_ramp_values(3.6)  # fully on the ramp (lane_width_m)
    for fallback in (False, True):
        result = predict(values, config, fallback=fallback, horizon_s=5)
        assert result.status == "NO_COMPLETION"
        assert result.reason == "predicted_no_completion_before_ramp_end"
        assert result.completion_s is None


def test_lane_change_in_progress_is_never_no_completion():
    from rene.prediction.rollouts import _cannot_complete_before_ramp_end

    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    sim.reset(seed=42)
    sim.ramp_x_m = sim.config["ramp_end_m"] - 4.0
    sim.ramp_speed_mps = 3.0
    sim.ramp_y_m = 1.8
    sim._lane_change_started = True
    assert not _cannot_complete_before_ramp_end(sim, sim.config)
    sim._lane_change_started = False
    sim.ramp_y_m = sim.config["lane_width_m"]
    assert _cannot_complete_before_ramp_end(sim, sim.config)


def test_nominal_start_never_reports_no_completion():
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    obs, _ = sim.reset(seed=42)
    values = decode(obs)
    assert predict(values, sim.config).status == "SAFE_COMPLETION"
    assert values["keep_status"] == pytest.approx(2, abs=1e-4)


def test_prediction_features_and_candidates_do_not_see_hidden_future():
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    before, _ = sim.reset(seed=42)
    sim.front_x_m += 100
    sim.front_speed_mps = 5
    sim.disturbance.disturbance_type = "braking"
    sim.disturbance.trigger_s = 0.01
    assert np.array_equal(before, sim._observation())
    values = decode(before)
    candidates = timing_candidates(values, sim.config)
    assert all(
        candidate.action in {ManagerAction.RENEGOTIATE_ADVANCE, ManagerAction.RENEGOTIATE_DELAY}
        for candidate in candidates
    )
    assert any(candidate.action == ManagerAction.RENEGOTIATE_ADVANCE for candidate in candidates)


def test_matched_baselines_use_vector_not_privileged_info():
    sim = MergeLifecycleEnv(
        {"disturbance_type": "none", "packet_loss": 0, "merge_start_m": 140.0}
    )  # wide merge zone: an advance is physically possible
    obs, _ = sim.reset(seed=42)
    assert make_manager("paper_cancel_merge_adapted").act(obs, {}) == ManagerAction.CONTINUE
    assert (
        make_manager("matched_heuristic").act(obs, {"secret": True})
        == ManagerAction.RENEGOTIATE_ADVANCE
    )


def test_braking_pulse_accel_matches_phases():
    from rene.disturbances.braking import BrakingPulse

    pulse = BrakingPulse(5.0, 2.0, 1.0, 3.0, 2.0, 25.0, 8.0)
    assert pulse.accel_at(4.9, 25.0) == 0.0
    assert pulse.accel_at(5.0, 25.0) == -3.0
    assert pulse.accel_at(6.0, 8.0) == 0.0  # at the speed floor
    assert pulse.accel_at(7.5, 19.0) == 0.0  # hold
    assert pulse.accel_at(8.0, 19.0) == 2.0  # recovery
    assert pulse.accel_at(9.0, 25.0) == 0.0


def _braking_env(trigger=1.0):
    sim = MergeLifecycleEnv(
        {"disturbance_type": "braking", "disturbance_trigger_s": trigger,
         "communication_delay_ms": 0, "packet_loss": 0}
    )
    obs, _ = sim.reset(seed=42)
    return sim, obs


def test_received_front_acceleration_is_a_shared_input():
    sim, obs = _braking_env()
    assert decode(obs)["front_accel_mps2"] == pytest.approx(0.0, abs=1e-3)
    obs, *_ = sim.step(0)  # t = 1 s: braking just began
    obs, *_ = sim.step(0)  # t = 2 s: mid-pulse, beacons delivered with zero delay
    assert decode(obs)["front_accel_mps2"] < -1.0


def test_predicted_braking_is_more_pessimistic_than_constant_velocity():
    sim, obs = _braking_env()
    for _ in range(2):
        obs, *_ = sim.step(0)
    values = decode(obs)
    with_accel = predict(values, sim.config)
    constant = predict({**values, "front_accel_mps2": 0.0}, sim.config)
    assert with_accel.status != "SAFE_COMPLETION" or (
        with_accel.min_gap_margin_m < constant.min_gap_margin_m
    )


def _cut_in_env(trigger):
    sim = MergeLifecycleEnv(
        {"disturbance_type": "cut_in", "disturbance_trigger_s": trigger,
         "communication_delay_ms": 0, "packet_loss": 0}
    )
    obs, _ = sim.reset(seed=42)
    return sim, obs


def test_intruder_lateral_speed_needs_observed_displacement():
    sim, obs = _cut_in_env(trigger=1.0)
    assert decode(obs)["intruder_lateral_speed_mps"] == pytest.approx(0.0, abs=1e-3)
    obs, *_ = sim.step(0)  # exactly at onset: no displacement sensed yet
    assert decode(obs)["intruder_lateral_speed_mps"] == pytest.approx(0.0, abs=1e-3)
    sim, obs = _cut_in_env(trigger=0.5)
    obs, *_ = sim.step(0)  # 0.5 s into a 2 s, 3.6 m maneuver
    expected = sim.config["lane_width_m"] / sim.config["cut_in_duration_s"]
    assert decode(obs)["intruder_lateral_speed_mps"] == pytest.approx(expected, abs=0.01)


def test_sensed_cut_in_motion_is_continued_by_prediction():
    from rene.prediction.rollouts import predicted_intruder

    sim, obs = _cut_in_env(trigger=0.5)
    obs, *_ = sim.step(0)
    values = decode(obs)
    now, lateral = values["time_s"], values["intruder_lateral_m"]
    moving = predicted_intruder(values, sim.config, sim.ramp_x_m)
    assert moving.body_at(now).y == pytest.approx(lateral, abs=1e-3)
    arrive = now + -lateral / values["intruder_lateral_speed_mps"]
    assert moving.body_at(arrive).y == pytest.approx(0.0, abs=1e-3)
    assert moving.body_at(now).x == pytest.approx(
        sim.ramp_x_m + values["intruder_relative_m"], abs=1e-3
    )
    frozen = predicted_intruder(
        {**values, "intruder_lateral_speed_mps": 0.0}, sim.config, sim.ramp_x_m
    )
    assert frozen.body_at(now + 5).y == pytest.approx(lateral, abs=1e-3)


def test_default_plan_is_earliest_feasible_so_advance_is_not_free():
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    obs, _ = sim.reset(seed=42)
    values = decode(obs)
    assert values["advance_feasible"] < 0.5 or (
        values["advance_completion_s"] >= values["keep_completion_s"] - 1e-6
    )
    assert make_manager("matched_heuristic").act(obs, {}) == ManagerAction.CONTINUE

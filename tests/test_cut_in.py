"""Hand-calculable physical cut-in and shared local-sensor fixtures."""

from dataclasses import replace

import numpy as np
import pytest

from rene.agreements.state import ManagerAction
from rene.disturbances.cut_in import CutInTrajectory
from rene.envs.geometry import bodies_overlap
from rene.envs.manager_inputs import FEATURES, INPUT_VERSION, decode
from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
from rene.policies.rule_based import RuleCancelManager


def env(**config):
    sim = MergeLifecycleEnv({"disturbance_type": "cut_in", "packet_loss": 0, **config})
    sim.reset(seed=42)
    return sim


def test_trajectory_exists_before_trigger_and_moves_continuously():
    path = CutInTrajectory(10, 25, 5.15, 2, 3.6, 4.5, 1.8)
    assert path.body_at(0).x == 10
    assert path.body_at(5.15).y == -3.6
    assert path.body_at(6.15).y == pytest.approx(-1.8)
    assert path.body_at(7.15).y == pytest.approx(0)
    assert path.body_at(9).x == 235
    assert path.body_at(9).y == 0
    for time in np.arange(0, 10, 0.1):
        before, after = path.body_at(time), path.body_at(time + 0.1)
        assert after.x - before.x == pytest.approx(2.5)
        assert abs(after.y - before.y) <= 0.18 + 1e-9


@pytest.mark.parametrize("dt", [0.1, 0.2, 0.25])
def test_off_grid_path_independent_of_integration_step(dt):
    sim = env(dt_s=dt, disturbance_trigger_s=5.15)
    for _ in range(6):
        sim.step(0)
    intruder = sim._traffic_bodies()[-1]
    assert intruder.x == pytest.approx(sim.cut_in_trajectory.initial_x_m + 150)
    assert intruder.y == pytest.approx(-2.07)


def test_five_bodies_but_only_two_v2x_peers():
    # Ego, two connected peers, the non-connected follower and the intruder.
    sim = env()
    assert len(sim._traffic_bodies()) == 5
    assert set(sim._beacon_payloads()) == {"mainline_front", "mainline_rear"}
    sim.step(0)
    assert all(event.get("sender") != "intruder" for event in sim.communication.bus.events)
    sim.reset(seed=42, options={"disturbance_type": "none"})
    assert len(sim._traffic_bodies()) == 4
    assert not sim._manager_values()["intruder_detected"]


def test_occupancy_is_observed_geometry_not_future_trigger_label():
    sim = env()
    assert not sim._true_slot_occupied()
    assert sim._manager_values()["intruder_detected"] == 1
    for _ in range(5):
        sim.step(0)
    assert not sim._manager_values()["slot_occupied"]
    sim.step(0)
    assert sim._true_slot_occupied()
    obs = sim._observation()
    assert decode(obs)["slot_occupied"] > 0.5
    assert RuleCancelManager().act(obs, {}) == ManagerAction.CANCEL
    assert not sim._info()["agreement_feasible"]
    assert sim._info()["feasibility_reason"] == "target_slot_occupied"
    assert not sim._slot_safe_for(0)
    assert sim.synthetic_gap_bonus_m == 0
    assert sim.gap_m == pytest.approx(60)  # Named-pair gap stays unchanged, but occupied.


def test_sensor_detects_intruder_even_during_v2x_outage():
    sim = env(packet_loss=1)
    for _ in range(6):
        sim.step(0)
    values = decode(sim._observation())
    assert values["intruder_detected"] > 0.5
    assert values["slot_occupied"] > 0.5
    assert values["front_message_age_s"] == pytest.approx(6, abs=1e-5)
    assert sim.communication.cache["mainline_front"].sequence == 0


def test_out_of_range_sensor_is_masked_and_does_not_leak_state():
    sim = env(local_sensor_range_m=5)
    before = sim._observation()
    values = decode(before)
    assert values["intruder_detected"] < 0.5
    assert values["intruder_relative_m"] == pytest.approx(0, abs=1e-5)
    assert values["intruder_speed_mps"] == pytest.approx(0)
    sim.cut_in_trajectory = replace(sim.cut_in_trajectory, initial_x_m=sim.ramp_x_m + 100)
    assert np.array_equal(before, sim._observation())


def test_cached_pair_not_corrected_using_hidden_truth():
    sim = env()
    before = sim._observation()
    sim.front_x_m += 100
    sim.front_speed_mps = 9
    sim.rear_x_m -= 100
    assert np.array_equal(before, sim._observation())


def test_new_sensor_contract_is_shared_and_checkpoint_incompatible():
    sim = env()
    obs = sim._observation()
    assert obs.shape == (len(FEATURES),)
    assert len(FEATURES) == 58
    assert INPUT_VERSION == "lifecycle-prediction-v7"
    assert sim._info()["manager_inputs"] == decode(obs)
    assert sim.observation_space.contains(obs)


def test_occupied_named_slot_cannot_report_success():
    sim = env(disturbance_trigger_s=0)
    sim.time_s = 2
    sim.ramp_x_m += 50
    sim.front_x_m += 50
    sim.rear_x_m += 50
    sim.ramp_y_m = 0
    for _ in range(10):
        sim._update_completion()
        sim.time_s += 0.2
        sim.ramp_x_m += 5
        sim.front_x_m += 5
        sim.rear_x_m += 5
    assert not sim.completed
    assert sim._stable_since_s is None


def test_collision_check_includes_intruder_between_tick_endpoints():
    sim = env(duration_s=0.2)
    sim.cut_in_trajectory = replace(
        sim.cut_in_trajectory,
        initial_x_m=sim.front_x_m - 10,
        speed_mps=100,
        trigger_s=0,
        duration_s=0.1,
    )
    before = sim._traffic_bodies()
    assert not bodies_overlap(before[1], before[3])
    _, _, terminated, _, info = sim.step(0)
    after = sim._traffic_bodies()
    assert not bodies_overlap(after[1], after[-1])
    assert terminated and info["episode_metrics"]["collision"]


def test_actual_ttc_and_headway_include_intruder():
    sim = env(disturbance_trigger_s=0)
    sim.cut_in_trajectory = replace(
        sim.cut_in_trajectory, initial_x_m=sim.front_x_m - 10, speed_mps=20, duration_s=0.01
    )
    sim.time_s = 0.02
    # Rear cruises at 25 m/s and closes on the unconnected car in the target lane.
    clearance = sim._traffic_bodies()[-1].x - sim.rear_x_m - 4.5
    assert sim.ttc_s == pytest.approx(clearance / 5)
    assert sim.actual_headway_s == pytest.approx(
        (sim.front_x_m - sim._traffic_bodies()[-1].x - 4.5) / 20
    )


def test_fallback_enforces_stop_cap_even_when_target_speed_is_already_lower():
    sim = env(disturbance_type="none")
    sim._apply_lifecycle_action(ManagerAction.CANCEL)
    sim.ramp_speed_mps = 25
    sim.ramp_x_m = 155
    sim.front_x_m += 300
    sim.rear_x_m += 300  # No usable target slot, so stopping is required.
    distance = sim.config["ramp_end_m"] - 2.25 - sim.ramp_x_m - 1
    cap = np.sqrt((4 * 0.2) ** 2 + 8 * distance) - 4 * 0.2
    assert 18 < cap < 25  # A target of 18 alone would brake too slowly.
    sim._advance_vehicles()
    assert sim.ramp_speed_mps <= cap + 1e-9


def test_off_grid_final_step_and_seeded_replay():
    trajectories = []
    for _ in range(2):
        sim = env(duration_s=6.05, disturbance_trigger_s=5.15)
        for _ in range(7):
            obs, _, terminated, truncated, info = sim.step(0)
        assert truncated and not terminated
        assert sim.time_s == pytest.approx(6.05)
        intruder = sim._traffic_bodies()[-1]
        assert intruder.y == pytest.approx(-1.98)
        trajectories.append((sim._traffic_bodies(), obs.tolist(), info["communication_log"]))
    assert trajectories[0] == trajectories[1]


@pytest.mark.parametrize("density", ["low", "medium", "high"])
@pytest.mark.parametrize("severity", ["mild", "moderate", "hard"])
def test_default_cut_in_fixtures_are_collision_free_but_do_not_complete_original_slot(
    density, severity
):
    sim = env(traffic_density=density, disturbance_severity=severity)
    manager = RuleCancelManager()
    obs, info = sim.reset(seed=42)
    while True:
        obs, _, terminated, truncated, info = sim.step(int(manager.act(obs, info)))
        if terminated or truncated:
            break
    assert not info["episode_metrics"]["collision"]
    # A perception fallback may use the next gap; the original slot never completes.
    assert info["episode_metrics"]["completion_mode"] != "agreement"
    assert info["episode_metrics"]["canceled"]
    assert not info["episode_metrics"]["ramp_end_violation"]


@pytest.mark.parametrize(
    "config",
    [
        {"cut_in_duration_s": 0},
        {"local_sensor_range_m": -1},
        {"cut_in_offset_fraction": np.nan},
        {"cut_in_offset_fraction": 0.6},
        {"disturbance_trigger_s": -1},
        {"disturbance_severity": "unknown"},
    ],
)
def test_invalid_cut_in_configuration_is_rejected(config):
    with pytest.raises(ValueError):
        env(**config)

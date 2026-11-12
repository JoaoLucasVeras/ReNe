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
    ],
)
def test_adapted_decision_table(keep, fallback, action):
    first, second = (Prediction(*item, "fixture", 5) for item in (keep, fallback))
    assert adapted_decision(first, second)[0] == action


def test_short_horizon_is_unknown_not_infeasible():
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    obs, _ = sim.reset(seed=42)
    assert predict(decode(obs), sim.config, horizon_s=1).status == "UNKNOWN"


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
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    obs, _ = sim.reset(seed=42)
    assert make_manager("paper_cancel_merge_adapted").act(obs, {}) == ManagerAction.CONTINUE
    assert (
        make_manager("matched_heuristic").act(obs, {"secret": True})
        == ManagerAction.RENEGOTIATE_ADVANCE
    )

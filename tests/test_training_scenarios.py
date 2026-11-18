from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
from rene.envs.scenarios import TrainingScenarios


def test_training_conditions_are_reproducible_and_not_revealed_in_info():
    first = TrainingScenarios(MergeLifecycleEnv())
    second = TrainingScenarios(MergeLifecycleEnv())
    first.reset(seed=7)
    second.reset(seed=7)
    assert first.last_scenario == second.last_scenario
    seen = set()
    for _ in range(8):
        _, info = first.reset()
        second.reset()
        assert first.last_scenario == second.last_scenario
        assert "disturbance_type" not in info
        seen.add(first.last_scenario["disturbance_type"])
    assert len(seen) > 1


def test_training_samples_only_protocol_ramp_lengths():
    from collections import Counter

    from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
    from rene.envs.scenarios import (
        EVALUATION_ONLY_RAMP_ENDS_M,
        TRAINING_RAMP_ENDS_M,
        TrainingScenarios,
    )

    env = TrainingScenarios(MergeLifecycleEnv({}))
    env.reset(seed=7)
    seen = Counter()
    for _ in range(80):
        env.reset()
        length = env.last_scenario["ramp_end_m"]
        seen[length] += 1
        assert env.unwrapped.config["ramp_end_m"] == length
    assert set(seen) == set(TRAINING_RAMP_ENDS_M)
    assert not set(seen) & EVALUATION_ONLY_RAMP_ENDS_M


def test_training_rejects_evaluation_only_ramp_lengths():
    import pytest

    from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
    from rene.envs.scenarios import TrainingScenarios

    with pytest.raises(ValueError):
        TrainingScenarios(MergeLifecycleEnv({}), ramp_ends_m=(260.0, 280.0))
    env = TrainingScenarios(MergeLifecycleEnv({}))
    with pytest.raises(ValueError):
        env.reset(seed=1, options={"ramp_end_m": 400.0})


def test_ramp_length_is_per_episode_and_reverts_to_base():
    import pytest

    from rene.envs.merge_lifecycle_env import MergeLifecycleEnv

    env = MergeLifecycleEnv({"disturbance_type": "none"})
    env.reset(seed=1, options={"ramp_end_m": 300.0})
    assert env.config["ramp_end_m"] == 300.0
    env.reset(seed=1)
    assert env.config["ramp_end_m"] == 240.0
    with pytest.raises(ValueError):
        env.reset(seed=1, options={"ramp_end_m": 150.0})


def test_evaluation_manifest_crosses_ramp_lengths_with_roles():
    from rene.envs.scenarios import EVALUATION_RAMP_ENDS_M
    from rene.evaluation.manifest import build_manifest, reset_options

    grid = {"disturbance": ["none", "braking"], "ramp_end_m": list(EVALUATION_RAMP_ENDS_M)}
    manifest = build_manifest(grid, [1001, 1002])
    assert len(manifest) == 2 * 2 * len(EVALUATION_RAMP_ENDS_M)
    roles = {row["ramp_end_m"]: row["ramp_role"] for row in manifest}
    assert roles[280.0] == "heldout" and roles[320.0] == "edge"
    assert roles[240.0] == roles[400.0] == "control"
    assert roles[290.0] == "training"
    assert len({row["scenario_id"] for row in manifest}) == len(manifest)
    options = reset_options(manifest[0])
    assert "ramp_role" not in options and "seed" not in options
    assert "ramp_end_m" in options


def test_action_mask_matches_shared_feasibility_flags():
    import numpy as np

    from rene.agreements.state import ManagerAction
    from rene.envs.manager_inputs import decode
    from rene.envs.merge_lifecycle_env import MergeLifecycleEnv

    for merge_start in (140.0, 175.0):
        env = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0,
                                 "merge_start_m": merge_start})
        obs, _ = env.reset(seed=42)
        mask = env.action_masks()
        values = decode(obs)
        assert mask[ManagerAction.CONTINUE] and mask[ManagerAction.CANCEL]
        assert not mask[ManagerAction.RENEGOTIATE_NEXT_GAP]
        assert not mask[ManagerAction.RENEGOTIATE_SWAP_ORDER]
        assert mask[ManagerAction.RENEGOTIATE_ADVANCE] == (values["advance_feasible"] > 0.5)
        assert mask[ManagerAction.RENEGOTIATE_DELAY] == (values["delay_feasible"] > 0.5)
        assert mask.dtype == np.bool_ and mask.shape == (len(ManagerAction),)


def test_masked_random_actions_never_trigger_infeasible_renegotiation_override():
    import numpy as np

    from rene.envs.merge_lifecycle_env import MergeLifecycleEnv

    rng = np.random.default_rng(3)
    for seed in range(6):
        env = MergeLifecycleEnv({"disturbance_type": "braking", "packet_loss": 0})
        env.reset(seed=seed)
        while True:
            allowed = np.flatnonzero(env.action_masks())
            _, _, terminated, truncated, _ = env.step(int(rng.choice(allowed)))
            if env._decision_log[-1]["override_reason"] == "counterproposal_infeasible":
                raise AssertionError("masked action was overridden as infeasible")
            if terminated or truncated:
                break

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

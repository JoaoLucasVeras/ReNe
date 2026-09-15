import gymnasium as gym
import numpy as np
from gymnasium.utils.env_checker import check_env

import rene  # noqa: F401


def rollout(seed: int):
    env = gym.make("ReNeMergeLifecycle-v0")
    obs, info = env.reset(seed=seed, options={"disturbance_type": "none"})
    observations = [obs]
    done = False
    while not done:
        obs, _, terminated, truncated, info = env.step(0)
        observations.append(obs)
        done = terminated or truncated
    env.close()
    return observations, info


def test_environment_checker():
    env = gym.make("ReNeMergeLifecycle-v0").unwrapped
    check_env(env, skip_render_check=True)


def test_episode_completes_and_emits_metrics():
    observations, info = rollout(42)
    assert observations[0].shape == (22,)
    assert all(np.isfinite(obs).all() for obs in observations)
    assert "episode_metrics" in info


def test_fixed_seed_reproduces_observations():
    first, _ = rollout(123)
    second, _ = rollout(123)
    assert len(first) == len(second)
    assert all(np.allclose(a, b) for a, b in zip(first, second, strict=True))

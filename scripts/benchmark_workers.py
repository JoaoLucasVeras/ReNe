"""Benchmark vectorized environment throughput on CPU."""

from __future__ import annotations

import argparse
import time

import gymnasium as gym
from stable_baselines3.common.env_util import make_vec_env

import rene  # noqa: F401


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=2000)
    args = parser.parse_args()

    for workers in (1, 4, 6, 8):
        vec = make_vec_env(lambda: gym.make("ReNeMergeLifecycle-v0"), n_envs=workers)
        vec.reset()
        start = time.perf_counter()
        transitions = 0
        while transitions < args.steps:
            actions = [vec.action_space.sample() for _ in range(workers)]
            vec.step(actions)
            transitions += workers
        elapsed = time.perf_counter() - start
        vec.close()
        print(f"workers={workers} steps_per_second={transitions / elapsed:.1f}")


if __name__ == "__main__":
    main()

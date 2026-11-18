"""Measure MaskablePPO training throughput on CPU and (if available) CUDA.

Development benchmark only: identical configuration and seeds per device, ramp-length
sampling on, no model kept. Prints transitions per second and projected wall-clock
time for a given research budget.
"""

from __future__ import annotations

import argparse
import json
from time import perf_counter

import gymnasium as gym
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecNormalize

import rene  # noqa: F401
from rene.envs.scenarios import TrainingScenarios
from rene.utils.configuration import load_yaml


def run(device: str, n_envs: int, steps: int, ppo: dict, backend: str) -> float:
    def factory():
        return TrainingScenarios(gym.make("ReNeMergeLifecycle-v0", config={}))

    cls = SubprocVecEnv if backend == "subproc" else DummyVecEnv
    vec = VecNormalize(
        make_vec_env(factory, n_envs=n_envs, seed=9301, vec_env_cls=cls),
        norm_obs=True, norm_reward=False, clip_obs=10.0,
    )
    kwargs = {k: v for k, v in ppo.items() if k not in {"policy", "device", "algorithm"}}
    model = MaskablePPO(ppo["policy"], vec, seed=9301, device=device, **kwargs)
    model.learn(total_timesteps=kwargs["n_steps"] * n_envs)  # warm-up rollout
    started = perf_counter()
    model.learn(total_timesteps=steps, reset_num_timesteps=False)
    elapsed = perf_counter() - started
    vec.close()
    return steps / elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-config", default="configs/agents/ppo.yaml")
    parser.add_argument("--steps", type=int, default=20480)
    parser.add_argument("--n-envs", type=int, nargs="+", default=[4, 8])
    parser.add_argument("--budget", type=int, default=1_000_000)
    parser.add_argument("--backend", default="subproc")
    args = parser.parse_args()
    torch.set_num_threads(1)
    ppo = load_yaml(args.agent_config)["ppo"]
    devices = ["cpu"] + (["cuda"] if torch.cuda.is_available() else [])
    report = {"torch": torch.__version__, "cuda_available": torch.cuda.is_available(),
              "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
              "steps": args.steps, "results": []}
    for n_envs in args.n_envs:
        for device in devices:
            rate = run(device, n_envs, args.steps, ppo, args.backend)
            report["results"].append({
                "device": device, "n_envs": n_envs, "transitions_per_s": round(rate, 1),
                "hours_for_budget": round(args.budget / rate / 3600, 2),
            })
            print(json.dumps(report["results"][-1]), flush=True)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

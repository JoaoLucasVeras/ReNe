"""Train a Stable-Baselines3 PPO lifecycle manager."""

from __future__ import annotations

import argparse
from pathlib import Path

import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecNormalize

import rene  # noqa: F401
from rene.utils.configuration import load_yaml


def env_config(source: dict) -> dict:
    env = dict(source.get("environment", {}))
    disturbance = source.get("disturbance", {})
    env.update(
        disturbance_type=disturbance.get("type", "none"),
        disturbance_trigger_s=disturbance.get("trigger_s", 5.0),
        disturbance_severity=disturbance.get("severity", "moderate"),
        communication_delay_ms=disturbance.get("communication_delay_ms", 0),
        packet_loss=disturbance.get("packet_loss", 0.0),
    )
    return env


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/experiments/train.yaml")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--timesteps", type=int)
    args = parser.parse_args()
    run = load_yaml(args.config)
    exp = run["experiment"]
    ppo = load_yaml(run["agent_config"])["ppo"]
    seed = args.seed if args.seed is not None else int(exp["seed"])
    output = Path(exp["output_dir"]) / f"seed-{seed}"
    output.mkdir(parents=True, exist_ok=True)
    config = env_config(load_yaml(run["env_config"]))

    def factory():
        return gym.make("ReNeMergeLifecycle-v0", config=config)

    vec = make_vec_env(factory, n_envs=int(exp["n_envs"]), seed=seed)
    vec = VecNormalize(vec, norm_obs=True, norm_reward=False, clip_obs=10.0)
    kwargs = dict(ppo)
    policy = kwargs.pop("policy")
    device = kwargs.pop("device", "cpu")
    model = PPO(policy, vec, seed=seed, device=device, tensorboard_log=str(output), **kwargs)
    model.learn(total_timesteps=args.timesteps or int(exp["total_timesteps"]))
    model.save(output / "model")
    vec.save(output / "vec_normalize.pkl")
    vec.close()
    print(output.resolve())


if __name__ == "__main__":
    main()

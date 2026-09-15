"""Evaluate one manager across seeded scenarios."""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

import rene  # noqa: F401
from rene.policies.rule_based import make_manager
from rene.utils.configuration import load_yaml
from rene.utils.logging import make_run_dir, save_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/experiments/final_eval.yaml")
    parser.add_argument("--manager", required=True)
    parser.add_argument("--model")
    parser.add_argument("--episodes", type=int)
    args = parser.parse_args()
    run = load_yaml(args.config)
    exp = run["experiment"]
    env_data = load_yaml(run["env_config"])
    grid = env_data.get("grid", {})
    base = env_data.get("environment", {})
    conditions = list(
        itertools.product(
            grid.get("traffic_density", ["medium"]),
            grid.get("delay_ms", [0]),
            grid.get("packet_loss", [0.0]),
            grid.get("disturbance", ["none"]),
        )
    )
    episode_budget = args.episodes or int(exp["episodes"])
    seeds = list(exp.get("seeds", [1001]))
    output = make_run_dir(exp["output_dir"], args.manager)
    learned = PPO.load(args.model, device="cpu") if args.manager == "learned" else None
    normalizer = None
    if learned:
        normalization_path = Path(args.model).with_name("vec_normalize.pkl")
        if normalization_path.exists():
            dummy = DummyVecEnv([lambda: gym.make("ReNeMergeLifecycle-v0", config=base)])
            normalizer = VecNormalize.load(normalization_path, dummy)
            normalizer.training = False
            normalizer.norm_reward = False
    manager = None if learned else make_manager(args.manager)
    rows: list[dict] = []

    env = gym.make("ReNeMergeLifecycle-v0", config=base)
    for episode_index in range(episode_budget):
        density, delay, loss, disturbance = conditions[episode_index % len(conditions)]
        seed = seeds[episode_index % len(seeds)] + episode_index
        options = {
            "traffic_density": density,
            "communication_delay_ms": delay,
            "packet_loss": loss,
            "disturbance_type": disturbance,
        }
        obs, info = env.reset(seed=seed, options=options)
        done = False
        while not done:
            if learned:
                policy_obs = normalizer.normalize_obs(obs) if normalizer else obs
                action, _ = learned.predict(policy_obs, deterministic=True)
                selected = int(action)
            else:
                selected = int(manager.act(obs, info))
            obs, _, terminated, truncated, info = env.step(selected)
            done = terminated or truncated
        row = dict(info["episode_metrics"])
        row.update(
            manager=args.manager,
            traffic_density=density,
            delay_ms=delay,
            packet_loss=loss,
            disturbance=disturbance,
        )
        rows.append(row)
    env.close()
    if normalizer:
        normalizer.close()
    save_rows(output / "episodes.csv", rows)
    print(f"evaluated {len(rows)} episodes")
    print(output.resolve())


if __name__ == "__main__":
    main()

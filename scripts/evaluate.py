"""Evaluate one manager across seeded scenarios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

import rene  # noqa: F401
from rene.envs.manager_inputs import INPUT_VERSION
from rene.evaluation.manifest import build_manifest
from rene.metrics.counterfactual import cancellation_snapshot, evaluate_retention
from rene.policies.rule_based import make_manager
from rene.utils.configuration import load_yaml
from rene.utils.logging import make_run_dir, save_rows
from rene.utils.provenance import source_fingerprint


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/experiments/final_eval.yaml")
    parser.add_argument("--manager", required=True)
    parser.add_argument("--model")
    parser.add_argument("--episodes", type=int)
    args = parser.parse_args()
    if args.manager == "learned" and not args.model:
        parser.error("--model is required for a learned manager")
    run = load_yaml(args.config)
    exp = run["experiment"]
    env_data = load_yaml(run["env_config"])
    grid = env_data.get("grid", {})
    base = env_data.get("environment", {})
    episode_budget = args.episodes or int(exp["episodes"])
    seeds = list(exp.get("seeds", [1001]))
    manifest = build_manifest(grid, seeds)
    if episode_budget > len(manifest):
        parser.error("episode budget exceeds the unique condition/seed manifest")
    manifest = manifest[:episode_budget]
    output = make_run_dir(exp["output_dir"], args.manager)
    fingerprint = source_fingerprint()
    if args.manager == "learned":
        metadata_path = Path(args.model).with_name("metadata.json")
        if not metadata_path.exists():
            parser.error(
                "checkpoint metadata.json missing; old checkpoints require explicit migration"
            )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            metadata.get("input_version") != INPUT_VERSION
            or metadata.get("source_fingerprint") != fingerprint
        ):
            parser.error("checkpoint input/source provenance does not match this evaluation")
        if not Path(args.model).with_name("vec_normalize.pkl").exists():
            parser.error("trained VecNormalize statistics are required")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
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
    for scenario in manifest:
        seed = scenario["seed"]
        options = {
            key: value for key, value in scenario.items() if key not in {"seed", "scenario_id"}
        }
        obs, info = env.reset(seed=seed, options=options)
        done = False
        snapshot = None
        while not done:
            if learned:
                policy_obs = normalizer.normalize_obs(obs) if normalizer else obs
                action, _ = learned.predict(policy_obs, deterministic=True)
                selected = int(action)
            else:
                selected = int(manager.act(obs, info))
            if snapshot is None:
                snapshot = cancellation_snapshot(env.unwrapped, selected)
            obs, _, terminated, truncated, info = env.step(selected)
            done = terminated or truncated
        row = dict(info["episode_metrics"])
        row.update(
            source_fingerprint=fingerprint,
            scenario_id=scenario["scenario_id"],
            manager=args.manager,
            training_seed=metadata["seed"] if learned else -1,
            traffic_density=scenario["traffic_density"],
            delay_ms=scenario["communication_delay_ms"],
            packet_loss=scenario["packet_loss"],
            disturbance=scenario["disturbance_type"],
        )
        row.update(evaluate_retention(snapshot))
        rows.append(row)
    env.close()
    if normalizer:
        normalizer.close()
    save_rows(output / "episodes.csv", rows)
    print(f"evaluated {len(rows)} episodes")
    print(output.resolve())


if __name__ == "__main__":
    main()

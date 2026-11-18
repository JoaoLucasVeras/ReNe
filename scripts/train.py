"""Train a Stable-Baselines3 PPO lifecycle manager."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import gymnasium as gym
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecNormalize

import rene  # noqa: F401
from rene.envs.manager_inputs import FEATURES, INPUT_VERSION
from rene.envs.scenarios import TRAINING_RAMP_ENDS_M, TrainingScenarios
from rene.utils.configuration import load_yaml
from rene.utils.provenance import source_fingerprint


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
    parser.add_argument(
        "--acknowledge-unvalidated-simulator",
        action="store_true",
        help="Explicitly acknowledge that M2 is not passed; for development only",
    )
    args = parser.parse_args()
    if not args.acknowledge_unvalidated_simulator:
        parser.error(
            "Research training is gated: simulator validation remains open. "
            "Run scripts/training_preflight.py for a tiny CPU API smoke. "
            "Use --acknowledge-unvalidated-simulator only for labeled development runs."
        )
    run = load_yaml(args.config)
    exp = run["experiment"]
    ppo = load_yaml(run["agent_config"])["ppo"]
    seed = args.seed if args.seed is not None else int(exp["seed"])
    output = Path(exp["output_dir"]) / f"seed-{seed}"
    if (output / "model.zip").exists():
        raise SystemExit(f"Refusing to overwrite existing model: {output}; choose a new output_dir")
    output.mkdir(parents=True, exist_ok=True)
    config = env_config(load_yaml(run["env_config"]))

    def factory():
        env = gym.make("ReNeMergeLifecycle-v0", config=config)
        return TrainingScenarios(env) if exp.get("sample_scenarios", False) else env

    torch.set_num_threads(int(exp.get("torch_threads", 1)))
    backend = SubprocVecEnv if exp.get("vec_backend") == "subproc" else DummyVecEnv
    vec = make_vec_env(factory, n_envs=int(exp["n_envs"]), seed=seed, vec_env_cls=backend)
    vec = VecNormalize(vec, norm_obs=True, norm_reward=False, clip_obs=10.0)
    kwargs = dict(ppo)
    policy = kwargs.pop("policy")
    device = kwargs.pop("device", "cpu")
    algorithm = kwargs.pop("algorithm", "maskable_ppo")
    if algorithm not in {"maskable_ppo", "ppo"}:
        raise SystemExit(f"unknown algorithm: {algorithm}")
    algo_cls = MaskablePPO if algorithm == "maskable_ppo" else PPO
    model = algo_cls(policy, vec, seed=seed, device=device, tensorboard_log=str(output), **kwargs)
    model.learn(total_timesteps=args.timesteps or int(exp["total_timesteps"]))
    model.save(output / "model")
    vec.save(output / "vec_normalize.pkl")
    metadata = {
        "input_version": INPUT_VERSION,
        "features": len(FEATURES),
        "source_fingerprint": source_fingerprint(),
        "seed": seed,
        "timesteps": model.num_timesteps,
        "device": str(model.device),
        "algorithm": algorithm,
        "environment_config": config,
        "experiment": exp,
        "training_ramp_ends_m": (
            list(TRAINING_RAMP_ENDS_M) if exp.get("sample_scenarios", False) else None
        ),
        "validation_status": "development_unvalidated_acknowledged",
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    vec.close()
    print(output.resolve())


if __name__ == "__main__":
    main()

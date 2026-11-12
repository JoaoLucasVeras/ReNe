"""Tiny CPU PPO API/throughput smoke, not a research training run."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import gymnasium as gym
import torch
from stable_baselines3 import PPO

import rene  # noqa: F401
from rene.envs.manager_inputs import FEATURES, INPUT_VERSION


def main():
    torch.set_num_threads(1)
    env = gym.make("ReNeMergeLifecycle-v0", config={"disturbance_type": "none", "packet_loss": 0})
    started = perf_counter()
    model = PPO(
        "MlpPolicy",
        env,
        n_steps=64,
        batch_size=32,
        n_epochs=1,
        policy_kwargs={"net_arch": [128, 128]},
        seed=42,
        device="cpu",
        verbose=0,
    )
    model.learn(total_timesteps=128)
    elapsed = perf_counter() - started
    report = {
        "purpose": "cpu_api_smoke_not_research_training",
        "timesteps": model.num_timesteps,
        "elapsed_s": elapsed,
        "transitions_per_s": model.num_timesteps / elapsed,
        "device": str(model.device),
        "cuda_available_on_this_machine": torch.cuda.is_available(),
        "torch_version": torch.__version__,
        "input_version": INPUT_VERSION,
        "features": len(FEATURES),
        "research_training_ready": False,
        "reason": "M2/controller/scenario validation and frozen baseline review remain open",
    }
    output = Path("results/raw/training-preflight") / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    env.close()
    print(json.dumps(report, indent=2))
    print(output.resolve())


if __name__ == "__main__":
    main()

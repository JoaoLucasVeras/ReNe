"""Pilot MaskablePPO run with periodic validation, to choose the training budget.

Validation uses training ramp lengths and development seeds only (never the reserved
final-test seeds or evaluation-only lengths). B2 is scored on the same scenarios for
reference. Output: a JSON learning curve; the model itself is not a research model.
"""

from __future__ import annotations

import argparse
import itertools
import json
from datetime import UTC, datetime
from pathlib import Path

import gymnasium as gym
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv, VecNormalize

import rene  # noqa: F401
from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
from rene.envs.scenarios import TRAINING_RAMP_ENDS_M, TrainingScenarios
from rene.policies.rule_based import make_manager
from rene.utils.configuration import load_yaml

VALIDATION_SEEDS = (42, 43)


def validation_set():
    return [
        {
            "seed": seed,
            "options": {
                "ramp_end_m": ramp, "traffic_density": density, "disturbance_type": dist,
                "communication_delay_ms": delay, "packet_loss": loss,
                "disturbance_severity": "hard", "disturbance_trigger_s": trigger,
            },
        }
        for ramp, density, dist, delay, loss, trigger, seed in itertools.product(
            TRAINING_RAMP_ENDS_M, ["low", "medium", "high"],
            ["none", "braking", "cut_in", "intent_mismatch"], [100, 800], [0.0, 0.2],
            [3.5, 5.0], VALIDATION_SEEDS,
        )
    ]


def score(act, scenarios):
    totals = dict(episodes=0, merged=0, agreement=0, collision=0, ramp_end=0, canceled=0,
                  reward=0.0)
    for scenario in scenarios:
        env = MergeLifecycleEnv({})
        obs, info = env.reset(seed=scenario["seed"], options=scenario["options"])
        while True:
            obs, reward, terminated, truncated, info = env.step(int(act(env, obs, info)))
            totals["reward"] += reward
            if terminated or truncated:
                break
        m = info["episode_metrics"]
        totals["episodes"] += 1
        totals["merged"] += m["completion_mode"] in ("agreement", "fallback")
        totals["agreement"] += m["completion_mode"] == "agreement"
        totals["collision"] += m["collision"]
        totals["ramp_end"] += m["ramp_end_violation"]
        totals["canceled"] += m["canceled"]
    totals["reward"] = round(totals["reward"] / totals["episodes"], 3)
    return totals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-config", default="configs/agents/ppo.yaml")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--n-envs", type=int, default=8)
    parser.add_argument("--total", type=int, default=400_000)
    parser.add_argument("--every", type=int, default=50_000)
    parser.add_argument("--output", default="results/raw/learning-curve")
    args = parser.parse_args()
    torch.set_num_threads(1)
    ppo = load_yaml(args.agent_config)["ppo"]
    out = Path(args.output) / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True)
    scenarios = validation_set()
    b2 = make_manager("paper_cancel_merge_adapted")
    curve = {"seed": args.seed, "n_envs": args.n_envs, "validation_episodes": len(scenarios),
             "b2": score(lambda env, obs, info: b2.act(obs, info), scenarios), "points": []}
    print("B2", json.dumps(curve["b2"]), flush=True)

    def factory():
        return TrainingScenarios(gym.make("ReNeMergeLifecycle-v0", config={}))

    vec = VecNormalize(
        make_vec_env(factory, n_envs=args.n_envs, seed=args.seed, vec_env_cls=SubprocVecEnv),
        norm_obs=True, norm_reward=False, clip_obs=10.0,
    )
    kwargs = {k: v for k, v in ppo.items() if k not in {"policy", "device", "algorithm"}}
    model = MaskablePPO(ppo["policy"], vec, seed=args.seed, device="cpu", **kwargs)
    done = 0
    while done < args.total:
        model.learn(total_timesteps=args.every, reset_num_timesteps=False)
        done = model.num_timesteps

        def act(env, obs, info, model=model):
            action, _ = model.predict(vec.normalize_obs(obs), deterministic=True,
                                      action_masks=env.action_masks())
            return int(action)

        point = {"timesteps": done, **score(act, scenarios)}
        curve["points"].append(point)
        print(json.dumps(point), flush=True)
        (out / "curve.json").write_text(json.dumps(curve, indent=2), encoding="utf-8")
    vec.close()
    print(out.resolve())


if __name__ == "__main__":
    np.set_printoptions(precision=3)
    main()

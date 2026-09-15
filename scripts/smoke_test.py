"""Run a short deterministic baseline smoke test."""

from __future__ import annotations

import argparse

import gymnasium as gym

import rene  # noqa: F401
from rene.policies.rule_based import make_manager
from rene.utils.configuration import load_yaml
from rene.utils.logging import make_run_dir, save_rows


def flatten_env_config(config: dict) -> dict:
    env = dict(config.get("environment", {}))
    disturbance = config.get("disturbance", {})
    env.update(
        {
            "disturbance_type": disturbance.get("type", "none"),
            "disturbance_trigger_s": disturbance.get("trigger_s", 5.0),
            "disturbance_severity": disturbance.get("severity", "moderate"),
            "communication_delay_ms": disturbance.get("communication_delay_ms", 0),
            "packet_loss": disturbance.get("packet_loss", 0.0),
        }
    )
    return env


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/experiments/smoke.yaml")
    args = parser.parse_args()
    experiment = load_yaml(args.config)
    settings = experiment["experiment"]
    env_source = load_yaml(experiment["env_config"])
    manager = make_manager(settings["manager"])
    output = make_run_dir(settings["output_dir"], settings["manager"])
    episode_rows: list[dict] = []
    decision_rows: list[dict] = []

    env = gym.make("ReNeMergeLifecycle-v0", config=flatten_env_config(env_source))
    for index in range(int(settings["episodes"])):
        seed = int(settings["seed"]) + index
        obs, info = env.reset(seed=seed)
        done = False
        while not done:
            action = manager.act(obs, info)
            obs, _, terminated, truncated, info = env.step(int(action))
            done = terminated or truncated
        metrics = dict(info["episode_metrics"])
        metrics["manager"] = settings["manager"]
        episode_rows.append(metrics)
        for row in info["decision_log"]:
            decision_rows.append({"episode_id": metrics["episode_id"], **row})
    env.close()
    save_rows(output / "episodes.csv", episode_rows)
    save_rows(output / "decisions.csv", decision_rows)
    completed = sum(row["completed_merge"] for row in episode_rows)
    print(f"completed {len(episode_rows)} episodes; successful merges={completed}")
    print(output.resolve())


if __name__ == "__main__":
    main()

"""Record a representative lifecycle episode as an animated GIF."""

from __future__ import annotations

import argparse
from pathlib import Path

import gymnasium as gym
from PIL import Image

import rene  # noqa: F401
from rene.policies.rule_based import make_manager


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manager", default="heuristic_renegotiate")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="results/figures/example_episode.gif")
    parser.add_argument("--disturbance", default="cut_in")
    args = parser.parse_args()
    manager = make_manager(args.manager)
    env = gym.make("ReNeMergeLifecycle-v0", render_mode="rgb_array")
    obs, info = env.reset(seed=args.seed, options={"disturbance_type": args.disturbance})
    frames = [Image.fromarray(env.render())]
    done = False
    while not done:
        action = manager.act(obs, info)
        obs, _, terminated, truncated, info = env.step(int(action))
        frames.append(Image.fromarray(env.render()))
        done = terminated or truncated
    env.close()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(output, save_all=True, append_images=frames[1:], duration=200, loop=0)
    print(output.resolve())


if __name__ == "__main__":
    main()

"""Record a representative lifecycle episode as an animated GIF."""

from __future__ import annotations

import argparse
from pathlib import Path

import gymnasium as gym
from PIL import Image, ImageDraw

import rene  # noqa: F401
from rene.policies.rule_based import make_manager


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manager", default="heuristic_renegotiate")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="results/figures/example_episode.gif")
    parser.add_argument("--disturbance", default="cut_in")
    parser.add_argument("--delay-ms", type=float, default=100)
    parser.add_argument("--loss", type=float, default=0.05)
    parser.add_argument(
        "--frame-ms",
        type=int,
        default=1000,
        help="Playback duration per decision frame (default approximately real time)",
    )
    args = parser.parse_args()
    if args.frame_ms <= 0:
        parser.error("--frame-ms must be positive")
    manager = make_manager(args.manager)
    env = gym.make("ReNeMergeLifecycle-v0", render_mode="rgb_array")
    obs, info = env.reset(
        seed=args.seed,
        options={
            "disturbance_type": args.disturbance,
            "communication_delay_ms": args.delay_ms,
            "packet_loss": args.loss,
        },
    )

    def frame() -> Image.Image:
        picture = Image.fromarray(env.render())
        drawing = ImageDraw.Draw(picture)
        drawing.text(
            (8, 8),
            f"t={info['time_s']:.1f}s  manager={args.manager}  agreement={info['agreement_state']}",
            fill=(20, 20, 20),
        )
        drawing.text(
            (8, 25),
            "Orange: merging car | Blue: freeway cars | "
            "Custom Step 3B prototype, not full validation",
            fill=(20, 20, 20),
        )
        drawing.text(
            (8, 42), "Camera follows the orange car; roadway moves past it", fill=(20, 20, 20)
        )
        drawing.text(
            (8, 59),
            f"V2X age={info['manager_inputs']['message_age_s']:.2f}s  "
            f"cancel={info['cancel_protocol_state']}",
            fill=(20, 20, 20),
        )
        return picture

    frames = [frame()]
    done = False
    while not done:
        action = manager.act(obs, info)
        obs, _, terminated, truncated, info = env.step(int(action))
        frames.append(frame())
        done = terminated or truncated
    env.close()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(output, save_all=True, append_images=frames[1:], duration=args.frame_ms, loop=0)
    print(output.resolve())


if __name__ == "__main__":
    main()

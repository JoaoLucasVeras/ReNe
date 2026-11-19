"""Record one final-evaluation scenario under several managers as stacked GIF panels.

Every panel replays the same manifest row (same seed and options), so the only
difference between panels is the lifecycle manager. Frames are captured at every
physics step (dt 0.2 s) and played back in real time. Visualization only; the episode
outcomes match results/raw/final for the same scenario id.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import gymnasium as gym
from PIL import Image, ImageDraw
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

import rene  # noqa: F401
from rene.evaluation.manifest import build_manifest, reset_options
from rene.policies.rule_based import make_manager
from rene.utils.configuration import load_yaml

LABELS = {
    "one_shot": "B1 Never cancel",
    "learned": "B4 AI (PPO)",
    "paper_cancel_merge_adapted": "B2 Paper's cancel rule",
    "matched_heuristic": "B3 Timing rule",
    "rule_cancel": "Threshold rule",
}
HEADER = 44
INK = (20, 20, 20)


def make_actor(name: str, model_path: str, base: dict):
    if name != "learned":
        manager = make_manager(name)
        return lambda env, obs, info: int(manager.act(obs, info))
    model = MaskablePPO.load(model_path, device="cpu")
    dummy = DummyVecEnv([lambda: gym.make("ReNeMergeLifecycle-v0", config=base)])
    norm = VecNormalize.load(str(Path(model_path).with_name("vec_normalize.pkl")), dummy)
    norm.training = False

    def act(env, obs, info):
        action, _ = model.predict(norm.normalize_obs(obs), deterministic=True,
                                  action_masks=env.unwrapped.action_masks())
        return int(action)

    return act


def record(name: str, act, scenario: dict, base: dict) -> tuple[list[Image.Image], dict]:
    env = gym.make("ReNeMergeLifecycle-v0", config=base, render_mode="rgb_array")
    raw = env.unwrapped
    obs, info = env.reset(seed=scenario["seed"], options=reset_options(scenario))
    state = {"info": info}
    frames: list[Image.Image] = []

    def snap():
        picture = Image.fromarray(raw.render())
        picture = picture.crop((0, 80, picture.width, 200))  # road band only
        canvas = Image.new("RGB", (picture.width, picture.height + HEADER), "white")
        canvas.paste(picture, (0, HEADER))
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 6), LABELS.get(name, name), fill=INK)
        draw.text((8, 24), f"t = {raw.time_s:4.1f} s   deal: {raw.agreement.state.name.lower()}"
                  f"   {'fallback (merging alone)' if raw.fallback_active else ''}", fill=INK)
        frames.append(canvas)

    original = raw._advance_vehicles

    def advance(dt):
        snap()
        original(dt)

    raw._advance_vehicles = advance
    done = False
    while not done:
        obs, _, terminated, truncated, info = env.step(act(env, obs, info))
        done = terminated or truncated
    snap()
    env.close()
    state["info"] = info
    return frames, info["episode_metrics"]


def outcome_text(m: dict) -> str:
    if m["collision"]:
        return "COLLISION"
    if m["completion_mode"] == "agreement":
        return "MERGED WITH THE DEAL"
    if m["completion_mode"] == "fallback":
        return "MERGED ALONE (deal canceled)"
    return "DID NOT MERGE"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="s1001-c147")
    parser.add_argument("--managers", nargs="+",
                        default=["one_shot", "learned", "paper_cancel_merge_adapted",
                                 "rule_cancel"])
    parser.add_argument("--model", default="models/ppo_final/seed-1/model.zip")
    parser.add_argument("--output", default="results/figures/comparison_s1001-c147.gif")
    parser.add_argument("--frame-ms", type=int, default=200)
    args = parser.parse_args()
    run = load_yaml("configs/experiments/final_eval.yaml")
    env_data = load_yaml(run["env_config"])
    base = env_data.get("environment", {})
    manifest = build_manifest(env_data.get("grid", {}), list(run["experiment"]["seeds"]))
    scenario = next(s for s in manifest if s["scenario_id"] == args.scenario)

    panels, outcomes = [], {}
    for name in args.managers:
        frames, metrics = record(name, make_actor(name, args.model, base), scenario, base)
        panels.append(frames)
        outcomes[name] = outcome_text(metrics)
    length = max(len(p) for p in panels) + 10  # hold the final frame ~2 s
    width, height = panels[0][0].size
    title_h = 40
    out_frames = []
    for i in range(length):
        sheet = Image.new("RGB", (width, title_h + height * len(panels)), "white")
        draw = ImageDraw.Draw(sheet)
        draw.text((8, 6), f"Same scenario {scenario['scenario_id']}: {scenario['ramp_end_m']:.0f} m "
                  f"ramp ({scenario['ramp_role']}), {scenario['traffic_density']} traffic, "
                  f"disturbance = {scenario['disturbance_type']}", fill=INK)
        draw.text((8, 22), "Orange: merging car | Blue: deal partners | Grey: other traffic | "
                  "Purple: cut-in car", fill=INK)
        for row, (name, frames) in enumerate(zip(args.managers, panels, strict=True)):
            frame = frames[min(i, len(frames) - 1)].copy()
            if i >= len(frames) - 1:
                ImageDraw.Draw(frame).text((width - 260, 6), outcomes[name], fill=(180, 30, 30))
            sheet.paste(frame, (0, title_h + row * height))
            draw.line([(0, title_h + row * height), (width, title_h + row * height)],
                      fill=(200, 200, 200))
        out_frames.append(sheet)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    out_frames[0].save(output, save_all=True, append_images=out_frames[1:],
                       duration=args.frame_ms, loop=0, optimize=True)
    print(json.dumps(outcomes))
    print(output.resolve())


if __name__ == "__main__":
    main()

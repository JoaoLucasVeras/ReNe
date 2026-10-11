"""Run a CPU-only episode and save received-state and protocol diagnostics."""

from __future__ import annotations

import argparse
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
from rene.policies.rule_based import make_manager
from rene.utils.logging import save_rows


def finite_json(value):
    if isinstance(value, dict):
        return {key: finite_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [finite_json(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay-ms", type=float, default=100)
    parser.add_argument("--loss", type=float, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--manager",
        default="rule_cancel",
        choices=["one_shot", "rule_cancel", "heuristic_renegotiate"],
    )
    parser.add_argument("--output", default="results/raw/communication")
    args = parser.parse_args()
    sim = MergeLifecycleEnv(
        config={
            "disturbance_type": "none",
            "communication_delay_ms": args.delay_ms,
            "packet_loss": args.loss,
        }
    )
    obs, info = sim.reset(seed=args.seed)
    manager = make_manager(args.manager)
    sim.metrics.manager = args.manager
    rows = []
    while True:
        requested = manager.act(obs, info)
        # Evaluator-only truth is deliberately separate from the manager's data.
        rows.append(
            {
                **info["manager_inputs"],
                "requested_action": requested.name,
                "true_front_x_m": sim.front_x_m,
                "true_rear_x_m": sim.rear_x_m,
                "true_front_speed_mps": sim.front_speed_mps,
                "protocol_state": sim.communication.session.state,
            }
        )
        obs, _, terminated, truncated, info = sim.step(int(requested))
        if terminated or truncated:
            break
    sim.close()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = Path(args.output) / f"{args.manager}-{stamp}"
    output.mkdir(parents=True, exist_ok=False)
    save_rows(output / "received_states.csv", rows)
    data = finite_json(
        {
            "settings": vars(args),
            "metrics": info["episode_metrics"],
            "decisions": info["decision_log"],
            "communication": info["communication_log"],
        }
    )
    (output / "trace.json").write_text(
        json.dumps(data, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(json.dumps(data["metrics"], indent=2))
    print(output.resolve())


if __name__ == "__main__":
    main()

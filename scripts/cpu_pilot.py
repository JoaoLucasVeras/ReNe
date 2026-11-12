"""Paired CPU implementation pilot, explicitly not frozen research evaluation."""

from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
from rene.metrics.counterfactual import cancellation_snapshot, evaluate_retention
from rene.policies.rule_based import make_manager
from rene.utils.logging import save_rows
from rene.utils.provenance import source_fingerprint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    parser.add_argument("--output", default="results/raw/cpu-pilot")
    parser.add_argument("--delay-ms", nargs="+", type=float, default=[100])
    parser.add_argument("--loss", nargs="+", type=float, default=[0])
    parser.add_argument("--severity", nargs="+", default=["moderate"])
    parser.add_argument("--trigger-s", nargs="+", type=float, default=[5])
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = Path(args.output) / stamp
    output.mkdir(parents=True, exist_ok=False)
    managers = ["one_shot", "rule_cancel", "paper_cancel_merge_adapted", "matched_heuristic"]
    rows = []
    fingerprint = source_fingerprint()
    config = {}
    manifest = list(
        itertools.product(
            args.seeds,
            ["low", "medium", "high"],
            ["none", "braking", "cut_in", "intent_mismatch"],
            args.delay_ms,
            args.loss,
            args.severity,
            args.trigger_s,
        )
    )
    started = perf_counter()
    for scenario, (seed, density, disturbance, delay, loss, severity, trigger) in enumerate(
        manifest
    ):
        for name in managers:
            sim = MergeLifecycleEnv(
                {
                    **config,
                    "traffic_density": density,
                    "disturbance_type": disturbance,
                    "communication_delay_ms": delay,
                    "packet_loss": loss,
                    "disturbance_severity": severity,
                    "disturbance_trigger_s": trigger,
                }
            )
            manager = make_manager(name)
            obs, info = sim.reset(seed=seed)
            sim.metrics.manager = name
            ramp_violation = False
            snapshot = None
            while True:
                action = manager.act(obs, info)
                if snapshot is None:
                    snapshot = cancellation_snapshot(sim, action)
                obs, _, terminal, truncated, info = sim.step(int(action))
                ramp_violation |= (
                    sim.ramp_y_m > 1e-6
                    and sim.ramp_x_m + sim.config["vehicle_length_m"] / 2
                    > sim.config["ramp_end_m"] + 1e-6
                )
                if terminal or truncated:
                    break
            rows.append(
                {
                    **info["episode_metrics"],
                    "source_fingerprint": fingerprint,
                    "scenario_id": scenario,
                    "density": density,
                    "delay_ms": delay,
                    "packet_loss": loss,
                    "severity": severity,
                    "trigger_s": trigger,
                    "disturbance": disturbance,
                    **evaluate_retention(snapshot),
                    "ramp_end_violation": ramp_violation,
                    "headway_below_configured_min": sim.metrics.min_headway_s
                    < sim.config["min_headway_s"],
                }
            )
            sim.close()
        print(f"paired scenario {scenario + 1}/{len(manifest)} complete", flush=True)
    save_rows(output / "episodes.csv", rows)
    groups = defaultdict(list)
    for row in rows:
        groups[(row["manager"], row["disturbance"])].append(row)
    summary = []
    for (name, disturbance), group in groups.items():
        summary.append(
            {
                "manager": name,
                "disturbance": disturbance,
                "episodes": len(group),
                **{
                    key: sum(bool(r[key]) for r in group)
                    for key in (
                        "collision",
                        "completed_merge",
                        "canceled",
                        "ramp_end_violation",
                        "headway_below_configured_min",
                    )
                },
                "mean_shield_overrides": sum(r["shield_overrides"] for r in group) / len(group),
                "mean_renegotiation_attempts": sum(r["renegotiation_attempts"] for r in group)
                / len(group),
            }
        )
    report = {
        "kind": "implementation_pilot_not_final_evaluation",
        "seeds": args.seeds,
        "conditions": config,
        "source_fingerprint": fingerprint,
        "paired_scenarios": len(manifest),
        "episodes": len(rows),
        "elapsed_s": perf_counter() - started,
        "summary": summary,
        "training_gate_passed": not any(
            row["ramp_end_violation"] or row["collision"] for row in rows
        ),
        "gate_scope": "necessary implementation check, not sufficient scientific validation",
        "remaining_gates": [
            "reactive peer traffic/sensor validation",
            "held-out scenario protocol",
            "counterfactual/fallback definition review",
            "scientific baseline review",
        ],
    }
    (output / "report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    print(output.resolve())


if __name__ == "__main__":
    main()

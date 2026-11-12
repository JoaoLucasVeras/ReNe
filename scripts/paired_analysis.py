"""Paired rate differences; resample independent models and common scenarios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def bootstrap_difference(differences, *, draws=2000, seed=2026):
    values = np.asarray(differences, dtype=float)
    if values.ndim == 1:
        values = values[None, :]
    if values.ndim != 2 or values.shape[1] < 2 or not np.isfinite(values).all():
        raise ValueError("finite model-by-scenario differences with >=2 scenarios required")
    if draws < 100:
        raise ValueError("use at least 100 bootstrap draws")
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(draws):
        models = rng.integers(0, values.shape[0], values.shape[0])
        scenarios = rng.integers(0, values.shape[1], values.shape[1])
        samples.append(values[np.ix_(models, scenarios)].mean())
    low, high = np.quantile(samples, [0.025, 0.975])
    return {
        "mean_difference": float(values.mean()),
        "ci95_low": float(low),
        "ci95_high": float(high),
        "models": values.shape[0],
        "scenarios": values.shape[1],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="One CSV containing identically paired runs")
    parser.add_argument("--reference", default="paper_cancel_merge_adapted")
    parser.add_argument("--output", default="results/summaries/paired_comparison.json")
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    for key in ("source_fingerprint", "input_version", "physics_version", "metrics_version"):
        if key not in data or data[key].isna().any() or data[key].nunique() != 1:
            raise SystemExit(f"absent/mixed {key}")
    if "training_seed" not in data:
        data["training_seed"] = -1
    if data.duplicated(["manager", "training_seed", "scenario_id"]).any():
        raise SystemExit("duplicate manager/model/scenario rows; do not pool unrelated manifests")
    reference = data[data.manager == args.reference].set_index("scenario_id")
    if reference.empty or reference.index.has_duplicates:
        raise SystemExit("reference needs one observation per unique scenario")
    results = []
    for manager, group in data[data.manager != args.reference].groupby("manager"):
        for metric in ("completed_merge", "collision", "ramp_end_violation"):
            matrix = group.pivot(index="training_seed", columns="scenario_id", values=metric)
            if set(matrix.columns) != set(reference.index) or matrix.isna().any().any():
                raise SystemExit("model/scenario manifests do not match the reference")
            difference = matrix.astype(float).to_numpy() - reference.loc[
                matrix.columns, metric
            ].to_numpy(dtype=float)
            results.append(
                {"manager": manager, "metric": metric, **bootstrap_difference(difference)}
            )
    report = {
        "reference": args.reference,
        "interpretation": "candidate minus reference; higher completion good, higher failures bad",
        "method": "paired scenarios; hierarchical resampling when multiple training seeds exist",
        "scope": "uncertainty conditional on sampled scenarios, not real-world safety",
        "zero_event_warning": "Collapsed bootstrap intervals do not bound unseen safety-event risk",
        "results": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(output.resolve())


if __name__ == "__main__":
    main()

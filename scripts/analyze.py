"""Generate reproducible summary tables and plots."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(".matplotlib-cache").resolve()))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/raw")
    parser.add_argument("--output", default="results/summaries")
    args = parser.parse_args()
    files = list(Path(args.input).rglob("episodes.csv"))
    if not files:
        raise SystemExit(f"no episodes.csv files found under {args.input}")
    frames = [pd.read_csv(path).assign(source_run=str(path.parent)) for path in files]
    data = pd.concat(frames, ignore_index=True)
    for version in ("physics_version", "input_version", "metrics_version", "source_fingerprint"):
        if version not in data or data[version].isna().any() or data[version].nunique() != 1:
            raise SystemExit(
                f"refusing to combine absent/mixed {version}; select a single versioned run"
            )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if "traffic_density" not in data and "density" in data:
        data["traffic_density"] = data["density"]
    if "merge_completion_time_s" in data and "completed_merge" in data:
        data.loc[~data["completed_merge"].astype(bool), "merge_completion_time_s"] = float("nan")
    group_cols = [c for c in ["manager", "disturbance", "traffic_density"] if c in data]
    metrics = [
        c
        for c in [
            "collision",
            "ramp_end_violation",
            "near_collision",
            "completed_merge",
            "failed_agreement_duration_s",
            "unnecessary_cancellation",
            "shield_overrides",
            "merge_completion_time_s",
        ]
        if c in data
    ]
    summary = data.groupby(group_cols, dropna=False)[metrics].agg(["count", "mean", "std"])
    summary.to_csv(output / "summary.csv")
    if "manager" in data and "failed_agreement_duration_s" in data:
        plt.figure(figsize=(9, 5))
        sns.boxplot(data=data, x="manager", y="failed_agreement_duration_s")
        plt.xticks(rotation=20, ha="right")
        plt.tight_layout()
        plt.savefig(output / "failed_agreement_duration.png", dpi=180)
        plt.close()
    print(output.resolve())


if __name__ == "__main__":
    main()

"""Final comparison tables with paired, hierarchical bootstrap intervals.

Reads every episodes.csv under --input (one final_eval run per manager/model) and writes
a JSON report: overall rates, rates by ramp length and role, and paired differences of
each candidate against each reference on completion, agreement completion,
cancellation, collision and ramp-end violation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from paired_analysis import bootstrap_difference

METRICS = ("completed_merge", "agreement_completion", "canceled", "collision",
           "ramp_end_violation")
REFERENCES = ("one_shot", "paper_cancel_merge_adapted")


def load(root: str) -> pd.DataFrame:
    frames = [pd.read_csv(p) for p in Path(root).rglob("episodes.csv")]
    data = pd.concat(frames, ignore_index=True)
    for key in ("source_fingerprint", "input_version", "physics_version", "metrics_version"):
        if data[key].nunique() != 1:
            raise SystemExit(f"mixed {key}")
    if data.duplicated(["manager", "training_seed", "scenario_id"]).any():
        raise SystemExit("duplicate manager/model/scenario rows")
    data["agreement_completion"] = (data.completion_mode == "agreement").astype(float)
    for m in METRICS:
        data[m] = data[m].astype(float)
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/raw/final")
    parser.add_argument("--output", default="results/summaries/final_report.json")
    args = parser.parse_args()
    data = load(args.input)
    report = {
        "episodes_per_manager": data.groupby(["manager", "training_seed"]).size()
        .groupby("manager").sum().to_dict(),
        "learned_seeds": sorted(data[data.manager == "learned"].training_seed.unique().tolist()),
        "overall": data.groupby("manager")[list(METRICS)].mean().round(4).to_dict("index"),
        "by_ramp_end_m": {
            m: data.groupby(["ramp_end_m", "manager"])[m].mean().unstack().round(4)
            .to_dict("index") for m in ("completed_merge", "agreement_completion")
        },
        "by_ramp_role": {
            m: data.groupby(["ramp_role", "manager"])[m].mean().unstack().round(4)
            .to_dict("index") for m in ("completed_merge", "agreement_completion")
        },
        "learned_by_seed": data[data.manager == "learned"].groupby("training_seed")
        [list(METRICS)].mean().round(4).to_dict("index"),
        "paired": [],
        "scope": "synthetic simulator; intervals are conditional on sampled scenarios",
    }
    for ref in REFERENCES:
        base = data[data.manager == ref].set_index("scenario_id")
        for cand, group in data[data.manager != ref].groupby("manager"):
            for metric in METRICS:
                matrix = group.pivot(index="training_seed", columns="scenario_id", values=metric)
                diff = matrix.to_numpy() - base.loc[matrix.columns, metric].to_numpy()
                report["paired"].append({"reference": ref, "candidate": cand, "metric": metric,
                                         **bootstrap_difference(diff, draws=1000)})
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=float), encoding="utf-8")
    for row in report["paired"]:
        print(f"{row['candidate'][:20]:20} vs {row['reference'][:12]:12} {row['metric']:22} "
              f"{row['mean_difference']*100:+.2f} pp [{row['ci95_low']*100:+.2f}, "
              f"{row['ci95_high']*100:+.2f}]")
    print(out.resolve())


if __name__ == "__main__":
    main()

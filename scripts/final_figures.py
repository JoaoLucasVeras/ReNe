"""Figures for the final comparison, from results/summaries/final_report.json."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

NAMES = {"one_shot": "Never cancel\n(B1)", "learned": "AI\n(B4)",
         "paper_cancel_merge_adapted": "Paper's rule\n(B2)",
         "matched_heuristic": "Timing rule\n(B3)", "rule_cancel": "Threshold\nrule"}
COLORS = {"one_shot": "#4C78A8", "learned": "#F58518", "paper_cancel_merge_adapted": "#54A24B",
          "matched_heuristic": "#B279A2", "rule_cancel": "#9D9D9D"}


def main():
    r = json.loads(Path("results/summaries/final_report.json").read_text(encoding="utf-8"))
    out = Path("results/figures")
    out.mkdir(parents=True, exist_ok=True)
    order = list(NAMES)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = range(len(order))
    done = [r["overall"][m]["completed_merge"] * 100 for m in order]
    agree = [r["overall"][m]["agreement_completion"] * 100 for m in order]
    ax.bar([i - 0.2 for i in x], done, 0.4, label="Merge completed (any way)", color="#BBBBBB")
    ax.bar([i + 0.2 for i in x], agree, 0.4, label="Completed through the deal",
           color=[COLORS[m] for m in order])
    for i, (a, b) in enumerate(zip(done, agree, strict=True)):
        ax.text(i - 0.2, a + 0.8, f"{a:.1f}", ha="center", fontsize=8)
        ax.text(i + 0.2, b + 0.8, f"{b:.1f}", ha="center", fontsize=8)
    ax.set_xticks(list(x), [NAMES[m] for m in order], fontsize=9)
    ax.set_ylabel("% of 7,680 test scenarios")
    ax.set_ylim(0, 60)
    ax.set_title("Same success rate for every strategy; never-cancel keeps the most deals")
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "final_overall.png", dpi=150)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    by = r["by_ramp_end_m"]["agreement_completion"]
    ramps = sorted(by, key=float)
    for m in ("one_shot", "learned", "paper_cancel_merge_adapted"):
        ax.plot([float(k) for k in ramps], [by[k][m] * 100 for k in ramps], marker="o",
                label=NAMES[m].replace("\n", " "), color=COLORS[m])
    ax.axvspan(255, 305, color="#EEEEEE", zorder=0)
    ax.text(280, 30.5, "decision band\n(280 m never trained on)", ha="center", fontsize=8)
    ax.set_xlabel("Ramp length (m)")
    ax.set_ylabel("% merged through the deal")
    ax.set_title("Strategies only differ on 270-300 m ramps")
    ax.legend(fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "final_by_ramp.png", dpi=150)

    fig, ax = plt.subplots(figsize=(8, 3.8))
    picks = [("learned", "one_shot", "AI vs Never cancel"),
             ("learned", "paper_cancel_merge_adapted", "AI vs Paper's rule"),
             ("paper_cancel_merge_adapted", "one_shot", "Paper's rule vs Never cancel")]
    for i, (c, ref, _label) in enumerate(picks):
        p = next(p for p in r["paired"] if p["metric"] == "agreement_completion"
                 and p["candidate"] == c and p["reference"] == ref)
        m, lo, hi = (p[k] * 100 for k in ("mean_difference", "ci95_low", "ci95_high"))
        ax.errorbar(m, i, xerr=[[m - lo], [hi - m]], fmt="o", color="#333333", capsize=4)
        ax.text(hi + 0.15, i, f"{m:+.1f} pts", va="center", fontsize=9)
    ax.axvline(0, color="#999999", lw=1)
    ax.set_yticks(range(len(picks)), [p[2] for p in picks])
    ax.set_xlabel("Difference in % merged through the deal (95% interval)")
    ax.set_title("AI beats the paper's rule, but not never-cancelling")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "final_differences.png", dpi=150)
    print("saved", sorted(p.name for p in out.glob("final_*.png")))


if __name__ == "__main__":
    main()

"""Measure how much the common safety shield determines ReNe outcomes.

Development diagnostic only (dev seeds, not the reserved 1001-1005 evaluation seeds).
For each paired scenario and manager it records:
  - every decision's requested vs applied action and override reason
  - who initiated the cancellation (manager vs shield)
  - for the first CONTINUE->CANCEL feasibility override, an offline UNSHIELDED
    hold-CONTINUE counterfactual: did invalidity clear, and was continuing unsafe?
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

import rene.envs.merge_lifecycle_env as env_module
from rene.agreements.state import ManagerAction
from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
from rene.policies.rule_based import make_manager
from rene.safety.shield import ShieldDecision, apply_shield

MANAGERS = [
    "one_shot",
    "paper_cancel_merge_adapted",
    "matched_heuristic",
    "random_all",
    "random_valid",
]


class RandomManager:
    def __init__(self, actions, seed):
        self.actions = actions
        self.rng = np.random.default_rng(seed)

    def act(self, obs, info):
        return self.actions[int(self.rng.integers(len(self.actions)))]


def manager_for(name, seed):
    if name == "random_all":
        return RandomManager(list(ManagerAction), seed)
    if name == "random_valid":
        return RandomManager(
            [
                ManagerAction.CONTINUE,
                ManagerAction.CANCEL,
                ManagerAction.RENEGOTIATE_DELAY,
                ManagerAction.RENEGOTIATE_ADVANCE,
            ],
            seed,
        )
    return make_manager(name)


def passthrough_shield(action, feasibility, *, renegotiation_feasible):
    if action.family == "renegotiate" and not renegotiation_feasible:
        return apply_shield(action, feasibility, renegotiation_feasible=False)
    return ShieldDecision(action, action, False, "unshielded_counterfactual")


def unshielded_hold_continue(snapshot):
    """Offline only: hold CONTINUE with the CONTINUE->CANCEL override disabled."""
    original = env_module.apply_shield
    env_module.apply_shield = passthrough_shield
    try:
        start = snapshot.time_s
        recovered_after = None
        while True:
            _, _, terminal, truncated, info = snapshot.step(int(ManagerAction.CONTINUE))
            if recovered_after is None and snapshot._feasibility().feasible:
                recovered_after = round(snapshot.time_s - start, 2)
            if terminal or truncated:
                break
    finally:
        env_module.apply_shield = original
    m = info["episode_metrics"]
    return {
        "cf_recovered_after_s": recovered_after,
        "cf_collision": bool(snapshot.collision),
        "cf_ramp_end": bool(snapshot.ramp_end_violation),
        "cf_agreement_completed": bool(snapshot.completed and not snapshot.fallback_active),
        "cf_min_ttc_s": m["min_ttc_s"],
        "cf_min_headway_s": m["min_headway_s"],
    }


ENV_OVERRIDES = {}


def run_scenario(args):
    scenario_id, (seed, density, disturbance, delay, loss, severity, trigger), overrides = args
    rows, decisions = [], []
    for name in MANAGERS:
        sim = MergeLifecycleEnv(
            {
                **overrides,
                "traffic_density": density,
                "disturbance_type": disturbance,
                "communication_delay_ms": delay,
                "packet_loss": loss,
                "disturbance_severity": severity,
                "disturbance_trigger_s": trigger,
            }
        )
        manager = manager_for(name, seed * 1000 + scenario_id)
        obs, info = sim.reset(seed=seed)
        cf = {}
        cancel_initiator = None
        while True:
            action = ManagerAction(int(manager.act(obs, info)))
            pre_canceled = sim.canceled
            snapshot = None
            if (
                not cf
                and not sim.canceled
                and action == ManagerAction.CONTINUE
                and not sim._feasibility().feasible
            ):
                snapshot = deepcopy(sim)
            obs, _, terminal, truncated, info = sim.step(int(action))
            d = sim._decision_log[-1]
            decisions.append(
                {
                    "manager": name,
                    "scenario_id": scenario_id,
                    "disturbance": disturbance,
                    "requested": d["requested_action"],
                    "applied": d["applied_action"],
                    "overridden": d["overridden"],
                    "reason": d["override_reason"],
                }
            )
            if not pre_canceled and sim.canceled and cancel_initiator is None:
                if not d["overridden"]:
                    cancel_initiator = "manager"
                elif d["requested_action"] == "CONTINUE":
                    cancel_initiator = "shield_infeasible"
                else:
                    cancel_initiator = "shield_bad_renegotiation"
            if snapshot is not None and d["overridden"]:
                cf = {
                    "cf_reason": d["override_reason"],
                    "cf_time_s": round(d["decision_time_s"], 2),
                    **unshielded_hold_continue(snapshot),
                }
            if terminal or truncated:
                break
        m = info["episode_metrics"]
        rows.append(
            {
                "scenario_id": scenario_id,
                "manager": name,
                "seed": seed,
                "density": density,
                "disturbance": disturbance,
                "delay_ms": delay,
                "loss": loss,
                "severity": severity,
                "collision": m["collision"],
                "ramp_end": m["ramp_end_violation"],
                "completion_mode": m["completion_mode"],
                "canceled": m["canceled"],
                "cancel_at_s": m["cancel_requested_at_s"],
                "cancel_initiator": cancel_initiator,
                "merge_time_s": round(m["merge_completion_time_s"], 2),
                "shield_overrides": m["shield_overrides"],
                "renegotiation_attempts": m["renegotiation_attempts"],
                **cf,
            }
        )
        sim.close()
    return rows, decisions


def outcome(r):
    return (
        r["completion_mode"],
        r["collision"],
        r["ramp_end"],
        r["canceled"],
        r["cancel_at_s"],
        r["merge_time_s"],
    )


def summarize(rows, decisions):
    out = {}
    by_mgr = defaultdict(list)
    for r in rows:
        by_mgr[r["manager"]].append(r)
    dec_by_mgr = defaultdict(list)
    for d in decisions:
        dec_by_mgr[d["manager"]].append(d)
    for name in MANAGERS:
        rs, ds = by_mgr[name], dec_by_mgr[name]
        n = len(rs)
        cf = [r for r in rs if "cf_reason" in r]
        out[name] = {
            "episodes": n,
            "decisions": len(ds),
            "decision_override_rate": round(sum(d["overridden"] for d in ds) / len(ds), 3),
            "override_reasons": dict(Counter(d["reason"] for d in ds if d["overridden"])),
            "episodes_canceled": sum(r["canceled"] for r in rs),
            "cancel_initiator": dict(Counter(r["cancel_initiator"] for r in rs if r["canceled"])),
            "completion_mode": dict(Counter(r["completion_mode"] for r in rs)),
            "collisions": sum(r["collision"] for r in rs),
            "ramp_end": sum(r["ramp_end"] for r in rs),
            "shield_infeasible_overrides_with_counterfactual": len(cf),
            "cf_infeasibility_cleared": sum(r["cf_recovered_after_s"] is not None for r in cf),
            "cf_cleared_within_1s": sum((r["cf_recovered_after_s"] or 99) <= 1.0 for r in cf),
            "cf_unshielded_collision": sum(r["cf_collision"] for r in cf),
            "cf_unshielded_ramp_end": sum(r["cf_ramp_end"] for r in cf),
            "cf_unshielded_agreement_completed_safely": sum(
                r["cf_agreement_completed"] and not r["cf_collision"] and not r["cf_ramp_end"]
                for r in cf
            ),
            "cf_unshielded_min_ttc_below_1s": sum(r["cf_min_ttc_s"] < 1.0 for r in cf),
        }
    scen = defaultdict(dict)
    for r in rows:
        scen[r["scenario_id"]][r["manager"]] = r
    pairs = [
        ("one_shot", "paper_cancel_merge_adapted"),
        ("paper_cancel_merge_adapted", "matched_heuristic"),
        ("one_shot", "matched_heuristic"),
    ]
    out["identical_outcome_fraction"] = {
        f"{a} vs {b}": round(
            sum(outcome(s[a]) == outcome(s[b]) for s in scen.values()) / len(scen), 3
        )
        for a, b in pairs
    }
    per_dist = defaultdict(lambda: [0, 0])
    for s in scen.values():
        d = s["one_shot"]["disturbance"]
        per_dist[d][0] += outcome(s["paper_cancel_merge_adapted"]) == outcome(
            s["matched_heuristic"]
        )
        per_dist[d][1] += 1
    out["B2_vs_B3_identical_by_disturbance"] = {k: f"{v[0]}/{v[1]}" for k, v in per_dist.items()}
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    p.add_argument("--delay-ms", nargs="+", type=float, default=[100, 800])
    p.add_argument("--loss", nargs="+", type=float, default=[0, 0.2])
    p.add_argument("--severity", nargs="+", default=["moderate", "hard"])
    p.add_argument("--trigger-s", nargs="+", type=float, default=[5])
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--output", default="results/raw/shield-measurement")
    p.add_argument("--env", default="{}", help="JSON environment overrides")
    a = p.parse_args()
    grid = list(
        itertools.product(
            a.seeds,
            ["low", "medium", "high"],
            ["none", "braking", "cut_in", "intent_mismatch"],
            a.delay_ms,
            a.loss,
            a.severity,
            a.trigger_s,
        )
    )
    rows, decisions = [], []
    with ProcessPoolExecutor(a.workers) as pool:
        for i, (r, d) in enumerate(
            pool.map(
                run_scenario, [(i, g, json.loads(a.env)) for i, g in enumerate(grid)], chunksize=4
            )
        ):
            rows += r
            decisions += d
            if (i + 1) % 24 == 0:
                print(f"{i + 1}/{len(grid)} scenarios", flush=True)
    out = Path(a.output) / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True)
    import csv

    keys = sorted({k for r in rows for k in r})
    with open(out / "episodes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    summary = summarize(rows, decisions)
    summary["grid"] = vars(a)
    summary["scenarios"] = len(grid)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    print(out.resolve())


if __name__ == "__main__":
    main()

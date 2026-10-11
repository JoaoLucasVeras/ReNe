"""CPU-only diagnostic traces for the prototype; not scientific validation.

Run: python scripts/audit_simulator.py
Prints JSON to stdout without changing the simulator or writing result files.
"""

from __future__ import annotations

import json
import math

from rene.agreements.state import ManagerAction
from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
from rene.policies.rule_based import make_manager


def json_safe(value):
    """Serialize non-applicable/infinite safety times as null, not fake durations."""
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def episode(manager_name: str, disturbance: str, loss: float = 0.0) -> dict:
    env = MergeLifecycleEnv()
    obs, info = env.reset(
        seed=42,
        options={
            "disturbance_type": disturbance,
            "communication_delay_ms": 0,
            "packet_loss": loss,
        },
    )
    initial = {
        "ramp_x_m": env.ramp_x_m,
        "front_x_m": env.front_x_m,
        "rear_x_m": env.rear_x_m,
        "gap_m": env.gap_m,
        "ttc_s": env.ttc_s,
    }
    manager = make_manager(manager_name)
    trace = []
    while True:
        decision_time = env.time_s
        obs, _, terminated, truncated, info = env.step(int(manager.act(obs, info)))
        trace.append(
            {
                "decision_time_s": round(decision_time, 3),
                "record": env._decision_log[-1],
                "front_x_m": env.front_x_m,
                "rear_x_m": env.rear_x_m,
                "ramp_x_m": env.ramp_x_m,
            }
        )
        if terminated or truncated:
            break
    result = {
        "manager": manager_name,
        "disturbance": disturbance,
        "loss": loss,
        "initial": initial,
        "metrics": info["episode_metrics"],
        "trace": trace,
    }
    env.close()
    return result


def targeted_probes() -> dict:
    env = MergeLifecycleEnv()
    env.reset(seed=42, options={"disturbance_type": "none", "packet_loss": 0.0})
    _, _, _, _, info = env.step(int(ManagerAction.CONTINUE))
    first_second = {"ttc_s": env.ttc_s, "rear_x_m": env.rear_x_m}
    before = env.gap_m
    env.step(int(ManagerAction.RENEGOTIATE_NEXT_GAP))
    next_gap = {
        "gap_before_m": before,
        "gap_after_m": env.gap_m,
        "synthetic_bonus_m": env.synthetic_gap_bonus_m,
        "physical_front_minus_rear_m": env.front_x_m - env.rear_x_m,
    }
    env.close()

    env = MergeLifecycleEnv(config={"duration_s": 1.0})
    env.reset(seed=42, options={"disturbance_type": "none"})
    _, _, terminated, truncated, info = env.step(int(ManagerAction.CONTINUE))
    timeout = {
        "terminated": terminated,
        "truncated": truncated,
        "completion_time_s": info["episode_metrics"]["merge_completion_time_s"],
    }
    env.close()

    ages = []
    env = MergeLifecycleEnv()
    env.reset(seed=42, options={"disturbance_type": "none", "packet_loss": 1.0})
    for _ in range(3):
        env.step(int(ManagerAction.CONTINUE))
        ages.append(max(env.communication.ages(env.time_s).values()))
    env.close()
    return {
        "after_one_second": first_second,
        "next_gap": next_gap,
        "timeout": timeout,
        "complete_outage_ages_s": ages,
    }


def main() -> None:
    episodes = [
        episode(manager, disturbance)
        for manager in ("one_shot", "rule_cancel", "heuristic_renegotiate")
        for disturbance in ("none", "cut_in", "braking", "intent_mismatch")
    ]
    episodes.extend(episode("one_shot", "none", loss) for loss in (0.0, 1.0))
    print(
        json.dumps(
            json_safe({"episodes": episodes, "probes": targeted_probes()}),
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()

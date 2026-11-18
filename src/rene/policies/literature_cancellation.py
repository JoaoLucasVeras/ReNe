"""Declared operationalizations, not an exact published-system reproduction."""

from math import isfinite

from rene.agreements.state import ManagerAction
from rene.envs.manager_inputs import decode
from rene.prediction.rollouts import STATUS_NAMES, Prediction


def reference_incentive(desired: float, current: float, target: float) -> float:
    if any(not isfinite(v) or v < 0 for v in (desired, current, target)):
        raise ValueError("lane-speed estimates must be finite and nonnegative")
    return min(target, desired) - min(current, desired)


def adapted_decision(keep: Prediction, fallback: Prediction, margin_s: float = 0):
    if keep.status == fallback.status == "SAFE_COMPLETION":
        benefit = fallback.completion_s - keep.completion_s
        if benefit < -margin_s:
            return ManagerAction.CANCEL, "accepted_plan_slower"
        return ManagerAction.CONTINUE, "retained_or_tied"
    if keep.status == "INFEASIBLE" and fallback.status == "SAFE_COMPLETION":
        return ManagerAction.CANCEL, "accepted_plan_infeasible"
    if keep.status == "NO_COMPLETION" and fallback.status == "SAFE_COMPLETION":
        # Spec section 4: demonstrated inability to complete before the usable ramp end.
        return ManagerAction.CANCEL, "accepted_plan_cannot_complete"
    if keep.status == "SAFE_COMPLETION":
        return ManagerAction.CONTINUE, "retained_safe_plan"
    return ManagerAction.CONTINUE, "prediction_unresolved"


class PaperCancelMergeAdapted:
    def __init__(self):
        self.last_decision = None

    def act(self, observation, info):
        values = decode(observation)
        if values["local_canceled"] > 0.5:
            return ManagerAction.CANCEL
        keep, fallback = prediction_pair(values)
        action, reason = adapted_decision(keep, fallback)
        self.last_decision = {"keep": keep, "fallback": fallback, "reason": reason}
        return action


def prediction_pair(values):
    return tuple(
        Prediction(
            STATUS_NAMES[round(values[f"{prefix}_status"])],
            values[f"{prefix}_completion_s"] or None,
            "shared_received_prediction",
            0,
        )
        for prefix in ("keep", "fallback")
    )


class MatchedHeuristic(PaperCancelMergeAdapted):
    """Deterministically rank the same feasible timing actions offered to PPO."""

    def act(self, observation, info):
        values = decode(observation)
        baseline = super().act(observation, info)
        if values["local_canceled"] > 0.5 or values["proposal_pending"] > 0.5:
            return baseline
        candidates = [
            (values[f"{prefix}_completion_s"], action)
            for prefix, action in (
                ("advance", ManagerAction.RENEGOTIATE_ADVANCE),
                ("delay", ManagerAction.RENEGOTIATE_DELAY),
            )
            if values[f"{prefix}_feasible"] > 0.5
        ]
        if not candidates:
            return baseline
        best_time, best_action = min(candidates)
        keep, fallback = prediction_pair(values)
        reference = fallback if baseline == ManagerAction.CANCEL else keep
        if reference.status != "SAFE_COMPLETION" or best_time + 0.05 < reference.completion_s:
            return best_action
        return baseline

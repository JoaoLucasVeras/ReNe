"""One shared bounded timing menu. No synthetic next gap or order swap."""

from dataclasses import dataclass

from rene.agreements.state import ManagerAction
from rene.prediction.rollouts import Prediction, predict


@dataclass(frozen=True)
class TimingCandidate:
    action: ManagerAction
    delta_s: float
    planned_at_s: float
    prediction: Prediction


def timing_candidates(values: dict, config: dict) -> tuple[TimingCandidate, ...]:
    if (
        not config["enable_timing_revisions"]
        or values["local_canceled"] > 0.5
        or values["proposal_pending"] > 0.5
        or round(values["renegotiation_count"]) >= config["max_renegotiations"]
        or values["ego_lateral_m"] < config["lane_width_m"] - 1e-5
    ):
        return ()
    candidates = []
    for action, delta in (
        (ManagerAction.RENEGOTIATE_DELAY, 1.0),
        (ManagerAction.RENEGOTIATE_ADVANCE, -1.0),
    ):
        planned = values["time_s"] + values["remaining_plan_s"] + delta
        # Leave one second for the abstract proposal handshake, independent of
        # hidden channel parameters; later delivery is checked at activation.
        if planned - config["lane_change_duration_s"] / 2 <= values["time_s"] + 1:
            continue
        result = predict(values, config, plan_delta_s=delta)
        if result.status == "SAFE_COMPLETION":
            candidates.append(TimingCandidate(action, delta, planned, result))
    return tuple(candidates)

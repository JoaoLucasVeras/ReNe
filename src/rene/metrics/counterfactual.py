"""Offline oracle only. Never pass true future or oracle labels to policies."""

from copy import deepcopy

from rene.agreements.state import ManagerAction


def cancellation_snapshot(sim, action):
    if sim.canceled:
        return None
    action = ManagerAction(int(action))
    cancels = (
        action == ManagerAction.CANCEL
        or (action == ManagerAction.CONTINUE and not sim._feasibility().feasible)
        or (action.family == "renegotiate" and not sim._renegotiation_feasible(action))
    )
    return deepcopy(sim) if cancels else None


def evaluate_retention(snapshot):
    """Hold CONTINUE under the common shield until the same episode deadline.

    True future/RNG cloning is permitted only for this offline outcome. Pending
    reservations are excluded because this label refers to the accepted revision.
    """
    if snapshot is None:
        return {"unnecessary_cancellation": None, "cancellation_label_status": "not_canceled"}
    if snapshot.revision_session.state == "pending":
        return {
            "unnecessary_cancellation": None,
            "cancellation_label_status": "pending_proposal_not_identified",
        }
    revision = snapshot.agreement.revision
    while True:
        _, _, terminal, truncated, _ = snapshot.step(int(ManagerAction.CONTINUE))
        if terminal or truncated:
            break
    retained = (
        snapshot.completed
        and not snapshot.canceled
        and not snapshot.fallback_active
        and snapshot.agreement.revision == revision
    )
    return {
        "unnecessary_cancellation": retained,
        "cancellation_label_status": "offline_hold_continue_v1",
        "counterfactual_completed": snapshot.completed,
        "counterfactual_canceled": snapshot.canceled,
        "counterfactual_ramp_failure": snapshot.ramp_end_violation,
    }

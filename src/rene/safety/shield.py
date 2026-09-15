"""Action-level deterministic safety shield."""

from __future__ import annotations

from dataclasses import dataclass

from rene.agreements.feasibility import FeasibilityResult
from rene.agreements.state import ManagerAction


@dataclass(frozen=True, slots=True)
class ShieldDecision:
    requested: ManagerAction
    applied: ManagerAction
    overridden: bool
    reason: str


def apply_shield(
    action: ManagerAction,
    feasibility: FeasibilityResult,
    *,
    renegotiation_feasible: bool,
) -> ShieldDecision:
    if action == ManagerAction.CONTINUE and not feasibility.feasible:
        return ShieldDecision(action, ManagerAction.CANCEL, True, feasibility.reason)
    if action.family == "renegotiate" and not renegotiation_feasible:
        return ShieldDecision(action, ManagerAction.CANCEL, True, "counterproposal_infeasible")
    return ShieldDecision(action, action, False, "accepted")

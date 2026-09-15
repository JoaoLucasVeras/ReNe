"""Agreement lifecycle state and action definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum


class AgreementState(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    EXECUTING = "executing"
    RENEGOTIATING = "renegotiating"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"


class ManagerAction(IntEnum):
    CONTINUE = 0
    CANCEL = 1
    RENEGOTIATE_DELAY = 2
    RENEGOTIATE_ADVANCE = 3
    RENEGOTIATE_NEXT_GAP = 4
    RENEGOTIATE_SWAP_ORDER = 5

    @property
    def family(self) -> str:
        return "renegotiate" if self.value >= 2 else self.name.lower()


LEGAL_TRANSITIONS: dict[AgreementState, set[AgreementState]] = {
    AgreementState.PROPOSED: {AgreementState.ACCEPTED, AgreementState.CANCELED},
    AgreementState.ACCEPTED: {
        AgreementState.EXECUTING,
        AgreementState.RENEGOTIATING,
        AgreementState.CANCELED,
    },
    AgreementState.EXECUTING: {
        AgreementState.RENEGOTIATING,
        AgreementState.COMPLETED,
        AgreementState.CANCELED,
        AgreementState.FAILED,
    },
    AgreementState.RENEGOTIATING: {
        AgreementState.EXECUTING,
        AgreementState.CANCELED,
        AgreementState.FAILED,
    },
    AgreementState.COMPLETED: set(),
    AgreementState.CANCELED: set(),
    AgreementState.FAILED: set(),
}


@dataclass(slots=True)
class Agreement:
    agreement_id: str
    episode_id: str
    participants: tuple[str, ...]
    target_gap_id: int
    merge_order: int
    planned_merge_time_s: float
    accepted_at_s: float
    state: AgreementState = AgreementState.ACCEPTED
    revision: int = 0
    message_count: int = 2
    renegotiation_count: int = 0
    last_requested_action: ManagerAction = ManagerAction.CONTINUE
    last_applied_action: ManagerAction = ManagerAction.CONTINUE
    feasible: bool = True
    feasibility_reason: str = "initially_feasible"
    history: list[tuple[float, AgreementState]] = field(default_factory=list)

    def transition(self, new_state: AgreementState, at_s: float) -> None:
        if new_state not in LEGAL_TRANSITIONS[self.state]:
            raise ValueError(f"illegal agreement transition: {self.state} -> {new_state}")
        self.state = new_state
        self.history.append((at_s, new_state))

    def revise(self, action: ManagerAction, at_s: float) -> None:
        if action.family != "renegotiate":
            raise ValueError("revision requires a renegotiation action")
        if self.state not in {AgreementState.ACCEPTED, AgreementState.EXECUTING}:
            raise ValueError(f"cannot revise agreement in state {self.state}")
        self.transition(AgreementState.RENEGOTIATING, at_s)
        self.revision += 1
        self.renegotiation_count += 1
        self.message_count += 2

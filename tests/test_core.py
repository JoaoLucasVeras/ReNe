import numpy as np
import pytest

from rene.agreements.feasibility import FeasibilityResult, evaluate_feasibility
from rene.agreements.protocol import create_accepted_agreement
from rene.agreements.state import AgreementState, ManagerAction
from rene.disturbances.base import DisturbanceState
from rene.safety.shield import apply_shield


def test_agreement_lifecycle_and_revision():
    agreement = create_accepted_agreement("episode")
    agreement.transition(AgreementState.EXECUTING, 0.0)
    agreement.revise(ManagerAction.RENEGOTIATE_NEXT_GAP, 1.0)
    assert agreement.revision == 1
    agreement.transition(AgreementState.EXECUTING, 1.0)
    agreement.transition(AgreementState.COMPLETED, 5.0)


def test_illegal_transition_rejected():
    agreement = create_accepted_agreement("episode")
    with pytest.raises(ValueError):
        agreement.transition(AgreementState.COMPLETED, 0.0)


def test_small_gap_is_infeasible_and_continue_is_blocked():
    result = evaluate_feasibility(
        gap_m=5.0,
        ttc_s=10.0,
        headway_s=2.0,
        distance_to_merge_m=50.0,
        speed_mps=20.0,
        min_gap_m=12.0,
        min_ttc_s=2.0,
        min_headway_s=0.8,
    )
    assert not result.feasible
    decision = apply_shield(
        ManagerAction.CONTINUE,
        FeasibilityResult(False, result.reason),
        renegotiation_feasible=False,
    )
    assert decision.applied == ManagerAction.CANCEL


def test_seeded_packet_delivery_is_reproducible():
    first = DisturbanceState("cut_in", trigger_s=2.0, packet_loss=0.5)
    second = DisturbanceState("cut_in", trigger_s=2.0, packet_loss=0.5)
    first.update(2.0, np.random.default_rng(7))
    second.update(2.0, np.random.default_rng(7))
    assert first.triggered
    assert first.message_received == second.message_received

import pytest

from rene.agreements.communication import CommunicationModel, Message
from rene.agreements.revision import RevisionSession
from rene.agreements.state import ManagerAction
from rene.envs.merge_lifecycle_env import MergeLifecycleEnv


def setup(delay=0.1, loss=0):
    comm = CommunicationModel(42, "a", delay, loss)
    comm.revision_session = RevisionSession(comm.bus, "a")
    comm.revision_session.request(0, 1, 6)

    def sample(at):
        return {peer: {"x_m": 0, "speed_mps": 25} for peer in ("mainline_front", "mainline_rear")}

    return comm, comm.revision_session, sample


@pytest.mark.parametrize("delay", [0, 0.05, 0.1, 0.4])
def test_acceptance_requires_both_delivered_replies(delay):
    comm, session, sample = setup(delay)
    if delay > 0:
        comm.advance(delay * 1.9, sample)
        assert session.state == "pending"
    comm.advance(delay * 2, sample)
    assert session.state == "accepted"
    assert session.accepted_at_s == pytest.approx(2 * delay)
    assert len(session.acks) == 2


def test_lost_messages_expire_without_fabricated_acceptance():
    comm, session, sample = setup(loss=1)
    comm.advance(1.1, sample)
    assert session.state == "expired"
    assert not session.acks


def test_rejection_and_stale_token_do_not_activate():
    comm, session, sample = setup()
    session.accept_peer = lambda peer, payload, at: False
    comm.advance(0.3, sample)
    assert session.state == "rejected"
    session.receive(
        Message(
            "mainline_front",
            "ramp",
            "timing_reply",
            "a",
            1,
            1,
            0.1,
            0.2,
            {"token": "old", "accepted": True},
        )
    )
    assert not session.acks


def test_cancel_aborts_pending_proposal():
    comm, session, sample = setup()
    comm.advance(0.1, sample)
    session.abort(0.1)
    comm.advance(0.5, sample)
    assert session.state == "aborted"


def test_real_revision_waits_for_acceptance_then_changes_physical_merge_time():
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    sim.reset(seed=42)
    initial_plan = sim.agreement.planned_merge_time_s
    initial_speed = sim.ramp_speed_mps
    sim._apply_lifecycle_action(ManagerAction.RENEGOTIATE_ADVANCE)
    assert sim.agreement.planned_merge_time_s == initial_plan
    assert sim.ramp_speed_mps == initial_speed
    assert sim.agreement.revision == 0
    while True:
        _, _, t, u, info = sim.step(0)
        if t or u:
            break
    assert sim.agreement.revision == 1
    assert sim.agreement.planned_merge_time_s == pytest.approx(initial_plan - 1)
    assert info["episode_metrics"]["completed_merge"]
    assert sim.time_s < 9.2


def test_unaccepted_outage_plan_never_changes():
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 1})
    sim.reset(seed=42)
    original = sim.agreement.planned_merge_time_s
    sim.step(3)
    assert sim.agreement.planned_merge_time_s == original
    assert sim.agreement.revision == 0


def test_duplicate_proposal_does_not_reset_timeout():
    comm, session, sample = setup(loss=1)
    session.request(0.5, 1, 7)
    assert session.deadline_s == 1
    comm.advance(1, sample)
    assert session.state == "expired"


def test_quantized_attempt_count_cannot_exceed_limit():
    from rene.policies.rule_based import make_manager

    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    obs, info = sim.reset(seed=42)
    manager = make_manager("matched_heuristic")
    while True:
        obs, _, t, u, info = sim.step(int(manager.act(obs, info)))
        if t or u:
            break
    assert info["episode_metrics"]["renegotiation_attempts"] == 1
    assert sim.agreement.revision == 1


def test_leaving_ramp_is_a_terminal_failure_not_a_silent_rollout():
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    sim.reset(seed=42)
    sim.ramp_x_m = sim.config["ramp_end_m"]
    _, _, terminated, _, info = sim.step(0)
    assert terminated
    assert info["episode_metrics"]["ramp_end_violation"]
    assert not info["episode_metrics"]["completed_merge"]

from copy import deepcopy

from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
from rene.metrics.counterfactual import cancellation_snapshot, evaluate_retention


def test_unperturbed_early_cancel_is_unnecessary_and_cannot_mutate_live_env():
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    sim.reset(seed=42)
    sim.step(0)
    time, messages = sim.time_s, sim.communication.counts()
    result = evaluate_retention(cancellation_snapshot(sim, 1))
    assert result["unnecessary_cancellation"] is True
    assert sim.time_s == time
    assert sim.communication.counts() == messages
    assert "unnecessary_cancellation" not in sim._info()


def test_shield_required_cancel_does_not_retain_original_agreement():
    sim = MergeLifecycleEnv({"disturbance_type": "cut_in", "packet_loss": 0})
    sim.reset(seed=42)
    for _ in range(6):
        sim.step(0)
    result = evaluate_retention(cancellation_snapshot(sim, 0))
    assert result["unnecessary_cancellation"] is False
    assert result["counterfactual_canceled"]


def test_no_cancellation_has_no_label():
    assert evaluate_retention(None)["unnecessary_cancellation"] is None


def test_pending_proposal_is_explicitly_unavailable():
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    sim.reset(seed=42)
    sim.revision_session.request(0, 1, 6)
    assert evaluate_retention(deepcopy(sim))["unnecessary_cancellation"] is None

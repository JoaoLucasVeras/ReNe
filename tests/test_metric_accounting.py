import pytest

from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
from rene.metrics.invalidity import InvalidityLedger


def test_recovery_does_not_erase_invalid_intervals():
    ledger = InvalidityLedger()
    increments = [ledger.observe(flag, 0.2, 0.3) for flag in [True, True, False, True, True]]
    assert increments == pytest.approx([0, 0.1, 0, 0, 0.1])
    assert ledger.total_s == pytest.approx(0.8)


def test_messages_and_cancellation_are_charged_once():
    sim = MergeLifecycleEnv({"disturbance_type": "none", "packet_loss": 0})
    sim.reset(seed=42)
    for index in range(20):
        _, _, terminated, truncated, info = sim.step(1 if index == 1 else 0)
        if terminated or truncated:
            break
    rows = info["decision_log"]
    metrics = info["episode_metrics"]
    assert sum(row["reward_message"] for row in rows) == pytest.approx(
        -0.01 * metrics["message_count"]
    )
    assert sum(row["reward_cancel"] for row in rows) == pytest.approx(-0.1)
    assert metrics["unnecessary_cancellation"] is None
    assert metrics["cancellation_label_status"] == "counterfactual_not_implemented"


def test_canceled_time_is_not_failed_active_agreement_duration():
    sim = MergeLifecycleEnv({"disturbance_type": "cut_in", "packet_loss": 0})
    sim.reset(seed=42)
    sim.step(1)
    for _ in range(19):
        _, _, t, u, info = sim.step(0)
        if t or u:
            break
    assert info["episode_metrics"]["failed_agreement_duration_s"] == 0

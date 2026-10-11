"""Deterministic Step 3B queue, cache, cancellation and information fixtures."""

from dataclasses import replace

import numpy as np
import pytest

from rene.agreements.communication import PEERS, CommunicationModel, Message, MessageBus
from rene.envs.manager_inputs import FEATURES, decode
from rene.envs.merge_lifecycle_env import MergeLifecycleEnv
from rene.policies.rule_based import RuleCancelManager


def sample(at):
    return {
        PEERS[0]: {"x_m": 30 + 10 * at, "speed_mps": 10},
        PEERS[1]: {"x_m": -30 + 10 * at, "speed_mps": 10},
    }


def model(delay=0.0, loss=0.0):
    result = CommunicationModel(42, "a", delay, loss)
    result.bootstrap(sample(0.0))
    return result


def env(delay=0.0, loss=0.0):
    result = MergeLifecycleEnv(
        config={
            "disturbance_type": "none",
            "packet_loss": loss,
            "communication_delay_ms": delay * 1000,
        }
    )
    result.reset(seed=42)
    return result


def message(**changes):
    base = Message(PEERS[0], "ramp", "beacon", "a", 0, 1, 0.1, 0.2, {"x_m": 31, "speed_mps": 10})
    return replace(base, **changes)


def test_zero_delay_updates_cache_at_generation_time():
    comm = model()
    comm.advance(0.1, sample)
    assert comm.cache[PEERS[0]].sent_at_s == pytest.approx(0.1)
    assert comm.cache[PEERS[0]].payload["x_m"] == 31
    assert comm.ages(0.1)[PEERS[0]] == pytest.approx(0)


def test_delayed_message_does_not_update_before_delivery():
    comm = model(delay=0.35)
    comm.advance(0.44, sample)
    assert comm.cache[PEERS[0]].sequence == 0
    assert comm.ages(0.44)[PEERS[0]] == pytest.approx(0.44)
    comm.advance(0.45, sample)
    assert comm.cache[PEERS[0]].sent_at_s == pytest.approx(0.1)
    assert comm.ages(0.45)[PEERS[0]] == pytest.approx(0.35)


def test_complete_outage_accumulates_age():
    comm = model(loss=1)
    for time in (1, 2, 3):
        comm.advance(time, sample)
        assert comm.ages(time)[PEERS[0]] == pytest.approx(time)
        assert comm.cache[PEERS[0]].sequence == 0
    assert comm.counts() == {"sent": 60, "delivered": 0, "dropped": 60}


def test_recovery_updates_received_state():
    comm = model(loss=1)
    comm.advance(1, sample)
    comm.bus.packet_loss = 0
    comm.advance(1.1, sample)
    assert comm.cache[PEERS[0]].payload["x_m"] == pytest.approx(41)
    assert comm.ages(1.1)[PEERS[0]] == pytest.approx(0)


def test_out_of_order_message_cannot_replace_newer_cache():
    comm = model()
    older = comm.bus.send(
        sender=PEERS[0],
        receiver="ramp",
        kind="beacon",
        agreement_id="a",
        revision=0,
        time_s=0.1,
        payload={"x_m": 31, "speed_mps": 10},
        delay_s=1,
    )
    newer = comm.bus.send(
        sender=PEERS[0],
        receiver="ramp",
        kind="beacon",
        agreement_id="a",
        revision=0,
        time_s=0.2,
        payload={"x_m": 32, "speed_mps": 10},
        delay_s=0,
    )
    for delivered in comm.bus.receive_due(0.2):
        comm.receive(delivered)
    assert comm.cache[PEERS[0]] == newer
    for delivered in comm.bus.receive_due(1.1):
        comm.receive(delivered)
    assert comm.cache[PEERS[0]] != older
    assert comm.cache[PEERS[0]] == newer


def test_duplicate_beacon_is_idempotent():
    comm = model()
    comm.receive(message())
    comm.receive(message())
    assert len([e for e in comm.bus.events if e["event"] == "cache_updated"]) == 1


@pytest.mark.parametrize(
    "changes",
    [{"agreement_id": "wrong"}, {"revision": 1}, {"receiver": "wrong"}, {"sender": "wrong"}],
)
def test_wrong_session_or_route_beacon_is_ignored(changes):
    comm = model()
    comm.receive(message(**changes))
    assert comm.cache[PEERS[0]].sequence == 0


def test_transmission_copies_payload():
    bus = MessageBus(42, 0, 0)
    payload = {"nested": {"x": 1}}
    sent = bus.send(
        sender=PEERS[0],
        receiver="ramp",
        kind="beacon",
        agreement_id="a",
        revision=0,
        time_s=0,
        payload=payload,
    )
    payload["nested"]["x"] = 2
    assert sent.payload["nested"]["x"] == 1


def test_zero_delay_cancellation_confirms_at_same_timestamp():
    comm = model()
    comm.session.request(0)
    comm.advance(0, sample)
    assert comm.session.state == "cancel_confirmed"
    assert comm.session.confirmed_at_s == 0
    assert comm.session.remote_released_at_s == dict.fromkeys(PEERS, 0)


def test_remote_release_precedes_delayed_host_confirmation():
    comm = model(delay=0.15)
    comm.session.request(0)
    comm.advance(0.14, sample)
    assert not comm.session.remote_released_at_s
    comm.advance(0.15, sample)
    assert comm.session.remote_released_at_s == dict.fromkeys(PEERS, 0.15)
    assert comm.session.state == "cancel_pending"
    comm.advance(0.30, sample)
    assert comm.session.state == "cancel_confirmed"
    assert comm.session.confirmed_at_s == pytest.approx(0.30)


@pytest.mark.parametrize("kind", ["cancel", "release_ack"])
def test_lost_first_request_or_reply_recovers_on_retry(kind):
    comm = model(delay=0.02)
    send = comm.bus.send
    dropped = []

    def faulty_send(**kwargs):
        if kwargs["kind"] == kind and not dropped:
            kwargs["drop"] = True
            dropped.append(True)
        return send(**kwargs)

    comm.bus.send = faulty_send
    comm.session.request(0)
    comm.advance(0.5, sample)
    assert comm.session.state == "cancel_confirmed"
    assert comm.session.confirmed_at_s == pytest.approx(0.14)
    assert len([e for e in comm.bus.events if e["event"] == "remote_released"]) == 2


def test_all_packet_loss_times_out_without_remote_release():
    comm = model(loss=1)
    comm.session.request(0)
    comm.advance(1, sample)
    comm.session.request(1)
    assert comm.session.requested_at_s == 0
    assert comm.session.deadline_s == 3
    comm.advance(3, sample)
    assert comm.session.state == "timed_out"
    assert not comm.session.remote_released_at_s
    assert not comm.session.acknowledged
    assert comm.session.timed_out_at_s == 3


def test_delayed_release_ack_at_deadline_beats_timeout():
    comm = model(delay=1.5)
    comm.session.request(0)
    comm.advance(3, sample)
    assert comm.session.state == "cancel_confirmed"
    assert comm.session.confirmed_at_s == 3
    assert comm.session.timed_out_at_s is None


@pytest.mark.parametrize(
    "changes",
    [{"agreement_id": "wrong"}, {"revision": 1}, {"sender": "wrong"}, {"receiver": "wrong"}],
)
def test_stale_or_wrong_ack_cannot_confirm(changes):
    comm = model(loss=1)
    comm.session.request(0)
    comm.receive(
        message(
            kind="release_ack", payload={"request_token": comm.session.request_token}, **changes
        )
    )
    assert not comm.session.acknowledged


def test_ack_after_timeout_does_not_reopen_session():
    comm = model(loss=1)
    comm.session.request(0)
    comm.advance(3, sample)
    comm.receive(message(kind="release_ack", sent_at_s=3, delivery_at_s=4))
    assert comm.session.state == "timed_out"
    assert not comm.session.acknowledged


def test_ack_from_earlier_request_is_ignored():
    comm = model(loss=1)
    comm.session.request(1)
    comm.receive(
        message(
            kind="release_ack", payload={"request_token": "old"}, sent_at_s=1.1, delivery_at_s=1.2
        )
    )
    assert not comm.session.acknowledged


def test_beacon_drop_stream_independent_of_cancellation():
    first, second = model(loss=0.4), model(loss=0.4)
    second.session.request(0)
    for comm in (first, second):
        comm.advance(3, sample)
    traces = [
        [
            (e["event"], e["sender"], e["sent_at_s"], e["sequence"])
            for e in comm.bus.events
            if e.get("kind") == "beacon"
        ]
        for comm in (first, second)
    ]
    assert traces[0] == traces[1]


def test_scheduler_uses_100ms_events_inside_200ms_dynamics():
    comm = model(delay=0.05)
    comm.advance(0.2, sample)
    delivered = [e["time_s"] for e in comm.bus.events if e["event"] == "delivered"]
    assert delivered == pytest.approx([0.15, 0.15])


def test_rules_receive_exactly_the_encoded_policy_information():
    sim = env(delay=0.3)
    obs, _, _, _, info = sim.step(0)
    assert obs.shape == (len(FEATURES),)
    assert info["manager_inputs"] == decode(obs)
    assert "disturbance" not in info
    assert "remote_released_at_s" not in info
    assert "actual_headway_s" not in info


def test_neighbor_truth_and_mismatch_diagnostics_do_not_leak_into_observations():
    sim = env(loss=1)
    before = sim._observation()
    sim.front_x_m += 100
    sim.front_speed_mps = 8
    sim._intent_position_error_m = 999
    assert np.array_equal(before, sim._observation())
    assert sim._info()["manager_inputs"]["front_speed_mps"] == pytest.approx(25)


def test_received_speed_updates_only_after_delivery():
    sim = env(delay=1.2)
    sim.front_speed_mps = 18
    _, _, _, _, info = sim.step(0)
    assert info["manager_inputs"]["front_speed_mps"] == pytest.approx(25)
    _, _, _, _, info = sim.step(0)
    assert info["manager_inputs"]["front_speed_mps"] == pytest.approx(18)


def test_environment_outage_age_is_real_and_rule_cancels():
    sim = env(loss=1)
    obs, _, _, _, info = sim.step(0)
    assert info["manager_inputs"]["message_age_s"] == pytest.approx(1, abs=1e-5)
    assert RuleCancelManager().act(obs, info).name == "CANCEL"
    sim.step(1)
    assert sim.communication.session.requested_at_s == pytest.approx(1)
    assert not sim.communication.session.remote_released_at_s


def test_signed_relative_position_is_not_clipped_to_zero():
    sim = env()
    sim.communication.cache[PEERS[0]] = replace(
        sim.communication.cache[PEERS[0]], payload={"x_m": sim.ramp_x_m - 20, "speed_mps": 25}
    )
    assert sim._info()["manager_inputs"]["front_relative_m"] == pytest.approx(-20)


def test_unavailable_cache_has_explicit_masks_and_finite_vector():
    sim = env()
    sim.communication.cache.clear()
    obs = sim._observation()
    assert np.isfinite(obs).all()
    values = decode(obs)
    assert values["front_received"] == 0
    assert values["rear_received"] == 0
    assert values["message_age_s"] == 60


@pytest.mark.parametrize("delay,loss", [(-1, 0), (0, -0.1), (0, 1.1), (float("nan"), 0)])
def test_invalid_channel_parameters_are_rejected(delay, loss):
    with pytest.raises(ValueError):
        model(delay, loss)


def test_model_clock_cannot_go_backwards():
    comm = model()
    comm.advance(1, sample)
    with pytest.raises(ValueError):
        comm.advance(0.5, sample)


@pytest.mark.parametrize("until", [float("nan"), float("inf"), -1])
def test_invalid_clock_is_rejected(until):
    with pytest.raises(ValueError):
        model().advance(until, sample)


def test_environment_communication_trace_is_seed_reproducible():
    first, second = env(delay=0.2, loss=0.4), env(delay=0.2, loss=0.4)
    for sim in (first, second):
        sim.step(1)
        sim.step(1)
    assert first.communication.bus.events == second.communication.bus.events


def test_delayed_request_without_reply_does_not_claim_remote_release():
    comm = model(delay=5)
    comm.session.request(0)
    comm.advance(6, sample)
    assert comm.session.state == "timed_out"
    assert not comm.session.remote_released_at_s


def test_episode_message_counts_include_inflight_not_as_dropped():
    sim = MergeLifecycleEnv(
        config={
            "disturbance_type": "none",
            "duration_s": 1,
            "packet_loss": 0,
            "communication_delay_ms": 500,
        }
    )
    sim.reset(seed=42)
    _, _, _, truncated, info = sim.step(0)
    assert truncated
    values = info["episode_metrics"]
    assert values["message_count"] == 20
    assert values["messages_delivered"] == 10
    assert values["messages_dropped"] == 0
    assert values["messages_in_flight"] == 10


@pytest.mark.parametrize("duration", [1.05, 20.0])
def test_episode_clock_never_overshoots_communication_window(duration):
    sim = MergeLifecycleEnv(
        config={
            "duration_s": duration,
            "disturbance_type": "none",
            "packet_loss": 1.0,
            "communication_delay_ms": 100,
        }
    )
    sim.reset(seed=42)
    while True:
        _, _, terminated, truncated, info = sim.step(1)
        if terminated or truncated:
            break
    assert sim.time_s == pytest.approx(duration)
    assert sim.communication.time_s == pytest.approx(duration)
    assert max(e["time_s"] for e in info["communication_log"]) <= duration + 1e-9


def test_missing_data_changes_no_rule_information_beyond_vector():
    sim = env(loss=1)
    obs, _, _, _, info = sim.step(0)
    malicious_info = {"manager_inputs": {"message_age_s": 0}, "true_gap_m": 1000}
    assert RuleCancelManager().act(obs, info) == RuleCancelManager().act(obs, malicious_info)


def test_cancel_can_be_pending_when_physical_merge_completes():
    sim = env(delay=2)
    while sim.ramp_y_m > 1e-9:
        sim.step(0)
    _, _, terminated, _, info = sim.step(1)
    assert terminated
    assert info["episode_metrics"]["completed_merge"]
    assert info["cancel_protocol_state"] == "cancel_pending"
    assert sim.communication.session.confirmed_at_s is None


def test_default_observation_clipping_is_equal_for_both_managers():
    sim = env()
    sim.ramp_x_m -= 1000
    obs = sim._observation()
    assert sim._info()["manager_inputs"] == decode(obs)
    assert decode(obs)["front_relative_m"] == 250

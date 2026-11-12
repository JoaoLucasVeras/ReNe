from dataclasses import replace

import pytest

from rene.agreements.communication import CommunicationModel, Message
from rene.agreements.revision import RevisionSession


@pytest.mark.parametrize(
    "changes",
    [
        {"revision": 99},
        {"agreement_id": "other"},
        {"receiver": "other"},
        {"payload": {"token": "stale", "accepted": True}},
    ],
)
def test_wrong_proposal_reply_cannot_count_as_assent(changes):
    comm = CommunicationModel(42, "a", 0.1, 0)
    session = RevisionSession(comm.bus, "a")
    session.request(0, 1, 6)
    message = Message(
        "mainline_front",
        "ramp",
        "timing_reply",
        "a",
        1,
        1,
        0.1,
        0.2,
        {"token": session.token, "accepted": True},
    )
    session.receive(replace(message, **changes))
    assert not session.acks
    assert session.state == "pending"


def test_reply_after_deadline_is_ignored_even_before_timeout_tick():
    comm = CommunicationModel(42, "a", 0.1, 0)
    session = RevisionSession(comm.bus, "a")
    session.request(0, 1, 6)
    session.receive(
        Message(
            "mainline_front",
            "ramp",
            "timing_reply",
            "a",
            1,
            1,
            0.5,
            1.1,
            {"token": session.token, "accepted": True},
        )
    )
    assert not session.acks


@pytest.mark.parametrize("retry,timeout", [(0, 1), (0.1, 0), (float("nan"), 1)])
def test_invalid_protocol_timing_is_rejected(retry, timeout):
    comm = CommunicationModel(42, "a", 0.1, 0)
    with pytest.raises(ValueError):
        RevisionSession(comm.bus, "a", retry, timeout)

"""Abstract two-peer reservation handshake for ego-only timing revisions.

Peers reserve a proposed ego time, not a changed peer trajectory. The host only
activates after both replies. This is not an atomic distributed commit protocol.
"""

from math import inf, isfinite

from rene.agreements.communication import PEERS


class RevisionSession:
    def __init__(self, bus, agreement_id, retry_s=0.1, timeout_s=1.0):
        if not all(isfinite(value) and value > 0 for value in (retry_s, timeout_s)):
            raise ValueError("proposal retry and timeout must be finite and positive")
        self.bus, self.agreement_id = bus, agreement_id
        self.retry_s, self.timeout_s = retry_s, timeout_s
        self.state = "idle"
        self.next_retry_s = self.deadline_s = inf
        self.acks = set()
        self.token = None
        self.revision = 0
        self.planned_at_s = 0.0
        self.requested_at_s = None
        self.accepted_at_s = None
        self.accept_peer = lambda peer, payload, at: True

    def request(self, now, revision, planned_at_s):
        if self.state == "pending":
            return
        if not isfinite(planned_at_s) or planned_at_s <= now:
            raise ValueError("proposal must name a finite future time")
        self.revision = revision
        self.planned_at_s = planned_at_s
        self.requested_at_s = now
        self.accepted_at_s = None
        self.token = f"{self.agreement_id}:proposal:{revision}:{now:.9f}"
        self.acks = set()
        self.state = "pending"
        self.next_retry_s, self.deadline_s = now, now + self.timeout_s
        self.bus.log("proposal_requested", now, revision=revision, planned_at_s=planned_at_s)

    def abort(self, now, reason="cancellation"):
        if self.state == "pending":
            self.state = "aborted"
            self.next_retry_s = self.deadline_s = inf
            self.bus.log("proposal_aborted", now, reason=reason)

    def receive(self, message):
        at = message.delivery_at_s
        if (
            self.state != "pending"
            or message.agreement_id != self.agreement_id
            or message.revision != self.revision
            or message.payload.get("token") != self.token
            or message.sent_at_s < self.requested_at_s - 1e-9
            or at > self.deadline_s + 1e-9
        ):
            self.bus.log("ignored_proposal", at, message)
            return
        if (
            message.kind == "timing_proposal"
            and message.sender == "ramp"
            and message.receiver in PEERS
        ):
            accepted = self.accept_peer(message.receiver, message.payload, at)
            self.bus.send(
                sender=message.receiver,
                receiver="ramp",
                kind="timing_reply",
                agreement_id=self.agreement_id,
                revision=self.revision,
                time_s=at,
                payload={"token": self.token, "accepted": bool(accepted)},
            )
        elif (
            message.kind == "timing_reply"
            and message.sender in PEERS
            and message.receiver == "ramp"
        ):
            if not message.payload.get("accepted"):
                self.state = "rejected"
                self.bus.log("proposal_rejected", at, message)
            else:
                self.acks.add(message.sender)
                if self.acks == set(PEERS):
                    self.state = "accepted"
                    self.accepted_at_s = at
                    self.bus.log("proposal_accepted", at, revision=self.revision)
            if self.state != "pending":
                self.next_retry_s = self.deadline_s = inf
        else:
            self.bus.log("ignored_proposal", at, message)

    def tick(self, now):
        if self.state != "pending":
            return
        if now >= self.deadline_s - 1e-9:
            self.state = "expired"
            self.bus.log("proposal_expired", self.deadline_s, revision=self.revision)
            self.next_retry_s = self.deadline_s = inf
        elif now >= self.next_retry_s - 1e-9:
            for peer in PEERS:
                if peer not in self.acks:
                    self.bus.send(
                        sender="ramp",
                        receiver=peer,
                        kind="timing_proposal",
                        agreement_id=self.agreement_id,
                        revision=self.revision,
                        time_s=self.next_retry_s,
                        payload={"token": self.token, "planned_at_s": self.planned_at_s},
                    )
            self.next_retry_s += self.retry_s

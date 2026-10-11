"""Abstract timestamped V2X delivery and post-acceptance cancellation protocol.

No wireless stack or initial negotiation is modeled. Event times are independent
of the dynamics dt; callers supply physical state at beacon generation times.
"""

from __future__ import annotations

import heapq
from collections import Counter
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict, dataclass
from math import inf, isfinite

import numpy as np

PEERS = ("mainline_front", "mainline_rear")


@dataclass(frozen=True, slots=True)
class Message:
    sender: str
    receiver: str
    kind: str
    agreement_id: str
    revision: int
    sequence: int
    sent_at_s: float
    delivery_at_s: float
    payload: dict


class MessageBus:
    """Fixed one-way delay, independent Bernoulli loss at transmission.

    Beacon RNG streams are independent per sender and separate from protocol
    traffic, so cancellation retries cannot change a scenario's beacon drops.
    """

    def __init__(self, seed: int, delay_s: float, packet_loss: float):
        if not isfinite(delay_s) or delay_s < 0:
            raise ValueError("delay must be finite and nonnegative")
        if not isfinite(packet_loss) or not 0 <= packet_loss <= 1:
            raise ValueError("packet loss must be in [0, 1]")
        self.delay_s, self.packet_loss = delay_s, packet_loss
        streams = np.random.SeedSequence(seed).spawn(3)
        self._rng = {peer: np.random.default_rng(streams[i]) for i, peer in enumerate(PEERS)}
        self._protocol_rng = np.random.default_rng(streams[2])
        self._queue: list[tuple[float, int, Message]] = []
        self._order = 0
        self._sequences: Counter = Counter()
        self.events: list[dict] = []
        self.event_counts: Counter = Counter()
        self.kind_counts: Counter = Counter()

    def log(self, event: str, time_s: float, message: Message | None = None, **fields):
        self.event_counts[event] += 1
        if message:
            self.kind_counts[(event, message.kind)] += 1
        self.events.append(
            {"event": event, "time_s": time_s, **(asdict(message) if message else {}), **fields}
        )

    def send(
        self,
        *,
        sender: str,
        receiver: str,
        kind: str,
        agreement_id: str,
        revision: int,
        time_s: float,
        payload: dict,
        delay_s: float | None = None,
        drop: bool | None = None,
    ) -> Message:
        delay = self.delay_s if delay_s is None else delay_s
        if not isfinite(delay) or delay < 0 or not isfinite(time_s) or time_s < 0:
            raise ValueError("invalid message time/delay")
        key = (sender, receiver, kind)
        self._sequences[key] += 1
        message = Message(
            sender,
            receiver,
            kind,
            agreement_id,
            revision,
            self._sequences[key],
            time_s,
            time_s + delay,
            deepcopy(payload),
        )
        self.log("sent", time_s, message)
        rng = self._rng[sender] if kind == "beacon" else self._protocol_rng
        dropped = bool(rng.random() < self.packet_loss) if drop is None else drop
        if dropped:
            self.log("dropped", time_s, message)
        else:
            self._order += 1
            heapq.heappush(self._queue, (message.delivery_at_s, self._order, message))
        return message

    @property
    def next_delivery_s(self) -> float:
        return self._queue[0][0] if self._queue else inf

    def receive_due(self, time_s: float) -> list[Message]:
        delivered = []
        while self._queue and self.next_delivery_s <= time_s + 1e-9:
            _, _, message = heapq.heappop(self._queue)
            self.log("delivered", message.delivery_at_s, message)
            delivered.append(message)
        return delivered


class CancellationSession:
    """Local fallback starts immediately; remote release requires a delivered request.

    Release ACK is a ReNe abstraction, not an exact reproduction of source Intent
    messages. Timeout does not imply that peers received cancellation.
    """

    def __init__(
        self,
        bus: MessageBus,
        agreement_id: str,
        revision: int = 0,
        retry_s: float = 0.1,
        timeout_s: float = 3.0,
    ):
        if not all(isfinite(v) and v > 0 for v in (retry_s, timeout_s)):
            raise ValueError("retry and timeout must be positive")
        self.bus, self.agreement_id, self.revision = bus, agreement_id, revision
        self.retry_s, self.timeout_s = retry_s, timeout_s
        self.state = "active"
        self.requested_at_s: float | None = None
        self.confirmed_at_s: float | None = None
        self.timed_out_at_s: float | None = None
        self.next_retry_s = inf
        self.deadline_s = inf
        self.acknowledged: set[str] = set()
        self.remote_released_at_s: dict[str, float] = {}  # Evaluator-only truth.
        self.request_token: str | None = None

    def request(self, time_s: float):
        if self.state != "active":
            return  # Repeated manager requests never reset timers.
        self.state = "cancel_pending"
        self.requested_at_s = time_s
        self.request_token = f"{self.agreement_id}:{self.revision}:{time_s:.9f}"
        self.deadline_s = time_s + self.timeout_s
        self.next_retry_s = time_s
        self.bus.log(
            "cancel_requested", time_s, agreement_id=self.agreement_id, revision=self.revision
        )

    def receive(self, message: Message):
        at = message.delivery_at_s
        if (
            message.agreement_id != self.agreement_id
            or message.revision != self.revision
            or self.state != "cancel_pending"
            or message.payload.get("request_token") != self.request_token
            or message.sent_at_s < self.requested_at_s - 1e-9
            or at > message.payload.get("expires_at_s", self.deadline_s) + 1e-9
        ):
            self.bus.log("ignored_protocol", at, message, reason="stale_or_terminal_session")
            return
        if message.kind == "cancel" and message.sender == "ramp" and message.receiver in PEERS:
            peer = message.receiver
            if peer not in self.remote_released_at_s:
                self.remote_released_at_s[peer] = at
                self.bus.log("remote_released", at, message)
            self.bus.send(
                sender=peer,
                receiver="ramp",
                kind="release_ack",
                agreement_id=self.agreement_id,
                revision=self.revision,
                time_s=at,
                payload={"request_token": self.request_token, "expires_at_s": self.deadline_s},
            )
        elif (
            message.kind == "release_ack" and message.sender in PEERS and message.receiver == "ramp"
        ):
            self.acknowledged.add(message.sender)
            self.bus.log("ack_received", at, message)
            if self.acknowledged == set(PEERS):
                self.state = "cancel_confirmed"
                self.confirmed_at_s = at
                self.next_retry_s = self.deadline_s = inf
                self.bus.log(
                    "cancel_confirmed", at, agreement_id=self.agreement_id, revision=self.revision
                )
        else:
            self.bus.log("ignored_protocol", at, message, reason="invalid_route_or_kind")

    def tick(self, time_s: float):
        if self.state != "cancel_pending":
            return
        if time_s >= self.deadline_s - 1e-9:
            self.state = "timed_out"
            self.timed_out_at_s = self.deadline_s
            self.bus.log(
                "cancel_timed_out",
                self.deadline_s,
                agreement_id=self.agreement_id,
                revision=self.revision,
            )
            self.next_retry_s = self.deadline_s = inf
        elif time_s >= self.next_retry_s - 1e-9:
            for peer in PEERS:
                if peer not in self.acknowledged:
                    self.bus.send(
                        sender="ramp",
                        receiver=peer,
                        kind="cancel",
                        agreement_id=self.agreement_id,
                        revision=self.revision,
                        time_s=self.next_retry_s,
                        payload={
                            "request_token": self.request_token,
                            "expires_at_s": self.deadline_s,
                            "retransmission": self.next_retry_s > self.requested_at_s + 1e-9,
                        },
                    )
            self.next_retry_s += self.retry_s


class CommunicationModel:
    def __init__(
        self,
        seed: int,
        agreement_id: str,
        delay_s: float,
        packet_loss: float,
        beacon_interval_s: float = 0.1,
        retry_s: float = 0.1,
        timeout_s: float = 3.0,
    ):
        if not isfinite(beacon_interval_s) or beacon_interval_s <= 0:
            raise ValueError("beacon interval must be positive")
        self.bus = MessageBus(seed, delay_s, packet_loss)
        self.session = CancellationSession(
            self.bus, agreement_id, retry_s=retry_s, timeout_s=timeout_s
        )
        self.beacon_interval_s = beacon_interval_s
        self._beacon_index = 1
        self.time_s = 0.0
        self.cache: dict[str, Message] = {}

    def bootstrap(self, payloads: dict[str, dict]):
        """Assumed last received states at acceptance, not simulated negotiation."""
        for peer in PEERS:
            self.cache[peer] = Message(
                peer,
                "ramp",
                "beacon",
                self.session.agreement_id,
                self.session.revision,
                0,
                0.0,
                0.0,
                deepcopy(payloads[peer]),
            )
        self.bus.log("accepted_fixture_initialized", 0.0)

    def receive(self, message: Message):
        if message.kind != "beacon":
            self.session.receive(message)
            return
        previous = self.cache.get(message.sender)
        valid = (
            message.sender in PEERS
            and message.receiver == "ramp"
            and message.agreement_id == self.session.agreement_id
            and message.revision == self.session.revision
        )
        newer = previous is None or (message.sent_at_s, message.sequence) > (
            previous.sent_at_s,
            previous.sequence,
        )
        if valid and newer:
            self.cache[message.sender] = message
            self.bus.log("cache_updated", message.delivery_at_s, message)
        else:
            self.bus.log(
                "ignored_beacon",
                message.delivery_at_s,
                message,
                reason="wrong_session_or_not_newer",
            )

    def advance(self, until_s: float, sample: Callable[[float], dict[str, dict]]):
        if not isfinite(until_s) or until_s < 0:
            raise ValueError("communication clock must be finite and nonnegative")
        if until_s < self.time_s - 1e-9:
            raise ValueError("communication clock cannot go backwards")
        while True:
            at = min(
                self.bus.next_delivery_s,
                self._beacon_index * self.beacon_interval_s,
                self.session.next_retry_s,
                self.session.deadline_s,
            )
            if at > until_s + 1e-9:
                break
            # Delivery before timeout/retry at identical timestamps. Zero-delay
            # replies generated here are drained before processing that timeout.
            while self.bus.next_delivery_s <= at + 1e-9:
                for message in self.bus.receive_due(at):
                    self.receive(message)
            self.session.tick(at)
            if self._beacon_index * self.beacon_interval_s <= at + 1e-9:
                payloads = sample(at)
                for peer in PEERS:
                    self.bus.send(
                        sender=peer,
                        receiver="ramp",
                        kind="beacon",
                        agreement_id=self.session.agreement_id,
                        revision=self.session.revision,
                        time_s=at,
                        payload=payloads[peer],
                    )
                self._beacon_index += 1
        self.time_s = until_s

    def ages(self, time_s: float) -> dict[str, float]:
        return {
            peer: max(time_s - self.cache[peer].sent_at_s, 0.0) if peer in self.cache else inf
            for peer in PEERS
        }

    def counts(self) -> dict[str, int]:
        counts = self.bus.event_counts
        return {key: counts[key] for key in ("sent", "delivered", "dropped")}

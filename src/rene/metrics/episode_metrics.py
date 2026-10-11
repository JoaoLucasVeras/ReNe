"""Episode-level metric accumulator."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class EpisodeMetrics:
    episode_id: str
    seed: int
    manager: str = "external"
    physics_version: str = "step3a-axis-aligned-v1"
    input_version: str = "received-state-v1"
    messages_delivered: int = 0
    messages_dropped: int = 0
    cancel_protocol_state: str = "active"
    beacons_sent: int = 0
    control_messages_sent: int = 0
    messages_in_flight: int = 0
    cancel_requested_at_s: float | None = None
    cancel_confirmed_at_s: float | None = None
    cancel_timed_out_at_s: float | None = None
    collision: bool = False
    near_collision: bool = False
    completed_merge: bool = False
    canceled: bool = False
    failed_agreement_duration_s: float = 0.0
    unnecessary_cancellation: bool = False
    renegotiation_attempts: int = 0
    renegotiation_successes: int = 0
    shield_overrides: int = 0
    message_count: int = 0
    min_ttc_s: float = float("inf")
    min_headway_s: float = float("inf")
    merge_completion_time_s: float = 0.0
    peak_abs_accel_mps2: float = 0.0
    peak_abs_jerk_mps3: float = 0.0
    total_reward: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)

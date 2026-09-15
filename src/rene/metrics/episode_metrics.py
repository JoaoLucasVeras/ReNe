"""Episode-level metric accumulator."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class EpisodeMetrics:
    episode_id: str
    seed: int
    manager: str = "external"
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
    min_ttc_s: float = 999.0
    min_headway_s: float = 999.0
    merge_completion_time_s: float = 0.0
    peak_abs_accel_mps2: float = 0.0
    peak_abs_jerk_mps3: float = 0.0
    total_reward: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)

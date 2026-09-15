"""Deterministic agreement protocol helpers."""

from __future__ import annotations

from uuid import uuid4

from rene.agreements.state import Agreement


def create_accepted_agreement(
    episode_id: str,
    target_gap_id: int = 0,
    merge_order: int = 1,
    planned_merge_time_s: float = 8.0,
) -> Agreement:
    return Agreement(
        agreement_id=str(uuid4()),
        episode_id=episode_id,
        participants=("ramp", "mainline_front", "mainline_rear"),
        target_gap_id=target_gap_id,
        merge_order=merge_order,
        planned_merge_time_s=planned_merge_time_s,
        accepted_at_s=0.0,
    )

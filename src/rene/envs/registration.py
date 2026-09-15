"""Gymnasium registration."""

from __future__ import annotations


def register_environments() -> None:
    try:
        from gymnasium.envs.registration import register, registry
    except ImportError:
        return
    if "ReNeMergeLifecycle-v0" not in registry:
        register(
            id="ReNeMergeLifecycle-v0",
            entry_point="rene.envs.merge_lifecycle_env:MergeLifecycleEnv",
        )

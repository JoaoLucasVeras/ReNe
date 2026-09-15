"""Non-learning agreement managers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from rene.agreements.state import ManagerAction


class Manager(Protocol):
    def act(self, observation: np.ndarray, info: dict) -> ManagerAction: ...


@dataclass(slots=True)
class OneShotManager:
    def act(self, observation: np.ndarray, info: dict) -> ManagerAction:
        return ManagerAction.CONTINUE


@dataclass(slots=True)
class RuleCancelManager:
    min_gap_m: float = 12.0
    min_ttc_s: float = 2.0
    max_message_age_s: float = 0.5

    def act(self, observation: np.ndarray, info: dict) -> ManagerAction:
        if (
            info["gap_m"] < self.min_gap_m
            or info["ttc_s"] < self.min_ttc_s
            or info["message_age_s"] > self.max_message_age_s
        ):
            return ManagerAction.CANCEL
        return ManagerAction.CONTINUE


@dataclass(slots=True)
class HeuristicRenegotiationManager(RuleCancelManager):
    def act(self, observation: np.ndarray, info: dict) -> ManagerAction:
        unsafe = RuleCancelManager.act(self, observation, info) == ManagerAction.CANCEL
        if not unsafe:
            return ManagerAction.CONTINUE
        if info["renegotiation_count"] == 0 and info["alternative_gap_feasible"]:
            return ManagerAction.RENEGOTIATE_NEXT_GAP
        return ManagerAction.CANCEL


def make_manager(name: str) -> Manager:
    if name in {"perception_only", "one_shot"}:
        return OneShotManager()
    if name == "rule_cancel":
        return RuleCancelManager()
    if name == "heuristic_renegotiate":
        return HeuristicRenegotiationManager()
    raise ValueError(f"unknown manager: {name}")

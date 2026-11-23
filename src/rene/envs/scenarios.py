"""Reproducible training-condition sampling, with no condition labels in inputs."""

import gymnasium as gym
import numpy as np

# Ramp-length protocol (adopted November 18 2026; see docs/EXPERIMENT_PROTOCOL.md).
# Training/tuning lengths lie in the band where lifecycle decisions change outcomes.
# 280 m is held out for evaluation only (interpolation); 320 m is an edge case and
# 240/400 m are no-decision controls. None of the evaluation-only lengths may be
# sampled during training or used to tune rules, rewards or hyperparameters.
TRAINING_RAMP_ENDS_M = (260.0, 270.0, 290.0, 300.0)
HELDOUT_RAMP_ENDS_M = (280.0,)
EDGE_RAMP_ENDS_M = (320.0,)
CONTROL_RAMP_ENDS_M = (240.0, 400.0)
EVALUATION_ONLY_RAMP_ENDS_M = frozenset(
    HELDOUT_RAMP_ENDS_M + EDGE_RAMP_ENDS_M + CONTROL_RAMP_ENDS_M
)
EVALUATION_RAMP_ENDS_M = tuple(
    sorted(TRAINING_RAMP_ENDS_M + HELDOUT_RAMP_ENDS_M + EDGE_RAMP_ENDS_M + CONTROL_RAMP_ENDS_M)
)


def ramp_role(ramp_end_m: float) -> str:
    """Reporting role of a ramp length under the adopted protocol."""
    value = float(ramp_end_m)
    for role, lengths in (
        ("training", TRAINING_RAMP_ENDS_M),
        ("heldout", HELDOUT_RAMP_ENDS_M),
        ("edge", EDGE_RAMP_ENDS_M),
        ("control", CONTROL_RAMP_ENDS_M),
    ):
        if value in lengths:
            return role
    return "unlisted"


class TrainingScenarios(gym.Wrapper):
    def __init__(self, env, ramp_ends_m=TRAINING_RAMP_ENDS_M):
        super().__init__(env)
        if not ramp_ends_m or EVALUATION_ONLY_RAMP_ENDS_M & {float(r) for r in ramp_ends_m}:
            raise ValueError("training ramp lengths must exclude evaluation-only lengths")
        self.ramp_ends_m = tuple(float(r) for r in ramp_ends_m)

    def reset(self, *, seed=None, options=None):
        if seed is not None or not hasattr(self, "_scenario_rng"):
            self._scenario_rng = np.random.default_rng(seed if seed is not None else 0)
        rng = self._scenario_rng
        self.last_scenario = {
            "traffic_density": str(rng.choice(["low", "medium", "high"])),
            "disturbance_type": str(rng.choice(["none", "braking", "cut_in", "intent_mismatch"])),
            "communication_delay_ms": float(rng.choice([0, 100, 300, 800])),
            "packet_loss": float(rng.choice([0, 0.05, 0.2, 0.5])),
            "disturbance_severity": str(rng.choice(["mild", "moderate", "hard"])),
            "disturbance_trigger_s": float(rng.choice([3.5, 5, 6.5])),
            "ramp_end_m": float(rng.choice(self.ramp_ends_m)),
        }
        self.last_scenario.update(options or {})
        if float(self.last_scenario["ramp_end_m"]) in EVALUATION_ONLY_RAMP_ENDS_M:
            raise ValueError("evaluation-only ramp length requested during training")
        episode_seed = int(rng.integers(0, 2**31 - 1))
        return self.env.reset(seed=episode_seed, options=self.last_scenario)

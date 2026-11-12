"""Reproducible training-condition sampling, with no condition labels in inputs."""

import gymnasium as gym
import numpy as np


class TrainingScenarios(gym.Wrapper):
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
        }
        self.last_scenario.update(options or {})
        episode_seed = int(rng.integers(0, 2**31 - 1))
        return self.env.reset(seed=episode_seed, options=self.last_scenario)

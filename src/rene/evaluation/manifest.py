"""Deterministic condition/seed manifest shared by every evaluated manager."""

from itertools import product

from rene.envs.scenarios import ramp_role

# Keys that label a scenario for reporting and must not be passed to env.reset.
REPORTING_ONLY_KEYS = frozenset({"seed", "scenario_id", "ramp_role"})


def build_manifest(grid, seeds):
    ramp_ends = grid.get("ramp_end_m", [None])
    conditions = list(
        product(
            grid.get("traffic_density", ["medium"]),
            grid.get("delay_ms", [0]),
            grid.get("packet_loss", [0]),
            grid.get("disturbance", ["none"]),
            ramp_ends,
        )
    )
    if not conditions or not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("nonempty conditions and unique evaluation seeds required")
    if len(set(ramp_ends)) != len(ramp_ends):
        raise ValueError("ramp lengths must be unique")
    manifest = []
    for seed in seeds:
        for index, (density, delay, loss, disturbance, ramp_end) in enumerate(conditions):
            row = {
                "scenario_id": f"s{seed}-c{index}",
                "seed": int(seed),
                "traffic_density": density,
                "communication_delay_ms": float(delay),
                "packet_loss": float(loss),
                "disturbance_type": disturbance,
            }
            if ramp_end is not None:
                row["ramp_end_m"] = float(ramp_end)
                row["ramp_role"] = ramp_role(ramp_end)
            manifest.append(row)
    return manifest


def reset_options(scenario: dict) -> dict:
    """Environment reset options for one manifest row (reporting labels removed)."""
    return {key: value for key, value in scenario.items() if key not in REPORTING_ONLY_KEYS}

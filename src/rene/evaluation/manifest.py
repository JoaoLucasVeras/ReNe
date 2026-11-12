"""Deterministic condition/seed manifest shared by every evaluated manager."""

from itertools import product


def build_manifest(grid, seeds):
    conditions = list(
        product(
            grid.get("traffic_density", ["medium"]),
            grid.get("delay_ms", [0]),
            grid.get("packet_loss", [0]),
            grid.get("disturbance", ["none"]),
        )
    )
    if not conditions or not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("nonempty conditions and unique evaluation seeds required")
    return [
        {
            "scenario_id": f"s{seed}-c{index}",
            "seed": int(seed),
            "traffic_density": density,
            "communication_delay_ms": float(delay),
            "packet_loss": float(loss),
            "disturbance_type": disturbance,
        }
        for seed in seeds
        for index, (density, delay, loss, disturbance) in enumerate(conditions)
    ]

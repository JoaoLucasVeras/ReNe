from rene.evaluation.manifest import build_manifest


def test_every_seed_crosses_every_condition_and_pairs_reproducibly():
    grid = {
        "traffic_density": ["low", "high"],
        "delay_ms": [0, 800],
        "disturbance": ["none", "braking"],
    }
    manifest = build_manifest(grid, [1001, 1002])
    assert len(manifest) == 16
    assert len({row["scenario_id"] for row in manifest}) == 16
    assert manifest == build_manifest(grid, [1001, 1002])
    assert all(row["seed"] >= 1001 for row in manifest)

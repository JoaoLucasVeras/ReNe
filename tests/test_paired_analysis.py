import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    "paired_analysis", Path(__file__).resolve().parents[1] / "scripts/paired_analysis.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("value", [0, 1, -1])
def test_constant_paired_differences_have_exact_intervals(value):
    result = module.bootstrap_difference(np.full((3, 8), value))
    assert result["mean_difference"] == value
    assert result["ci95_low"] == value
    assert result["ci95_high"] == value


def test_bootstrap_reproducibly_preserves_between_model_uncertainty():
    values = np.array([[0] * 8, [1] * 8])
    first = module.bootstrap_difference(values)
    assert first == module.bootstrap_difference(values)
    assert first["mean_difference"] == 0.5
    assert first["ci95_low"] == 0
    assert first["ci95_high"] == 1


@pytest.mark.parametrize("values", [[1], [np.nan, 1]])
def test_unusable_samples_are_rejected(values):
    with pytest.raises(ValueError):
        module.bootstrap_difference(values)

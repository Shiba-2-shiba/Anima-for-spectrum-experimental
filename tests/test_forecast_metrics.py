import math

import pytest
import torch

from core.forecast_metrics import (
    clip_fraction,
    compute_forecast_metrics,
    cosine_similarity,
    relative_l2,
    tensor_mse,
)


def test_tensor_mse_and_relative_l2_are_computed_on_flattened_float_tensors():
    forecast = torch.tensor([[2.0, 4.0]])
    actual = torch.tensor([[1.0, 2.0]])

    assert tensor_mse(forecast, actual) == pytest.approx(2.5)
    assert relative_l2(forecast, actual) == pytest.approx(1.0)


def test_relative_l2_handles_zero_actual_norm():
    assert relative_l2(torch.zeros(2), torch.zeros(2)) == 0.0
    assert math.isinf(relative_l2(torch.ones(2), torch.zeros(2)))


def test_cosine_similarity_handles_orthogonal_and_zero_vectors():
    assert cosine_similarity(torch.tensor([1.0, 0.0]), torch.tensor([0.0, 1.0])) == pytest.approx(0.0)
    assert cosine_similarity(torch.zeros(2), torch.ones(2)) == 0.0


def test_clip_fraction_counts_values_above_limit():
    assert clip_fraction(torch.tensor([-11.0, -10.0, 0.0, 10.1]), limit=10.0) == pytest.approx(0.5)


def test_compute_forecast_metrics_returns_json_ready_scalars():
    metrics = compute_forecast_metrics(
        torch.tensor([2.0, 4.0]),
        torch.tensor([1.0, 2.0]),
        clip_limit=3.0,
    )

    assert metrics.mse == pytest.approx(2.5)
    assert metrics.relative_l2 == pytest.approx(1.0)
    assert metrics.cosine_similarity == pytest.approx(1.0)
    assert metrics.actual_norm == pytest.approx(math.sqrt(5.0))
    assert metrics.forecast_norm == pytest.approx(math.sqrt(20.0))
    assert metrics.norm_ratio == pytest.approx(2.0)
    assert metrics.delta_norm == pytest.approx(math.sqrt(5.0))
    assert metrics.clip_fraction == pytest.approx(0.5)

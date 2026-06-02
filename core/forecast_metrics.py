from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class ForecastMetrics:
    mse: float
    relative_l2: float
    cosine_similarity: float
    actual_norm: float
    forecast_norm: float
    norm_ratio: float
    delta_norm: float
    clip_fraction: float


def _as_float_vector(tensor: torch.Tensor) -> torch.Tensor:
    return tensor.detach().to(torch.float32).reshape(-1)


def _safe_float(value: torch.Tensor) -> float:
    return float(value.detach().cpu().item())


def tensor_mse(forecast: torch.Tensor, actual: torch.Tensor) -> float:
    forecast_vector = _as_float_vector(forecast)
    actual_vector = _as_float_vector(actual)
    diff = forecast_vector - actual_vector
    return _safe_float((diff * diff).mean())


def relative_l2(forecast: torch.Tensor, actual: torch.Tensor) -> float:
    forecast_vector = _as_float_vector(forecast)
    actual_vector = _as_float_vector(actual)
    diff_norm = forecast_vector.sub(actual_vector).norm()
    actual_norm = actual_vector.norm()
    if _safe_float(actual_norm) == 0.0:
        return 0.0 if _safe_float(diff_norm) == 0.0 else float("inf")
    return _safe_float(diff_norm / actual_norm)


def cosine_similarity(forecast: torch.Tensor, actual: torch.Tensor) -> float:
    forecast_vector = _as_float_vector(forecast)
    actual_vector = _as_float_vector(actual)
    denominator = forecast_vector.norm() * actual_vector.norm()
    if _safe_float(denominator) == 0.0:
        return 0.0
    return _safe_float(torch.dot(forecast_vector, actual_vector) / denominator)


def clip_fraction(tensor: torch.Tensor, limit: float = 10.0) -> float:
    vector = _as_float_vector(tensor)
    return _safe_float((vector.abs() > float(limit)).float().mean())


def compute_forecast_metrics(
    forecast: torch.Tensor,
    actual: torch.Tensor,
    *,
    clip_limit: float = 10.0,
) -> ForecastMetrics:
    forecast_vector = _as_float_vector(forecast)
    actual_vector = _as_float_vector(actual)
    diff_vector = forecast_vector - actual_vector

    actual_norm = _safe_float(actual_vector.norm())
    forecast_norm = _safe_float(forecast_vector.norm())
    if actual_norm == 0.0:
        norm_ratio = 0.0 if forecast_norm == 0.0 else float("inf")
    else:
        norm_ratio = forecast_norm / actual_norm

    return ForecastMetrics(
        mse=tensor_mse(forecast, actual),
        relative_l2=relative_l2(forecast, actual),
        cosine_similarity=cosine_similarity(forecast, actual),
        actual_norm=actual_norm,
        forecast_norm=forecast_norm,
        norm_ratio=norm_ratio,
        delta_norm=_safe_float(diff_vector.norm()),
        clip_fraction=clip_fraction(forecast, limit=clip_limit),
    )

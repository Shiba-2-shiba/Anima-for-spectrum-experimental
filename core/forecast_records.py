from dataclasses import asdict
from typing import Any, Optional

import torch

from .forecast_metrics import compute_forecast_metrics
from .feature_sites import FEATURE_SITE_PRE_DECODER_HEAD

RECORD_RUN_START = "anima_spectrum_run_start"
RECORD_TOPOLOGY = "anima_spectrum_topology"
RECORD_SHADOW_STEP = "anima_spectrum_shadow_step"
RECORD_REPLACE_STEP = "anima_spectrum_replace_step"
RECORD_ACTUAL_STEP = "anima_spectrum_actual_step"


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, dict):
        return dict(value)
    return {"repr": repr(value)}


def build_run_start_record(
    *,
    run_id: str,
    timestamp_utc: str,
    estimated_total_steps: int,
    patcher_config,
    feature_site_id: str = FEATURE_SITE_PRE_DECODER_HEAD,
) -> dict[str, Any]:
    return {
        "event": "run_start",
        "record_type": RECORD_RUN_START,
        "run_id": run_id,
        "timestamp_utc": timestamp_utc,
        "estimated_total_steps": int(estimated_total_steps),
        "feature_site_id": feature_site_id,
        "patcher_config": _as_dict(patcher_config),
    }


def build_topology_record(
    *,
    run_id: str,
    feature_site_id: str,
    topology_report,
    support_report=None,
) -> dict[str, Any]:
    return {
        "event": "topology",
        "record_type": RECORD_TOPOLOGY,
        "run_id": run_id,
        "feature_site_id": feature_site_id,
        "topology": _as_dict(topology_report),
        "support": _as_dict(support_report),
    }


def record_type_for_step(step_kind: str) -> str:
    if step_kind == "shadow":
        return RECORD_SHADOW_STEP
    if step_kind == "forecast":
        return RECORD_REPLACE_STEP
    return RECORD_ACTUAL_STEP


def _tensor_shape(tensor: Optional[torch.Tensor]):
    if tensor is None:
        return None
    return list(tensor.shape)


def _tensor_dtype(tensor: Optional[torch.Tensor]):
    if tensor is None:
        return None
    return str(tensor.dtype)


def _tensor_device(tensor: Optional[torch.Tensor]):
    if tensor is None:
        return None
    return str(tensor.device)


def build_step_record(
    *,
    run_id: str,
    feature_site_id: str,
    forecast_mode: str,
    step_kind: str,
    step_index: int,
    timestep_value: float,
    estimated_total_steps: int,
    estimated_last_step_index: int,
    progress: float,
    batch_index: int,
    num_cached_before: int,
    window_size: int,
    config,
    raw_guess: torch.Tensor,
    calibrated_guess: torch.Tensor,
    correction: torch.Tensor,
    apply_result,
    actual_x: Optional[torch.Tensor] = None,
    observation=None,
    timings: Optional[dict[str, float]] = None,
    clip_limit: float = 10.0,
) -> dict[str, Any]:
    raw_norm = float(raw_guess.detach().to(torch.float32).norm().item())
    correction_norm = float(correction.detach().to(torch.float32).norm().item())

    payload = {
        "event": "step",
        "record_type": record_type_for_step(step_kind),
        "run_id": run_id,
        "feature_site_id": feature_site_id,
        "forecast_mode": str(forecast_mode),
        "step_index": int(step_index),
        "timestep": float(timestep_value),
        "estimated_total_steps": int(estimated_total_steps),
        "estimated_last_step_index": int(estimated_last_step_index),
        "progress": float(progress),
        "actual_or_forecast": step_kind,
        "batch_idx": int(batch_index),
        "batch_cached_before": int(num_cached_before),
        "window_size": int(window_size),
        "tensor": {
            "shape": _tensor_shape(raw_guess),
            "dtype": _tensor_dtype(raw_guess),
            "device": _tensor_device(raw_guess),
            "actual_shape": _tensor_shape(actual_x),
        },
        "calibration": {
            "enabled": bool(config.enable_calibration),
            "mode": config.calibration_mode,
            "strength": float(config.calibration_strength),
            "decay": float(config.calibration_decay),
            "buckets": int(config.calibration_buckets),
            "min_obs": int(config.calibration_min_obs),
            "bucket_id": int(apply_result.bucket_id),
            "obs_count_before_apply": int(apply_result.obs_count),
            "obs_count_after_observe": int(observation.obs_count) if observation is not None else None,
            "residual_norm_before_apply": float(apply_result.residual_norm),
            "residual_norm_after_observe": float(observation.residual_norm) if observation is not None else None,
        },
        "norms": {
            "raw_norm": raw_norm,
            "calibrated_norm": float(calibrated_guess.detach().to(torch.float32).norm().item()),
            "actual_norm": float(actual_x.detach().to(torch.float32).norm().item()) if actual_x is not None else None,
            "correction_norm": correction_norm,
        },
        "safety": {
            "clip_frac_before": float((raw_guess.detach().to(torch.float32).abs() > clip_limit).float().mean().item()),
            "clip_frac_after": float(
                (calibrated_guess.detach().to(torch.float32).abs() > clip_limit).float().mean().item()
            ),
            "correction_raw_ratio": 0.0 if raw_norm == 0.0 else float(correction_norm / raw_norm),
        },
        "timings": {key: float(value) for key, value in (timings or {}).items()},
        "errors": None,
        "metrics": None,
    }

    if actual_x is not None:
        raw_metrics = compute_forecast_metrics(raw_guess, actual_x, clip_limit=clip_limit)
        calibrated_metrics = compute_forecast_metrics(calibrated_guess, actual_x, clip_limit=clip_limit)
        payload["errors"] = {
            "raw_vs_actual_mse": raw_metrics.mse,
            "raw_vs_actual_rel_l2": raw_metrics.relative_l2,
            "raw_vs_actual_cosine": raw_metrics.cosine_similarity,
            "calibrated_vs_actual_mse": calibrated_metrics.mse,
            "calibrated_vs_actual_rel_l2": calibrated_metrics.relative_l2,
            "calibrated_vs_actual_cosine": calibrated_metrics.cosine_similarity,
        }
        payload["metrics"] = {
            "raw_vs_actual": asdict(raw_metrics),
            "calibrated_vs_actual": asdict(calibrated_metrics),
        }

    return payload

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

import torch

from .calibration import CALIBRATION_MODE_LATEST
from .helpers import batch_index_tensor, safe_float_timestep
from .intermediate_features import (
    IntermediateFeatureState,
    batch_size_from_intermediate_feature_state,
    decode_intermediate_feature_state,
    extract_intermediate_feature_state,
    replace_intermediate_feature_x,
    resolve_intermediate_feature_model,
    run_blocks_from_intermediate_state,
    slice_intermediate_feature_state,
)
from .schedule import estimate_last_step_index, estimate_total_steps, should_reset_for_new_pass
from .spectrum import CalibratedChebyshevForecaster


DEBUG_CLAMP_LIMIT = 10.0
DEBUG_LOG_DIR = Path(__file__).resolve().parents[1] / "docs" / "context_refactor" / "logs"


@dataclass(frozen=True)
class IntermediateForecastConfig:
    enabled: bool
    w: float
    m: int
    lam: float
    warmup_steps: int
    window_size: int
    flex_window: float
    stop_caching_step: int
    enable_calibration: bool
    calibration_strength: float
    calibration_mode: str = CALIBRATION_MODE_LATEST
    calibration_decay: float = 0.9
    calibration_buckets: int = 4
    calibration_min_obs: int = 1
    debug_logging: bool = False


class Phase2DebugLogger:
    def __init__(self, enabled: bool):
        self.enabled = bool(enabled)
        self.run_counter = 0
        self.run_id: Optional[str] = None
        self.log_path: Optional[Path] = None

    def reset(self) -> None:
        self.run_id = None
        self.log_path = None

    def ensure_run(self, config: IntermediateForecastConfig, estimated_total_steps: int) -> None:
        if not self.enabled or self.log_path is not None:
            return

        self.run_counter += 1
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        self.run_id = f"phase2-{timestamp}-run{self.run_counter:02d}"
        self.log_path = DEBUG_LOG_DIR / f"{self.run_id}.jsonl"

        try:
            DEBUG_LOG_DIR.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.enabled = False
            self.run_id = None
            self.log_path = None
            return

        self.write(
            {
                "event": "run_start",
                "run_id": self.run_id,
                "timestamp_utc": timestamp,
                "estimated_total_steps": int(estimated_total_steps),
                "patcher_config": asdict(config),
            }
        )

    def write(self, payload: dict) -> None:
        if not self.enabled or self.log_path is None:
            return

        try:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except OSError:
            self.enabled = False


class IntermediateForecastController:
    def __init__(self, config: IntermediateForecastConfig):
        self.config = IntermediateForecastConfig(
            enabled=bool(config.enabled),
            w=max(0.0, min(1.0, float(config.w))),
            m=max(1, int(config.m)),
            lam=max(0.0, float(config.lam)),
            warmup_steps=max(0, int(config.warmup_steps)),
            window_size=max(1, int(config.window_size)),
            flex_window=max(0.0, float(config.flex_window)),
            stop_caching_step=int(config.stop_caching_step),
            enable_calibration=bool(config.enable_calibration),
            calibration_strength=max(0.0, min(1.0, float(config.calibration_strength))),
            calibration_mode=str(getattr(config, "calibration_mode", CALIBRATION_MODE_LATEST)),
            calibration_decay=max(0.0, min(0.999, float(getattr(config, "calibration_decay", 0.9)))),
            calibration_buckets=max(1, int(getattr(config, "calibration_buckets", 4))),
            calibration_min_obs=max(1, int(getattr(config, "calibration_min_obs", 1))),
            debug_logging=bool(getattr(config, "debug_logging", False)),
        )
        self.debug_logger = Phase2DebugLogger(enabled=self.config.debug_logging)
        self.reset()

    def reset(self, batch_size: int = 0) -> None:
        self.forecasters: Optional[List[CalibratedChebyshevForecaster]] = None
        self.cnt = 0
        self.num_cached = [0] * batch_size
        self.curr_ws = float(self.config.window_size)
        self.last_t = float("inf")
        self.estimated_total_steps = 50
        self.estimated_last_step_index = estimate_last_step_index(self.estimated_total_steps)
        self._warned_never_forecast = False
        self.debug_logger.reset()

    def _build_forecasters(self, batch_size: int) -> List[CalibratedChebyshevForecaster]:
        forecasters = [
            CalibratedChebyshevForecaster(m=self.config.m, lam=self.config.lam)
            for _ in range(batch_size)
        ]
        for forecaster in forecasters:
            forecaster.t_max = float(max(1, self.estimated_last_step_index))
        return forecasters

    def _ensure_batch_state(self, batch_size: int) -> None:
        if self.forecasters is None:
            self.forecasters = self._build_forecasters(batch_size)
            self.num_cached = [0] * batch_size
            return

        if len(self.forecasters) != batch_size or len(self.num_cached) != batch_size:
            self.forecasters = self._build_forecasters(batch_size)
            self.num_cached = [0] * batch_size

    def _is_micro_final(self) -> bool:
        if self.config.stop_caching_step == -1:
            auto_stop = int(self.estimated_total_steps * 0.8)
            return self.cnt >= auto_stop
        if self.config.stop_caching_step > 0:
            return self.cnt >= self.config.stop_caching_step
        return False

    def _compute_actual_mask(self, batch_size: int, device: torch.device) -> torch.Tensor:
        do_actual = torch.ones(batch_size, dtype=torch.bool, device=device)

        if self.cnt < self.config.warmup_steps or self._is_micro_final():
            return do_actual

        current_ws = max(1, int(math.floor(self.curr_ws)))
        for index in range(batch_size):
            do_actual[index] = ((self.num_cached[index] + 1) % current_ws) == 0
            if not self.forecasters[index].can_predict():
                do_actual[index] = True

        return do_actual

    def _current_progress(self) -> float:
        return max(0.0, min(1.0, float(self.cnt) / max(float(self.estimated_last_step_index), 1.0)))

    def _tensor_to_float32(self, tensor: torch.Tensor) -> torch.Tensor:
        return tensor.detach().to(torch.float32)

    def _tensor_norm(self, tensor: torch.Tensor) -> float:
        return float(self._tensor_to_float32(tensor).norm().item())

    def _clip_fraction(self, tensor: torch.Tensor) -> float:
        float_tensor = self._tensor_to_float32(tensor)
        return float((float_tensor.abs() > DEBUG_CLAMP_LIMIT).float().mean().item())

    def _cosine_similarity(self, left: torch.Tensor, right: torch.Tensor) -> float:
        left_vector = self._tensor_to_float32(left).reshape(-1)
        right_vector = self._tensor_to_float32(right).reshape(-1)
        denominator = left_vector.norm() * right_vector.norm()
        if float(denominator.item()) == 0.0:
            return 0.0
        return float(torch.dot(left_vector, right_vector).item() / denominator.item())

    def _mse(self, left: torch.Tensor, right: torch.Tensor) -> float:
        diff = self._tensor_to_float32(left) - self._tensor_to_float32(right)
        return float((diff * diff).mean().item())

    def _relative_l2(self, left: torch.Tensor, right: torch.Tensor) -> float:
        diff_norm = self._tensor_to_float32(left).sub(self._tensor_to_float32(right)).norm().item()
        base_norm = self._tensor_to_float32(right).norm().item()
        if base_norm == 0.0:
            return 0.0 if diff_norm == 0.0 else float("inf")
        return float(diff_norm / base_norm)

    def _log_step(
        self,
        *,
        step_kind: str,
        batch_index: int,
        timestep_value: float,
        progress: float,
        num_cached_before: int,
        raw_guess: torch.Tensor,
        apply_result,
        actual_x: Optional[torch.Tensor] = None,
        observation=None,
    ) -> None:
        if not self.config.debug_logging:
            return

        self.debug_logger.ensure_run(self.config, self.estimated_total_steps)
        calibrated_guess = apply_result.corrected
        raw_norm = self._tensor_norm(raw_guess)
        correction_norm = self._tensor_norm(apply_result.correction)

        payload = {
            "event": "step",
            "run_id": self.debug_logger.run_id,
            "step_index": int(self.cnt),
            "timestep": float(timestep_value),
            "estimated_total_steps": int(self.estimated_total_steps),
            "estimated_last_step_index": int(self.estimated_last_step_index),
            "progress": float(progress),
            "actual_or_forecast": step_kind,
            "batch_idx": int(batch_index),
            "batch_cached_before": int(num_cached_before),
            "window_size": int(max(1, int(math.floor(self.curr_ws)))),
            "calibration": {
                "enabled": bool(self.config.enable_calibration),
                "mode": self.config.calibration_mode,
                "strength": float(self.config.calibration_strength),
                "decay": float(self.config.calibration_decay),
                "buckets": int(self.config.calibration_buckets),
                "min_obs": int(self.config.calibration_min_obs),
                "bucket_id": int(apply_result.bucket_id),
                "obs_count_before_apply": int(apply_result.obs_count),
                "obs_count_after_observe": int(observation.obs_count) if observation is not None else None,
                "residual_norm_before_apply": float(apply_result.residual_norm),
                "residual_norm_after_observe": float(observation.residual_norm) if observation is not None else None,
            },
            "norms": {
                "raw_norm": raw_norm,
                "calibrated_norm": self._tensor_norm(calibrated_guess),
                "actual_norm": self._tensor_norm(actual_x) if actual_x is not None else None,
                "correction_norm": correction_norm,
            },
            "safety": {
                "clip_frac_before": self._clip_fraction(raw_guess),
                "clip_frac_after": self._clip_fraction(calibrated_guess),
                "correction_raw_ratio": 0.0 if raw_norm == 0.0 else float(correction_norm / raw_norm),
            },
            "errors": None,
        }

        if actual_x is not None:
            payload["errors"] = {
                "raw_vs_actual_mse": self._mse(raw_guess, actual_x),
                "raw_vs_actual_rel_l2": self._relative_l2(raw_guess, actual_x),
                "raw_vs_actual_cosine": self._cosine_similarity(raw_guess, actual_x),
                "calibrated_vs_actual_mse": self._mse(calibrated_guess, actual_x),
                "calibrated_vs_actual_rel_l2": self._relative_l2(calibrated_guess, actual_x),
                "calibrated_vs_actual_cosine": self._cosine_similarity(calibrated_guess, actual_x),
            }

        self.debug_logger.write(payload)

    def run(
        self,
        state: IntermediateFeatureState,
        timestep,
        schedule_context: dict,
        compute_actual_feature_state: Callable[[torch.Tensor], IntermediateFeatureState],
    ) -> IntermediateFeatureState:
        if not self.config.enabled:
            full_index = torch.arange(
                batch_size_from_intermediate_feature_state(state),
                device=state.x.device,
                dtype=torch.long,
            )
            return compute_actual_feature_state(full_index)

        batch_size = batch_size_from_intermediate_feature_state(state)
        t_scalar = safe_float_timestep(timestep)

        if should_reset_for_new_pass(t_scalar, self.last_t):
            self.reset(batch_size=batch_size)

        self.last_t = t_scalar
        self.estimated_total_steps = estimate_total_steps(
            current_step=self.cnt,
            c=schedule_context,
            fallback=self.estimated_total_steps,
        )
        self.estimated_last_step_index = estimate_last_step_index(self.estimated_total_steps)

        if not self._warned_never_forecast and self.config.warmup_steps >= self.estimated_total_steps:
            print(
                f"[AnimaSpectrum] Forecast is effectively disabled because warmup_steps={self.config.warmup_steps} "
                f">= estimated_total_steps={self.estimated_total_steps}."
            )
            self._warned_never_forecast = True

        self._ensure_batch_state(batch_size)
        self.debug_logger.ensure_run(self.config, self.estimated_total_steps)
        for forecaster in self.forecasters:
            forecaster.t_max = float(max(1, self.estimated_last_step_index))

        progress = self._current_progress()
        actual_mask = self._compute_actual_mask(batch_size, state.x.device)
        forecast_mask = ~actual_mask
        combined_x = torch.empty_like(state.x)

        if actual_mask.any():
            actual_indices = batch_index_tensor(actual_mask)
            actual_state = compute_actual_feature_state(actual_indices)
            combined_x[actual_mask] = actual_state.x

            for local_index, batch_index in enumerate(actual_indices.tolist()):
                forecaster = self.forecasters[batch_index]
                actual_x = actual_state.x[local_index]
                raw_current = None
                preview = None
                observation = None
                num_cached_before = self.num_cached[batch_index]

                if forecaster.can_predict():
                    raw_current = forecaster.compute_raw_guess(self.cnt, w=self.config.w)
                    preview = forecaster.apply_calibration(
                        raw_current,
                        enabled=self.config.enable_calibration,
                        strength=self.config.calibration_strength,
                        progress=progress,
                        mode=self.config.calibration_mode,
                        min_obs=self.config.calibration_min_obs,
                        buckets=self.config.calibration_buckets,
                    )
                    if self.config.enable_calibration:
                        observation = forecaster.observe_calibration(
                            raw_current,
                            actual_x,
                            progress=progress,
                            mode=self.config.calibration_mode,
                            decay=self.config.calibration_decay,
                            buckets=self.config.calibration_buckets,
                        )

                forecaster.update(self.cnt, actual_x)
                self.num_cached[batch_index] = 0

                if raw_current is not None and preview is not None:
                    self._log_step(
                        step_kind="actual",
                        batch_index=batch_index,
                        timestep_value=t_scalar,
                        progress=progress,
                        num_cached_before=num_cached_before,
                        raw_guess=raw_current,
                        apply_result=preview,
                        actual_x=actual_x,
                        observation=observation,
                    )

        if forecast_mask.any():
            forecast_indices = batch_index_tensor(forecast_mask).tolist()
            for batch_index in forecast_indices:
                forecaster = self.forecasters[batch_index]
                num_cached_before = self.num_cached[batch_index]
                raw_current = forecaster.compute_raw_guess(self.cnt, w=self.config.w)
                apply_result = forecaster.apply_calibration(
                    raw_current,
                    enabled=self.config.enable_calibration,
                    strength=self.config.calibration_strength,
                    progress=progress,
                    mode=self.config.calibration_mode,
                    min_obs=self.config.calibration_min_obs,
                    buckets=self.config.calibration_buckets,
                )
                # Phase 2 forecasts intermediate features, not final denoiser output.
                # The Phase 1 output-space clamp is too aggressive here and can wash out color/detail.
                predicted_x = apply_result.corrected.to(state.x.dtype)
                combined_x[batch_index] = predicted_x
                self.num_cached[batch_index] += 1
                self._log_step(
                    step_kind="forecast",
                    batch_index=batch_index,
                    timestep_value=t_scalar,
                    progress=progress,
                    num_cached_before=num_cached_before,
                    raw_guess=raw_current,
                    apply_result=apply_result,
                )

        if self.cnt >= self.config.warmup_steps:
            self.curr_ws += self.config.flex_window

        self.cnt += 1
        return replace_intermediate_feature_x(state, combined_x)


def _cast_extra(extra, dtype, device):
    try:
        import comfy.model_management
    except ImportError:
        return extra

    if hasattr(extra, "dtype"):
        if extra.dtype != torch.int and extra.dtype != torch.long:
            return comfy.model_management.cast_to_device(extra, device, dtype)
        return comfy.model_management.cast_to_device(extra, device, None)
    return extra


def _prepare_base_model_inputs(base_model, wrapper_kwargs: dict):
    c = dict(wrapper_kwargs.get("c", {}))
    sigma = wrapper_kwargs["timestep"]
    x = wrapper_kwargs["input"]

    c_concat = c.pop("c_concat", None)
    context = c.pop("c_crossattn", None)
    control = c.pop("control", None)
    transformer_options = c.pop("transformer_options", {})

    xc = base_model.model_sampling.calculate_input(sigma, x)
    dtype = base_model.get_dtype_inference()
    device = xc.device

    if c_concat is not None:
        xc = torch.cat([xc, _cast_extra(c_concat, dtype, device)], dim=1)

    xc = xc.to(dtype)
    t = base_model.model_sampling.timestep(sigma).float()

    if context is not None:
        context = _cast_extra(context, dtype, device)

    extra_conds = {}
    for key, value in c.items():
        if isinstance(value, list):
            extra_conds[key] = [_cast_extra(item, dtype, device) for item in value]
        else:
            extra_conds[key] = _cast_extra(value, dtype, device)

    if control is not None:
        extra_conds["control"] = control

    t = base_model.process_timestep(t, x=x, **extra_conds)

    if "latent_shapes" in extra_conds:
        try:
            import comfy.utils

            xc = comfy.utils.unpack_latents(xc, extra_conds.pop("latent_shapes"))
        except Exception:
            pass

    return xc, t, context, transformer_options, extra_conds, sigma, x


def _prepare_intermediate_args(target_model, context, extra_conds: dict):
    context_for_model = context
    phase2_kwargs = dict(extra_conds)

    t5xxl_ids = phase2_kwargs.pop("t5xxl_ids", None)
    if t5xxl_ids is not None and hasattr(target_model, "preprocess_text_embeds"):
        t5xxl_weights = phase2_kwargs.pop("t5xxl_weights", None)
        context_for_model = target_model.preprocess_text_embeds(
            context_for_model,
            t5xxl_ids,
            t5xxl_weights=t5xxl_weights,
        )

    attention_mask = phase2_kwargs.pop("attention_mask", None)
    return context_for_model, attention_mask, phase2_kwargs


def run_intermediate_forecast_path(
    diffusion_model,
    controller: IntermediateForecastController,
    x: torch.Tensor,
    timesteps: torch.Tensor,
    context: torch.Tensor,
    attention_mask: Optional[torch.Tensor] = None,
    transformer_options: Optional[dict] = None,
    **kwargs,
) -> torch.Tensor:
    base_state = extract_intermediate_feature_state(
        diffusion_model,
        x=x,
        timesteps=timesteps,
        context=context,
        attention_mask=attention_mask,
        transformer_options=transformer_options or {},
        **kwargs,
    )

    def compute_actual_feature_state(index_tensor: torch.Tensor) -> IntermediateFeatureState:
        sliced_state = slice_intermediate_feature_state(base_state, index_tensor)
        return run_blocks_from_intermediate_state(
            diffusion_model,
            sliced_state,
            transformer_options=transformer_options,
        )

    feature_state = controller.run(
        state=base_state,
        timestep=timesteps,
        schedule_context={"transformer_options": transformer_options or {}},
        compute_actual_feature_state=compute_actual_feature_state,
    )
    return decode_intermediate_feature_state(diffusion_model, feature_state)


def run_intermediate_apply_model(
    base_model,
    controller: IntermediateForecastController,
    wrapper_kwargs: dict,
) -> torch.Tensor:
    diffusion_model = base_model.diffusion_model
    target_model, _ = resolve_intermediate_feature_model(diffusion_model)
    xc, t, context, transformer_options, extra_conds, sigma, x = _prepare_base_model_inputs(base_model, wrapper_kwargs)
    context_for_model, attention_mask, phase2_kwargs = _prepare_intermediate_args(
        target_model,
        context,
        extra_conds,
    )

    model_output = run_intermediate_forecast_path(
        target_model,
        controller=controller,
        x=xc,
        timesteps=t,
        context=context_for_model,
        attention_mask=attention_mask,
        transformer_options=transformer_options,
        **phase2_kwargs,
    )

    if len(model_output) > 1 and not torch.is_tensor(model_output):
        try:
            import comfy.utils

            model_output, _ = comfy.utils.pack_latents(model_output)
        except Exception:
            pass

    return base_model.model_sampling.calculate_denoised(sigma, model_output.float(), x)

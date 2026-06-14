import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

import torch

from .calibration import CALIBRATION_MODE_LATEST
from .feature_sites import (
    FEATURE_SITE_POST_BLOCK,
    FEATURE_SITE_PRE_DECODER_HEAD,
    get_feature_site,
)
from .forecast_records import (
    build_run_start_record,
    build_step_record,
    build_topology_record,
)
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
from .topology import discover_topology


DEBUG_CLAMP_LIMIT = 10.0
DEBUG_LOG_DIR = Path(__file__).resolve().parents[1] / "docs" / "context_refactor" / "logs"
FORECAST_MODE_REPLACE = "replace"
FORECAST_MODE_SHADOW = "shadow"
FORECAST_MODE_ACTUAL_ONLY = "actual_only"
VALID_FORECAST_MODES = {
    FORECAST_MODE_REPLACE,
    FORECAST_MODE_SHADOW,
    FORECAST_MODE_ACTUAL_ONLY,
}


def _parse_step_set(value) -> frozenset[int]:
    if value is None:
        return frozenset()
    if isinstance(value, (set, frozenset, list, tuple)):
        items = value
    else:
        text = str(value).strip()
        if not text:
            return frozenset()
        items = text.replace(";", ",").split(",")

    steps = set()
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        try:
            step = int(text)
        except ValueError:
            continue
        if step >= 0:
            steps.add(step)
    return frozenset(steps)


def _normalize_forecast_mode(value) -> str:
    text = str(value or FORECAST_MODE_REPLACE).strip().lower()
    if text not in VALID_FORECAST_MODES:
        return FORECAST_MODE_REPLACE
    return text


def _sync_for_timing(tensor: torch.Tensor) -> None:
    if tensor.device.type != "cuda":
        return
    try:
        torch.cuda.synchronize(tensor.device)
    except (AssertionError, RuntimeError):
        pass


def _timed_call(enabled: bool, tensor: torch.Tensor, fn):
    if not enabled:
        return fn(), 0.0
    _sync_for_timing(tensor)
    started = time.perf_counter()
    result = fn()
    _sync_for_timing(tensor)
    return result, (time.perf_counter() - started) * 1000.0


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
    extra_forecast_steps: str
    enable_calibration: bool
    calibration_strength: float
    taylor_damping: float = 1.0
    multistep_damping: float = 1.0
    calibration_mode: str = CALIBRATION_MODE_LATEST
    calibration_decay: float = 0.9
    calibration_buckets: int = 4
    calibration_min_obs: int = 1
    feature_site: str = FEATURE_SITE_PRE_DECODER_HEAD
    target_block_index: int = 13
    forecast_mode: str = FORECAST_MODE_REPLACE
    debug_logging: bool = False


class Phase2DebugLogger:
    def __init__(self, enabled: bool):
        self.enabled = bool(enabled)
        self.run_counter = 0
        self.run_id: Optional[str] = None
        self.log_path: Optional[Path] = None
        self._topology_written = False
        self._pending_topology_record: Optional[dict] = None

    def reset(self) -> None:
        self.run_id = None
        self.log_path = None
        self._topology_written = False

    def set_topology(self, topology_report, support_report, feature_site_id: str) -> None:
        self._pending_topology_record = {
            "topology_report": topology_report,
            "support_report": support_report,
            "feature_site_id": feature_site_id,
        }

    def ensure_run(self, config: IntermediateForecastConfig, estimated_total_steps: int) -> None:
        if not self.enabled or self.log_path is not None:
            self._write_topology_if_ready()
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
            build_run_start_record(
                run_id=self.run_id,
                timestamp_utc=timestamp,
                estimated_total_steps=estimated_total_steps,
                patcher_config=config,
                feature_site_id=config.feature_site,
            )
        )
        self._write_topology_if_ready()

    def _write_topology_if_ready(self) -> None:
        if (
            not self.enabled
            or self.log_path is None
            or self.run_id is None
            or self._topology_written
            or self._pending_topology_record is None
        ):
            return

        self.write(
            build_topology_record(
                run_id=self.run_id,
                feature_site_id=self._pending_topology_record["feature_site_id"],
                topology_report=self._pending_topology_record["topology_report"],
                support_report=self._pending_topology_record["support_report"],
            )
        )
        self._topology_written = True

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
            extra_forecast_steps=",".join(str(step) for step in sorted(_parse_step_set(config.extra_forecast_steps))),
            enable_calibration=bool(config.enable_calibration),
            calibration_strength=max(0.0, min(1.0, float(config.calibration_strength))),
            taylor_damping=max(0.0, min(1.0, float(getattr(config, "taylor_damping", 1.0)))),
            multistep_damping=max(0.0, min(1.0, float(getattr(config, "multistep_damping", 1.0)))),
            calibration_mode=str(getattr(config, "calibration_mode", CALIBRATION_MODE_LATEST)),
            calibration_decay=max(0.0, min(0.999, float(getattr(config, "calibration_decay", 0.9)))),
            calibration_buckets=max(1, int(getattr(config, "calibration_buckets", 4))),
            calibration_min_obs=max(1, int(getattr(config, "calibration_min_obs", 1))),
            feature_site=get_feature_site(getattr(config, "feature_site", FEATURE_SITE_PRE_DECODER_HEAD)).id,
            target_block_index=max(0, int(getattr(config, "target_block_index", 13))),
            forecast_mode=_normalize_forecast_mode(getattr(config, "forecast_mode", "replace")),
            debug_logging=bool(getattr(config, "debug_logging", False)),
        )
        self.debug_logger = Phase2DebugLogger(enabled=self.config.debug_logging)
        self.extra_forecast_steps = _parse_step_set(self.config.extra_forecast_steps)
        self.reset()

    def set_topology(self, topology_report, support_report) -> None:
        self.debug_logger.set_topology(
            topology_report,
            support_report,
            self.config.feature_site,
        )

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
            CalibratedChebyshevForecaster(
                m=self.config.m,
                lam=self.config.lam,
                taylor_damping=self.config.taylor_damping,
                multistep_damping=self.config.multistep_damping,
            )
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

        if self.config.forecast_mode in {FORECAST_MODE_ACTUAL_ONLY, FORECAST_MODE_SHADOW}:
            return do_actual

        if self.cnt < self.config.warmup_steps or self._is_micro_final():
            return do_actual

        current_ws = max(1, int(math.floor(self.curr_ws)))
        for index in range(batch_size):
            do_actual[index] = ((self.num_cached[index] + 1) % current_ws) == 0
            if do_actual[index] and self.cnt in self.extra_forecast_steps:
                do_actual[index] = False
            if not self.forecasters[index].can_predict():
                do_actual[index] = True

        return do_actual

    def _current_progress(self) -> float:
        return max(0.0, min(1.0, float(self.cnt) / max(float(self.estimated_last_step_index), 1.0)))

    def _advance_window_after_actual(self) -> None:
        if self.cnt >= self.config.warmup_steps:
            self.curr_ws += self.config.flex_window

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
        timings: Optional[dict[str, float]] = None,
    ) -> None:
        if not self.config.debug_logging:
            return

        self.debug_logger.ensure_run(self.config, self.estimated_total_steps)
        calibrated_guess = apply_result.corrected
        self.debug_logger.write(
            build_step_record(
                run_id=self.debug_logger.run_id,
                feature_site_id=self.config.feature_site,
                forecast_mode=self.config.forecast_mode,
                step_kind=step_kind,
                step_index=self.cnt,
                timestep_value=timestep_value,
                estimated_total_steps=self.estimated_total_steps,
                estimated_last_step_index=self.estimated_last_step_index,
                progress=progress,
                batch_index=batch_index,
                num_cached_before=num_cached_before,
                window_size=max(1, int(math.floor(self.curr_ws))),
                config=self.config,
                raw_guess=raw_guess,
                calibrated_guess=calibrated_guess,
                correction=apply_result.correction,
                apply_result=apply_result,
                actual_x=actual_x,
                observation=observation,
                timings=timings,
                clip_limit=DEBUG_CLAMP_LIMIT,
            )
        )

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
        profile_enabled = bool(self.config.debug_logging)

        if actual_mask.any():
            actual_indices = batch_index_tensor(actual_mask)
            actual_state, actual_feature_ms = _timed_call(
                profile_enabled,
                state.x,
                lambda: compute_actual_feature_state(actual_indices),
            )
            combined_x[actual_mask] = actual_state.x
            if self.config.forecast_mode == FORECAST_MODE_REPLACE:
                self._advance_window_after_actual()

            for local_index, batch_index in enumerate(actual_indices.tolist()):
                forecaster = self.forecasters[batch_index]
                actual_x = actual_state.x[local_index]
                raw_current = None
                preview = None
                observation = None
                num_cached_before = self.num_cached[batch_index]
                raw_guess_ms = 0.0
                calibration_apply_ms = 0.0
                calibration_observe_ms = 0.0
                forecaster_update_ms = 0.0

                if self.config.forecast_mode != FORECAST_MODE_ACTUAL_ONLY and forecaster.can_predict():
                    raw_current, raw_guess_ms = _timed_call(
                        profile_enabled,
                        actual_x,
                        lambda: forecaster.compute_raw_guess(self.cnt, w=self.config.w),
                    )
                    preview, calibration_apply_ms = _timed_call(
                        profile_enabled,
                        actual_x,
                        lambda: forecaster.apply_calibration(
                            raw_current,
                            enabled=self.config.enable_calibration,
                            strength=self.config.calibration_strength,
                            progress=progress,
                            mode=self.config.calibration_mode,
                            min_obs=self.config.calibration_min_obs,
                            buckets=self.config.calibration_buckets,
                        ),
                    )
                    if self.config.enable_calibration:
                        observation, calibration_observe_ms = _timed_call(
                            profile_enabled,
                            actual_x,
                            lambda: forecaster.observe_calibration(
                                raw_current,
                                actual_x,
                                progress=progress,
                                mode=self.config.calibration_mode,
                                decay=self.config.calibration_decay,
                                buckets=self.config.calibration_buckets,
                            ),
                        )

                _update_result, forecaster_update_ms = _timed_call(
                    profile_enabled,
                    actual_x,
                    lambda: forecaster.update(self.cnt, actual_x),
                )
                self.num_cached[batch_index] = 0

                if raw_current is not None and preview is not None:
                    self._log_step(
                        step_kind="shadow" if self.config.forecast_mode == FORECAST_MODE_SHADOW else "actual",
                        batch_index=batch_index,
                        timestep_value=t_scalar,
                        progress=progress,
                        num_cached_before=num_cached_before,
                        raw_guess=raw_current,
                        apply_result=preview,
                        actual_x=actual_x,
                        observation=observation,
                        timings={
                            "actual_feature_ms": actual_feature_ms,
                            "raw_guess_ms": raw_guess_ms,
                            "calibration_apply_ms": calibration_apply_ms,
                            "calibration_observe_ms": calibration_observe_ms,
                            "forecaster_update_ms": forecaster_update_ms,
                            "path_total_ms": (
                                actual_feature_ms
                                + raw_guess_ms
                                + calibration_apply_ms
                                + calibration_observe_ms
                                + forecaster_update_ms
                            ),
                        },
                    )

        if forecast_mask.any():
            forecast_indices = batch_index_tensor(forecast_mask).tolist()
            for batch_index in forecast_indices:
                forecaster = self.forecasters[batch_index]
                num_cached_before = self.num_cached[batch_index]
                raw_current, raw_guess_ms = _timed_call(
                    profile_enabled,
                    state.x,
                    lambda: forecaster.compute_raw_guess(
                        self.cnt,
                        w=self.config.w,
                        forecast_horizon=num_cached_before + 1,
                    ),
                )
                apply_result, calibration_apply_ms = _timed_call(
                    profile_enabled,
                    state.x,
                    lambda: forecaster.apply_calibration(
                        raw_current,
                        enabled=self.config.enable_calibration,
                        strength=self.config.calibration_strength,
                        progress=progress,
                        mode=self.config.calibration_mode,
                        min_obs=self.config.calibration_min_obs,
                        buckets=self.config.calibration_buckets,
                    ),
                )
                # Phase 2 forecasts intermediate features, not final denoiser output.
                # The Phase 1 output-space clamp is too aggressive here and can wash out color/detail.
                predicted_x, cast_ms = _timed_call(
                    profile_enabled,
                    state.x,
                    lambda: apply_result.corrected.to(state.x.dtype),
                )
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
                    timings={
                        "raw_guess_ms": raw_guess_ms,
                        "calibration_apply_ms": calibration_apply_ms,
                        "forecast_cast_ms": cast_ms,
                        "path_total_ms": raw_guess_ms + calibration_apply_ms + cast_ms,
                    },
                )

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
    _, support = resolve_intermediate_feature_model(diffusion_model)

    if controller.config.feature_site == FEATURE_SITE_POST_BLOCK:
        block_stop = min(controller.config.target_block_index + 1, int(support.block_count))
        site_state = run_blocks_from_intermediate_state(
            diffusion_model,
            base_state,
            start_block=0,
            end_block=block_stop,
            transformer_options=transformer_options,
        )

        def compute_actual_feature_state(index_tensor: torch.Tensor) -> IntermediateFeatureState:
            return slice_intermediate_feature_state(site_state, index_tensor)

        feature_state = controller.run(
            state=site_state,
            timestep=timesteps,
            schedule_context={"transformer_options": transformer_options or {}},
            compute_actual_feature_state=compute_actual_feature_state,
        )
        final_state = run_blocks_from_intermediate_state(
            diffusion_model,
            feature_state,
            start_block=block_stop,
            end_block=None,
            transformer_options=transformer_options,
        )
        return decode_intermediate_feature_state(diffusion_model, final_state)

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
    target_model, support = resolve_intermediate_feature_model(diffusion_model)
    controller.set_topology(discover_topology(target_model), support)
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

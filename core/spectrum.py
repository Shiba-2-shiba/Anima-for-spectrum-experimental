import math
from dataclasses import dataclass
from typing import Callable, List, Optional

import torch

from .calibration import CALIBRATION_MODE_LATEST, ResidualCalibrationState
from .helpers import batch_index_tensor, safe_float_timestep, slice_model_kwargs
from .schedule import estimate_last_step_index, estimate_total_steps, should_reset_for_new_pass


_WARNED_ROCM_PINV_PATH = False


def _should_use_rocm_pinv(tensor: torch.Tensor) -> bool:
    return bool(getattr(torch.version, "hip", None)) and tensor.is_cuda


class CalibratedChebyshevForecaster:
    def __init__(
        self,
        m: int = 8,
        lam: float = 0.5,
        taylor_damping: float = 1.0,
        multistep_damping: float = 1.0,
    ):
        self.M = m
        self.K = max(m + 2, 8)
        self.lam = lam
        self.taylor_damping = max(0.0, min(1.0, float(taylor_damping)))
        self.multistep_damping = max(0.0, min(1.0, float(multistep_damping)))
        self.H_buf: List[torch.Tensor] = []
        self.T_buf: List[float] = []
        self.Cnt_buf: List[float] = []
        self.shape = None
        self.dtype = None
        self.t_max = 49.0
        self.calibration = ResidualCalibrationState()

    def _taus(self, t: float) -> float:
        return (float(t) / max(float(self.t_max), 1.0)) * 2.0 - 1.0

    def _build_design(self, taus: torch.Tensor) -> torch.Tensor:
        taus = taus.reshape(-1, 1)
        terms = [torch.ones((taus.shape[0], 1), device=taus.device, dtype=torch.float32)]
        if self.M > 0:
            terms.append(taus)
            for _ in range(2, self.M + 1):
                terms.append(2 * taus * terms[-1] - terms[-2])
        return torch.cat(terms[: self.M + 1], dim=1)

    def _solve_coefficients(self, design: torch.Tensor, history: torch.Tensor) -> torch.Tensor:
        global _WARNED_ROCM_PINV_PATH

        device = design.device
        eye = torch.eye(self.M + 1, device=device, dtype=torch.float32)
        xtx = design.T @ design + self.lam * eye
        xty = design.T @ history
        jitter = (1e-5 * xtx.diag().abs().mean()).clamp_min(1e-8)
        regularized_xtx = xtx + jitter * eye

        if _should_use_rocm_pinv(design):
            if not _WARNED_ROCM_PINV_PATH:
                print("[AnimaSpectrum] Using ROCm-safe GPU pinv solver for Spectrum coefficient fit.")
                _WARNED_ROCM_PINV_PATH = True
            return torch.linalg.pinv(regularized_xtx) @ xty

        try:
            return torch.linalg.solve(xtx, xty)
        except RuntimeError:
            try:
                return torch.linalg.solve(regularized_xtx, xty)
            except RuntimeError:
                return torch.linalg.pinv(regularized_xtx) @ xty

    def can_predict(self) -> bool:
        return len(self.H_buf) > 0

    def update(self, cnt: int, h: torch.Tensor) -> None:
        if self.shape is not None and h.shape != self.shape:
            self.reset_buffers()

        self.shape = h.shape
        self.dtype = h.dtype

        self.H_buf.append(h.detach().reshape(-1))
        self.T_buf.append(self._taus(cnt))
        self.Cnt_buf.append(float(cnt))
        if len(self.H_buf) > self.K:
            self.H_buf.pop(0)
            self.T_buf.pop(0)
            self.Cnt_buf.pop(0)

    def _compute_taylor_guess(self, cnt: int, *, forecast_horizon: int = 1) -> torch.Tensor:
        if len(self.H_buf) < 2:
            return self.H_buf[-1].to(torch.float32)

        h_i = self.H_buf[-1].to(torch.float32)
        h_im1 = self.H_buf[-2].to(torch.float32)
        step_i = self.Cnt_buf[-1]
        step_im1 = self.Cnt_buf[-2]
        step_delta = max(step_i - step_im1, 1e-8)
        target_delta = float(cnt) - step_i
        raw_scale = target_delta / step_delta
        if int(forecast_horizon) > 1:
            raw_scale *= self.multistep_damping
        scale = raw_scale * self.taylor_damping
        return h_i + scale * (h_i - h_im1)

    def compute_raw_guess(self, cnt: int, w: float, *, forecast_horizon: int = 1) -> torch.Tensor:
        if not self.H_buf:
            raise RuntimeError("Cannot compute a raw forecast without any cached history.")

        device = self.H_buf[-1].device
        history = torch.stack(self.H_buf, dim=0).to(torch.float32)
        taus = torch.tensor(self.T_buf, dtype=torch.float32, device=device)

        design = self._build_design(taus)
        coef = self._solve_coefficients(design, history)

        tau_star = torch.tensor([self._taus(cnt)], device=device, dtype=torch.float32)
        x_star = self._build_design(tau_star)
        pred_cheb = (x_star @ coef).squeeze(0)

        h_taylor = self._compute_taylor_guess(cnt, forecast_horizon=forecast_horizon)

        return ((1.0 - w) * h_taylor + w * pred_cheb).view(self.shape)

    def apply_calibration(
        self,
        raw_guess: torch.Tensor,
        *,
        enabled: bool,
        strength: float,
        progress: float,
        mode: str = CALIBRATION_MODE_LATEST,
        min_obs: int = 1,
        buckets: int = 4,
    ):
        return self.calibration.apply(
            raw_guess,
            enabled=enabled,
            strength=strength,
            progress=progress,
            mode=mode,
            min_obs=min_obs,
            buckets=buckets,
        )

    def observe_calibration(
        self,
        raw_guess: torch.Tensor,
        actual: torch.Tensor,
        *,
        progress: float,
        mode: str = CALIBRATION_MODE_LATEST,
        decay: float = 0.9,
        buckets: int = 4,
    ):
        return self.calibration.observe(
            raw_guess,
            actual,
            progress=progress,
            mode=mode,
            decay=decay,
            buckets=buckets,
        )

    def predict(
        self,
        cnt: int,
        w: float,
        enable_calibration: bool = False,
        calibration_strength: float = 0.5,
        *,
        forecast_horizon: int = 1,
        progress: float = 0.0,
        calibration_mode: str = CALIBRATION_MODE_LATEST,
        calibration_decay: float = 0.9,
        calibration_buckets: int = 4,
        calibration_min_obs: int = 1,
    ) -> torch.Tensor:
        raw_guess = self.compute_raw_guess(cnt, w=w, forecast_horizon=forecast_horizon)
        apply_result = self.apply_calibration(
            raw_guess,
            enabled=enable_calibration,
            strength=calibration_strength,
            progress=progress,
            mode=calibration_mode,
            min_obs=calibration_min_obs,
            buckets=calibration_buckets,
        )
        del calibration_decay
        return torch.clamp(apply_result.corrected, -10.0, 10.0).to(self.dtype).view(self.shape)

    def reset_buffers(self) -> None:
        self.H_buf.clear()
        self.T_buf.clear()
        self.Cnt_buf.clear()
        self.shape = None
        self.dtype = None
        self.calibration.reset()


@dataclass(frozen=True)
class SpectrumConfig:
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
    taylor_damping: float = 1.0
    multistep_damping: float = 1.0
    calibration_mode: str = CALIBRATION_MODE_LATEST
    calibration_decay: float = 0.9
    calibration_buckets: int = 4
    calibration_min_obs: int = 1


class SpectrumController:
    def __init__(self, config: SpectrumConfig):
        self.config = SpectrumConfig(
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
            taylor_damping=max(0.0, min(1.0, float(getattr(config, "taylor_damping", 1.0)))),
            multistep_damping=max(0.0, min(1.0, float(getattr(config, "multistep_damping", 1.0)))),
            calibration_mode=str(getattr(config, "calibration_mode", CALIBRATION_MODE_LATEST)),
            calibration_decay=max(0.0, min(0.999, float(getattr(config, "calibration_decay", 0.9)))),
            calibration_buckets=max(1, int(getattr(config, "calibration_buckets", 4))),
            calibration_min_obs=max(1, int(getattr(config, "calibration_min_obs", 1))),
        )
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
        self.total_runs = 0

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

    def _compute_actual_mask(self, x: torch.Tensor) -> torch.Tensor:
        batch_size = x.shape[0]
        do_actual = torch.ones(batch_size, dtype=torch.bool, device=x.device)

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

    def _advance_window_after_actual(self) -> None:
        if self.cnt >= self.config.warmup_steps:
            self.curr_ws += self.config.flex_window

    def run(self, kwargs: dict, compute_actual: Callable[[dict], torch.Tensor]):
        if not self.config.enabled:
            return compute_actual(kwargs)

        x = kwargs["input"]
        batch_size = x.shape[0]
        t_scalar = safe_float_timestep(kwargs["timestep"])

        if should_reset_for_new_pass(t_scalar, self.last_t):
            self.forecasters = None
            self.cnt = 0
            self.num_cached = [0] * batch_size
            self.curr_ws = float(self.config.window_size)
            self.total_runs += 1

        self.last_t = t_scalar
        self.estimated_total_steps = estimate_total_steps(
            current_step=self.cnt,
            c=kwargs.get("c", {}),
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
        for forecaster in self.forecasters:
            forecaster.t_max = float(max(1, self.estimated_last_step_index))

        progress = self._current_progress()
        actual_mask = self._compute_actual_mask(x)
        forecast_mask = ~actual_mask
        out = torch.empty_like(x)

        if actual_mask.any():
            actual_indices = batch_index_tensor(actual_mask)
            actual_kwargs = slice_model_kwargs(kwargs, actual_indices, batch_size)
            actual_out = compute_actual(actual_kwargs)
            out[actual_mask] = actual_out
            self._advance_window_after_actual()

            for local_index, batch_index in enumerate(actual_indices.tolist()):
                forecaster = self.forecasters[batch_index]
                actual_value = actual_out[local_index]
                if self.config.enable_calibration and forecaster.can_predict():
                    raw_current = forecaster.compute_raw_guess(self.cnt, w=self.config.w)
                    forecaster.observe_calibration(
                        raw_current,
                        actual_value,
                        progress=progress,
                        mode=self.config.calibration_mode,
                        decay=self.config.calibration_decay,
                        buckets=self.config.calibration_buckets,
                    )
                forecaster.update(self.cnt, actual_value)
                self.num_cached[batch_index] = 0

        if forecast_mask.any():
            forecast_indices = batch_index_tensor(forecast_mask).tolist()
            forecast_out = torch.empty(
                (len(forecast_indices), *x.shape[1:]),
                device=x.device,
                dtype=x.dtype,
            )
            for local_index, batch_index in enumerate(forecast_indices):
                forecast_out[local_index] = self.forecasters[batch_index].predict(
                    self.cnt,
                    w=self.config.w,
                    enable_calibration=self.config.enable_calibration,
                    calibration_strength=self.config.calibration_strength,
                    forecast_horizon=self.num_cached[batch_index] + 1,
                    progress=progress,
                    calibration_mode=self.config.calibration_mode,
                    calibration_decay=self.config.calibration_decay,
                    calibration_buckets=self.config.calibration_buckets,
                    calibration_min_obs=self.config.calibration_min_obs,
                ).to(x.dtype)
                self.num_cached[batch_index] += 1
            out[forecast_mask] = forecast_out

        self.cnt += 1
        return out

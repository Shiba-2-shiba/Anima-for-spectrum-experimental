from dataclasses import dataclass, field
from typing import Dict, Optional

import torch


CALIBRATION_MODE_OFF = "off"
CALIBRATION_MODE_LATEST = "latest"
CALIBRATION_MODE_EMA = "ema"
CALIBRATION_MODE_BUCKETED_EMA = "bucketed_ema"
SUPPORTED_CALIBRATION_MODES = (
    CALIBRATION_MODE_OFF,
    CALIBRATION_MODE_LATEST,
    CALIBRATION_MODE_EMA,
    CALIBRATION_MODE_BUCKETED_EMA,
)


@dataclass
class ResidualBucketState:
    residual: Optional[torch.Tensor] = None
    obs_count: int = 0


@dataclass(frozen=True)
class CalibrationApplyResult:
    corrected: torch.Tensor
    correction: torch.Tensor
    bucket_id: int
    obs_count: int
    residual_norm: float


@dataclass(frozen=True)
class CalibrationObservation:
    bucket_id: int
    obs_count: int
    residual_norm: float


@dataclass
class ResidualCalibrationState:
    global_state: ResidualBucketState = field(default_factory=ResidualBucketState)
    bucket_states: Dict[int, ResidualBucketState] = field(default_factory=dict)

    def _normalize_mode(self, mode: str) -> str:
        if mode in SUPPORTED_CALIBRATION_MODES:
            return mode
        return CALIBRATION_MODE_LATEST

    def _bucket_id(self, mode: str, progress: float, buckets: int) -> int:
        if self._normalize_mode(mode) != CALIBRATION_MODE_BUCKETED_EMA:
            return 0

        progress_value = max(0.0, min(1.0, float(progress)))
        bucket_count = max(1, int(buckets))
        return min(bucket_count - 1, int(progress_value * bucket_count))

    def _resolve_bucket(self, mode: str, progress: float, buckets: int) -> tuple[int, ResidualBucketState]:
        bucket_id = self._bucket_id(mode, progress, buckets)
        if bucket_id == 0 and self._normalize_mode(mode) != CALIBRATION_MODE_BUCKETED_EMA:
            return bucket_id, self.global_state
        return bucket_id, self.bucket_states.setdefault(bucket_id, ResidualBucketState())

    def apply(
        self,
        raw_guess: torch.Tensor,
        enabled: bool,
        strength: float,
        *,
        progress: float = 0.0,
        mode: str = CALIBRATION_MODE_LATEST,
        min_obs: int = 1,
        buckets: int = 4,
    ) -> CalibrationApplyResult:
        raw_tensor = raw_guess.detach().to(torch.float32)
        raw_vector = raw_tensor.reshape(-1)
        correction_vector = torch.zeros_like(raw_vector)

        normalized_mode = self._normalize_mode(mode)
        bucket_id, bucket = self._resolve_bucket(normalized_mode, progress, buckets)
        obs_count = bucket.obs_count
        residual_norm = float(bucket.residual.norm().item()) if bucket.residual is not None else 0.0

        if enabled and normalized_mode != CALIBRATION_MODE_OFF:
            if bucket.residual is not None and obs_count >= max(1, int(min_obs)):
                correction_vector = bucket.residual.to(
                    device=raw_vector.device,
                    dtype=torch.float32,
                ) * float(strength)

        corrected = (raw_vector + correction_vector).view_as(raw_tensor)
        correction = correction_vector.view_as(raw_tensor)
        return CalibrationApplyResult(
            corrected=corrected,
            correction=correction,
            bucket_id=bucket_id,
            obs_count=obs_count,
            residual_norm=residual_norm,
        )

    def observe(
        self,
        predicted: torch.Tensor,
        actual: torch.Tensor,
        *,
        progress: float = 0.0,
        mode: str = CALIBRATION_MODE_LATEST,
        decay: float = 0.9,
        buckets: int = 4,
    ) -> CalibrationObservation:
        normalized_mode = self._normalize_mode(mode)
        if normalized_mode == CALIBRATION_MODE_OFF:
            return CalibrationObservation(bucket_id=0, obs_count=0, residual_norm=0.0)

        predicted_vector = predicted.detach().reshape(-1).to(torch.float32)
        actual_vector = actual.detach().reshape(-1).to(torch.float32)
        residual = actual_vector - predicted_vector

        bucket_id, bucket = self._resolve_bucket(normalized_mode, progress, buckets)
        if bucket.residual is None or normalized_mode == CALIBRATION_MODE_LATEST:
            bucket.residual = residual
        else:
            decay_value = max(0.0, min(0.999, float(decay)))
            bucket.residual = bucket.residual * decay_value + residual * (1.0 - decay_value)

        bucket.obs_count += 1
        residual_norm = float(bucket.residual.norm().item()) if bucket.residual is not None else 0.0
        return CalibrationObservation(
            bucket_id=bucket_id,
            obs_count=bucket.obs_count,
            residual_norm=residual_norm,
        )

    def reset(self) -> None:
        self.global_state = ResidualBucketState()
        self.bucket_states.clear()

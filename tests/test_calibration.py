import torch

from core.calibration import (
    CALIBRATION_MODE_BUCKETED_EMA,
    CALIBRATION_MODE_EMA,
    CALIBRATION_MODE_LATEST,
    CALIBRATION_MODE_OFF,
    ResidualCalibrationState,
)


def test_calibration_apply_is_noop_without_observations():
    state = ResidualCalibrationState()
    raw = torch.tensor([1.0, 2.0])

    result = state.apply(raw, enabled=True, strength=0.5)

    assert torch.equal(result.corrected, raw)
    assert torch.equal(result.correction, torch.zeros_like(raw))
    assert result.obs_count == 0


def test_latest_calibration_applies_last_observed_residual():
    state = ResidualCalibrationState()
    state.observe(
        predicted=torch.tensor([1.0, 1.0]),
        actual=torch.tensor([3.0, 5.0]),
        mode=CALIBRATION_MODE_LATEST,
    )

    result = state.apply(
        torch.tensor([10.0, 10.0]),
        enabled=True,
        strength=0.5,
        mode=CALIBRATION_MODE_LATEST,
    )

    assert torch.equal(result.corrected, torch.tensor([11.0, 12.0]))
    assert result.obs_count == 1


def test_ema_calibration_blends_residuals_with_decay():
    state = ResidualCalibrationState()
    state.observe(torch.tensor([0.0]), torch.tensor([10.0]), mode=CALIBRATION_MODE_EMA, decay=0.5)
    state.observe(torch.tensor([0.0]), torch.tensor([2.0]), mode=CALIBRATION_MODE_EMA, decay=0.5)

    result = state.apply(torch.tensor([1.0]), enabled=True, strength=1.0, mode=CALIBRATION_MODE_EMA)

    assert torch.equal(result.corrected, torch.tensor([7.0]))
    assert result.obs_count == 2


def test_bucketed_ema_uses_progress_specific_buckets():
    state = ResidualCalibrationState()
    state.observe(
        torch.tensor([0.0]),
        torch.tensor([1.0]),
        progress=0.1,
        mode=CALIBRATION_MODE_BUCKETED_EMA,
        buckets=4,
    )
    state.observe(
        torch.tensor([0.0]),
        torch.tensor([9.0]),
        progress=0.9,
        mode=CALIBRATION_MODE_BUCKETED_EMA,
        buckets=4,
    )

    early = state.apply(
        torch.tensor([0.0]),
        enabled=True,
        strength=1.0,
        progress=0.1,
        mode=CALIBRATION_MODE_BUCKETED_EMA,
        buckets=4,
    )
    late = state.apply(
        torch.tensor([0.0]),
        enabled=True,
        strength=1.0,
        progress=0.9,
        mode=CALIBRATION_MODE_BUCKETED_EMA,
        buckets=4,
    )

    assert torch.equal(early.corrected, torch.tensor([1.0]))
    assert torch.equal(late.corrected, torch.tensor([9.0]))


def test_calibration_off_observes_nothing_and_applies_nothing():
    state = ResidualCalibrationState()
    observation = state.observe(torch.tensor([0.0]), torch.tensor([10.0]), mode=CALIBRATION_MODE_OFF)
    result = state.apply(torch.tensor([1.0]), enabled=True, strength=1.0, mode=CALIBRATION_MODE_OFF)

    assert observation.obs_count == 0
    assert torch.equal(result.corrected, torch.tensor([1.0]))

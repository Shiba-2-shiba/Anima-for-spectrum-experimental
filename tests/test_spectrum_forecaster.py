import pytest
import torch

from core.spectrum import CalibratedChebyshevForecaster


def test_raw_guess_taylor_component_scales_with_target_step_distance():
    forecaster = CalibratedChebyshevForecaster(m=1, lam=0.1)
    forecaster.update(10, torch.tensor([10.0]))
    forecaster.update(12, torch.tensor([14.0]))

    raw_guess = forecaster.compute_raw_guess(16, w=0.0)

    assert raw_guess.item() == pytest.approx(22.0)


def test_taylor_damping_reduces_the_taylor_delta_without_changing_history():
    forecaster = CalibratedChebyshevForecaster(m=1, lam=0.1, taylor_damping=0.5)
    forecaster.update(10, torch.tensor([10.0]))
    forecaster.update(12, torch.tensor([14.0]))

    raw_guess = forecaster.compute_raw_guess(16, w=0.0)

    assert raw_guess.item() == pytest.approx(18.0)
    assert forecaster.Cnt_buf == [10.0, 12.0]


def test_multistep_damping_preserves_one_step_taylor_extrapolation():
    forecaster = CalibratedChebyshevForecaster(m=1, lam=0.1, multistep_damping=0.0)
    forecaster.update(10, torch.tensor([10.0]))
    forecaster.update(12, torch.tensor([14.0]))

    raw_guess = forecaster.compute_raw_guess(14, w=0.0)

    assert raw_guess.item() == pytest.approx(18.0)


def test_multistep_damping_does_not_change_default_horizon_prediction():
    forecaster = CalibratedChebyshevForecaster(m=1, lam=0.1, multistep_damping=0.5)
    forecaster.update(10, torch.tensor([10.0]))
    forecaster.update(12, torch.tensor([14.0]))

    raw_guess = forecaster.compute_raw_guess(16, w=0.0)

    assert raw_guess.item() == pytest.approx(22.0)


def test_multistep_damping_reduces_consecutive_forecast_horizon_prediction():
    forecaster = CalibratedChebyshevForecaster(m=1, lam=0.1, multistep_damping=0.5)
    forecaster.update(10, torch.tensor([10.0]))
    forecaster.update(12, torch.tensor([14.0]))

    raw_guess = forecaster.compute_raw_guess(16, w=0.0, forecast_horizon=2)

    assert raw_guess.item() == pytest.approx(18.0)


def test_reset_buffers_clears_cached_step_history():
    forecaster = CalibratedChebyshevForecaster(m=1, lam=0.1)
    forecaster.update(10, torch.tensor([10.0]))

    forecaster.reset_buffers()

    assert forecaster.H_buf == []
    assert forecaster.T_buf == []
    assert forecaster.Cnt_buf == []

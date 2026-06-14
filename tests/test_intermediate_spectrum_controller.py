import torch

from core.intermediate_spectrum import IntermediateForecastConfig, IntermediateForecastController
from core.spectrum import SpectrumConfig, SpectrumController


def _config(stop_caching_step: int) -> IntermediateForecastConfig:
    return IntermediateForecastConfig(
        enabled=True,
        w=0.05,
        m=16,
        lam=0.5,
        warmup_steps=18,
        window_size=2,
        flex_window=0.0,
        stop_caching_step=stop_caching_step,
        extra_forecast_steps="",
        enable_calibration=False,
        calibration_strength=0.35,
    )


class _ReadyForecaster:
    def can_predict(self) -> bool:
        return True


def _flex_config() -> IntermediateForecastConfig:
    return IntermediateForecastConfig(
        enabled=True,
        w=0.05,
        m=16,
        lam=0.5,
        warmup_steps=5,
        window_size=2,
        flex_window=0.75,
        stop_caching_step=0,
        extra_forecast_steps="",
        enable_calibration=False,
        calibration_strength=0.35,
    )


def _spectrum_flex_config() -> SpectrumConfig:
    return SpectrumConfig(
        enabled=True,
        w=0.05,
        m=16,
        lam=0.5,
        warmup_steps=5,
        window_size=2,
        flex_window=0.75,
        stop_caching_step=0,
        enable_calibration=False,
        calibration_strength=0.35,
    )


def _simulate_intermediate_schedule(controller: IntermediateForecastController, steps: int) -> list[int]:
    actual_steps = []
    controller.forecasters = [_ReadyForecaster()]
    controller.num_cached = [0]
    controller.estimated_total_steps = steps

    for step in range(steps):
        controller.cnt = step
        actual_mask = controller._compute_actual_mask(batch_size=1, device=torch.device("cpu"))
        if bool(actual_mask.item()):
            actual_steps.append(step)
            controller.num_cached[0] = 0
            controller._advance_window_after_actual()
        else:
            controller.num_cached[0] += 1

    return actual_steps


def _simulate_output_schedule(controller: SpectrumController, steps: int) -> list[int]:
    actual_steps = []
    controller.forecasters = [_ReadyForecaster()]
    controller.num_cached = [0]
    controller.estimated_total_steps = steps
    x = torch.zeros((1, 1))

    for step in range(steps):
        controller.cnt = step
        actual_mask = controller._compute_actual_mask(x)
        if bool(actual_mask.item()):
            actual_steps.append(step)
            controller.num_cached[0] = 0
            controller._advance_window_after_actual()
        else:
            controller.num_cached[0] += 1

    return actual_steps


def test_default_stop_guard_switches_to_actual_path_after_eighty_percent():
    controller = IntermediateForecastController(_config(stop_caching_step=-1))
    controller.estimated_total_steps = 30

    controller.cnt = 23
    assert controller._is_micro_final() is False

    controller.cnt = 24
    assert controller._is_micro_final() is True


def test_zero_stop_guard_disables_late_actual_only_guard():
    controller = IntermediateForecastController(_config(stop_caching_step=0))
    controller.estimated_total_steps = 30

    controller.cnt = 24
    assert controller._is_micro_final() is False

    controller.cnt = 29
    assert controller._is_micro_final() is False


def test_flex_window_advances_only_after_actual_intermediate_steps():
    controller = IntermediateForecastController(_flex_config())

    assert _simulate_intermediate_schedule(controller, steps=30) == [
        0,
        1,
        2,
        3,
        4,
        6,
        8,
        11,
        15,
        20,
        25,
    ]


def test_extra_forecast_steps_preserve_default_when_empty():
    controller = IntermediateForecastController(_config(stop_caching_step=0))

    assert _simulate_intermediate_schedule(controller, steps=30) == [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        19,
        21,
        23,
        25,
        27,
        29,
    ]


def test_extra_forecast_steps_can_add_one_w18_skip():
    config = _config(stop_caching_step=0)
    config = IntermediateForecastConfig(
        enabled=config.enabled,
        w=config.w,
        m=config.m,
        lam=config.lam,
        warmup_steps=config.warmup_steps,
        window_size=config.window_size,
        flex_window=config.flex_window,
        stop_caching_step=config.stop_caching_step,
        extra_forecast_steps="23",
        enable_calibration=config.enable_calibration,
        calibration_strength=config.calibration_strength,
    )
    controller = IntermediateForecastController(config)

    assert _simulate_intermediate_schedule(controller, steps=30) == [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        19,
        21,
        25,
        27,
        29,
    ]


def test_flex_window_advances_only_after_actual_output_steps():
    controller = SpectrumController(_spectrum_flex_config())

    assert _simulate_output_schedule(controller, steps=30) == [
        0,
        1,
        2,
        3,
        4,
        6,
        8,
        11,
        15,
        20,
        25,
    ]

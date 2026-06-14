try:
    from ..core.intermediate_features import detect_intermediate_feature_support
    from ..core.intermediate_spectrum import (
        IntermediateForecastConfig,
        IntermediateForecastController,
        run_intermediate_apply_model,
    )
    from .input_specs import (
        ANIMA_NODE_CATEGORY,
        PHASE2_NODE_DESCRIPTION,
        PHASE2_NODE_DISPLAY_NAME,
        PHASE2_NODE_ID,
        SPECTRUM_PRESET_MANUAL,
        SPECTRUM_PRESET_W15_F05_MS000,
        SPECTRUM_PRESET_W18_STOP0,
        build_phase2_input_types,
    )
except ImportError:
    from core.intermediate_features import detect_intermediate_feature_support
    from core.intermediate_spectrum import (
        IntermediateForecastConfig,
        IntermediateForecastController,
        run_intermediate_apply_model,
    )
    from nodes.input_specs import (
        ANIMA_NODE_CATEGORY,
        PHASE2_NODE_DESCRIPTION,
        PHASE2_NODE_DISPLAY_NAME,
        PHASE2_NODE_ID,
        SPECTRUM_PRESET_MANUAL,
        SPECTRUM_PRESET_W15_F05_MS000,
        SPECTRUM_PRESET_W18_STOP0,
        build_phase2_input_types,
    )


def resolve_spectrum_preset(
    spectrum_preset: str,
    *,
    spectrum_w: float,
    spectrum_warmup_steps: int,
    spectrum_window_size: int,
    enable_calibration: bool,
    spectrum_m: int,
    spectrum_lam: float,
    spectrum_taylor_damping: float,
    spectrum_multistep_damping: float,
    spectrum_flex_window: float,
    spectrum_stop_caching_step: int,
    spectrum_extra_forecast_steps: str,
) -> dict:
    settings = {
        "spectrum_w": spectrum_w,
        "spectrum_warmup_steps": spectrum_warmup_steps,
        "spectrum_window_size": spectrum_window_size,
        "enable_calibration": enable_calibration,
        "spectrum_m": spectrum_m,
        "spectrum_lam": spectrum_lam,
        "spectrum_taylor_damping": spectrum_taylor_damping,
        "spectrum_multistep_damping": spectrum_multistep_damping,
        "spectrum_flex_window": spectrum_flex_window,
        "spectrum_stop_caching_step": spectrum_stop_caching_step,
        "spectrum_extra_forecast_steps": spectrum_extra_forecast_steps,
    }

    if spectrum_preset in ("", None, SPECTRUM_PRESET_MANUAL):
        return settings

    if spectrum_preset == SPECTRUM_PRESET_W18_STOP0:
        settings.update(
            spectrum_w=0.05,
            spectrum_warmup_steps=18,
            spectrum_window_size=2,
            enable_calibration=False,
            spectrum_m=16,
            spectrum_lam=0.5,
            spectrum_taylor_damping=1.0,
            spectrum_multistep_damping=1.0,
            spectrum_flex_window=0.0,
            spectrum_stop_caching_step=0,
            spectrum_extra_forecast_steps="",
        )
        return settings

    if spectrum_preset == SPECTRUM_PRESET_W15_F05_MS000:
        settings.update(
            spectrum_w=0.05,
            spectrum_warmup_steps=15,
            spectrum_window_size=2,
            enable_calibration=False,
            spectrum_m=16,
            spectrum_lam=0.5,
            spectrum_taylor_damping=1.0,
            spectrum_multistep_damping=0.0,
            spectrum_flex_window=0.5,
            spectrum_stop_caching_step=0,
            spectrum_extra_forecast_steps="",
        )
        return settings

    raise ValueError(f"Unknown Anima Spectrum preset: {spectrum_preset!r}")


class AnimaIntermediateSpectrumPatcher:
    """Runtime wrapper that forecasts intermediate features before decode."""

    DESCRIPTION = PHASE2_NODE_DESCRIPTION
    CATEGORY = ANIMA_NODE_CATEGORY
    RETURN_NAMES = ("patched_model",)

    @classmethod
    def INPUT_TYPES(cls):
        return build_phase2_input_types()

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "patch"

    def patch(
        self,
        model,
        spectrum_preset: str,
        spectrum_w: float,
        spectrum_warmup_steps: int,
        spectrum_window_size: int,
        enable_calibration: bool,
        calibration_strength: float,
        calibration_mode: str,
        spectrum_m: int,
        spectrum_lam: float,
        spectrum_taylor_damping: float,
        spectrum_multistep_damping: float,
        spectrum_flex_window: float,
        spectrum_stop_caching_step: int,
        spectrum_extra_forecast_steps: str,
        calibration_decay: float,
        calibration_buckets: int,
        calibration_min_obs: int,
        debug_enable_spectrum: bool,
        feature_site: str,
        target_block_index: int,
        forecast_mode: str,
        debug_logging: bool,
    ):
        patched_model = model.clone()
        diffusion_model = patched_model.get_model_object("diffusion_model")

        support = detect_intermediate_feature_support(diffusion_model)
        if support is None:
            cls_name = diffusion_model.__class__.__name__
            mod_name = diffusion_model.__class__.__module__
            raise RuntimeError(
                "AnimaIntermediateSpectrumPatcher only supports Anima-style diffusion models "
                "with forward_before_blocks(), decoder_head(), and a repeated block container. "
                f"Got {mod_name}.{cls_name}."
            )

        previous_wrapper = patched_model.model_options.get("model_function_wrapper")
        if previous_wrapper is not None:
            raise RuntimeError(
                "AnimaIntermediateSpectrumPatcher cannot be stacked with another "
                "model_function_wrapper patch yet. Apply it to a clean MODEL input."
            )

        preset_settings = resolve_spectrum_preset(
            spectrum_preset,
            spectrum_w=spectrum_w,
            spectrum_warmup_steps=spectrum_warmup_steps,
            spectrum_window_size=spectrum_window_size,
            enable_calibration=enable_calibration,
            spectrum_m=spectrum_m,
            spectrum_lam=spectrum_lam,
            spectrum_taylor_damping=spectrum_taylor_damping,
            spectrum_multistep_damping=spectrum_multistep_damping,
            spectrum_flex_window=spectrum_flex_window,
            spectrum_stop_caching_step=spectrum_stop_caching_step,
            spectrum_extra_forecast_steps=spectrum_extra_forecast_steps,
        )

        controller = IntermediateForecastController(
            IntermediateForecastConfig(
                enabled=debug_enable_spectrum,
                w=preset_settings["spectrum_w"],
                m=preset_settings["spectrum_m"],
                lam=preset_settings["spectrum_lam"],
                taylor_damping=preset_settings["spectrum_taylor_damping"],
                multistep_damping=preset_settings["spectrum_multistep_damping"],
                warmup_steps=preset_settings["spectrum_warmup_steps"],
                window_size=preset_settings["spectrum_window_size"],
                flex_window=preset_settings["spectrum_flex_window"],
                stop_caching_step=preset_settings["spectrum_stop_caching_step"],
                extra_forecast_steps=preset_settings["spectrum_extra_forecast_steps"],
                enable_calibration=preset_settings["enable_calibration"],
                calibration_strength=calibration_strength,
                calibration_mode=calibration_mode,
                calibration_decay=calibration_decay,
                calibration_buckets=calibration_buckets,
                calibration_min_obs=calibration_min_obs,
                feature_site=feature_site,
                target_block_index=target_block_index,
                forecast_mode=forecast_mode,
                debug_logging=debug_logging,
            )
        )

        def intermediate_unet_wrapper(model_function, kwargs):
            if not controller.config.enabled:
                return model_function(
                    kwargs["input"],
                    kwargs["timestep"],
                    **kwargs["c"],
                )

            base_model = getattr(model_function, "__self__", None)
            if base_model is None:
                raise RuntimeError(
                    "Phase 2 intermediate-spectrum wrapper expected a bound BaseModel.apply_model call."
                )

            return run_intermediate_apply_model(base_model, controller, kwargs)

        patched_model.set_model_unet_function_wrapper(intermediate_unet_wrapper)
        return (patched_model,)


NODE_CLASS_MAPPINGS = {
    PHASE2_NODE_ID: AnimaIntermediateSpectrumPatcher,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    PHASE2_NODE_ID: PHASE2_NODE_DISPLAY_NAME,
}

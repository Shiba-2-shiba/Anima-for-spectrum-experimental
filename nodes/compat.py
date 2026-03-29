try:
    from ..core.model_introspection import looks_like_supported_model
    from ..core.replay import ReplayConfig, ReplayController
    from .input_specs import (
        ANIMA_NODE_CATEGORY,
        COMPAT_NODE_DESCRIPTION,
        COMPAT_NODE_DISPLAY_NAME,
        COMPAT_NODE_ID,
        build_compat_input_types,
    )
except ImportError:
    from core.model_introspection import looks_like_supported_model
    from core.replay import ReplayConfig, ReplayController
    from nodes.input_specs import (
        ANIMA_NODE_CATEGORY,
        COMPAT_NODE_DESCRIPTION,
        COMPAT_NODE_DISPLAY_NAME,
        COMPAT_NODE_ID,
        build_compat_input_types,
    )


class AnimaLayerReplayPatcher:
    """Backward-compatible runtime wrapper for replay-only patching."""

    DESCRIPTION = COMPAT_NODE_DESCRIPTION
    CATEGORY = ANIMA_NODE_CATEGORY
    RETURN_NAMES = ("patched_model",)

    @classmethod
    def INPUT_TYPES(cls):
        return build_compat_input_types()

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "patch"

    def patch(
        self,
        model,
        enable_replay: bool,
        block_indices: str,
        denoise_start_pct: float,
        denoise_end_pct: float,
    ):
        patched_model = model.clone()
        diffusion_model = patched_model.get_model_object("diffusion_model")

        if not looks_like_supported_model(diffusion_model):
            raise RuntimeError(
                "AnimaLayerReplayPatcher only supports Anima/Cosmos/Predict2-style diffusion models in ComfyUI."
            )

        replay_controller = ReplayController(
            diffusion_model,
            ReplayConfig(
                enabled=enable_replay,
                block_indices_text=block_indices,
                denoise_start_pct=denoise_start_pct,
                denoise_end_pct=denoise_end_pct,
            ),
        )

        previous_wrapper = patched_model.model_options.get("model_function_wrapper")

        def anima_unet_wrapper(model_function, kwargs):
            def call_underlying(call_kwargs):
                if previous_wrapper is not None:
                    return previous_wrapper(model_function, call_kwargs)
                return model_function(
                    call_kwargs["input"],
                    call_kwargs["timestep"],
                    **call_kwargs["c"],
                )

            replay_active = replay_controller.is_active(
                kwargs["timestep"],
                kwargs.get("c", {}),
            )

            return replay_controller.run(
                lambda: call_underlying(kwargs),
                replay_active=replay_active,
            )

        patched_model.set_model_unet_function_wrapper(anima_unet_wrapper)
        return (patched_model,)


NODE_CLASS_MAPPINGS = {
    COMPAT_NODE_ID: AnimaLayerReplayPatcher,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    COMPAT_NODE_ID: COMPAT_NODE_DISPLAY_NAME,
}

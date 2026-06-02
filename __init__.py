try:
    try:
        from .v3_nodes import comfy_entrypoint
    except ImportError:
        from v3_nodes import comfy_entrypoint

    __all__ = ["comfy_entrypoint"]
except ImportError:
    try:
        from .nodes import (
            AnimaIntermediateSpectrumPatcher,
            AnimaLayerReplayPatcher,
            NODE_CLASS_MAPPINGS,
            NODE_DISPLAY_NAME_MAPPINGS,
        )
    except ImportError:
        from nodes import (
            AnimaIntermediateSpectrumPatcher,
            AnimaLayerReplayPatcher,
            NODE_CLASS_MAPPINGS,
            NODE_DISPLAY_NAME_MAPPINGS,
        )

    __all__ = [
        "AnimaLayerReplayPatcher",
        "AnimaIntermediateSpectrumPatcher",
        "NODE_CLASS_MAPPINGS",
        "NODE_DISPLAY_NAME_MAPPINGS",
    ]

from nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from nodes.input_specs import (
    COMPAT_NODE_DISPLAY_NAME,
    COMPAT_NODE_ID,
    LEGACY_COMPAT_NODE_ID,
    LEGACY_PHASE2_NODE_ID,
    LEGACY_PUBLIC_COMPAT_NODE_ID,
    PHASE2_NODE_DISPLAY_NAME,
    PHASE2_NODE_ID,
    build_compat_input_types,
    build_phase2_input_types,
)


def test_public_node_ids_are_stable():
    assert COMPAT_NODE_ID == "ShibaAnimaForReplay"
    assert PHASE2_NODE_ID == "ShibaAnimaForSpectrumExperimental"
    assert LEGACY_COMPAT_NODE_ID == "AnimaLayerReplayPatcher"
    assert LEGACY_PHASE2_NODE_ID == "AnimaIntermediateSpectrumPatcher"
    assert LEGACY_PUBLIC_COMPAT_NODE_ID == "ShibaAnimaForSpectrum"


def test_legacy_node_exports_include_replay_and_spectrum_nodes():
    assert set(NODE_CLASS_MAPPINGS) == {COMPAT_NODE_ID, PHASE2_NODE_ID}
    assert NODE_DISPLAY_NAME_MAPPINGS == {
        COMPAT_NODE_ID: COMPAT_NODE_DISPLAY_NAME,
        PHASE2_NODE_ID: PHASE2_NODE_DISPLAY_NAME,
    }


def test_compat_input_order_and_defaults_are_stable():
    required = build_compat_input_types()["required"]
    assert list(required) == [
        "model",
        "enable_replay",
        "block_indices",
        "denoise_start_pct",
        "denoise_end_pct",
    ]

    assert required["enable_replay"][1]["default"] is True
    assert required["block_indices"][1]["default"] == "3,4,5"
    assert required["denoise_start_pct"][1]["default"] == 0.50
    assert required["denoise_end_pct"][1]["default"] == 1.00


def test_phase2_input_order_defaults_and_advanced_flags_are_stable():
    required = build_phase2_input_types()["required"]
    assert list(required) == [
        "model",
        "spectrum_w",
        "spectrum_warmup_steps",
        "spectrum_window_size",
        "enable_calibration",
        "calibration_strength",
        "calibration_mode",
        "spectrum_m",
        "spectrum_lam",
        "spectrum_flex_window",
        "spectrum_stop_caching_step",
        "calibration_decay",
        "calibration_buckets",
        "calibration_min_obs",
        "debug_enable_spectrum",
        "debug_logging",
    ]

    assert required["spectrum_w"][1]["default"] == 0.10
    assert required["spectrum_warmup_steps"][1]["default"] == 6
    assert required["spectrum_window_size"][1]["default"] == 2
    assert required["enable_calibration"][1]["default"] is False
    assert required["calibration_strength"][1]["default"] == 0.35
    assert required["calibration_mode"][0] == ["latest", "ema", "bucketed_ema"]
    assert required["calibration_mode"][1]["default"] == "ema"
    assert required["spectrum_stop_caching_step"][1]["default"] == -1
    assert required["debug_enable_spectrum"][1]["default"] is True
    assert required["debug_logging"][1]["default"] is False

    advanced_fields = [
        "spectrum_m",
        "spectrum_lam",
        "spectrum_flex_window",
        "spectrum_stop_caching_step",
        "calibration_decay",
        "calibration_buckets",
        "calibration_min_obs",
        "debug_enable_spectrum",
        "debug_logging",
    ]
    for field in advanced_fields:
        assert required[field][1]["advanced"] is True

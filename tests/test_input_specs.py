from nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from nodes.phase2 import resolve_spectrum_preset
from nodes.input_specs import (
    COMPAT_NODE_DISPLAY_NAME,
    COMPAT_NODE_ID,
    LEGACY_COMPAT_NODE_ID,
    LEGACY_PHASE2_NODE_ID,
    LEGACY_PUBLIC_COMPAT_NODE_ID,
    PHASE2_NODE_DISPLAY_NAME,
    PHASE2_NODE_ID,
    SPECTRUM_PRESET_CHOICES,
    SPECTRUM_PRESET_W15_F05_MS000,
    SPECTRUM_PRESET_W18_STOP0,
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
        "spectrum_preset",
        "spectrum_w",
        "spectrum_warmup_steps",
        "spectrum_window_size",
        "enable_calibration",
        "calibration_strength",
        "calibration_mode",
        "spectrum_m",
        "spectrum_lam",
        "spectrum_taylor_damping",
        "spectrum_multistep_damping",
        "spectrum_flex_window",
        "spectrum_stop_caching_step",
        "spectrum_extra_forecast_steps",
        "calibration_decay",
        "calibration_buckets",
        "calibration_min_obs",
        "debug_enable_spectrum",
        "feature_site",
        "target_block_index",
        "forecast_mode",
        "debug_logging",
    ]

    assert required["spectrum_preset"][0] == SPECTRUM_PRESET_CHOICES
    assert required["spectrum_preset"][1]["default"] == SPECTRUM_PRESET_W18_STOP0
    assert SPECTRUM_PRESET_W15_F05_MS000 in required["spectrum_preset"][0]
    assert required["spectrum_w"][1]["default"] == 0.05
    assert required["spectrum_warmup_steps"][1]["default"] == 18
    assert required["spectrum_window_size"][1]["default"] == 2
    assert required["enable_calibration"][1]["default"] is False
    assert required["calibration_strength"][1]["default"] == 0.35
    assert required["calibration_mode"][0] == ["latest", "ema", "bucketed_ema"]
    assert required["calibration_mode"][1]["default"] == "ema"
    assert required["spectrum_stop_caching_step"][1]["default"] == 0
    assert required["spectrum_taylor_damping"][1]["default"] == 1.0
    assert required["spectrum_multistep_damping"][1]["default"] == 1.0
    assert required["spectrum_extra_forecast_steps"][1]["default"] == ""
    assert "0" in required["spectrum_stop_caching_step"][1]["tooltip"]
    assert required["debug_enable_spectrum"][1]["default"] is True
    assert required["feature_site"][0] == ["pre_decoder_head", "post_block"]
    assert required["feature_site"][1]["default"] == "pre_decoder_head"
    assert required["target_block_index"][1]["default"] == 13
    assert required["forecast_mode"][0] == ["replace", "shadow", "actual_only"]
    assert required["forecast_mode"][1]["default"] == "replace"
    assert required["debug_logging"][1]["default"] is False
    assert required["spectrum_preset"][1].get("advanced") is None

    advanced_fields = [
        "spectrum_w",
        "spectrum_warmup_steps",
        "spectrum_window_size",
        "enable_calibration",
        "calibration_strength",
        "calibration_mode",
        "spectrum_m",
        "spectrum_lam",
        "spectrum_taylor_damping",
        "spectrum_multistep_damping",
        "spectrum_flex_window",
        "spectrum_stop_caching_step",
        "spectrum_extra_forecast_steps",
        "calibration_decay",
        "calibration_buckets",
        "calibration_min_obs",
        "debug_enable_spectrum",
        "feature_site",
        "target_block_index",
        "forecast_mode",
        "debug_logging",
    ]
    for field in advanced_fields:
        assert required[field][1]["advanced"] is True


def test_phase2_w18_preset_resolves_to_quality_default():
    settings = resolve_spectrum_preset(
        SPECTRUM_PRESET_W18_STOP0,
        spectrum_w=0.99,
        spectrum_warmup_steps=1,
        spectrum_window_size=9,
        enable_calibration=True,
        spectrum_m=3,
        spectrum_lam=9.0,
        spectrum_taylor_damping=0.25,
        spectrum_multistep_damping=0.25,
        spectrum_flex_window=0.75,
        spectrum_stop_caching_step=-1,
        spectrum_extra_forecast_steps="21,25",
    )

    assert settings == {
        "spectrum_w": 0.05,
        "spectrum_warmup_steps": 18,
        "spectrum_window_size": 2,
        "enable_calibration": False,
        "spectrum_m": 16,
        "spectrum_lam": 0.5,
        "spectrum_taylor_damping": 1.0,
        "spectrum_multistep_damping": 1.0,
        "spectrum_flex_window": 0.0,
        "spectrum_stop_caching_step": 0,
        "spectrum_extra_forecast_steps": "",
    }


def test_phase2_w15_preset_resolves_to_speed_first_candidate():
    settings = resolve_spectrum_preset(
        SPECTRUM_PRESET_W15_F05_MS000,
        spectrum_w=0.99,
        spectrum_warmup_steps=1,
        spectrum_window_size=9,
        enable_calibration=True,
        spectrum_m=3,
        spectrum_lam=9.0,
        spectrum_taylor_damping=0.25,
        spectrum_multistep_damping=1.0,
        spectrum_flex_window=0.0,
        spectrum_stop_caching_step=-1,
        spectrum_extra_forecast_steps="21,25",
    )

    assert settings["spectrum_warmup_steps"] == 15
    assert settings["spectrum_flex_window"] == 0.5
    assert settings["spectrum_multistep_damping"] == 0.0
    assert settings["enable_calibration"] is False
    assert settings["spectrum_stop_caching_step"] == 0


def test_phase2_manual_preset_preserves_explicit_values():
    settings = resolve_spectrum_preset(
        "Manual",
        spectrum_w=0.2,
        spectrum_warmup_steps=12,
        spectrum_window_size=3,
        enable_calibration=True,
        spectrum_m=4,
        spectrum_lam=0.1,
        spectrum_taylor_damping=0.5,
        spectrum_multistep_damping=0.25,
        spectrum_flex_window=0.6,
        spectrum_stop_caching_step=26,
        spectrum_extra_forecast_steps="23",
    )

    assert settings["spectrum_warmup_steps"] == 12
    assert settings["spectrum_multistep_damping"] == 0.25
    assert settings["spectrum_extra_forecast_steps"] == "23"
    assert settings["enable_calibration"] is True

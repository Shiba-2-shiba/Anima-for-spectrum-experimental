import torch

from core.forecast_records import (
    RECORD_RUN_START,
    RECORD_SHADOW_STEP,
    RECORD_TOPOLOGY,
    build_run_start_record,
    build_step_record,
    build_topology_record,
)
from core.feature_sites import FEATURE_SITE_PRE_DECODER_HEAD
from core.intermediate_spectrum import IntermediateForecastConfig
from core.calibration import CalibrationApplyResult
from core.topology import TopologyReport


def _config():
    return IntermediateForecastConfig(
        enabled=True,
        w=0.1,
        m=16,
        lam=0.5,
        warmup_steps=6,
        window_size=2,
        flex_window=0.0,
        stop_caching_step=-1,
        extra_forecast_steps="",
        enable_calibration=False,
        calibration_strength=0.35,
        calibration_mode="ema",
        calibration_decay=0.9,
        calibration_buckets=4,
        calibration_min_obs=2,
        forecast_mode="shadow",
        debug_logging=True,
    )


def test_run_start_record_keeps_legacy_event_and_adds_record_type():
    record = build_run_start_record(
        run_id="phase2-test",
        timestamp_utc="20260613T000000.000000Z",
        estimated_total_steps=31,
        patcher_config=_config(),
    )

    assert record["event"] == "run_start"
    assert record["record_type"] == RECORD_RUN_START
    assert record["feature_site_id"] == FEATURE_SITE_PRE_DECODER_HEAD
    assert record["patcher_config"]["forecast_mode"] == "shadow"


def test_topology_record_serializes_report_payloads():
    topology = TopologyReport(
        model_class="Tiny",
        model_module="tests",
        transformer_path=None,
        transformer_class="Tiny",
        transformer_module="tests",
        has_forward_before_blocks=True,
        has_decoder_head=True,
        modulelist_candidates=[],
        selected_block_container=None,
    )

    record = build_topology_record(
        run_id="phase2-test",
        feature_site_id=FEATURE_SITE_PRE_DECODER_HEAD,
        topology_report=topology,
        support_report={"api_variant": "cosmos_forward_before_blocks"},
    )

    assert record["event"] == "topology"
    assert record["record_type"] == RECORD_TOPOLOGY
    assert record["topology"]["model_class"] == "Tiny"
    assert record["support"]["api_variant"] == "cosmos_forward_before_blocks"


def test_shadow_step_record_preserves_legacy_error_fields_and_adds_metrics():
    raw = torch.tensor([1.0, 2.0])
    calibrated = torch.tensor([1.0, 1.5])
    actual = torch.tensor([1.0, 1.0])
    correction = calibrated - raw
    apply_result = CalibrationApplyResult(
        corrected=calibrated,
        correction=correction,
        bucket_id=0,
        obs_count=0,
        residual_norm=0.0,
    )

    record = build_step_record(
        run_id="phase2-test",
        feature_site_id=FEATURE_SITE_PRE_DECODER_HEAD,
        forecast_mode="shadow",
        step_kind="shadow",
        step_index=3,
        timestep_value=0.5,
        estimated_total_steps=31,
        estimated_last_step_index=30,
        progress=0.1,
        batch_index=0,
        num_cached_before=0,
        window_size=2,
        config=_config(),
        raw_guess=raw,
        calibrated_guess=calibrated,
        correction=correction,
        apply_result=apply_result,
        actual_x=actual,
        timings={"actual_feature_ms": 12.5, "path_total_ms": 13.0},
    )

    assert record["event"] == "step"
    assert record["record_type"] == RECORD_SHADOW_STEP
    assert record["feature_site_id"] == FEATURE_SITE_PRE_DECODER_HEAD
    assert record["forecast_mode"] == "shadow"
    assert record["actual_or_forecast"] == "shadow"
    assert record["errors"]["raw_vs_actual_rel_l2"] > record["errors"]["calibrated_vs_actual_rel_l2"]
    assert record["metrics"]["raw_vs_actual"]["mse"] == record["errors"]["raw_vs_actual_mse"]
    assert record["tensor"]["shape"] == [2]
    assert record["timings"]["actual_feature_ms"] == 12.5

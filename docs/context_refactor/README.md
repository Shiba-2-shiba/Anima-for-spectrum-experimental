# Context Refactor Summary

## Overview

このディレクトリは、Phase 1 / Phase 2 の比較メモ、チェックリスト、JSONL ログ置き場です。
削除した作業メモや測定テキストの要約は `docs/refactor-history.md` に集約しました。

## Phase 1 status

Phase 1 is closed.

Closed conclusions:

- replay, spectrum, calibration, schedule, and model introspection were split into `core/`
- the existing `AnimaLayerReplayPatcher` node stayed as a compatibility layer in `nodes/compat.py`
- spectrum state moved from a single-forecaster design to per-sample forecasters
- `spectrum_stop_caching_step`, `enable_calibration`, and `calibration_strength` were added to the compatibility node
- schedule handling now distinguishes sampler step count from the last 0-based step index used for forecast normalization
- `D` became the Phase 1 Spectrum baseline, and calibration was not promoted to the default path

## Phase 2 status

Phase 2 has started.

Implemented so far:

- `core/intermediate_features.py` was added
- supported Anima-style models can now be checked for intermediate-feature support
- `forward_before_blocks` output can be captured as a structured state
- blocks can be rerun from that state
- `decoder_head` can be called from that state
- `Anima/MiniTrainDIT` style models can now rebuild an equivalent pre-block state through `prepare_embedded_sequence()`, `t_embedder`, `final_layer`, and `unpatchify`
- `core/intermediate_spectrum.py` now provides a feature forecasting controller and `BaseModel.apply_model` integration helper
- Phase 2 calibration was changed from previous-guess carryover to same-step observe/apply
- Phase 2 now supports `latest`, `ema`, and `bucketed_ema` calibration modes
- Phase 2 can emit JSONL step logs under `docs/context_refactor/logs/`
- `nodes/phase2.py` now exposes the current Spectrum runtime path with calibration mode controls

Current measured state:

- the Phase 2 node still expects a clean `MODEL` input and does not stack with another `model_function_wrapper` patch yet
- `enable_spectrum=false` matches baseline nearly perfectly on Anima
- `enable_spectrum=true` with `warmup_steps=6` runs at Phase 1-like speed but quality collapses
- `enable_spectrum=true` with `warmup_steps=20` returns to near-perfect baseline quality

This still means the intermediate-feature path reconstruction itself is correct enough for no-op and all-actual execution, while the current forecast path remains the main failure point.

## 2026-03-29 measurement snapshot

Consolidated source:

- `docs/refactor-history.md`

What is confirmed from the recorded run:

- `A vs B` was a perfect match, so patcher insertion with replay and spectrum disabled preserved baseline output exactly
- measured runtimes were `A=36s`, `B=37s`, `C=39s`, `D=33s post-fix`, `E=32s post-fix`, `F=34s post-fix`
- `D` is the cleanest recorded Spectrum case on the base workflow
- `E` did not establish calibration as a default-on quality improvement over `D`
- `F` still requires visual confirmation because benchmark auto-alignment was triggered
- Phase 2 `G0` (`enable_spectrum=false`) produced `SSIM 0.99930`, `MSE 0.000005`
- Phase 2 `G` (`enable_spectrum=true`, `warmup_steps=6`) produced `SSIM 0.27905`, `MSE 0.146775`, with auto-align `(1, 0)`
- Phase 2 actual-path isolation (`enable_spectrum=true`, `warmup_steps=20`) returned to `SSIM 0.99930`, `MSE 0.000005`

Important limitation:

- the original measurement note did not capture the fixed workflow metadata, image paths, or visual review notes
- Phase 1 calibration remains a lightweight output-side correction only
- Phase 2 forecast quality is not yet acceptable
- same-step logging was added after these measurements, so a fresh rerun is still required

## Block container priority

Replay block selection currently uses this order:

1. `diffusion_model.blocks`
2. `diffusion_model.net.blocks`
3. `diffusion_model.model.blocks`
4. fallback scoring over repeated `nn.ModuleList` containers discovered by `named_modules()`

Fallback scoring prefers names like `blocks` or `layers`, repeated block-like module types, and penalizes obvious non-block containers such as norm, embedding, positional, adapter, or projection stacks.

## Phase 2 handoff notes

These items define the current Phase 2 queue:

- rerun the failing `warmup_steps=6` case with `debug_logging=true`
- compare `no calibration`, `latest`, `ema`, and `bucketed_ema` without changing forecast hyperparameters at the same time
- current practical default candidate on the 20-step workflow is `ema` with `calibration_strength=0.35` and `spectrum_w=0.10`
- inspect `raw_vs_actual_*`, `calibrated_vs_actual_*`, `clip_frac_*`, and `correction_raw_ratio` in the JSONL logs
- keep `enable_calibration=false` as the default until a logged case beats the no-cal baseline
- extend debug coverage later with sampled shadow-actual runs if step logs alone are insufficient
- keep workflow metadata, seed, image path, and visual notes in the comparison record alongside the JSONL path

## Files

- `docs/refactor-history.md`
- `docs/context_refactor/base-workflow-comparison-checklist.md`
- `docs/context_refactor/base-workflow-comparison-record-template.md`
- `docs/context_refactor/base-workflow-comparison-2026-03-29.md`
- `docs/context_refactor/logs/`

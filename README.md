# Anima-for-spectrum

ComfyUI custom nodes for improving **Anima** generations with two cooperating mechanisms:

- **Replay**: temporarily replay selected internal blocks during the denoise window.
- **Spectrum**: skip some full evaluations by forecasting intermediate features from recent history.

This repository is prepared as a separate package for publication at `Shiba-2-shiba/Anima-for-spectrum`. The public node ids and labels are intentionally different from the original `ComfyUI-Anima-Enhancer` package so both can coexist without key collisions.

## Nodes

ComfyUI shows the nodes as:

- **Anima for Replay**
- **Anima for Spectrum**

The stable node is now replay-only. `Anima for Spectrum` is now the main Spectrum node, with most detailed tuning controls moved under Advanced.

## Compatibility

- Modern ComfyUI uses a **V3 entrypoint** via `comfy_entrypoint()` in [__init__.py](./__init__.py) and [v3_nodes.py](./v3_nodes.py).
- Older ComfyUI falls back to legacy `NODE_CLASS_MAPPINGS` from [nodes/compat.py](./nodes/compat.py) and [nodes/phase2.py](./nodes/phase2.py).
- Nodes 2.0 metadata is supplied through V3 `Schema` fields such as `display_name`, `description`, `category`, `search_aliases`, and `essentials_category`.
- V3 replacement rules migrate old workflow node ids `ShibaAnimaForSpectrum`, `AnimaLayerReplayPatcher`, and `AnimaIntermediateSpectrumPatcher` to the current package ids when V3 loading is available.

## New Public Ids

- Stable node id: `ShibaAnimaForReplay`
- Spectrum node id: `ShibaAnimaForSpectrumExperimental`
- Legacy ids kept only for migration: `ShibaAnimaForSpectrum`, `AnimaLayerReplayPatcher`, `AnimaIntermediateSpectrumPatcher`

## Usage

Use **Anima for Replay** for the stable replay-only path.

Core inputs:

- `enable_replay`: enable or disable replay patching.
- `block_indices`: comma-separated indices or ranges such as `3,4,5` or `3-5,8`.
- `denoise_start_pct`: normalized replay start point.
- `denoise_end_pct`: normalized replay end point.

Use **Anima for Spectrum** for all spectrum-based runs on supported Anima-style models.

Main visible controls:

- `spectrum_w`: main quality-versus-speed balance.
- `spectrum_warmup_steps`: how many real steps to observe before forecasting.
- `spectrum_window_size`: base spacing between real feature evaluations.
- `enable_calibration`: optional residual correction toggle.
- `calibration_strength`: correction strength when calibration is enabled.
- `calibration_mode`: correction accumulation style.

Spectrum inputs:

- `spectrum_w`: blend between Taylor-like extrapolation and Chebyshev prediction.
- `spectrum_warmup_steps`: number of actual steps collected before forecasting.
- `spectrum_window_size`: base interval between actual feature evaluations.
- `enable_calibration`
- `calibration_strength`
- `calibration_mode`
- `spectrum_m`
- `spectrum_lam`
- `spectrum_flex_window`
- `spectrum_stop_caching_step`

Advanced-only inputs:

- `calibration_decay`
- `calibration_buckets`
- `calibration_min_obs`
- `debug_enable_spectrum`: internal compatibility switch
- `debug_logging`

## Recommended Starting Settings

Stable baseline:

- `enable_replay = true`
- `block_indices = 3,4,5`
- `denoise_start_pct = 0.50`
- `denoise_end_pct = 1.00`

Spectrum baseline:

- `spectrum_w = 0.10`
- `spectrum_warmup_steps = 6`
- `spectrum_window_size = 2`
- `enable_calibration = false`

## Repository Layout

- `v3_nodes.py`: V3 schema definitions, Nodes 2.0 metadata, and replacement registration.
- `nodes/input_specs.py`: shared ids, labels, categories, and legacy input ordering.
- `nodes/compat.py`: stable runtime patching logic exposed for legacy fallback.
- `nodes/phase2.py`: experimental runtime patching logic exposed for legacy fallback.
- `core/replay.py`: replay window logic and temporary block patching.
- `core/calibration.py`: same-step residual calibration state and modes.
- `core/intermediate_features.py`: Phase 2 intermediate-feature extraction, block rerun, and decode scaffolding.
- `core/intermediate_spectrum.py`: Phase 2 intermediate-feature forecasting controller and debug logging.
- `docs/refactor-history.md`: consolidated refactor and measurement history after repository cleanup.
- `docs/context_refactor/`: comparison notes, templates, and JSONL step logs.

## Publish Notes

Before publishing the new repository, rename the directory itself to `Anima-for-spectrum` so the on-disk package name matches the GitHub repository and Comfy registry metadata.


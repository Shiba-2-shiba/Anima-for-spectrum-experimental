# Next Codex Handoff - 2026-06-13

## Start Here

This repository is `C:\ComfyUI\custom_nodes\Anima-for-spectrum`.

Read these first:

1. `AGENTS.md`
2. `docs/ANIMA_SPECTRUM_REFACTOR_PROGRESS.md`
3. `docs/refactor-history.md`
4. this handoff file

Current ComfyUI target:

- URL: `http://localhost:8000`
- ComfyUI reported during this session: `0.24.0`
- Python reported during this session: `3.12.11`
- Workflow used for API runs: `docs/context_refactor/workflows/image_anima_base_v1_spectrum_debug(api).json`
- Source workflow: `image_anima_base_v1.json`
- KSampler settings in the API workflow: `steps=30`, `sampler_name=er_sde`, `scheduler=simple`, `denoise=1.0`, `1024x1024`

Backend Python custom node changes require a manual ComfyUI restart before API validation.

## Current Decision

Use W18Stop0 as the first practical quality-preserving candidate, with W15F05MS000 available as the second speed-first candidate.

Default UI preset:

```text
spectrum_preset=W18Stop0
```

W18Stop0 settings:

```text
forecast_mode=replace
feature_site=pre_decoder_head
enable_calibration=false
spectrum_w=0.05
spectrum_warmup_steps=18
spectrum_window_size=2
spectrum_stop_caching_step=0
debug_logging=false
spectrum_taylor_damping=1.0
spectrum_multistep_damping=1.0
spectrum_extra_forecast_steps=""
```

Second candidate preset:

```text
spectrum_preset=W15F05MS000
spectrum_warmup_steps=15
spectrum_flex_window=0.5
spectrum_multistep_damping=0.0
spectrum_stop_caching_step=0
```

W15F05MS000 is fast but visibly worse, so keep it as a speed-first second candidate rather than the default. Do not adopt W18Extra25MS025. It was the least-damaging extra-step experiment, but the four-prompt validation showed no average speed gain and lower quality than W18Stop0.

## Key Results

Spectrum Off / W18Stop0 / W15F05MS000, four prompts:

```text
Off: avg 22.239s
W18Stop0: avg 19.571s, speedup 2.668s, PSNR 25.865, MAE 5.509
W15F05MS000: avg 16.999s, speedup 5.240s, PSNR 21.354, MAE 10.808
```

User visual review:

- W18Stop0 looks good and is a useful 10%-range speedup.
- W15F05MS000 quality loss is noticeable, but it remains useful as a speed-first second candidate.
- Main path should preserve W18Stop0 visual quality.

Extra step policy result:

```text
Off: avg 22.299s
W18Stop0: avg 19.553s, speedup 2.746s, PSNR 25.865, MAE 5.509
W18Extra25MS025: avg 19.576s, speedup 2.724s, PSNR 24.833, MAE 6.370
```

Decision: extra-step policy is rejected for now. Keep `spectrum_extra_forecast_steps` as diagnostic only. The UI now exposes `spectrum_preset` so W18Stop0 is the default and W15F05MS000 can be selected directly.

## Latest Implemented Work

Added diagnostic/profiling support for W18Stop0:

- `core/forecast_records.py`
  - JSONL step records now accept a `timings` object.
- `core/intermediate_spectrum.py`
  - debug-only timing using CUDA synchronization when `debug_logging=true`.
  - timing fields include:
    - `actual_feature_ms`
    - `raw_guess_ms`
    - `calibration_apply_ms`
    - `calibration_observe_ms`
    - `forecast_cast_ms`
    - `forecaster_update_ms`
    - `path_total_ms`
- `docs/context_refactor/run_flex_window_api_comparison.py`
  - added `--case-set w18profile`
  - Markdown reports now include `Timing summary` and `Worst forecast errors`.
- `tests/test_forecast_records.py`
  - covers `timings`.

Important: this profiling instrumentation has not yet been validated in a live ComfyUI run after restart.

## Next Step

Restart ComfyUI, then run:

```powershell
python docs\context_refactor\run_flex_window_api_comparison.py --url http://localhost:8000 --case-set w18profile
```

Expected output files:

```text
docs/context_refactor/visual_review/flex_window_api_w18profile_2026-06-13.json
docs/context_refactor/flex-window-api-w18profile-2026-06-13.md
docs/context_refactor/visual_review/anima_flex_window_api_w18profile_2026-06-13.png
```

After the run, inspect:

- `Timing summary`
- `Worst forecast errors`
- forecast steps in the JSONL summaries
- contact sheet for obvious visual drift

Interpretation:

- If forecast timing is already small relative to unavoidable actual/decode cost, stop trying to add skip steps and focus on quality stabilization.
- If one or two W18 forecast steps dominate shadow errors, try step-specific damping or a guard for those steps only.
- If actual feature extraction remains the dominant cost, investigate implementation overhead and whether pre/post block boundaries can reduce recomputation without quality loss.

## Useful Commands

Runtime preflight:

```powershell
python C:\Users\inott\.codex\skills\comfyui-local-runtime\scripts\comfy_runtime.py preflight --url http://localhost:8000 --workflow "docs\context_refactor\workflows\image_anima_base_v1_spectrum_debug(api).json"
```

Check node schema after restart:

```powershell
$info = Invoke-RestMethod -Uri http://localhost:8000/object_info/ShibaAnimaForSpectrumExperimental
$info.ShibaAnimaForSpectrumExperimental.input.required.PSObject.Properties.Name -contains 'spectrum_extra_forecast_steps'
```

Unit/static verification:

```powershell
python -m pytest
python -m compileall core nodes tests docs\context_refactor\run_flex_window_api_comparison.py docs\context_refactor\run_off_w18_w15_multi_prompt.py
git -c safe.directory=C:/ComfyUI/custom_nodes/Anima-for-spectrum diff --check
```

## Verification Already Done

Latest local verification after profiling implementation:

```text
python -m pytest -> 46 passed
python -m compileall core nodes tests docs\context_refactor\run_flex_window_api_comparison.py docs\context_refactor\run_off_w18_w15_multi_prompt.py -> passed
git diff --check -> no whitespace errors, CRLF warnings only
```

Latest live verification before profiling implementation:

- `/object_info` exposed `spectrum_extra_forecast_steps` after manual restart.
- API runs completed for:
  - `--case-set extra`
  - `--case-set extradamping`
  - `run_off_w18_w15_multi_prompt.py --case-set extra25`

## Main Files Changed In This Refactor

Core/runtime:

- `core/intermediate_spectrum.py`
- `core/spectrum.py`
- `core/feature_sites.py`
- `core/forecast_records.py`
- `nodes/input_specs.py`
- `nodes/phase2.py`
- `v3_nodes.py`

Tests:

- `tests/test_input_specs.py`
- `tests/test_intermediate_spectrum_controller.py`
- `tests/test_spectrum_forecaster.py`
- `tests/test_feature_sites.py`
- `tests/test_forecast_records.py`

Comparison scripts and workflows:

- `docs/context_refactor/run_flex_window_api_comparison.py`
- `docs/context_refactor/run_off_w18_w15_multi_prompt.py`
- `docs/context_refactor/workflows/image_anima_base_v1_spectrum_debug(api).json`
- `docs/context_refactor/workflows/image_anima_base_v1_spectrum_debug.json`

Primary progress docs:

- `docs/ANIMA_SPECTRUM_REFACTOR_PROGRESS.md`
- `docs/ANIMA_SPECTRUM_REFACTOR_TASKS.md`
- `docs/refactor-history.md`
- `docs/context_refactor/README.md`

## Important Artifacts

Quality/speed comparison:

- `docs/context_refactor/off-w18-w15-multi-prompt-2026-06-13.md`
- `docs/context_refactor/visual_review/anima_off_w18_w15_multi_prompt_2026-06-13.png`

Extra-step rejection:

- `docs/context_refactor/flex-window-api-extra-2026-06-13.md`
- `docs/context_refactor/flex-window-api-extradamping-2026-06-13.md`
- `docs/context_refactor/off-w18-extra25-multi-prompt-2026-06-13.md`
- `docs/context_refactor/visual_review/anima_off_w18_extra25_multi_prompt_2026-06-13.png`

Earlier W18 validation:

- `docs/context_refactor/multi-prompt-w18-stop0-validation-2026-06-13.md`
- `docs/context_refactor/visual_review/anima_multi_prompt_w18_stop0_2026-06-13.png`

Paper/reference:

- `docs/Adaptive Spectral Feature Forecasting for Diffusion Sampling Acceleration.pdf`
- `docs/Spectrum/`

## Worktree State Warning

The worktree is intentionally dirty and contains many untracked generated comparison files and logs. Do not clean, reset, delete, or revert unrelated files without explicit user instruction.

Use:

```powershell
git -c safe.directory=C:/ComfyUI/custom_nodes/Anima-for-spectrum status --short
```

Expect many modified and untracked files.

## Current Open Tasks

From `docs/ANIMA_SPECTRUM_REFACTOR_TASKS.md`:

- P7-T16 remains open:
  - run `w18profile` on real ComfyUI
  - decide whether to pursue speed overhead work or step-specific quality stabilization
- P9 cleanup/stabilization remains future work.

Do not start cleanup until behavior is locked by the current tests and the W18 profiling result has been recorded.

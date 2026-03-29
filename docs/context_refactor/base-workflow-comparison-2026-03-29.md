# Base Workflow Comparison Record 2026-03-29

## Session Summary

- Date: 2026-03-29
- Operator: local manual run
- Goal: Phase 1 baseline comparison for replay / spectrum / calibration cases
- Base workflow: historical local base workflow, path not preserved in the repository
- Saved comparison workflow: not recorded in the original measurement note
- Source log: consolidated into `docs/refactor-history.md`

## Important Note

This record now contains:

- baseline and no-op compatibility evidence for `A/B`
- replay-only evidence for `C`
- post-fix runtime and post-fix quality metrics for `D/E/F`

What is still missing is not the benchmark numbers themselves, but the workflow metadata and visual review record.

## Environment

- ComfyUI version: not recorded
- Frontend version: not recorded
- OS: not recorded
- GPU: not recorded
- VRAM: not recorded
- Precision / dtype notes: not recorded

## Fixed Workflow Settings

The source log did not preserve these fields. Reconstruct them from the workflow file on rerun.

- UNET: not recorded
- CLIP: not recorded
- VAE: not recorded
- LoRA: not recorded
- Positive prompt: not recorded
- Negative prompt: not recorded
- Width: not recorded
- Height: not recorded
- Steps: 20 inferred from progress bars
- Scheduler: not recorded
- Sampler: not recorded
- Seed: not recorded
- APG: not recorded
- TCFG: not recorded
- Mahiro: not recorded

## Comparison Matrix

| Case | Purpose | Runtime | Benchmark summary | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| A | Baseline | 36s | reference | recorded | baseline image path not captured |
| B | No-op compatibility | 37s | `S (Perfect)`, `SSIM 1.00000`, `MSE 0.000000` vs A | confirmed | exact-match evidence for disabled replay/spectrum path |
| C | Replay only | 39s | `B (Good)`, `SSIM 0.71155`, `MSE 0.015268` vs A | confirmed | non-spectrum path, step-fix influenceなし |
| D | Spectrum only | 32s pre-fix, 33s post-fix | post-fix `B (Good)`, `SSIM 0.65972`, `MSE 0.024265` vs A | confirmed | current Phase 1 baseline for Spectrum quality |
| E | Spectrum + calibration | 32s pre-fix, 32s post-fix | post-fix `B (Good)`, `SSIM 0.65254`, `MSE 0.025772` vs A | confirmed_with_note | calibration did not beat `D` on this workflow |
| F | Replay + spectrum + calibration | 34s pre-fix, 34s post-fix | post-fix `B (Good)`, `SSIM 0.57558`, `MSE 0.030723` vs A | confirmed_with_note | auto-align detected max shift `(-1, -1)` |

## Benchmark Excerpts

### A vs B

- Grade: `S (Perfect)`
- LPIPS: `0.00000`
- SSIM: `1.00000`
- CLIP: `1.00000`
- MSE: `0.000000`

### A vs C

- Grade: `B (Good)`
- LPIPS: `0.00000`
- SSIM: `0.71155`
- CLIP: `1.00000`
- MSE: `0.015268`

### A vs D (post-fix)

- Grade: `B (Good)`
- Alignment: no shift detected
- LPIPS: `0.00000`
- SSIM: `0.65972`
- CLIP: `1.00000`
- MSE: `0.024265`

### A vs E (post-fix)

- Grade: `B (Good)`
- Alignment: no shift detected
- LPIPS: `0.00000`
- SSIM: `0.65254`
- CLIP: `1.00000`
- MSE: `0.025772`

### A vs F (post-fix)

- Grade: `B (Good)`
- Alignment: auto-align active, max shift `(-1, -1)`
- LPIPS: `0.00000`
- SSIM: `0.57558`
- CLIP: `1.00000`
- MSE: `0.030723`

## Post-Fix Runtime Rerun

- D: `33s` (`1.67s/it`)
- E: `32s` (`1.63s/it`)
- F: `34s` (`1.74s/it`)

## Missing Evidence

The source log still does not capture:

- output image paths
- patcher input snapshots per case
- visual review notes for face / hands / hair / background / color shift
- exception or stale-state observations
- batch-size variation checks

## Current Reading

- `D` is the cleanest Spectrum case in the recorded metrics.
- `E` is close to `D`, but does not justify calibration as a default-on quality feature in Phase 1.
- `F` works, but the alignment shift warning means it should not be treated as equally stable without visual confirmation.
- Substantive quality improvement is therefore deferred to Phase 2 intermediate-feature forecasting.

## Next Checklist

- save image paths and seed alongside the benchmark text
- add visual notes using `docs/context_refactor/base-workflow-comparison-checklist.md`
- inspect whether `F` shows an actual visible spatial drift or only a benchmark-side alignment correction
- treat `D` as the default Spectrum path until Phase 2 work begins
- keep the local workflow path and revision in the next rerun record because the original repository copy was removed

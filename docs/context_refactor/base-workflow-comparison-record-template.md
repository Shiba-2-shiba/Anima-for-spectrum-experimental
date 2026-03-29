# Base Workflow Comparison Record Template

## Session Summary

- Date:
- Operator:
- Goal:
- Base workflow:
- Saved comparison workflow:

## Environment

- ComfyUI version:
- Frontend version:
- OS:
- GPU:
- VRAM:
- Precision / dtype notes:

## Fixed Workflow Settings

- UNET:
- CLIP:
- VAE:
- LoRA:
- Positive prompt:
- Negative prompt:
- Width:
- Height:
- Steps:
- Scheduler:
- Sampler:
- Seed:
- APG:
- TCFG:
- Mahiro:

## Patcher Placement

- Inserted between:
- Sampler node:
- Notes:

## Comparison Matrix

| Case | Purpose | Patcher present | Replay | Spectrum | Calibration | Result image | Runtime | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Baseline | no | off | off | off |  |  |  |  |
| B | No-op compatibility | yes | off | off | off |  |  |  |  |
| C | Replay only | yes | on | off | off |  |  |  |  |
| D | Spectrum only | yes | off | on | off |  |  |  |  |
| E | Spectrum + calibration | yes | off | on | on |  |  |  |  |
| F | Replay + spectrum + calibration | yes | on | on | on |  |  | optional |  |
| G0 | Phase 2 no-op | yes | n/a | off | off |  |  |  |  |
| G | Phase 2 forecast baseline | yes | n/a | on | off |  |  |  |  |
| G-latest | Phase 2 same-step latest | yes | n/a | on | latest |  |  |  |  |
| G-ema | Phase 2 same-step EMA | yes | n/a | on | ema |  |  |  |  |
| G-bucket | Phase 2 bucketed EMA | yes | n/a | on | bucketed_ema |  |  |  |  |
| G-actual | Phase 2 actual-path sanity | yes | n/a | on | off |  |  |  | `warmup_steps=20` |

## Detailed Record

### Case A

- Image path:
- Runtime:
- Seed:
- Patcher settings:
- Visual notes:
- Stability notes:
- Verdict:

### Case B

- Image path:
- Runtime:
- Seed:
- Patcher settings:
- Visual notes:
- Stability notes:
- Verdict:

### Case C

- Image path:
- Runtime:
- Seed:
- Patcher settings:
- Visual notes:
- Stability notes:
- Verdict:

### Case D

- Image path:
- Runtime:
- Seed:
- Patcher settings:
- Visual notes:
- Stability notes:
- Verdict:

### Case E

- Image path:
- Runtime:
- Seed:
- Patcher settings:
- Visual notes:
- Stability notes:
- Verdict:

### Case F

- Image path:
- Runtime:
- Seed:
- Patcher settings:
- Visual notes:
- Stability notes:
- Verdict:

### Case G0

- Image path:
- Runtime:
- Seed:
- Patcher settings:
- JSONL path:
- Visual notes:
- Stability notes:
- Verdict:

### Case G

- Image path:
- Runtime:
- Seed:
- Patcher settings:
- JSONL path:
- Visual notes:
- Stability notes:
- Verdict:

### Case G-latest

- Image path:
- Runtime:
- Seed:
- Patcher settings:
- JSONL path:
- Visual notes:
- Stability notes:
- Verdict:

### Case G-ema

- Image path:
- Runtime:
- Seed:
- Patcher settings:
- JSONL path:
- Visual notes:
- Stability notes:
- Verdict:

### Case G-bucket

- Image path:
- Runtime:
- Seed:
- Patcher settings:
- JSONL path:
- Visual notes:
- Stability notes:
- Verdict:

### Case G-actual

- Image path:
- Runtime:
- Seed:
- Patcher settings:
- JSONL path:
- Visual notes:
- Stability notes:
- Verdict:

## Visual Comparison Notes

### Face and Eyes

- Baseline:
- Replay:
- Spectrum:
- Spectrum + calibration:
- Phase 2 no-cal:
- Phase 2 bucketed EMA:

### Hair and Fine Lines

- Baseline:
- Replay:
- Spectrum:
- Spectrum + calibration:
- Phase 2 no-cal:
- Phase 2 bucketed EMA:

### Hands and Small Shapes

- Baseline:
- Replay:
- Spectrum:
- Spectrum + calibration:
- Phase 2 no-cal:
- Phase 2 bucketed EMA:

### Background and Texture

- Baseline:
- Replay:
- Spectrum:
- Spectrum + calibration:
- Phase 2 no-cal:
- Phase 2 bucketed EMA:

### Color Shift / Noise

- Baseline:
- Replay:
- Spectrum:
- Spectrum + calibration:
- Phase 2 no-cal:
- Phase 2 bucketed EMA:

## Stability Notes

- Exception during run:
- Stale patch suspicion:
- State carry-over suspicion:
- Batch size change result:

## Parameter Tuning Notes

- Best replay settings:
- Best spectrum settings:
- Best calibration settings:
- Settings to avoid:

## Phase 2 Step Log Summary

- Log directory:
- Compared cases:
- Forecast hyperparameters fixed across cases:
- Calibration modes compared:
- Step count covered:
- Main failing step range:
- Best raw_vs_actual trend:
- Best calibrated_vs_actual trend:
- clip_frac warning:
- correction/raw ratio warning:
- Follow-up debug need:

## Conclusion

- Best quality case:
- Best speed / quality balance:
- Reproducible issues:
- README updates needed:
- Phase 2 handoff notes:

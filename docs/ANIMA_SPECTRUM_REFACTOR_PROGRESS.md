# ANIMA_SPECTRUM_REFACTOR_PROGRESS.md

Project: Anima-for-spectrum
Repository: https://github.com/Shiba-2-shiba/Anima-for-spectrum
Status: P1 behavior lock verified on live ComfyUI; P4 shadow mode available for current Phase 2 site
Last updated: 2026-06-13

## Current Status

現在のパッケージは構造面では整理されているが、Spectrum 品質はまだ production behavior として扱える段階ではない。

実装状態:

- `Anima for Replay` は安定寄りの replay-only node。
- `Anima for Spectrum` は experimental Spectrum node。
- Spectrum math は Chebyshev/Taylor blend + ridge regression として実装済み。
- Phase 2 は decode 前の intermediate feature を予測する構成。
- `core/intermediate_spectrum.py` に debug logging がある。
- `forecast_mode=replace|shadow|actual_only` を advanced/debug control として追加済み。
- `core/forecast_records.py` に JSONL record builder を分離し、`record_type` / `feature_site_id` / tensor metadata / metrics を固定済み。
- `core/feature_sites.py` に現行 `pre_decoder_head` site を最小 `FeatureSite` として定義済み。
- `feature_site=post_block` と `target_block_index` を advanced diagnostic input として追加済み。実機API検証は次回再起動後に行う。
- calibration mode は存在するが、default-on にする根拠はまだない。
- 目視確認では `spectrum_w=0.05`, `window_size=2`, warmup 18/20/22 はいずれも近く見えたため、品質許容ライン上の速度目標は warmup 18 とする。`spectrum_stop_caching_step=0` で終盤停止を無効化すると、2026-06-13 の API timing で W18 が実時間短縮を示した。

現在の証拠:

- 2026-06-13 の ComfyUI 0.24.0 実機 API run で、baseline / no-op / shadow 出力がピクセル完全一致した。
- shadow mode は現行 Phase 2 site で生成を変えず、forecast-vs-actual JSONL を出せる。
- low-warmup forecast replacement は大きく画像品質を落とす。
- high-warmup actual-heavy run は baseline-like output に戻る。
- 目視 review set では warmup 18/20/22 の差が小さい。
- default の自動終盤停止では W18 が 3 step しか forecast せず、debug off timing は baseline とほぼ同等だった。
- `spectrum_stop_caching_step=0` では W18 が 6 step forecast し、debug off timing は baseline avg 38.84s から W18Stop0 avg 34.82s に短縮した。
- UI default は W18Stop0 を第一候補にし、W15F05MS000 は速度優先の第二候補 preset として選べるようにする。

読み:

リファクタリングは `w`, `m`, `lam`, calibration のチューニングから始めない。先に、Anima/Cosmos のどの内部 feature stream が forecastable かを特定する。

## Decision Summary

### D1. Replay を安定面として残す

Decision:

`Anima for Replay` は分離された安定ノードとして維持する。

Reason:

Replay は現状で最も安全な実用経路であり、Spectrum diagnostics の影響を受けるべきではない。

### D2. Spectrum は topology-dependent として扱う

Decision:

現行 Phase 2 の feature site が正しいと仮定しない。

Reason:

ConceptAttention 関連リポジトリで、Anima/Cosmos では SDXL 的な raw attention 前提より DiT output-space の方が有効になりうることが分かった。

### D3. replace 前に shadow forecast を追加する

Decision:

新しい置換挙動の前に forecast-vs-actual logging を入れる。2026-06-13 時点では、現行 Phase 2 site に `forecast_mode=shadow` を追加し、生成出力を baseline と一致させたまま予測誤差を記録できることを実機で確認済み。

Reason:

現在の失敗は quality collapse であり、replace だけを見るとどの feature / step で drift が始まったか分からない。

### D4. calibration は二次課題にする

Decision:

安定 feature site が見つかるまで calibration は default-off のままにする。

Reason:

既存記録では calibration が no-calibration Spectrum baseline を明確に上回っていない。

### D5. 公開 API は保守的にする

Decision:

まず advanced/debug control として追加し、公開ノード構成を大きく変えない。

Reason:

このパッケージには既に V3 ID、legacy replacement、README guidance がある。診断機能追加中に既存 workflow 互換性を壊さない。

## Known Gaps

- topology inspector がまだない。
- feature-site abstraction がまだない。
- formal JSONL record は最小導入済みだが、versioning と run_summary はまだない。
- fake-model no-op parity / actual-only parity の自動テストがまだない。
- current Phase 2 site 以外の candidate feature site 比較がまだない。

## Verification Log

### 2026-06-02 - Refactor planning documents added

Changed:

- `ANIMA_SPECTRUM_REFACTOR_SPEC.md` を追加。
- `ANIMA_SPECTRUM_REFACTOR_PROGRESS.md` を追加。
- `ANIMA_SPECTRUM_REFACTOR_TASKS.md` を追加。

Verification:

- documentation-only change。
- この step ではコードテスト不要。

Next:

P1 として既存 public node metadata / no-op behavior のテストを追加し、その後 read-only topology discovery を始める。

### 2026-06-02 - ComfyUI-free regression tests and metrics added

Changed:

- Added pytest coverage for public node IDs, legacy node exports, input order, and defaults.
- Added pytest coverage for replay block-index parsing and schedule helpers.
- Added pytest coverage for residual calibration modes.
- Fixed root entrypoint fallback imports so pytest and local non-package imports can load the legacy node surface without ComfyUI.
- Added `core/forecast_metrics.py` for shadow forecast error metrics.

Verification:

- `python -m pytest -q` -> 24 passed.

Next:

Add topology discovery and feature-site diagnostics without changing generation output.

### 2026-06-02 - Read-only topology discovery foundation added

Changed:

- Added `core/topology.py`.
- Added `TopologyReport` and `ModuleListCandidate` records.
- Added read-only discovery for model identity, candidate transformer object, repeated block containers, known Anima methods, block class names, and forward signatures.
- Added fake-model tests for direct models, nested transformer models, JSON-ready reports, and models without block containers.

Verification:

- `python -m pytest -q` -> 29 passed.

Next:

Wire topology report emission into an observe-only diagnostics path, then add feature-site abstractions.

### 2026-06-13 - Live ComfyUI baseline/no-op/shadow API comparison

Changed:

- Added `forecast_mode=replace|shadow|actual_only` to the Spectrum node as an advanced debug input.
- Updated the fixed API/UI workflows under `docs/context_refactor/workflows/`.
- Added a repeatable comparison record for the live API run.

Verification:

- `/object_info/ShibaAnimaForSpectrumExperimental` exposes `forecast_mode`.
- `python -m pytest` -> 29 passed.
- ComfyUI 0.24.0 API run on `http://localhost:8000` completed:
  - baseline image: `C:\ComfyUI\output\AnimaCompareBaseline_00001_.png`
  - no-op image: `C:\ComfyUI\output\AnimaCompareNoop_00001_.png`
  - shadow image: `C:\ComfyUI\output\AnimaCompareShadow_00001_.png`
- Pixel comparison:
  - no-op vs baseline: exact match, MSE 0
  - shadow vs baseline: exact match, MSE 0
- Shadow log: `docs/context_refactor/logs/phase2-20260613T071525.810041Z-run01.jsonl`
  - 59 lines, 58 `shadow` step records
  - raw_vs_actual_rel_l2 average 0.0694, min 0.0340, max 0.2320
  - raw_vs_actual_cosine average 0.9970, min 0.9753, max 0.9995

Next:

Formalize JSONL record types and compare additional feature-site candidates before treating replace mode as quality-safe.

### 2026-06-13 - JSONL records and current feature-site boundary

Changed:

- Added `core/forecast_records.py` for stable run, topology, and step records.
- Added `core/feature_sites.py` with the current `pre_decoder_head` feature site.
- Wired `anima_spectrum_topology`, `anima_spectrum_shadow_step`, `anima_spectrum_replace_step`, and `anima_spectrum_actual_step` record types into Phase 2 logging.
- Kept legacy log keys such as `event`, `actual_or_forecast`, `errors`, `norms`, and `safety` for compatibility with existing analysis commands.

Verification:

- `python -m pytest` -> 34 passed.
- `python -m compileall core nodes tests` -> pass.

Next:

Restart ComfyUI and rerun the shadow API workflow to confirm the live JSONL contains `record_type=anima_spectrum_topology` and `record_type=anima_spectrum_shadow_step`.

### 2026-06-13 - Live JSONL record-type verification

Changed:

- Confirmed the restarted ComfyUI runtime emitted the new JSONL record types.
- Renamed the current feature-site ID from `forward_before_blocks` to `pre_decoder_head` after topology showed this model uses the `predict2_minidit` path and the measured forecast tensor is the block output before final decode.

Verification:

- API output: `C:\ComfyUI\output\AnimaRecordCheckShadow_00001_.png`
- JSONL: `docs/context_refactor/logs/phase2-20260613T072907.640125Z-run01.jsonl`
- Record counts:
  - `anima_spectrum_run_start`: 1
  - `anima_spectrum_topology`: 1
  - `anima_spectrum_shadow_step`: 58
- Topology:
  - model: `comfy.ldm.anima.model.Anima`
  - api_variant: `predict2_minidit`
  - block container: `blocks`
  - block count: 28

Next:

After the next ComfyUI restart, rerun the shadow workflow once to confirm new logs use `feature_site_id=pre_decoder_head`, then add `post_block` candidates.

### 2026-06-13 - Post-block diagnostic candidate added

Changed:

- Added `feature_site=pre_decoder_head|post_block`.
- Added `target_block_index` for `post_block` diagnostics.
- Wired `post_block` shadow execution by measuring the selected block output, then running the remaining blocks before decode.
- Updated API/UI workflow JSON with the new required inputs.

Verification:

- `python -m pytest` -> 34 passed.
- `python -m compileall core nodes tests` -> pass.
- Workflow JSON parse -> pass.

Next:

Restart ComfyUI and run:

```text
--set 79.forecast_mode=shadow --set 79.feature_site=post_block --set 79.target_block_index=13
```

Expected gate:

- output remains pixel-identical to baseline
- JSONL contains `feature_site_id=post_block`
- `anima_spectrum_shadow_step` metrics can be compared against `pre_decoder_head`

### 2026-06-13 - Feature-site shadow comparison

Changed:

- Ran API shadow comparisons for:
  - `pre_decoder_head`
  - `post_block`, target block 6
  - `post_block`, target block 13
  - `post_block`, target block 20
- Added `docs/context_refactor/feature-site-shadow-comparison-2026-06-13.md`.

Verification:

- All four shadow outputs matched baseline exactly at pixel level.
- `pre_decoder_head` remained the strongest site:
  - rel-L2 avg 0.069403
  - rel-L2 max 0.231968
  - cosine avg 0.997036
- Tested `post_block` sites were much less stable:
  - block 6 rel-L2 avg 0.330476
  - block 13 rel-L2 avg 0.689447
  - block 20 rel-L2 avg 0.526751
- All tested `post_block` sites crossed rel-L2 >= 0.5 at step 1.

Decision:

Keep `pre_decoder_head` as the current main candidate. Do not promote `post_block` to replace mode based on this run.

### 2026-06-13 - Calibration shadow comparison

Changed:

- Ran API shadow comparisons for calibration off, `latest`, `ema`, and `bucketed_ema`.
- Added `docs/context_refactor/calibration-shadow-comparison-2026-06-13.md`.

Verification:

- All four shadow outputs matched baseline exactly at pixel level.
- Calibration did not improve the no-calibration baseline:
  - off rel-L2 avg 0.069403
  - latest calibrated rel-L2 avg 0.074496
  - ema calibrated rel-L2 avg 0.072083
  - bucketed_ema calibrated rel-L2 avg 0.070530
- `bucketed_ema` was least harmful among enabled modes, but still worse than off.

Decision:

Keep `enable_calibration=false` as the default. Do not promote calibration before broader evidence shows a real gain.

Next:

Explore safer `pre_decoder_head` forecast hyperparameters in shadow mode, especially lower `spectrum_w`, before trying replace mode again.

### 2026-06-13 - Conservative replace checks

Changed:

- Ran `pre_decoder_head` shadow sweeps for `spectrum_w=0.05`, `0.10`, and `0.20`.
- Postprocessed shadow logs for candidate warmup/window replace masks.
- Ran conservative replace checks for `spectrum_w=0.05`, `window_size=2`, warmup 14/18/20/22.
- Added `docs/context_refactor/forecast-hyperparameter-shadow-replace-2026-06-13.md`.

Verification:

- Shadow outputs for all `spectrum_w` values matched baseline exactly.
- `spectrum_w=0.05` had the lowest shadow drift:
  - rel-L2 avg 0.067830
  - rel-L2 max 0.221681
- Replace checks completed without runtime errors.
- Baseline image drift decreased as warmup increased:
  - warmup 14: MSE 363.648773
  - warmup 18: MSE 155.839279
  - warmup 20: MSE 147.801147
  - warmup 22: MSE 72.415337

Decision:

Keep `pre_decoder_head`, calibration off, and `spectrum_w=0.05` for future replace checks. Treat warmup 20/22 as the next visual-review candidates. Do not use warmup 14 as a quality candidate on this workflow.

### 2026-06-13 - Visual speed selection

Changed:

- Generated a 3-seed visual review set for baseline, W22, W20, and W18.
- Added `docs/context_refactor/visual-review-2026-06-13.md`.
- Added `docs/context_refactor/visual-speed-selection-2026-06-13.md`.
- After restart, ran a 4-prompt validation for W18 + `spectrum_stop_caching_step=0`.
- Added `docs/context_refactor/multi-prompt-w18-stop0-validation-2026-06-13.md`.

Verification:

- Contact sheet rendered successfully at `docs/context_refactor/visual_review/anima_visual_compare_2026-06-13.png`.
- Visual review judged W18/W20/W22 close enough that the fastest acceptable candidate should win.
- API timing with `debug_logging=false` and default auto-stop did not show a measurable speed win.
- Follow-up API timing with `spectrum_stop_caching_step=0` did show a measurable speed win:
  - baseline avg 38.84s
  - W18AutoStop avg 38.83s
  - W18Stop0 avg 34.82s

Decision:

Treat W18 + `spectrum_stop_caching_step=0` as the preferred measured quality/speed target, with W20/W22 as fallbacks. Keep node defaults conservative until broader prompts/seeds confirm the target.

### 2026-06-13 - Multi-prompt W18 stop=0 validation

Changed:

- Verified restarted ComfyUI exposes the updated `spectrum_stop_caching_step` tooltip through `/object_info`.
- Ran baseline vs W18Stop0 across four prompt/seed cases, including one reverse-order timing check.
- Added contact sheet `docs/context_refactor/visual_review/anima_multi_prompt_w18_stop0_2026-06-13.png`.

Verification:

- `image_anima_base_v1_spectrum_debug(api).json` preflight passed after restart.
- Average timing:
  - baseline avg 39.861s
  - W18Stop0 avg 34.845s
  - average speedup 5.016s
- Reverse-order case still showed W18Stop0 faster:
  - W18Stop0 34.861s
  - baseline 38.851s
- Visual sheet did not show obvious collapse in face, body, linework, or background composition.
- M04 had the largest pixel metric drift (PSNR 23.282), so it remains a case to keep in future visual checks.

Decision:

Promote W18 + `spectrum_stop_caching_step=0` from target hypothesis to the current measured candidate. Keep broader validation open before changing defaults.

### 2026-06-13 - Paper-aligned flex schedule and Taylor pass

Changed:

- Rechecked the Spectrum paper and bundled author repository under `docs/Spectrum`.
- Fixed `flex_window` scheduling so the flexible window advances only after actual forward steps.
- Changed Taylor extrapolation to scale by target-step distance instead of a fixed `0.5` delta.
- Added regression tests for both schedule behavior and Taylor step history.
- Added `docs/context_refactor/run_flex_window_api_comparison.py` for repeatable API sweeps.

Verification:

- Unit verification after the implementation:
  - `python -m pytest` -> `40 passed`
  - `python -m compileall core nodes tests` -> pass
  - `git diff --check` -> whitespace errors none, CRLF warnings only
- Restarted ComfyUI API validation:
  - preflight passed for `image_anima_base_v1_spectrum_debug(api).json`
  - `shadow` W18/W14 outputs matched baseline exactly at pixel level
  - W14F05 debug forecast steps: `14,16,18,19,21,22,24,25,26,28,29`
- M04 replace sweep:
  - baseline: `29.640s`
  - W18Stop0: `19.466s`, PSNR `22.383`, MAE `8.895`
  - W16F05: `19.553s`, PSNR `18.769`, MAE `15.638`
  - W14F05: `16.943s`, PSNR `16.425`, MAE `22.413`
  - W12F05: `16.880s`, PSNR `17.379`, MAE `18.481`
- W18/W17 refine sweep did not beat W18Stop0 on the speed/quality tradeoff:
  - W18F025: `19.468s`, PSNR `19.265`
  - W18F05: `19.509s`, PSNR `17.583`
  - W17F00: `19.496s`, PSNR `19.599`
  - W17F025: `19.454s`, PSNR `17.326`

Decision:

Keep W18 + `spectrum_stop_caching_step=0`, `feature_site=pre_decoder_head`, calibration off, `spectrum_w=0.05`, `window_size=2`, and `flex_window=0.0` as the current measured candidate. `flex_window>0` can produce much larger speedups, but the current predictor does not preserve quality well enough on the M04 regression prompt.

### 2026-06-13 - Multi-step predictor parameter and guard probes

Changed:

- Extended `docs/context_refactor/run_flex_window_api_comparison.py` with `predictor` and `guard` case sets.
- Ran W14F05 multi-step predictor probes with paper-like `m=4`, `lam=0.1`, and higher Chebyshev blend weights.
- Ran stop-guard probes using existing `spectrum_stop_caching_step` to return late steps to actual forward.

Verification:

- Predictor sweep on M04 regression prompt:
  - W18Stop0: `19.480s`, PSNR `24.398`, MAE `6.923`
  - W14F05 current: `16.877s`, PSNR `17.254`, MAE `19.949`
  - W14F05 `m=4`, `lam=0.1`, `w=0.05`: PSNR `17.063`
  - W14F05 `m=4`, `lam=0.1`, `w=0.20`: PSNR `17.253`
  - W14F05 `m=4`, `lam=0.1`, `w=0.50`: PSNR `17.155`
  - W14F05 `m=8`, `lam=0.1`, `w=0.20`: PSNR `17.098`
- Stop-guard sweep on M04 regression prompt:
  - W18Stop0: `19.464s`, PSNR `22.463`, MAE `6.802`
  - W14F05Stop24: `22.038s`, PSNR `19.560`, MAE `9.889`
  - W14F05Stop26: `19.462s`, PSNR `19.541`, MAE `9.972`
  - W15F05Stop26: `19.477s`, PSNR `20.201`, MAE `9.167`
  - W16F05Stop26: `19.498s`, PSNR `20.243`, MAE `8.818`

Decision:

Parameter-only changes do not recover W14F05 quality. Late actual guards reduce some drift, but do not beat W18Stop0 on quality and do not produce meaningful additional speed. Continue W18Stop0 as the adopted candidate. The next useful predictor experiment should change the extrapolation model itself, not just `w/m/lam` or stop guards.

Artifacts:

- `docs/context_refactor/flex-window-api-predictor-2026-06-13.md`
- `docs/context_refactor/flex-window-api-guard-2026-06-13.md`
- `docs/context_refactor/visual_review/anima_flex_window_api_predictor_2026-06-13.png`
- `docs/context_refactor/visual_review/anima_flex_window_api_guard_2026-06-13.png`

### 2026-06-13 - Taylor damping probe

Changed:

- Added advanced `spectrum_taylor_damping` input.
- Default is `1.0`, preserving the current W18Stop0 behavior.
- Added unit coverage for damping reducing only the Taylor delta.
- Added `damping` case set to `docs/context_refactor/run_flex_window_api_comparison.py`.

Verification:

- Restarted ComfyUI exposed `spectrum_taylor_damping` through `/object_info`.
- API workflow preflight passed after adding the new default input.
- Damping sweep on M04 regression prompt:
  - Baseline: `29.679s`
  - W18Stop0D100: `22.055s`, PSNR `22.903`, MAE `8.094`
  - W14F05D100: `16.853s`, PSNR `16.345`, MAE `22.453`
  - W14F05D075: `17.001s`, PSNR `17.144`, MAE `20.067`
  - W14F05D050: `16.967s`, PSNR `17.747`, MAE `18.401`
  - W14F05D025: `16.945s`, PSNR `18.046`, MAE `17.494`
  - W16F05D050: `19.560s`, PSNR `20.026`, MAE `12.925`

Decision:

Taylor damping improves W14F05 monotonically in this run, so it is a useful predictor-quality lever. It still does not reach W18Stop0 quality, and W16F05D050 is not faster enough to justify the quality loss. Keep W18Stop0 as the adopted candidate and keep `spectrum_taylor_damping=1.0` default.

Artifacts:

- `docs/context_refactor/flex-window-api-damping-2026-06-13.md`
- `docs/context_refactor/visual_review/anima_flex_window_api_damping_2026-06-13.png`

### 2026-06-13 - Forecast-horizon multi-step damping probe

Changed:

- Added advanced `spectrum_multistep_damping` input.
- Initial implementation used `k > 1` step-distance detection, but the first API run showed all W14F05 multi-step damping values were pixel-identical.
- Updated the implementation to use consecutive forecast horizon (`num_cached_before + 1`) so only the second and later consecutive forecast steps are damped.
- Added unit coverage that default horizon is unchanged and explicit multi-step horizon is damped.

Verification:

- Restarted ComfyUI exposed `spectrum_multistep_damping` through `/object_info`.
- API workflow preflight passed after the update.
- Corrected gap-damping sweep on M04 regression prompt:
  - W18Stop0MS000: `21.991s`, PSNR `25.012`, MAE `6.574`
  - W14F05MS100: `17.030s`, PSNR `18.407`, MAE `17.134`
  - W14F05MS075: `16.916s`, PSNR `18.699`, MAE `16.429`
  - W14F05MS050: `16.968s`, PSNR `18.951`, MAE `15.835`
  - W14F05MS025: `16.988s`, PSNR `19.138`, MAE `15.404`
  - W14F05MS000: `16.843s`, PSNR `19.207`, MAE `15.243`
- W15/W16 refine sweep:
  - W18Stop0MS000: `19.471s`, PSNR `22.209`, MAE `8.326`
  - W16F05MS000: `19.474s`, PSNR `20.584`, MAE `11.812`
  - W16F05MS025: `19.436s`, PSNR `20.693`, MAE `11.525`
  - W15F05MS000: `16.975s`, PSNR `19.829`, MAE `13.582`
  - W15F05MS025: `16.986s`, PSNR `19.774`, MAE `13.658`

Decision:

Forecast-horizon based multi-step damping is working and improves W14/W16 quality relative to undamped flex runs. It still does not beat W18Stop0 on the quality/speed tradeoff. Keep W18Stop0 as the adopted candidate and keep both damping controls defaulted to `1.0`. The remaining acceleration path likely needs a different predictor model or a more selective per-step/site policy.

Artifacts:

- `docs/context_refactor/flex-window-api-gapdamping-2026-06-13.md`
- `docs/context_refactor/flex-window-api-gaprefine-2026-06-13.md`
- `docs/context_refactor/visual_review/anima_flex_window_api_gapdamping_2026-06-13.png`
- `docs/context_refactor/visual_review/anima_flex_window_api_gaprefine_2026-06-13.png`

### 2026-06-13 - Spectrum off / W18Stop0 / W15F05MS000 multi-prompt comparison

Changed:

- Added `docs/context_refactor/run_off_w18_w15_multi_prompt.py` to compare Spectrum disabled, W18Stop0, and W15F05MS000 across the same prompt/seed set.
- Spectrum disabled is represented by `debug_enable_spectrum=false` while keeping the same Phase 2 node in the workflow.

Verification:

- API preflight passed against the running ComfyUI instance.
- Four prompt/seed cases completed for each of `Off`, `W18Stop0`, and `W15F05MS000`.
- Average timing and image-difference metrics versus `Off`:
  - Off: `22.239s`
  - W18Stop0: `19.571s`, speedup `2.668s`, PSNR `25.865`, MAE `5.509`
  - W15F05MS000: `16.999s`, speedup `5.240s`, PSNR `21.354`, MAE `10.808`
- Per-prompt worst case remained M04:
  - W18Stop0: PSNR `21.407`, MAE `10.337`
  - W15F05MS000: PSNR `17.984`, MAE `17.924`

Decision:

W15F05MS000 is clearly faster than both Off and W18Stop0, reducing average runtime by about `23.6%` versus Off and about `13.1%` versus W18Stop0 in this run. The quality cost is also clear: average MAE is roughly doubled versus W18Stop0, and the M04 regression prompt shows a large visible/metric drift. Keep W18Stop0 as the first quality-preserving candidate. Treat W15F05MS000 as the second speed-first preset candidate.

User visual review:

- W18Stop0 is the preferred visual result and provides a useful 10%-range acceleration.
- W15F05MS000 is visibly lower quality, so it should remain a speed-first second candidate rather than the default path.
- The main optimization target is now additional speed while preserving W18Stop0-level quality, not reaching W15F05MS000 speed at any quality cost.

Follow-up implementation:

- Added advanced `spectrum_extra_forecast_steps` as an empty-default experiment control.
- The control accepts comma-separated 0-based step indexes, for example `23` or `21,25`.
- Empty default preserves the W18Stop0 schedule exactly.
- Added schedule tests showing W18Stop0 default actual steps are unchanged, and `extra_forecast_steps="23"` removes one additional actual step from the 30-step schedule.
- Added `extra` case set to `docs/context_refactor/run_flex_window_api_comparison.py` for M04 first-pass testing:
  - W18Stop0
  - W18Extra21
  - W18Extra23
  - W18Extra25
  - W18Extra21_25

Verification:

- `python -m pytest`: `46 passed`
- `python -m compileall core nodes tests docs\context_refactor\run_flex_window_api_comparison.py docs\context_refactor\run_off_w18_w15_multi_prompt.py`: passed
- `git diff --check`: no whitespace errors; CRLF warnings only
- After ComfyUI restart, `/object_info` exposed `spectrum_extra_forecast_steps`.
- M04 `extra` first-pass comparison:
  - W18Stop0: `19.926s`, PSNR `24.724`, MAE `6.704`
  - W18Extra21: `19.537s`, PSNR `22.489`, MAE `8.800`
  - W18Extra23: `19.556s`, PSNR `22.640`, MAE `8.661`
  - W18Extra25: `19.616s`, PSNR `23.607`, MAE `7.750`
  - W18Extra21_25: `19.531s`, PSNR `21.996`, MAE `9.450`
- M04 `extradamping` follow-up selected W18Extra25MS025 as the least-damaging extra-step variant:
  - W18Stop0: `22.009s`, PSNR `22.366`, MAE `8.909`
  - W18Extra25MS025: `19.577s`, PSNR `22.121`, MAE `9.522`
- Four-prompt practical comparison against Spectrum Off:
  - Off: avg `22.299s`
  - W18Stop0: avg `19.553s`, avg speedup `2.746s`, avg PSNR `25.865`, avg MAE `5.509`
  - W18Extra25MS025: avg `19.576s`, avg speedup `2.724s`, avg PSNR `24.833`, avg MAE `6.370`

Decision:

Extra step policy can improve isolated M04 timing in debug/logged runs, and `extra_steps=25` with `multistep_damping=0.25` is the best observed variant. However, in the four-prompt practical comparison it did not improve average runtime over W18Stop0 and consistently reduced quality. Do not adopt W18Extra25MS025. Keep `spectrum_extra_forecast_steps` as an experimental diagnostic control only, with the default empty value preserving W18Stop0. Expose W18Stop0 and W15F05MS000 through `spectrum_preset` so users can select the first quality-preserving candidate or the second speed-first candidate without hand-editing all knobs.

### 2026-06-13 - W18Stop0 profiling instrumentation

Changed:

- Added debug-only timing fields to JSONL step records.
- Timing collection synchronizes CUDA only when `debug_logging=true`; normal generation with logging off is unchanged.
- Step records now include a `timings` object with fields such as:
  - `actual_feature_ms`
  - `raw_guess_ms`
  - `calibration_apply_ms`
  - `forecast_cast_ms`
  - `forecaster_update_ms`
  - `path_total_ms`
- Added timing and worst-error summaries to `docs/context_refactor/run_flex_window_api_comparison.py` reports.
- Added `--case-set w18profile`:
  - `Baseline`
  - `W18Stop0Profile` in replace mode, for existing 6 forecast step timing
  - `ShadowW18Stop0Profile` in shadow mode, for per-step forecast-vs-actual error ranking

Verification:

- `python -m pytest`: `46 passed`
- `python -m compileall core nodes tests docs\context_refactor\run_flex_window_api_comparison.py docs\context_refactor\run_off_w18_w15_multi_prompt.py`: passed
- `git diff --check`: no whitespace errors; CRLF warnings only

Next runtime command after ComfyUI restart:

```powershell
python docs\context_refactor\run_flex_window_api_comparison.py --url http://localhost:8000 --case-set w18profile
```

Decision:

Use `w18profile` before further predictor changes. If timing shows forecast steps are already cheap relative to unavoidable decode/overhead, pursue quality stabilization instead of more skipping. If shadow worst-error rows concentrate around specific W18 forecast steps, target those steps with damping/guard policy rather than changing the whole schedule.

Artifacts:

- `docs/context_refactor/off-w18-w15-multi-prompt-2026-06-13.md`
- `docs/context_refactor/flex-window-api-extra-2026-06-13.md`
- `docs/context_refactor/flex-window-api-extradamping-2026-06-13.md`
- `docs/context_refactor/off-w18-extra25-multi-prompt-2026-06-13.md`
- `docs/context_refactor/visual_review/off_w18_w15_multi_prompt_2026-06-13.json`
- `docs/context_refactor/visual_review/anima_off_w18_w15_multi_prompt_2026-06-13.png`
- `docs/context_refactor/visual_review/anima_flex_window_api_extra_2026-06-13.png`
- `docs/context_refactor/visual_review/anima_flex_window_api_extradamping_2026-06-13.png`
- `docs/context_refactor/visual_review/anima_off_w18_extra25_multi_prompt_2026-06-13.png`

## Current Phase

```text
P7 replacement validation is active; W18Stop0 is the current measured first candidate and UI default, W15F05MS000 is the speed-first second candidate, and next work targets extra speed without dropping below W18Stop0 visual quality
```

P1-P4 は実機で確認済み。W18Stop0 を品質基準に固定する。単純な追加 step policy は複数 prompt で速度優位が出なかったため、次は `w18profile` で既存 6 forecast step の時間内訳と shadow 誤差集中stepを測定する。

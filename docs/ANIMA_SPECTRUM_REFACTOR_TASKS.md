# ANIMA_SPECTRUM_REFACTOR_TASKS.md

Project: Anima-for-spectrum
Repository: https://github.com/Shiba-2-shiba/Anima-for-spectrum
Task plan: topology-aware Spectrum refactor

## P0 - Planning and Scope Lock

- [x] P0-T01 現在の診断と失敗仮説を記録する。
- [x] P0-T02 詳細リファクタリング仕様を書く。
- [x] P0-T03 進捗 tracker を書く。
- [x] P0-T04 タスク checklist を書く。
- [ ] P0-T05 repeatable manual run 用の ComfyUI / Anima workflow を確定する。
- [ ] P0-T06 baseline workflow metadata を記録する: model, seed, sampler, steps, scheduler, resolution, prompt, negative prompt, precision, ComfyUI version。

## P1 - Behavior Lock Before Refactor

- [ ] P1-T01 public node ID の static test を追加する。
- [ ] P1-T02 V3 schema の input 名と default 値の static test を追加する。
- [ ] P1-T03 legacy replacement mapping の static test を追加する。
- [ ] P1-T04 `build_compat_input_types()` の test を追加する。
- [ ] P1-T05 `build_phase2_input_types()` の test を追加する。
- [ ] P1-T06 fake model で Replay disabled path の no-op test を追加する。
- [ ] P1-T07 fake model で Spectrum disabled path の no-op test を追加する。
- [ ] P1-T08 actual-only mode 実装後、fake model actual-only test を追加する。

## P2 - Topology Discovery

- [ ] P2-T01 `core/topology.py` を追加する。
- [ ] P2-T02 diffusion model class / module を記録する。
- [ ] P2-T03 candidate transformer object を探索する。
- [ ] P2-T04 repeated block container の name / length を探索する。
- [ ] P2-T05 block class name と forward signature を記録する。
- [ ] P2-T06 Anima 既知 method を検出する: `forward_before_blocks`, `decoder_head`, block runner shape。
- [ ] P2-T07 `anima_spectrum_topology` JSONL record を出す。
- [ ] P2-T08 topology report serialization の unit test を追加する。
- [ ] P2-T09 real Anima workflow で topology discovery を実行する。

## P3 - Feature Site Abstraction

- [ ] P3-T01 `core/feature_sites.py` を追加する。
- [ ] P3-T02 最小限の `FeatureSite` protocol を定義する。
- [ ] P3-T03 現行 `forward_before_blocks` site を実装する。
- [ ] P3-T04 topology が対応する場合、`pre_decoder_head` 候補を実装する。
- [ ] P3-T05 block replay path で安全に露出できる場合、selected `post_block` 候補を実装する。
- [ ] P3-T06 feature-site fallback record を追加する。
- [ ] P3-T07 unsupported feature site fallback の fake-model test を追加する。
- [ ] P3-T08 shape / dtype / device preservation test を追加する。

## P4 - Shadow Forecast Foundation

- [ ] P4-T01 `core/forecast_metrics.py` を追加する。
- [ ] P4-T02 MSE, relative L2, cosine, norm ratio, clamp fraction の metric 関数を追加する。
- [ ] P4-T03 `core/forecast_records.py` を追加する。
- [ ] P4-T04 `core/forecast_shadow.py` を追加する。
- [ ] P4-T05 内部的に `forecast_mode=off|actual_only|shadow|replace` を追加する。
- [ ] P4-T06 output を変えずに `actual_only` を wire する。
- [ ] P4-T07 actual を返したまま forecast-vs-actual を計算する `shadow` を wire する。
- [ ] P4-T08 `anima_spectrum_shadow_step` JSONL を出す。
- [ ] P4-T09 fake tensor で shadow mode が actual output を正確に返す test を追加する。
- [ ] P4-T10 forecast metric record の test を追加する。

## P5 - Public Debug Controls

- [ ] P5-T01 advanced `forecast_mode` input を追加する。
- [ ] P5-T02 advanced `feature_site` input を追加する。
- [ ] P5-T03 advanced `target_block_indices` input を追加する。
- [ ] P5-T04 advanced `shadow_sample_rate` input を追加する。
- [ ] P5-T05 advanced `fail_mode` input を追加する。
- [ ] P5-T06 V3 schema と legacy fallback input spec を一貫して更新する。
- [ ] P5-T07 新しい advanced input を持たない旧 workflow の migration behavior を追加する。
- [ ] P5-T08 README の使い方を更新する。

## P6 - Candidate Site Measurement

- [ ] P6-T01 現行 Phase 2 site で shadow mode を実行する。
- [ ] P6-T02 利用可能なら `pre_decoder_head` で shadow mode を実行する。
- [ ] P6-T03 selected `post_block` sites で shadow mode を実行する。
- [ ] P6-T04 step / site ごとの relative L2 を比較する。
- [ ] P6-T05 step / site ごとの cosine similarity を比較する。
- [ ] P6-T06 各 site の first-collapse step を特定する。
- [ ] P6-T07 low warmup でも安定する feature site を特定する。
- [ ] P6-T08 結果を `docs/context_refactor/` に記録する。

## P7 - Replacement Mode Reintroduction

- [ ] P7-T01 測定上もっとも安定した feature site だけで `replace` を有効化する。
- [ ] P7-T02 replacement を `fail_mode` で guard する。
- [ ] P7-T03 baseline vs `actual_only` を実行する。
- [ ] P7-T04 baseline vs `shadow` を実行する。
- [ ] P7-T05 baseline vs `replace` を実行する。
- [ ] P7-T06 image path、workflow metadata、node settings を保存する。
- [ ] P7-T07 visual review notes を追加する: face, hands, hair, background, color, composition, texture。
- [ ] P7-T08 runtime と quality metrics を比較する。

## P8 - Calibration Re-evaluation

- [ ] P8-T01 no-calibration と `latest` を比較する。
- [ ] P8-T02 no-calibration と `ema` を比較する。
- [ ] P8-T03 no-calibration と `bucketed_ema` を比較する。
- [ ] P8-T04 calibration 比較中は `w`, `m`, `lam`, `window_size`, feature site を固定する。
- [ ] P8-T05 shadow record 上で calibration gain を測定する。
- [ ] P8-T06 複数 run で no-cal を上回った場合だけ calibration default を昇格する。

## P9 - Cleanup and Stabilization

- [ ] P9-T01 挙動が test で保護された後、不要な Phase 1-only code を削除する。
- [ ] P9-T02 新 controller が共有できる場合、重複した schedule / reset logic を整理する。
- [ ] P9-T03 重複が出た場合、JSONL logging helper を統合する。
- [ ] P9-T04 test が必要としない限り Replay runtime は触らない。
- [ ] P9-T05 unit tests を実行する。
- [ ] P9-T06 ComfyUI import smoke test を実行する。
- [ ] P9-T07 fixed-seed workflow validation を手動実行する。
- [ ] P9-T08 最終判断を `refactor-history.md` に追記する。

## Completion Criteria

リファクタリング完了条件:

- Replay stable path が維持されている。
- Spectrum disabled / actual-only path が baseline と一致する。
- shadow log が少なくとも 1 つの stable feature site を特定する、または現時点では安定 site がないことを示す。
- replacement mode は測定済み site だけで test されている。
- README に experimental status と推奨 default が書かれている。
- 残リスクが具体的な next step とともに記録されている。

# Base Workflow Comparison Checklist

## Purpose

削除済みの `baseワークフロー.json` をもとにしていた Phase 1 比較手順を、再実行できる形で残すためのチェックリスト。

比較対象:

- ベースライン
- replay only
- spectrum only
- spectrum + calibration
- no-op compatibility

## Base Workflow Notes

基準 workflow:

- 旧 `baseワークフロー.json` の構成を引き継いだローカル保存 workflow を使う
- 現在はリポジトリ外の任意パスに保存し、そのパスを比較記録に残す

この workflow には、もともと `Anima Layer Replay Patcher` が入っていなかった想定で比較する。

比較時は、`LoraLoaderTriggerWords` の `MODEL` 出力から `ClownsharKSampler_Beta` の `model` 入力へつながっている経路に、`Anima Layer Replay Patcher` を差し込む。

推奨接続位置:

- 既存: `LoraLoaderTriggerWords -> ClownsharKSampler_Beta`
- 比較時: `LoraLoaderTriggerWords -> Anima Layer Replay Patcher -> ClownsharKSampler_Beta`

## Fixed Conditions

比較中は以下を固定する。

- UNET
- CLIP
- VAE
- LoRA
- positive prompt
- negative prompt
- width / height
- steps
- scheduler
- sampler
- seed
- CFG 相当パラメータ
- APG / TCFG / Mahiro の有無と設定

変更してよいのは以下だけ。

- `Anima Layer Replay Patcher` の有無
- `Anima Layer Replay Patcher` の各入力値

## Pre-Run Checks

- [ ] 基準 workflow を読み込んだ
- [ ] 比較用 workflow を別名保存した
- [ ] seed を固定した
- [ ] 保存先 prefix を比較用に分けた
- [ ] モデル、LoRA、prompt、解像度、steps が全ケースで同一である
- [ ] sampler 側の設定が全ケースで同一である
- [ ] VRAM 状態や他ジョブの混入がないことを確認した

## Workflow Wiring Checks

- [ ] `Anima Layer Replay Patcher` を sampler の直前に入れた
- [ ] `model` の流れが `LoraLoaderTriggerWords -> Anima Layer Replay Patcher -> ClownsharKSampler_Beta` になっている
- [ ] sampler の `positive` / `negative` / `latent_image` / `sigmas` / `steps` は元 workflow と同じ
- [ ] patcher を使わないケースでは、元の直結経路か、no-op compatibility ケースを明示的に使い分けた

## Suggested Comparison Matrix

### Case A: Baseline

- Patcher なし
- 目的: 元 workflow の基準画像と時間を固定する

### Case B: No-op Compatibility

- `enable_replay = false`
- `enable_spectrum = false`
- 目的: patcher を挿しただけで挙動が崩れないか確認する

### Case C: Replay Only

- `enable_replay = true`
- `enable_spectrum = false`
- 推奨初期値:
- `block_indices = 3,4,5`
- `denoise_start_pct = 0.50`
- `denoise_end_pct = 1.00`

### Case D: Spectrum Only

- `enable_replay = false`
- `enable_spectrum = true`
- `enable_calibration = false`
- 推奨初期値:
- `spectrum_w = 0.20`
- `spectrum_m = 16`
- `spectrum_lam = 0.50`
- `spectrum_warmup_steps = 6`
- `spectrum_window_size = 2`
- `spectrum_flex_window = 0.0`
- `spectrum_stop_caching_step = -1`

### Case E: Spectrum + Calibration

- `enable_replay = false`
- `enable_spectrum = true`
- `enable_calibration = true`
- 推奨初期値:
- `spectrum_w = 0.20`
- `spectrum_m = 16`
- `spectrum_lam = 0.50`
- `spectrum_warmup_steps = 6`
- `spectrum_window_size = 2`
- `spectrum_flex_window = 0.0`
- `spectrum_stop_caching_step = -1`
- `calibration_strength = 0.50`

### Optional Case F: Replay + Spectrum + Calibration

- `enable_replay = true`
- `enable_spectrum = true`
- `enable_calibration = true`
- 目的: 実運用候補の総合確認

## Per-Case Run Checklist

各ケースごとに以下を確認する。

- [ ] 実行前に画像保存 prefix をケース名に変更した
- [ ] 実行前に patcher 入力値を記録した
- [ ] 生成時間または体感速度を記録した
- [ ] 出力画像を保存した
- [ ] 破綻の有無を確認した
- [ ] 色ズレの有無を確認した
- [ ] 細部の潰れ具合を確認した
- [ ] 終盤 detail の戻り具合を確認した
- [ ] 再実行して同条件で再現するか確認した

## Visual Review Points

見る場所を毎回固定する。

- 顔の輪郭
- 目
- 髪の束感
- 手指
- 衣服の境界
- 小物の線
- 背景の細部
- 全体の色ズレ
- ノイズ感
- 終盤の micro detail

## Stability Checks

- [ ] patcher 有効化後も例外なく完走した
- [ ] 再実行時に前回 state を引きずった挙動がない
- [ ] batch size を変えた場合でも shape 不整合がない
- [ ] replay 無効時に replay 由来の変化が出ない
- [ ] spectrum 無効時に spectrum 由来の変化が出ない

## Artifact Naming

保存物の名前はケースと条件が分かるように揃える。

例:

- `20260329_caseA_baseline_seed1234.png`
- `20260329_caseC_replay_only_seed1234.png`
- `20260329_caseE_spectrum_calibration_seed1234.png`

## Exit Criteria

最低限、以下が埋まったら Phase 1 の比較証跡として扱う。

- [ ] Case A から E の画像
- [ ] 各ケースの patcher 設定
- [ ] seed
- [ ] 実行時間メモ
- [ ] 画質所見
- [ ] 破綻や違和感の有無
- [ ] 次に調整すべき入力値

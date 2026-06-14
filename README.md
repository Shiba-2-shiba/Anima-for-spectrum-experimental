# Anima-for-spectrum

Anima 系モデル向けの ComfyUI カスタムノードです。  
このリポジトリは **Replay** と **Spectrum** の 2 系統を扱い、画質維持と高速化の両方を狙えるようにしています。

- **Replay**: 指定した denoise 区間で内部ブロックを一時的に再実行し、細部や整合性を補いやすくします。
- **Spectrum**: 過去ステップの履歴から中間特徴を予測し、一部のフル評価を省略して高速化します。

このプロジェクトは [`AdamNizol/ComfyUI-Anima-Enhancer`](https://github.com/AdamNizol/ComfyUI-Anima-Enhancer) を出発点に大幅改訂し、別パッケージとして公開するために再構成したものです。  
元リポジトリとはノード ID と表示名を分けているため、同じ ComfyUI 環境に共存させやすくしています。

## 提供ノード

ComfyUI 上では次の 2 ノードとして表示されます。

- **Anima for Replay**
- **Anima for Spectrum**

役割は次のとおりです。

- **Anima for Replay**: 安定運用向けの Replay 専用ノードです。Spectrum を使わず、元の Replay 系の挙動だけを使いたい場合に向いています。
- **Anima for Spectrum**: Spectrum を使うメインノードです。通常はこのノードを使い、細かい調整が必要なときだけ Advanced 項目を開く想定です。

## インストール

`ComfyUI/custom_nodes` で次を実行してください。

```bash
git clone https://github.com/Shiba-2-shiba/Anima-for-spectrum.git
```

その後、ComfyUI を再起動してください。

## 互換性

- 新しい ComfyUI では [__init__.py](./__init__.py) と [v3_nodes.py](./v3_nodes.py) の `comfy_entrypoint()` を使う V3 エントリーポイントで読み込まれます。
- 旧来の ComfyUI では [nodes/compat.py](./nodes/compat.py) と [nodes/phase2.py](./nodes/phase2.py) を使う `NODE_CLASS_MAPPINGS` フォールバックに対応しています。
- Nodes 2.0 向けの `display_name`、`description`、`category`、`search_aliases`、`essentials_category` などのメタデータを V3 Schema で定義しています。
- V3 読み込み時は、旧ワークフローで使われていたノード ID から現在の公開 ID へ移行できるよう置換ルールを持っています。

## 公開ノード ID

- 安定ノード ID: `ShibaAnimaForReplay`
- Spectrum ノード ID: `ShibaAnimaForSpectrumExperimental`
- 移行用に保持している旧 ID: `ShibaAnimaForSpectrum`
- 移行用に保持している旧 ID: `AnimaLayerReplayPatcher`
- 移行用に保持している旧 ID: `AnimaIntermediateSpectrumPatcher`

## 使い方

### 1. Anima for Replay

Replay だけを使いたい場合は **Anima for Replay** を使います。  
モデルをこのノードに通し、その出力を sampler の直前へつなぐ使い方を想定しています。

主な入力:

- `enable_replay`: Replay の有効 / 無効
- `block_indices`: 再実行するブロック番号。例: `3,4,5`、`3-5,8`
- `denoise_start_pct`: Replay を開始する denoise 進行率
- `denoise_end_pct`: Replay を終了する denoise 進行率

### 2. Anima for Spectrum

Spectrum を使って高速化したい場合は **Anima for Spectrum** を使います。  
通常運用ではまずこちらを基準に調整するのが前提です。

主な入力:

- `spectrum_preset`: 測定済みプリセット。通常は `W18Stop0`、速度優先時は `W15F05MS000`、手動調整時は `Manual`
- `spectrum_w`: 画質と速度のバランス。低いほど安全寄り、高いほど攻めた設定です。
- `spectrum_warmup_steps`: 予測を始める前に実測するステップ数です。
- `spectrum_window_size`: 実際に特徴を計算する間隔です。大きいほど高速ですがズレやすくなります。
- `enable_calibration`: 補正処理の有効 / 無効
- `calibration_strength`: 補正をどれだけ強く反映するか
- `calibration_mode`: 補正値の蓄積方法

Advanced 項目:

- `spectrum_m`
- `spectrum_lam`
- `spectrum_taylor_damping`
- `spectrum_multistep_damping`
- `spectrum_flex_window`
- `spectrum_stop_caching_step`
- `spectrum_extra_forecast_steps`
- `calibration_decay`
- `calibration_buckets`
- `calibration_min_obs`
- `debug_enable_spectrum`
- `debug_logging`

## 推奨初期値

### Replay の基準値

- `enable_replay = true`
- `block_indices = 3,4,5`
- `denoise_start_pct = 0.50`
- `denoise_end_pct = 1.00`

### Spectrum の基準値

第一候補は `spectrum_preset = W18Stop0` です。

- `spectrum_w = 0.05`
- `spectrum_warmup_steps = 18`
- `spectrum_window_size = 2`
- `spectrum_flex_window = 0.0`
- `spectrum_stop_caching_step = 0`
- `spectrum_multistep_damping = 1.0`
- `enable_calibration = false`

速度を優先する第二候補は `spectrum_preset = W15F05MS000` です。これは `warmup=15`, `flex_window=0.5`, `multistep_damping=0.0`, `stop_caching_step=0` の攻めた設定で、W18Stop0 より速い一方、品質低下が出やすいです。

細かく調整する場合は `spectrum_preset = Manual` にしてから各値を変更してください。

## リポジトリ構成

- [v3_nodes.py](./v3_nodes.py): V3 Schema 定義、Nodes 2.0 用メタデータ、置換ルール登録
- [nodes/input_specs.py](./nodes/input_specs.py): ノード ID、表示名、カテゴリ、旧入力順の共通定義
- [nodes/compat.py](./nodes/compat.py): 安定版 Replay 系のランタイム実装
- [nodes/phase2.py](./nodes/phase2.py): Spectrum 系のランタイム実装
- [core/replay.py](./core/replay.py): Replay 窓処理と一時ブロック差し替え
- [core/calibration.py](./core/calibration.py): 同ステップ残差補正の状態管理と各モード
- [core/intermediate_features.py](./core/intermediate_features.py): 中間特徴抽出、ブロック再実行、デコード補助
- [core/intermediate_spectrum.py](./core/intermediate_spectrum.py): 中間特徴予測の制御とデバッグログ
- [docs/refactor-history.md](./docs/refactor-history.md): 整理後の改修履歴と計測メモ
- [docs/context_refactor/](./docs/context_refactor/): 比較メモ、テンプレート、JSONL ログ

## このリポジトリでの整理方針

- 元の `ComfyUI-Anima-Enhancer` から、公開用にノード ID・表示名・構成を整理しています。
- 安定系の Replay ノードと、Spectrum を使うメインノードを役割ごとに分離しています。
- 新しい ComfyUI の V3 / Nodes 2.0 系メタデータに合わせて、公開パッケージとして扱いやすい形へ再構成しています。

## 謝辞

このリポジトリは、以下の先行実装を大きな参考にしています。

### Anima モデル対応の参考

[`AdamNizol/ComfyUI-Anima-Enhancer`](https://github.com/AdamNizol/ComfyUI-Anima-Enhancer)

- Anima 系モデルに対して Replay を適用する発想と、ComfyUI ノードとして扱う出発点を提供してくれたリポジトリです。
- 本リポジトリはこの実装をベースにしつつ、ノード構成、公開 ID、V3 対応、Spectrum 系の整理を含めて大幅に改修しています。

### Calibration 実装の参考

[`ruwwww/comfyui-spectrum-sdxl`](https://github.com/ruwwww/comfyui-spectrum-sdxl)

- Spectrum の高速化ノードに calibration を組み合わせる考え方と、補正付き運用の方向性を考えるうえで参考にしたリポジトリです。
- 本リポジトリでは Anima 系モデル向けに合わせて構成やパラメータを再設計しています。

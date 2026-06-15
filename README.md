# Anima-for-spectrum-experimental

Anima 系モデル向けの ComfyUI カスタムノードです。

このリポジトリは、Anima 系モデルで使う **Replay** と、Spectrum 由来の中間特徴予測を使う **Spectrum** の 2 系統を扱います。Replay は安定運用向け、Spectrum は出力変化をできるだけ抑えながら生成時間を少し短くするための実験的なノードです。

> **Status**
>
> Spectrum 側は experimental です。手元の Anima 検証では、`W18Stop0` が出力変化をかなり小さく抑えたまま、おおむね 10% 台の生成時間短縮を狙える条件でした。この「変化の少なさを優先した実用候補」をメインにしています。
>
> このリポジトリは `comfyui-spectrum-sdxl` より高速であることを主張するものではありません。対象モデルと実装箇所が異なるため、単純な速度比較はできません。

## Nodes

ComfyUI 上では次の 2 ノードとして表示されます。

- **Anima for Replay**
- **Anima for Spectrum**

### Anima for Replay

Replay だけを使う安定寄りのノードです。指定した denoise 区間で内部ブロックを一時的に再実行し、細部や整合性を補いやすくします。

主な入力:

- `enable_replay`: Replay の有効 / 無効
- `block_indices`: 再実行するブロック番号。例: `3,4,5`、`3-5,8`
- `denoise_start_pct`: Replay を開始する denoise 進行率
- `denoise_end_pct`: Replay を終了する denoise 進行率

### Anima for Spectrum

Spectrum 由来の考え方で中間特徴を予測し、一部の full evaluation を省略する実験ノードです。メインの推奨は、速度よりも出力変化の少なさを優先した `spectrum_preset = W18Stop0` です。

通常利用では **Spectrum Preset** だけを選びます。Preset 使用時は下の詳細パラメータが内部で固定されるため、手動調整用の入力は Advanced に隠しています。
Nodes 2.0 をオフにした旧UIでも、Preset が `Manual` 以外のときは同じ詳細パラメータを非表示にします。

通常表示:

- `spectrum_preset`: 測定済みプリセット。通常は `W18Stop0`、速度優先で試す場合は `W15F05MS000`、手動調整時は `Manual`

Advanced 項目:

- `spectrum_w`: 予測値のブレンド量。現在の推奨候補では `0.05`
- `spectrum_warmup_steps`: 予測を始める前に実測するステップ数
- `spectrum_window_size`: 実際に特徴を計算する間隔。大きいほど速くなりやすい一方、差分も出やすくなります
- `enable_calibration`: 残差補正の有効 / 無効。現時点の推奨初期値は `false`
- `calibration_strength`: 補正をどれだけ強く反映するか
- `calibration_mode`: 補正値の蓄積方法
- `spectrum_m`
- `spectrum_lam`
- `spectrum_taylor_damping`
- `spectrum_multistep_damping`
- `spectrum_flex_window`
- `spectrum_stop_caching_step`
- `spectrum_extra_forecast_steps`
- `feature_site`
- `target_block_index`
- `forecast_mode`
- `calibration_decay`
- `calibration_buckets`
- `calibration_min_obs`
- `debug_enable_spectrum`
- `debug_logging`

## Installation

`ComfyUI/custom_nodes` で次を実行してください。

```bash
git clone https://github.com/Shiba-2-shiba/Anima-for-spectrum-experimental.git
```

その後、ComfyUI を再起動してください。

## Recommended Settings

### Replay

- `enable_replay = true`
- `block_indices = 3,4,5`
- `denoise_start_pct = 0.50`
- `denoise_end_pct = 1.00`

### Spectrum: main candidate with small output changes

第一候補は `spectrum_preset = W18Stop0` です。

- `spectrum_w = 0.05`
- `spectrum_warmup_steps = 18`
- `spectrum_window_size = 2`
- `spectrum_flex_window = 0.0`
- `spectrum_stop_caching_step = 0`
- `spectrum_multistep_damping = 1.0`
- `enable_calibration = false`

手元の Anima 検証では、`W18Stop0` は `Spectrum disabled` に比べて平均で 10% 台の wall-clock 短縮を確認した実用候補です。大きく速くすることよりも、見た目の変化をかなり小さく抑えた条件を出せたことを重視しています。

公開 README では再現条件が環境依存になるため、固定のベンチマーク値としてではなく、Anima 向けの調整開始点として扱っています。

### Spectrum: aggressive speed-first candidate

速度優先で試す場合は `spectrum_preset = W15F05MS000` を使えます。

これは `warmup=15`, `flex_window=0.5`, `multistep_damping=0.0`, `stop_caching_step=0` の攻めた設定です。`W18Stop0` より速くなることがありますが、出力変化も大きくなりやすいため、このリポジトリのメイン候補ではありません。

細かく調整する場合は `spectrum_preset = Manual` にしてから各値を変更してください。

## Compatibility

- 新しい ComfyUI では [__init__.py](./__init__.py) と [v3_nodes.py](./v3_nodes.py) の `comfy_entrypoint()` を使う V3 エントリーポイントで読み込まれます。
- 旧来の ComfyUI では [nodes/compat.py](./nodes/compat.py) と [nodes/phase2.py](./nodes/phase2.py) を使う `NODE_CLASS_MAPPINGS` フォールバックに対応しています。
- Nodes 2.0 向けの `display_name`、`description`、`category`、`search_aliases`、`essentials_category` などのメタデータを V3 Schema で定義しています。
- V3 読み込み時は、旧ワークフローで使われていたノード ID から現在の公開 ID へ移行できるよう置換ルールを持っています。

## Public Node IDs

- Replay node: `ShibaAnimaForReplay`
- Spectrum node: `ShibaAnimaForSpectrumExperimental`
- Migration-only legacy ID: `ShibaAnimaForSpectrum`
- Migration-only legacy ID: `AnimaLayerReplayPatcher`
- Migration-only legacy ID: `AnimaIntermediateSpectrumPatcher`

## Repository Layout

- [v3_nodes.py](./v3_nodes.py): V3 Schema 定義、Nodes 2.0 用メタデータ、置換ルール登録
- [nodes/input_specs.py](./nodes/input_specs.py): ノード ID、表示名、カテゴリ、旧入力順の共通定義
- [nodes/compat.py](./nodes/compat.py): Replay 系のランタイム実装
- [nodes/phase2.py](./nodes/phase2.py): Spectrum 系のランタイム実装
- [core/replay.py](./core/replay.py): Replay 窓処理と一時ブロック差し替え
- [core/calibration.py](./core/calibration.py): 同ステップ残差補正の状態管理と各モード
- [core/intermediate_features.py](./core/intermediate_features.py): 中間特徴抽出、ブロック再実行、デコード補助
- [core/intermediate_spectrum.py](./core/intermediate_spectrum.py): 中間特徴予測の制御とデバッグログ
- [docs/refactor-history.md](./docs/refactor-history.md): 整理後の改修履歴と計測メモ
- [docs/context_refactor/](./docs/context_refactor/): 比較メモ、テンプレート、JSONL ログ

## Notes For Public Release

- このリポジトリには大型モデルファイルや参照リポジトリのコピーを含めていません。
- Spectrum の品質評価は、まず `forecast_mode = shadow` や `debug_logging = true` で差分を確認してから、必要に応じて `replace` で試すことを想定しています。
- `debug_logging = true` の場合、`docs/context_refactor/logs/` に JSONL ログを書き出します。

## License

このリポジトリは [MIT License](./LICENSE) で公開します。

Spectrum 関連の実装は、MIT ライセンスの [Spectrum](https://github.com/hanjq17/Spectrum) と [comfyui-spectrum-sdxl](https://github.com/ruwwww/comfyui-spectrum-sdxl) を参考にしています。Anima 向け Replay の構成は [ComfyUI-Anima-Enhancer](https://github.com/AdamNizol/ComfyUI-Anima-Enhancer) を参考にしており、詳細は下の Credits に記載しています。

## Credits

このリポジトリは、以下の先行実装と研究を参考にしています。

### Anima model support

[`AdamNizol/ComfyUI-Anima-Enhancer`](https://github.com/AdamNizol/ComfyUI-Anima-Enhancer)

- Anima 系モデルに対して Replay を適用する発想と、ComfyUI ノードとして扱う出発点を提供してくれたリポジトリです。
- 本リポジトリはこの実装を出発点にしつつ、ノード構成、公開 ID、V3 対応、Spectrum 系の整理を含めて大幅に再構成しています。

### Spectrum implementation reference

[`ruwwww/comfyui-spectrum-sdxl`](https://github.com/ruwwww/comfyui-spectrum-sdxl)

- Spectrum の ComfyUI 実装、パラメータ設計、calibration を含む実験的な運用を考えるうえで参考にしたリポジトリです。
- 本リポジトリでは SDXL 汎用ノードではなく、Anima 系モデル向けの中間特徴予測として構成し直しています。
- そのため、速度や品質の数値は `comfyui-spectrum-sdxl` との優劣比較ではなく、このリポジトリ内の Anima 検証条件での参考値として扱ってください。

### Spectrum paper

Spectrum の元論文:

> Adaptive Spectral Feature Forecasting for Diffusion Sampling Acceleration
> Jiaqi Han, Juntong Shi, Puheng Li, Haotian Ye, Qiushan Guo, Stefano Ermon

- Paper: <https://arxiv.org/abs/2603.01623>
- Project page: <https://hanjq17.github.io/Spectrum/>
- Official code: <https://github.com/hanjq17/Spectrum>

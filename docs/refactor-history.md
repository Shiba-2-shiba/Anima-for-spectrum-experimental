# Refactor History

このドキュメントは、リポジトリ整理のために削除した以下の資料を要約して残すものです。

- `リファクタリング/`
- `参考リポジトリ/`
- `測定結果.txt`
- `Phase2の方向性.txt`
- `baseワークフロー.json`

## Repository Cleanup

整理方針:

- 実装に直接不要な参照リポジトリ、モデル例、作業メモ、ワークフロー実体はリポジトリから除外する
- 残すべき経緯は `docs/` 配下に集約する
- 詳細な比較ログやテンプレートは `docs/context_refactor/` に残す

削除対象に含まれていた内容:

- refactor の phase1 / phase2 仕様、進捗、監査、handoff メモ
- 手元確認用の参考リポジトリと大型 safetensors
- 2026-03-29 時点の測定メモ
- Phase 2 calibration 改善方針メモ
- 比較に使っていた base workflow 実体

## Phase 1 Summary

Phase 1 で確定した内容:

- replay / spectrum / calibration / schedule / model introspection を `core/` へ分離
- 既存の `AnimaLayerReplayPatcher` は `nodes/compat.py` の互換レイヤとして維持
- spectrum state は単一 forecaster から per-sample forecaster 構成へ移行
- `spectrum_stop_caching_step`, `enable_calibration`, `calibration_strength` を互換ノードへ追加
- schedule 正規化は sampler の step 数と 0-based index を区別するよう修正
- Phase 1 の既定 Spectrum 経路は calibration なしの構成を維持

評価上の読み:

- no-op compatibility は baseline と一致した
- Replay only は成立
- Spectrum only は品質低下はあるが、当時の実運用候補として最も素直だった
- calibration は Phase 1 では default-on に上げる根拠が足りなかった

## Phase 2 Summary

Phase 2 で実装した内容:

- `core/intermediate_features.py` を追加
- Anima 系モデルで中間特徴を扱えるか判定する仕組みを追加
- `forward_before_blocks()` 出力の取得、blocks 再実行、`decoder_head()` 呼び出しを実装
- `core/intermediate_spectrum.py` に中間特徴予測 controller と `BaseModel.apply_model` 連携を追加
- same-step observe/apply 型の calibration へ修正
- `latest`, `ema`, `bucketed_ema` の calibration mode を追加
- JSONL step log を `docs/context_refactor/logs/` に出せるようにした
- 現在の main Spectrum node は `Anima for Spectrum` として UI を整理

測定から読めること:

- `enable_spectrum=false` は baseline にほぼ一致
- `warmup_steps=20` の actual-path 相当は baseline 近傍まで戻る
- `warmup_steps=6` の予測経路は大きく崩れる

このため、Phase 2 の主要課題は再構成経路ではなく forecast path の品質である。

## 2026-03-29 Measurement Snapshot

元メモ `測定結果.txt` から残すべき要点:

- A vs B は完全一致
  - `SSIM 1.00000`
  - `MSE 0.000000`
- A vs C は Replay only の成立を確認
  - `SSIM 0.71155`
  - `MSE 0.015268`
- A vs D は Phase 1 Spectrum baseline として記録
  - post-fix `SSIM 0.65972`
  - post-fix `MSE 0.024265`
- A vs E は calibration を足しても D を明確には上回らなかった
  - post-fix `SSIM 0.65254`
  - post-fix `MSE 0.025772`
- A vs F は自動アラインが入っており、視覚確認が必要
  - post-fix `SSIM 0.57558`
  - post-fix `MSE 0.030723`

Phase 2 について元メモから確定できる点:

- `enable_spectrum=false` は `SSIM 0.99930`, `MSE 0.000005`
- `enable_spectrum=true`, `warmup_steps=6` は `SSIM 0.27905`, `MSE 0.146775`
- `enable_spectrum=true`, `warmup_steps=20` は `SSIM 0.99930`, `MSE 0.000005`

元メモの欠点:

- workflow metadata
- image path
- visual review note
- patcher 入力スナップショット

これらは後続の `docs/context_refactor/` のテンプレートで補う前提だった。

## Phase 2 Direction Notes

`Phase2の方向性.txt` から残すべき方針:

- calibration_strength だけ触っても改善しにくい
- 先に same-step の予測誤差を学習する形へ揃える
- どの step / どの特徴で壊れているかを残す step log を優先する
- forecast パラメータと calibration パラメータは同時に動かさず比較する
- 初期比較は `off`, `latest`, `ema`, `bucketed_ema` を同条件で回す
- no-cal を超えるケースが出るまで calibration default は上げない

優先実装として整理されていた項目:

1. same-step calibration へ修正
2. `core/intermediate_spectrum.py` の step-level logging 強化
3. calibration mode の比較
4. 必要なら sampled shadow-actual debug の追加

## Base Workflow Note

`baseワークフロー.json` は比較用の手元 workflow であり、現在はリポジトリから除外した。

今後の扱い:

- rerun に使う workflow は各自のローカル保存物を使う
- 比較記録には workflow の保存先、revision、seed、主要 node 設定を明記する
- 比較手順は `docs/context_refactor/base-workflow-comparison-checklist.md` を使う

## Reference Repository Note

`参考リポジトリ/` には次の用途のローカル参照資産が入っていた。

- ComfyUI 実装確認用 checkout
- 元 Spectrum 実装の参照
- `comfyui-spectrum-sdxl` の比較参照
- Anima / SDXL の大型モデル例

これらは開発時の検証には有用だが、配布用リポジトリには不要なため削除した。

必要になった場合は、再取得する前提とする。

## Remaining Docs

整理後に残す履歴系ドキュメント:

- `docs/context_refactor/README.md`
- `docs/context_refactor/base-workflow-comparison-checklist.md`
- `docs/context_refactor/base-workflow-comparison-record-template.md`
- `docs/context_refactor/base-workflow-comparison-2026-03-29.md`
- `docs/context_refactor/logs/`

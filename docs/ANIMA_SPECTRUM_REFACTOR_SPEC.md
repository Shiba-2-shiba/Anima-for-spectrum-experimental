# ANIMA_SPECTRUM_REFACTOR_SPEC.md

Project: Anima-for-spectrum
Repository: https://github.com/Shiba-2-shiba/Anima-for-spectrum
作成日: 2026-06-02
範囲: Anima/Cosmos 系モデル向け Spectrum 実装のリファクタリング仕様

## 0. 要約

`Anima-for-spectrum` は現在、次の 2 つの公開ノードを持つ。

- `Anima for Replay`: 安定運用向けの Replay 専用ノード
- `Anima for Spectrum`: Spectrum 高速化を狙う実験ノード

構成面では、参考実装である `ComfyUI-Anima-Enhancer` より大きく整理されている。Replay、Spectrum、calibration、ComfyUI V3 schema、legacy replacement は分離済みで、公開パッケージとしての形はできている。

一方、Spectrum の品質はまだ安定していない。現時点の主要仮説は、ComfyUI の登録や wrapper、decode 復元が壊れているのではなく、**Anima/Cosmos 系 DiT で予測すべき feature space をまだ正しく特定できていない**というもの。

このリファクタリングでは、速度改善やパラメータ調整より先に、Anima/Cosmos の内部 topology に基づいて「どの特徴を予測すべきか」を測定できる構造へ変える。

## 1. 現状診断

### 1.1 成立している部分

- Replay runtime は `core/replay.py` と `nodes/compat.py` に分離済み。
- model introspection と stale patch 復元は `core/model_introspection.py` に分離済み。
- Spectrum の Chebyshev/Taylor/ridge 予測器は `core/spectrum.py` に分離済み。
- Phase 2 の中間特徴予測 runtime は `core/intermediate_spectrum.py` に分離済み。
- ComfyUI V3 schema は `v3_nodes.py` に実装済み。
- 旧ノード ID から現行ノード ID への replacement が実装済み。
- `enable_spectrum=false` や高 warmup の actual-heavy 経路は baseline 近傍へ戻るため、wrapper と再構成経路はおおむね成立している可能性が高い。

### 1.2 未解決の部分

記録済みの測定では、低 warmup の Phase 2 forecast が大きく崩れる。

- `enable_spectrum=false`: baseline 近傍 (`SSIM 0.99930`, `MSE 0.000005`)
- `enable_spectrum=true`, `warmup_steps=6`: 大きく劣化 (`SSIM 0.27905`, `MSE 0.146775`)
- `enable_spectrum=true`, `warmup_steps=20`: baseline 近傍へ回復

この結果は、基本実行経路よりも forecast path の品質に問題があることを示している。

### 1.3 SDXL 的前提が疑わしい理由

別リポジトリ `Anima-coceptattention-survey-for-comfyui` では、SDXL/UNet 的な raw cross-attention mass では Anima の挙動をうまく捉えられなかった。その後、`2502.04320v2` の ConceptAttention の考え方を取り入れ、DiT attention の output space に寄せることで実用的な probe へ近づいた。

Spectrum でも同じ構図が疑われる。

```text
高レベルの Spectrum 理論は妥当
+ Anima/Cosmos に合わない特徴空間を予測している
= forecast が不安定になる
```

Spectrum 論文自体は SDXL 専用ではない。問題は理論ではなく、Anima/Cosmos で予測対象にしている内部表現が適切かどうかにある。

## 2. リファクタリング目標

`Anima for Spectrum` を、次の問いに答えられる topology-aware な forecasting framework へ変える。

```text
Anima/Cosmos のどの内部 feature stream が低 drift で予測可能か？
```

この問いに測定で答える前に、forecast で実際の生成経路を置換してはならない。

## 3. 非交渉の制約

### 3.1 Replay を安定面として維持する

`Anima for Replay` は安定ノードとして維持する。Spectrum 側のリファクタリングで Replay の既定値、ノード ID、入力順、挙動を変えない。変更する場合は専用の回帰テストと比較記録を先に用意する。

### 3.2 Spectrum は実験扱いを維持する

`Anima for Spectrum` は、低 warmup の replace run で視覚・数値の安定性が確認されるまで experimental 扱いを維持する。現行の公開 ID `ShibaAnimaForSpectrumExperimental` は妥当であり、安定 ID へ昇格しない。

### 3.3 no-op / actual-path parity を先に固定する

新しい hook、adapter、feature site は必ず次を満たす。

- disabled mode では元の model path を返す。
- observe/shadow mode では生成出力を変えない。
- actual-only mode では baseline と許容誤差内で一致する。

### 3.4 置換前に測定する

新しい forecast 候補は、最初に shadow mode で実行する。

1. actual feature を計算する。
2. 同じ step の forecast feature を計算する。
3. forecast-vs-actual error を JSONL に記録する。
4. 生成には actual output を返す。

replace mode はこの後。

### 3.5 新規依存を増やさない

PyTorch と既存 ComfyUI API を使う。Spectrum や ConceptAttention の参照リポジトリを vendoring しない。

### 3.6 fail closed

topology、tensor shape、block signature、branch layout、dtype/device が検証できない場合は、次の挙動にする。

```text
fail_mode=fallback -> original/actual path を返し、diagnostic record を出す
fail_mode=raise    -> ローカルデバッグ用に例外を投げる
```

## 4. 目標アーキテクチャ

### 4.1 維持する公開レイヤ

次の分離は維持する。

```text
v3_nodes.py
nodes/input_specs.py
nodes/compat.py
nodes/phase2.py
core/replay.py
core/model_introspection.py
```

V3 schema と runtime 実装を再び単一ファイルへ戻さない。

### 4.2 追加または再整理する内部モジュール

推奨する追加構成:

```text
core/
  topology.py
  feature_sites.py
  forecast_shadow.py
  forecast_records.py
  forecast_metrics.py
```

責務:

- `topology.py`: Anima/Cosmos の block topology と forward signature を調べる。
- `feature_sites.py`: 抽出・再構成できる forecast 候補点を定義する。
- `forecast_shadow.py`: 生成を変えずに forecast-vs-actual を測定する。
- `forecast_records.py`: topology、plan、step、fallback の JSONL record を作る。
- `forecast_metrics.py`: rel-L2、MSE、cosine、norm drift、clamp stats を計算する。

既存モジュールは再利用する。

- `core/spectrum.py`: Chebyshev/Taylor/ridge forecaster
- `core/calibration.py`: residual calibration state
- `core/schedule.py`: step 推定と pass reset 判定
- `core/intermediate_features.py`: 現行の中間特徴抽出

### 4.3 Feature site abstraction

大きな framework ではなく、小さな adapter として定義する。

```text
FeatureSite
  id: string
  description: string
  supports(diffusion_model) -> bool
  extract(...) -> FeatureState
  run_actual_from_state(...) -> FeatureState
  decode(...) -> Tensor
```

初期候補:

- `model_output`: 現行 Phase 1 に近い最終 denoiser output。
- `forward_before_blocks`: 現行 Phase 2 の入口。
- `post_selected_block`: 選択した transformer block 後の出力。
- `pre_decoder_head`: `decoder_head()` 直前。
- `attention_output_space`: attention `probs @ v` または projection 近傍の output space。

ConceptAttention 側の教訓から、raw attention や最終 denoiser output よりも、block-level / output-space feature の方が Anima では安定する可能性がある。

### 4.4 Shadow forecast mode

replace の前に内部 mode を追加する。

```text
forecast_mode = off | actual_only | shadow | replace
```

挙動:

- `off`: patch 効果なし。
- `actual_only`: 新しい feature-site 経路を通るが forecast しない。
- `shadow`: actual と forecast を計算し、error を記録し、actual を返す。
- `replace`: forecast step で forecast を使う。

UI では当面 advanced/debug 扱いにする。

### 4.5 JSONL record

既存の debug log 領域を使う。

```text
docs/context_refactor/logs/
```

record type:

```text
anima_spectrum_topology
anima_spectrum_feature_site_plan
anima_spectrum_shadow_step
anima_spectrum_replace_step
anima_spectrum_fallback
anima_spectrum_run_summary
```

step record には最低限次を入れる。

- run ID
- step index / estimated total steps
- timestep / sigma
- feature site ID
- block index / module path
- batch index
- actual / forecast decision
- raw forecast metrics
- calibrated forecast metrics
- dtype / device / shape
- norm / clamp stats
- `w`, `m`, `lam`, `window_size`, `flex_window`
- calibration mode / observation count

### 4.6 Metrics

最低限:

```text
mse
relative_l2
cosine_similarity
actual_norm
forecast_norm
norm_ratio
delta_norm
clip_fraction
```

集計候補:

```text
per_step_mean_rel_l2
per_site_median_rel_l2
per_block_failure_rate
forecast_window_error_growth
calibration_gain
```

### 4.7 Calibration policy

calibration は、shadow run と replace run の両方で no-calibration を上回るまで default-off のままにする。

同一条件で比較する。

- `off`
- `latest`
- `ema`
- `bucketed_ema`

`spectrum_w`、`window_size`、calibration parameter を同じ比較 pass で同時に動かさない。

## 5. 公開ノード方針

公開面は 2 ノードを維持する。

- `Anima for Replay`
- `Anima for Spectrum`

まず advanced/debug input だけを追加する。

```text
forecast_mode
feature_site
target_block_indices
shadow_sample_rate
fail_mode
```

UI が複雑になりすぎる場合は、別ノードを検討する。

```text
Anima Spectrum Diagnostics
```

この diagnostic node は observe-only とし、通常ユーザー向け既定面にしない。

## 6. 検証戦略

### 6.1 static / unit coverage

コード変更前に追加する。

- feature-site selection / fallback
- topology report serialization
- shadow metrics math
- fake model での no-op wrapper parity
- 旧 node ID replacement の登録確認
- legacy `NODE_CLASS_MAPPINGS` の export 確認

### 6.2 Runtime validation

固定 seed、固定 workflow、記録済み node settings で手動検証する。

必須 case:

- baseline, no node
- Replay disabled no-op
- Replay only
- Spectrum `off`
- Spectrum `actual_only`
- Spectrum `shadow`
- Spectrum `replace`

`replace` は shadow metrics で安定 feature site が見つかった後だけ実行する。

### 6.3 Acceptance gates

feature site を replace mode に昇格する条件:

- no-op parity が通る。
- actual-only path が baseline と一致する。
- shadow metrics が少なくとも 2 prompt / seed で安定する。
- visual comparison で明らかな semantic collapse がない。
- low-warmup replace run が許容品質内で runtime を改善する。

## 7. 初期実装順

1. 生成を変えない topology / feature-site diagnostics を追加する。
2. 現行 Phase 2 site に shadow forecast record を追加する。
3. 現行 Phase 2 site と追加候補 site を比較する。
4. drift が最も小さい site を選び、その後に replace test を行う。
5. 安定 site が見つかった後に calibration を再評価する。

## 8. 明示的な非目標

- Spectrum リポジトリ全体を再実装しない。
- full ConceptAttention をこのパッケージ内で再実装しない。
- forecast target の安定性が不明なまま性能最適化しない。
- 1 回の run だけで calibration を default-on にしない。
- Replay と Spectrum を再び 1 つの公開ノードへ統合しない。

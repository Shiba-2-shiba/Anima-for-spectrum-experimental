# ANIMA_SPECTRUM_REFACTOR_PROGRESS.md

Project: Anima-for-spectrum
Repository: https://github.com/Shiba-2-shiba/Anima-for-spectrum
Status: planning artifacts added; implementation not started
Last updated: 2026-06-02

## Current Status

現在のパッケージは構造面では整理されているが、Spectrum 品質はまだ production behavior として扱える段階ではない。

実装状態:

- `Anima for Replay` は安定寄りの replay-only node。
- `Anima for Spectrum` は experimental Spectrum node。
- Spectrum math は Chebyshev/Taylor blend + ridge regression として実装済み。
- Phase 2 は decode 前の intermediate feature を予測する構成。
- `core/intermediate_spectrum.py` に debug logging がある。
- calibration mode は存在するが、default-on にする根拠はまだない。

現在の証拠:

- no-op / actual-path は baseline に近く戻せる。
- low-warmup forecast replacement は大きく画像品質を落とす。
- high-warmup actual-heavy run は baseline-like output に戻る。

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

新しい置換挙動の前に forecast-vs-actual logging を入れる。

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
- shadow forecast mode がまだない。
- candidate feature site 比較用 JSONL schema がまだない。
- このリポジトリには no-op parity / node schema の自動テストがまだない。
- 現在の比較記録には workflow metadata と image path が不足している。

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

## Current Phase

```text
P0 - Planning and scope lock
```

P1-P4 が終わるまで feature replacement 実装へ進まない。

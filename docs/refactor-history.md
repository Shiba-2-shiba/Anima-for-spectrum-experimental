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

## 2026-06-13 Live API Validation

2026-06-13 に ComfyUI 0.24.0 の実機 API で、固定 seed の baseline / no-op / shadow 比較を実行した。

追加した比較用 workflow:

- `docs/context_refactor/workflows/image_anima_base_v1_spectrum_debug.json`
- `docs/context_refactor/workflows/image_anima_base_v1_spectrum_debug(api).json`

実行条件:

- UNET: `anima-base-v1.0.safetensors`
- CLIP: `qwen_3_06b_base.safetensors`
- VAE: `qwen_image_vae.safetensors`
- seed: `875817230929465`
- steps: `30`
- sampler: `er_sde`
- scheduler: `simple`
- resolution: `1024x1024`

確認したケース:

- baseline: `UNETLoader -> KSampler`
- no-op: `UNETLoader -> ShibaAnimaForSpectrumExperimental -> KSampler`, `debug_enable_spectrum=false`
- shadow: `UNETLoader -> ShibaAnimaForSpectrumExperimental -> KSampler`, `forecast_mode=shadow`

結果:

- no-op vs baseline は PNG ピクセル完全一致。
- shadow vs baseline も PNG ピクセル完全一致。
- shadow run は `docs/context_refactor/logs/phase2-20260613T071525.810041Z-run01.jsonl` に 58 件の `shadow` step record を出した。
- shadow log の `raw_vs_actual_rel_l2` は平均 `0.0694`、最大 `0.2320`。
- shadow log の `raw_vs_actual_cosine` は平均 `0.9970`、最小 `0.9753`。

読み:

- 現行 Phase 2 の intermediate-feature reconstruction は、baseline parity を壊さずに shadow 測定へ使える。
- no-op / shadow の parity は確認できたが、replace mode の品質安全性はまだ確認できていない。
- 次は replace ではなく、shadow mode で feature-site 候補と calibration mode を比較する。

後続実装として、JSONL record builder と現行 feature-site 境界を追加した。これにより、次回以降の実機 shadow run では旧来の `event` / `errors` キーを維持しつつ、`record_type=anima_spectrum_topology` と `record_type=anima_spectrum_shadow_step` を基準に解析できる。

再起動後の実機確認では、Anima 実体は `predict2_minidit` path であり、block output を final decode 直前で測定していることが確認できた。そのため、現行 site 名は `forward_before_blocks` ではなく `pre_decoder_head` に直した。

次の候補として `feature_site=post_block` と `target_block_index` を追加した。これは指定 block 後の特徴を shadow 測定し、その後の block と decode は actual path を通す診断用経路である。速度評価や replace 昇格ではなく、step/site ごとの drift 比較を目的にする。

実機 API で `post_block=6/13/20` を比較したところ、全ケースで出力は baseline とピクセル完全一致したが、shadow metric は `pre_decoder_head` より大きく悪化した。現時点では `pre_decoder_head` を主候補として維持し、`post_block` は replace mode に進めない。

続いて `pre_decoder_head` 固定で calibration off / latest / ema / bucketed_ema を shadow 比較した。出力はいずれも baseline とピクセル完全一致したが、enabled calibration は平均 rel-L2 と cosine を改善しなかった。`bucketed_ema` が最も悪化幅は小さいものの、no-calibration を上回らないため `enable_calibration=false` を維持する。

その後、`pre_decoder_head` / calibration off で `spectrum_w` を shadow 比較した。`spectrum_w=0.05` が最も低driftで、`0.20` は悪化した。保守的な replace check では `w=0.05`, `window_size=2`, `warmup_steps=22` が最も baseline に近く、`warmup_steps=20` も次点だった。`warmup_steps=14` は初回品質候補としては差分が大きいため避ける。

目視確認用に 3 seed x baseline/W22/W20/W18 の比較画像とコンタクトシートを生成した。目視上は W18/W20/W22 の差が小さく、許容品質内なら速度が最も速い候補を選ぶ方針にする。初回の API wall-clock timing では `debug_logging=false` でも baseline/W18/W20 がほぼ同等で、replace skip は実時間短縮として観測できなかった。原因は default の自動終盤停止により W18 が 3 step しか forecast していなかったことだった。`spectrum_stop_caching_step=0` で終盤停止を無効化したところ、W18 は 6 step forecast し、平均実行時間は baseline `38.84s` から W18Stop0 `34.82s` に短縮した。したがって、品質/速度の測定済み目標候補は `w=0.05`, `window_size=2`, `warmup_steps=18`, `spectrum_stop_caching_step=0` とする。

ComfyUI 再起動後、`/object_info` で `spectrum_stop_caching_step` の tooltip 更新を確認し、W18Stop0 を 4 prompt/seed で追加検証した。平均は baseline `39.861s`、W18Stop0 `34.845s` で、逆順実行でも W18Stop0 が速かった。コンタクトシート上で明確な破綻はないが、M04 は PSNR `23.282` と最も差分が大きいため、今後の visual regression set に残す。

論文/作者実装との差分を再確認し、`flex_window` の進め方と Taylor 外挿を修正した。作者実装では flexible window は actual forward の後だけ増えるため、毎step増やしていた現行実装は flex 設定で過剰に aggressive だった。また Taylor 側は target step と直近実測 step の距離を使うため、固定 `0.5` 外挿をやめて、最後の2つの実測step間隔から倍率を計算するようにした。

ComfyUI 再起動後、M04 regression prompt で API 比較を実行した。`forecast_mode=shadow` は W18/W14 の両方で baseline とピクセル完全一致し、診断モードとして維持できている。replace では W14F05 が baseline `29.640s` に対して `16.943s` と大きく速いが、PSNR `16.425` / MAE `22.413` まで悪化した。W18Stop0 は `19.466s`, PSNR `22.383`, MAE `8.895` で、速度と品質の現時点の最良バランスを維持した。W18 近辺の flex 追加や W17 は品質が悪化する一方、実時間は W18Stop0 とほぼ同等だったため、`flex_window>0` はまだ推奨候補にしない。

今回の比較記録:

- `docs/context_refactor/flex-window-api-comparison-2026-06-13.md`
- `docs/context_refactor/flex-window-api-refine-2026-06-13.md`
- `docs/context_refactor/flex-window-api-shadow-2026-06-13.md`
- `docs/context_refactor/flex-window-api-predictor-2026-06-13.md`
- `docs/context_refactor/flex-window-api-guard-2026-06-13.md`
- `docs/context_refactor/flex-window-api-damping-2026-06-13.md`
- `docs/context_refactor/visual_review/anima_flex_window_compare_2026-06-13.png`
- `docs/context_refactor/visual_review/anima_flex_window_api_refine_2026-06-13.png`
- `docs/context_refactor/visual_review/anima_flex_window_api_shadow_2026-06-13.png`
- `docs/context_refactor/visual_review/anima_flex_window_api_predictor_2026-06-13.png`
- `docs/context_refactor/visual_review/anima_flex_window_api_guard_2026-06-13.png`
- `docs/context_refactor/visual_review/anima_flex_window_api_damping_2026-06-13.png`

判断として、品質を保つ前提では W18Stop0 を継続採用する。さらなる高速化は W14F05 のように可能だが、現 predictor では multi-step skip の累積差分が大きく、デフォルト昇格には不十分である。次に攻めるなら schedule ではなく、multi-step 予測の品質改善か、終盤だけをより慎重に戻す guard を検討する。

続けて、W18Stop0 採用を固定したまま multi-step 品質改善の小実験を行った。まず W14F05 に対して作者実装寄りの `m=4`, `lam=0.1` と高めの Chebyshev blend (`w=0.2/0.5`) を試したが、PSNR は `17.0-17.3` 付近で、W18Stop0 の `24.398` には届かなかった。次に既存の `spectrum_stop_caching_step` を使い、終盤だけ actual forward に戻す guard を試した。W14F05Stop26 は W18Stop0 とほぼ同じ実時間になったが、PSNR は `19.541` に留まり、W15/W16 の guard も `20.2` 前後だった。

この結果から、単純な `w/m/lam` 調整や late-stop guard では W18Stop0 を超える品質/速度点は見つからなかった。次に進める場合は、予測器内部の外挿モデルを変える必要がある。候補は、multi-step だけ Taylor 成分を縮退させる damping、step gap 別の blend、または residual 予測のような形で、W18Stop0 の 1-step skip を壊さない制約を置く。

その候補のうち、最小変更として `spectrum_taylor_damping` を追加した。default `1.0` は現行動作を保ち、値を下げると Taylor 外挿の差分だけを弱める。M04 regression prompt では W14F05D100 の PSNR `16.345` に対して、D075 `17.144`、D050 `17.747`、D025 `18.046` と単調に改善した。ただし W18Stop0D100 は PSNR `22.903` であり、damping を入れた W14/W16 はまだ採用候補には届かない。したがって damping は実験用 advanced input として残し、default と採用候補は W18Stop0 / damping `1.0` のままとする。

さらに `spectrum_multistep_damping` を追加した。最初は step gap の `k > 1` で判定したが、実機 API では W14F05 の各 multi-step damping 値がピクセル一致し、実際の連続 forecast には効いていなかった。そのため、`num_cached_before + 1` による forecast horizon 判定へ変更した。修正版では W14F05MS100 の PSNR `18.407` に対し、MS075 `18.699`、MS050 `18.951`、MS025 `19.138`、MS000 `19.207` と改善した。W15/W16 の refine でも改善は見えたが、W16F05MS025 は W18Stop0 とほぼ同じ実時間で PSNR `20.693` に留まり、W18Stop0 の品質を超えなかった。

この結果から、multi-step damping は有効な診断・調整ノブだが、採用候補を W18Stop0 から置き換えるには足りない。今後さらに攻めるなら、単純な外挿倍率ではなく、step/site ごとの選択 policy か residual 予測モデル側を変える必要がある。

追加で、Spectrum disabled (`debug_enable_spectrum=false`) を基準に、W18Stop0 と W15F05MS000 を 4 prompt/seed で比較した。平均実行時間は Off `22.239s`、W18Stop0 `19.571s`、W15F05MS000 `16.999s` だった。W15F05MS000 は Off 比で `5.240s`、約 `23.6%` の短縮になり、W18Stop0 よりもさらに `2.572s` 速い。一方、品質指標は W18Stop0 が平均 PSNR `25.865` / MAE `5.509`、W15F05MS000 が平均 PSNR `21.354` / MAE `10.808` で、W15 は W18 より明確に劣化する。特に M04 regression prompt では W18Stop0 が PSNR `21.407` / MAE `10.337`、W15F05MS000 が PSNR `17.984` / MAE `17.924` まで落ちる。

このため、W15F05MS000 は「かなり高速化している」と言えるが、品質維持候補ではなく speed-first/aggressive 候補として扱う。ユーザー目視で許容できる用途では選択肢になるが、デフォルトまたは品質維持プリセットは引き続き W18Stop0 とする。比較記録は `docs/context_refactor/off-w18-w15-multi-prompt-2026-06-13.md` と `docs/context_refactor/visual_review/anima_off_w18_w15_multi_prompt_2026-06-13.png` に保存した。

ユーザー目視でも W18Stop0 が明確に良く、10%台の高速化として実用的という判断になった。W15F05MS000 は速度面では魅力があるが、質の低下が気になるためメイン方針から外す。以後の最適化は W18Stop0 を品質基準として固定し、同等の見た目を保ったまま 1-2 step 分だけ追加で forecast できるかを調べる。具体的には、W18Stop0 の偶数 step skip をベースに、M04 のような高drift promptで破綻しやすい終盤や特定 site は守りつつ、安定しやすい step/site に限定して追加 skip を試す。

この方針に合わせ、空デフォルトの実験用入力 `spectrum_extra_forecast_steps` を追加した。通常は空なので W18Stop0 の schedule は変わらない。値を `23` や `21,25` のような0-based step番号で指定したときだけ、本来 actual になる step を追加で forecast に回す。まず M04 regression prompt で `W18Extra21`, `W18Extra23`, `W18Extra25`, `W18Extra21_25` を比較できるように `run_flex_window_api_comparison.py --case-set extra` を追加した。単体テストと compile は通過したが、実機ComfyUIの `/object_info` には再起動前のため新入力がまだ出ていない。画像比較は再起動後に続行する。

ComfyUI 再起動後、M04 regression prompt で extra step policy を検証した。素の追加stepでは `W18Extra25` が最も良く、W18Stop0 の PSNR `24.724` / MAE `6.704` に対して PSNR `23.607` / MAE `7.750` だった。さらに `W18Extra25` に multi-step damping を組み合わせると、`W18Extra25MS025` が W18Stop0 の PSNR `22.366` / MAE `8.909` に対して PSNR `22.121` / MAE `9.522` まで戻ったため、複数prompt候補にした。

ただし 4 prompt の実用比較では、W18Stop0 が平均 `19.553s` / PSNR `25.865` / MAE `5.509`、W18Extra25MS025 が平均 `19.576s` / PSNR `24.833` / MAE `6.370` だった。つまり速度は改善せず、品質だけ下がった。単純な追加step policy は採用しない。`spectrum_extra_forecast_steps` は今後の診断用 advanced input として残すが、空デフォルトの W18Stop0 を実用候補として維持する。

次の方針として、W18Stop0 の既存 6 forecast step を変える前に、debug JSONL に内部 timing を出す計測を追加した。`debug_logging=true` のときだけ CUDA 同期込みで `actual_feature_ms`, `raw_guess_ms`, `calibration_apply_ms`, `forecast_cast_ms`, `forecaster_update_ms`, `path_total_ms` を記録する。通常生成では logging off のため影響しない。`run_flex_window_api_comparison.py --case-set w18profile` では replace mode の W18Stop0 で時間内訳を見て、shadow mode の W18Stop0 で step ごとの forecast-vs-actual worst error を見る。これにより、次に速度改善へ進むべきか、特定 step の品質安定化へ進むべきかを判断する。

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

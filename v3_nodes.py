try:
    from comfy_api.latest import ComfyAPI, ComfyExtension, io
except ImportError as exc:
    raise

api = ComfyAPI()

try:
    from .nodes.compat import AnimaLayerReplayPatcher
    from .nodes.phase2 import AnimaIntermediateSpectrumPatcher
    from .nodes.input_specs import (
        ANIMA_ESSENTIALS_CATEGORY,
        ANIMA_NODE_CATEGORY,
        COMPAT_NODE_DESCRIPTION,
        COMPAT_NODE_DISPLAY_NAME,
        COMPAT_NODE_ID,
        COMPAT_NODE_SEARCH_ALIASES,
        LEGACY_COMPAT_NODE_ID,
        LEGACY_PUBLIC_COMPAT_NODE_ID,
        LEGACY_PHASE2_NODE_ID,
        PHASE2_NODE_DESCRIPTION,
        PHASE2_NODE_DISPLAY_NAME,
        PHASE2_NODE_ID,
        PHASE2_NODE_SEARCH_ALIASES,
        SPECTRUM_PRESET_CHOICES,
        SPECTRUM_PRESET_MANUAL,
        SPECTRUM_PRESET_W18_STOP0,
    )
except ImportError:
    from nodes.compat import AnimaLayerReplayPatcher
    from nodes.phase2 import AnimaIntermediateSpectrumPatcher
    from nodes.input_specs import (
        ANIMA_ESSENTIALS_CATEGORY,
        ANIMA_NODE_CATEGORY,
        COMPAT_NODE_DESCRIPTION,
        COMPAT_NODE_DISPLAY_NAME,
        COMPAT_NODE_ID,
        COMPAT_NODE_SEARCH_ALIASES,
        LEGACY_COMPAT_NODE_ID,
        LEGACY_PUBLIC_COMPAT_NODE_ID,
        LEGACY_PHASE2_NODE_ID,
        PHASE2_NODE_DESCRIPTION,
        PHASE2_NODE_DISPLAY_NAME,
        PHASE2_NODE_ID,
        PHASE2_NODE_SEARCH_ALIASES,
        SPECTRUM_PRESET_CHOICES,
        SPECTRUM_PRESET_MANUAL,
        SPECTRUM_PRESET_W18_STOP0,
    )


class AnimaForReplayNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id=COMPAT_NODE_ID,
            display_name=COMPAT_NODE_DISPLAY_NAME,
            category=ANIMA_NODE_CATEGORY,
            description=COMPAT_NODE_DESCRIPTION,
            search_aliases=COMPAT_NODE_SEARCH_ALIASES,
            essentials_category=ANIMA_ESSENTIALS_CATEGORY,
            inputs=[
                io.Model.Input("model", tooltip="サンプリング中にパッチを適用する対象モデルです。"),
                io.Boolean.Input("enable_replay", display_name="Replay", default=True, tooltip="指定した denoise 範囲でブロックの再実行を有効にします。"),
                io.String.Input("block_indices", display_name="Replay Blocks", default="3,4,5", tooltip="再実行するブロック番号です。例: 3,4,5 または 3-5,8"),
                io.Float.Input("denoise_start_pct", display_name="Replay Start", default=0.50, min=0.0, max=1.0, step=0.01, tooltip="Replay を開始する denoise 進行率です。"),
                io.Float.Input("denoise_end_pct", display_name="Replay End", default=1.00, min=0.0, max=1.0, step=0.01, tooltip="Replay を終了する denoise 進行率です。"),
            ],
            outputs=[
                io.Model.Output(display_name="patched_model"),
            ],
        )

    @classmethod
    def execute(
        cls,
        model,
        enable_replay: bool,
        block_indices: str,
        denoise_start_pct: float,
        denoise_end_pct: float,
    ) -> io.NodeOutput:
        patched_model, = AnimaLayerReplayPatcher().patch(
            model=model,
            enable_replay=enable_replay,
            block_indices=block_indices,
            denoise_start_pct=denoise_start_pct,
            denoise_end_pct=denoise_end_pct,
        )
        return io.NodeOutput(patched_model)


class AnimaForSpectrumNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id=PHASE2_NODE_ID,
            display_name=PHASE2_NODE_DISPLAY_NAME,
            category=ANIMA_NODE_CATEGORY,
            description=PHASE2_NODE_DESCRIPTION,
            search_aliases=PHASE2_NODE_SEARCH_ALIASES,
            essentials_category=ANIMA_ESSENTIALS_CATEGORY,
            inputs=[
                io.Model.Input("model", tooltip="Spectrum パッチを適用するクリーンなモデル入力です。"),
                io.Combo.Input("spectrum_preset", SPECTRUM_PRESET_CHOICES, display_name="Spectrum Preset", default=SPECTRUM_PRESET_W18_STOP0, tooltip="測定済みプリセットです。W18Stop0 は品質優先の第一候補、W15F05MS000 は速度優先の第二候補です。Manual は下の詳細値をそのまま使います。"),
                io.Float.Input("spectrum_w", display_name="Blend", default=0.05, min=0.0, max=1.0, step=0.01, tooltip="画質と速度のバランスです。W18Stop0/W15F05MS000 は 0.05 を使います。", advanced=True),
                io.Int.Input("spectrum_warmup_steps", display_name="Warmup", default=18, min=0, max=50, step=1, tooltip="予測を始める前に実測するステップ数です。W18Stop0 は 18、W15F05MS000 は 15 です。", advanced=True),
                io.Int.Input("spectrum_window_size", display_name="Forecast Window", default=2, min=1, step=1, tooltip="実際に特徴を計算する間隔です。大きいほど高速ですが、ズレやすくなります。", advanced=True),
                io.Boolean.Input("enable_calibration", display_name="Residual Calibration", default=False, tooltip="予測誤差を補正する処理を有効にします。オフのときは下の Calibration 設定は無視されます。", advanced=True),
                io.Float.Input("calibration_strength", display_name="Calibration Strength", default=0.35, min=0.0, max=1.0, step=0.05, tooltip="Calibration 有効時に補正をどれだけ強く反映するかです。", advanced=True),
                io.Combo.Input("calibration_mode", ["latest", "ema", "bucketed_ema"], display_name="Calibration Mode", default="ema", tooltip="補正値の蓄積方法です。", advanced=True),
                io.Int.Input("spectrum_m", display_name="Chebyshev Order", default=16, min=1, max=32, step=1, tooltip="予測器で使う多項式の次数です。", advanced=True),
                io.Float.Input("spectrum_lam", display_name="Ridge Lambda", default=0.50, min=0.0, max=100.0, step=0.01, tooltip="係数フィッティング時の正則化の強さです。", advanced=True),
                io.Float.Input("spectrum_taylor_damping", display_name="Taylor Damping", default=1.0, min=0.0, max=1.0, step=0.05, tooltip="Taylor 外挿の強さです。1.0 で現行動作、低いほど外挿を弱めます。", advanced=True),
                io.Float.Input("spectrum_multistep_damping", display_name="Multi-step Damping", default=1.0, min=0.0, max=1.0, step=0.05, tooltip="複数ステップ先を予測するときだけ Taylor 外挿の追加分を弱めます。1.0 で現行動作です。", advanced=True),
                io.Float.Input("spectrum_flex_window", display_name="Flex Window", default=0.0, min=0.0, max=1.0, step=0.01, tooltip="Warmup 後に予測ウィンドウを追加で広げる量です。W15F05MS000 は 0.5 です。", advanced=True),
                io.Int.Input("spectrum_stop_caching_step", display_name="Stop Forecast Step", default=0, min=-1, max=200, step=1, tooltip="予測を止める最終ステップです。W18Stop0/W15F05MS000 は 0 で終盤停止なしです。-1 で終盤を自動停止します。", advanced=True),
                io.String.Input("spectrum_extra_forecast_steps", display_name="Extra Forecast Steps", default="", tooltip="追加で予測に回す0-basedステップ番号です。例: 23 または 21,25。空なら通常スケジュールです。", advanced=True),
                io.Float.Input("calibration_decay", display_name="Calibration Decay", default=0.90, min=0.0, max=0.999, step=0.01, tooltip="ema / bucketed_ema で使う減衰率です。", advanced=True),
                io.Int.Input("calibration_buckets", display_name="Calibration Buckets", default=4, min=1, max=16, step=1, tooltip="bucketed_ema で使う進行率バケット数です。", advanced=True),
                io.Int.Input("calibration_min_obs", display_name="Calibration Min Obs", default=2, min=1, max=64, step=1, tooltip="Calibration を開始するのに必要な最小観測数です。", advanced=True),
                io.Boolean.Input("debug_enable_spectrum", display_name="Enable Forecasting (Debug)", default=True, tooltip="内部デバッグ用の互換スイッチです。調査時以外はオンのままにしてください。", advanced=True),
                io.Combo.Input("feature_site", ["pre_decoder_head", "post_block"], display_name="Feature Site", default="pre_decoder_head", tooltip="shadow 比較で測定する特徴位置です。post_block は Target Block を使います。", advanced=True),
                io.Int.Input("target_block_index", display_name="Target Block", default=13, min=0, max=200, step=1, tooltip="feature_site=post_block のときに測定する block index です。", advanced=True),
                io.Combo.Input("forecast_mode", ["replace", "shadow", "actual_only"], display_name="Forecast Mode", default="replace", tooltip="replace は予測を生成へ反映し、shadow は生成を変えずに予測誤差だけ記録します。", advanced=True),
                io.Boolean.Input("debug_logging", display_name="Debug Logging", default=False, tooltip="docs/context_refactor/logs/ に JSONL のステップログを書き出します。", advanced=True),
            ],
            outputs=[
                io.Model.Output(display_name="patched_model"),
            ],
        )

    @classmethod
    def execute(
        cls,
        model,
        spectrum_preset: str,
        debug_enable_spectrum: bool,
        spectrum_w: float,
        spectrum_warmup_steps: int,
        spectrum_window_size: int,
        enable_calibration: bool,
        calibration_strength: float,
        calibration_mode: str,
        spectrum_m: int,
        spectrum_lam: float,
        spectrum_taylor_damping: float,
        spectrum_multistep_damping: float,
        spectrum_flex_window: float,
        spectrum_stop_caching_step: int,
        spectrum_extra_forecast_steps: str,
        calibration_decay: float,
        calibration_buckets: int,
        calibration_min_obs: int,
        feature_site: str,
        target_block_index: int,
        forecast_mode: str,
        debug_logging: bool,
    ) -> io.NodeOutput:
        patched_model, = AnimaIntermediateSpectrumPatcher().patch(
            model=model,
            spectrum_preset=spectrum_preset,
            debug_enable_spectrum=debug_enable_spectrum,
            spectrum_w=spectrum_w,
            spectrum_warmup_steps=spectrum_warmup_steps,
            spectrum_window_size=spectrum_window_size,
            enable_calibration=enable_calibration,
            calibration_strength=calibration_strength,
            calibration_mode=calibration_mode,
            spectrum_m=spectrum_m,
            spectrum_lam=spectrum_lam,
            spectrum_taylor_damping=spectrum_taylor_damping,
            spectrum_multistep_damping=spectrum_multistep_damping,
            spectrum_flex_window=spectrum_flex_window,
            spectrum_stop_caching_step=spectrum_stop_caching_step,
            spectrum_extra_forecast_steps=spectrum_extra_forecast_steps,
            calibration_decay=calibration_decay,
            calibration_buckets=calibration_buckets,
            calibration_min_obs=calibration_min_obs,
            feature_site=feature_site,
            target_block_index=target_block_index,
            forecast_mode=forecast_mode,
            debug_logging=debug_logging,
        )
        return io.NodeOutput(patched_model)


async def register_replacements() -> None:
    replay_widget_ids = [
        "enable_replay",
        "block_indices",
        "denoise_start_pct",
        "denoise_end_pct",
        "enable_spectrum",
        "spectrum_w",
        "spectrum_m",
        "spectrum_lam",
        "spectrum_warmup_steps",
        "spectrum_window_size",
        "spectrum_flex_window",
        "spectrum_stop_caching_step",
        "enable_calibration",
        "calibration_strength",
    ]
    replay_input_mapping = [
        {"new_id": "model", "old_id": "model"},
        {"new_id": "enable_replay", "old_id": "enable_replay"},
        {"new_id": "block_indices", "old_id": "block_indices"},
        {"new_id": "denoise_start_pct", "old_id": "denoise_start_pct"},
        {"new_id": "denoise_end_pct", "old_id": "denoise_end_pct"},
    ]

    await api.node_replacement.register(
        io.NodeReplace(
            new_node_id=COMPAT_NODE_ID,
            old_node_id=LEGACY_COMPAT_NODE_ID,
            old_widget_ids=replay_widget_ids,
            input_mapping=replay_input_mapping,
            output_mapping=[
                {"new_idx": 0, "old_idx": 0},
            ],
        )
    )

    await api.node_replacement.register(
        io.NodeReplace(
            new_node_id=COMPAT_NODE_ID,
            old_node_id=LEGACY_PUBLIC_COMPAT_NODE_ID,
            old_widget_ids=replay_widget_ids,
            input_mapping=replay_input_mapping,
            output_mapping=[
                {"new_idx": 0, "old_idx": 0},
            ],
        )
    )

    await api.node_replacement.register(
        io.NodeReplace(
            new_node_id=PHASE2_NODE_ID,
            old_node_id=LEGACY_PHASE2_NODE_ID,
            old_widget_ids=[
                "enable_spectrum",
                "spectrum_w",
                "spectrum_m",
                "spectrum_lam",
                "spectrum_taylor_damping",
                "spectrum_multistep_damping",
                "spectrum_warmup_steps",
                "spectrum_window_size",
                "spectrum_flex_window",
                "spectrum_stop_caching_step",
                "spectrum_extra_forecast_steps",
                "enable_calibration",
                "calibration_strength",
                "calibration_mode",
                "calibration_decay",
                "calibration_buckets",
                "calibration_min_obs",
                "feature_site",
                "target_block_index",
                "forecast_mode",
                "debug_logging",
            ],
            input_mapping=[
                {"new_id": "model", "old_id": "model"},
                {"new_id": "spectrum_preset", "set_value": SPECTRUM_PRESET_MANUAL},
                {"new_id": "debug_enable_spectrum", "set_value": True},
                {"new_id": "spectrum_w", "old_id": "spectrum_w"},
                {"new_id": "spectrum_warmup_steps", "old_id": "spectrum_warmup_steps"},
                {"new_id": "spectrum_window_size", "old_id": "spectrum_window_size"},
                {"new_id": "enable_calibration", "old_id": "enable_calibration"},
                {"new_id": "calibration_strength", "old_id": "calibration_strength"},
                {"new_id": "calibration_mode", "old_id": "calibration_mode"},
                {"new_id": "spectrum_m", "old_id": "spectrum_m"},
                {"new_id": "spectrum_lam", "old_id": "spectrum_lam"},
                {"new_id": "spectrum_taylor_damping", "set_value": 1.0},
                {"new_id": "spectrum_multistep_damping", "set_value": 1.0},
                {"new_id": "spectrum_flex_window", "old_id": "spectrum_flex_window"},
                {"new_id": "spectrum_stop_caching_step", "old_id": "spectrum_stop_caching_step"},
                {"new_id": "spectrum_extra_forecast_steps", "set_value": ""},
                {"new_id": "calibration_decay", "old_id": "calibration_decay"},
                {"new_id": "calibration_buckets", "old_id": "calibration_buckets"},
                {"new_id": "calibration_min_obs", "old_id": "calibration_min_obs"},
                {"new_id": "feature_site", "set_value": "pre_decoder_head"},
                {"new_id": "target_block_index", "set_value": 13},
                {"new_id": "forecast_mode", "set_value": "replace"},
                {"new_id": "debug_logging", "old_id": "debug_logging"},
            ],
            output_mapping=[
                {"new_idx": 0, "old_idx": 0},
            ],
        )
    )


class AnimaForSpectrumExtension(ComfyExtension):
    async def on_load(self) -> None:
        await register_replacements()

    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [AnimaForReplayNode, AnimaForSpectrumNode]


async def comfy_entrypoint() -> AnimaForSpectrumExtension:
    return AnimaForSpectrumExtension()

"""Shared metadata and input specs for Anima-for-spectrum nodes."""

ANIMA_NODE_CATEGORY = "model/patches/anima-for-spectrum"
ANIMA_ESSENTIALS_CATEGORY = "Model Patches"

COMPAT_NODE_ID = "ShibaAnimaForReplay"
COMPAT_NODE_DISPLAY_NAME = "Anima for Replay"
COMPAT_NODE_DESCRIPTION = (
    "対応する Anima/Cosmos 系モデル向けの安定した Replay 専用パッチです。"
    "Spectrum 予測を使わず、元の Replay 動作だけを使いたいときに使います。"
)
COMPAT_NODE_SEARCH_ALIASES = [
    "anima for replay",
    "anima replay",
    "anima enhancer",
    "anima layer replay patcher",
]

PHASE2_NODE_ID = "ShibaAnimaForSpectrumExperimental"
PHASE2_NODE_DISPLAY_NAME = "Anima for Spectrum"
PHASE2_NODE_DESCRIPTION = (
    "対応する Anima 系モデル向けのメイン Spectrum パッチです。"
    "通常利用ではこのノードを使い、細かい調整が必要なときだけ Advanced を開いてください。"
)
PHASE2_NODE_SEARCH_ALIASES = [
    "anima intermediate spectrum patcher",
    "anima phase2",
    "anima for spectrum",
    "anima for spectrum experimental",
    "intermediate spectrum",
]

LEGACY_COMPAT_NODE_ID = "AnimaLayerReplayPatcher"
LEGACY_PHASE2_NODE_ID = "AnimaIntermediateSpectrumPatcher"
LEGACY_PUBLIC_COMPAT_NODE_ID = "ShibaAnimaForSpectrum"

SPECTRUM_PRESET_W18_STOP0 = "W18Stop0"
SPECTRUM_PRESET_W15_F05_MS000 = "W15F05MS000"
SPECTRUM_PRESET_MANUAL = "Manual"
SPECTRUM_PRESET_CHOICES = [
    SPECTRUM_PRESET_W18_STOP0,
    SPECTRUM_PRESET_W15_F05_MS000,
    SPECTRUM_PRESET_MANUAL,
]


def build_compat_input_types() -> dict:
    return {
        "required": {
            "model": ("MODEL",),
            "enable_replay": (
                "BOOLEAN",
                {
                    "default": True,
                    "tooltip": "指定した denoise 範囲でブロックの再実行を有効にします。",
                },
            ),
            "block_indices": (
                "STRING",
                {
                    "default": "3,4,5",
                    "multiline": False,
                    "tooltip": "再実行するブロック番号です。例: 3,4,5 または 3-5,8",
                },
            ),
            "denoise_start_pct": (
                "FLOAT",
                {
                    "default": 0.50,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "Replay を開始する denoise 進行率です。",
                },
            ),
            "denoise_end_pct": (
                "FLOAT",
                {
                    "default": 1.00,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "Replay を終了する denoise 進行率です。",
                },
            ),
        }
    }


def build_phase2_input_types() -> dict:
    required = {
        "model": ("MODEL",),
        "spectrum_preset": (
            SPECTRUM_PRESET_CHOICES,
            {
                "default": SPECTRUM_PRESET_W18_STOP0,
                "tooltip": (
                    "測定済みプリセットです。W18Stop0 は品質優先の第一候補、"
                    "W15F05MS000 は速度優先の第二候補です。Manual は下の詳細値をそのまま使います。"
                ),
            },
        ),
        "spectrum_w": (
            "FLOAT",
            {
                "default": 0.05,
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "tooltip": "画質と速度のバランスです。W18Stop0/W15F05MS000 は 0.05 を使います。",
            },
        ),
        "spectrum_warmup_steps": (
            "INT",
            {
                "default": 18,
                "min": 0,
                "max": 50,
                "step": 1,
                "tooltip": "予測を始める前に実測するステップ数です。W18Stop0 は 18、W15F05MS000 は 15 です。",
            },
        ),
        "spectrum_window_size": (
            "INT",
            {
                "default": 2,
                "min": 1,
                "step": 1,
                "tooltip": "実際に特徴を計算する間隔です。大きいほど高速ですが、ズレやすくなります。",
            },
        ),
        "enable_calibration": (
            "BOOLEAN",
            {
                "default": False,
                "tooltip": "予測誤差を補正する処理を有効にします。オフのときは下の Calibration 設定は無視されます。",
            },
        ),
        "calibration_strength": (
            "FLOAT",
            {
                "default": 0.35,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "tooltip": "Calibration 有効時に補正をどれだけ強く反映するかです。",
            },
        ),
        "calibration_mode": (
            ["latest", "ema", "bucketed_ema"],
            {
                "default": "ema",
                "tooltip": "補正値の蓄積方法です。",
            },
        ),
        "spectrum_m": (
            "INT",
            {
                "default": 16,
                "min": 1,
                "max": 32,
                "step": 1,
                "advanced": True,
                "tooltip": "予測器で使う多項式の次数です。",
            },
        ),
        "spectrum_lam": (
            "FLOAT",
            {
                "default": 0.50,
                "min": 0.0,
                "max": 100.0,
                "step": 0.01,
                "advanced": True,
                "tooltip": "係数フィッティング時の正則化の強さです。",
            },
        ),
        "spectrum_taylor_damping": (
            "FLOAT",
            {
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "advanced": True,
                "tooltip": "Taylor 外挿の強さです。1.0 で現行動作、低いほど外挿を弱めます。",
            },
        ),
        "spectrum_multistep_damping": (
            "FLOAT",
            {
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "advanced": True,
                "tooltip": "複数ステップ先を予測するときだけ Taylor 外挿の追加分を弱めます。1.0 で現行動作です。",
            },
        ),
        "spectrum_flex_window": (
            "FLOAT",
            {
                "default": 0.0,
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "advanced": True,
                "tooltip": "Warmup 後に予測ウィンドウを追加で広げる量です。W15F05MS000 は 0.5 です。",
            },
        ),
        "spectrum_stop_caching_step": (
            "INT",
            {
                "default": 0,
                "min": -1,
                "max": 200,
                "step": 1,
                "advanced": True,
                "tooltip": "予測を止める最終ステップです。W18Stop0/W15F05MS000 は 0 で終盤停止なしです。-1 で終盤を自動停止します。",
            },
        ),
        "spectrum_extra_forecast_steps": (
            "STRING",
            {
                "default": "",
                "multiline": False,
                "advanced": True,
                "tooltip": "追加で予測に回す0-basedステップ番号です。例: 23 または 21,25。空なら通常スケジュールです。",
            },
        ),
        "calibration_decay": (
            "FLOAT",
            {
                "default": 0.90,
                "min": 0.0,
                "max": 0.999,
                "step": 0.01,
                "advanced": True,
                "tooltip": "ema / bucketed_ema で使う減衰率です。",
            },
        ),
        "calibration_buckets": (
            "INT",
            {
                "default": 4,
                "min": 1,
                "max": 16,
                "step": 1,
                "advanced": True,
                "tooltip": "bucketed_ema で使う進行率バケット数です。",
            },
        ),
        "calibration_min_obs": (
            "INT",
            {
                "default": 2,
                "min": 1,
                "max": 64,
                "step": 1,
                "advanced": True,
                "tooltip": "Calibration を開始するのに必要な最小観測数です。",
            },
        ),
        "debug_enable_spectrum": (
            "BOOLEAN",
            {
                "default": True,
                "advanced": True,
                "tooltip": "内部デバッグ用の互換スイッチです。調査時以外はオンのままにしてください。",
            },
        ),
        "feature_site": (
            ["pre_decoder_head", "post_block"],
            {
                "default": "pre_decoder_head",
                "advanced": True,
                "tooltip": "shadow 比較で測定する特徴位置です。post_block は target_block_index を使います。",
            },
        ),
        "target_block_index": (
            "INT",
            {
                "default": 13,
                "min": 0,
                "max": 200,
                "step": 1,
                "advanced": True,
                "tooltip": "feature_site=post_block のときに測定する block index です。",
            },
        ),
        "forecast_mode": (
            ["replace", "shadow", "actual_only"],
            {
                "default": "replace",
                "advanced": True,
                "tooltip": "replace は予測を生成へ反映し、shadow は生成を変えずに予測誤差だけ記録します。",
            },
        ),
        "debug_logging": (
            "BOOLEAN",
            {
                "default": False,
                "advanced": True,
                "tooltip": "docs/context_refactor/logs/ に JSONL のステップログを書き出します。",
            },
        ),
    }
    return {"required": required}

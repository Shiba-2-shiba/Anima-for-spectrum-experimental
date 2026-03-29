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
        "spectrum_w": (
            "FLOAT",
            {
                "default": 0.10,
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "tooltip": "画質と速度のバランスです。低いほど安全寄り、高いほど攻めた設定です。",
            },
        ),
        "spectrum_warmup_steps": (
            "INT",
            {
                "default": 6,
                "min": 0,
                "max": 50,
                "step": 1,
                "tooltip": "予測を始める前に実測するステップ数です。",
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
        "spectrum_flex_window": (
            "FLOAT",
            {
                "default": 0.0,
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "advanced": True,
                "tooltip": "Warmup 後に予測ウィンドウを追加で広げる量です。",
            },
        ),
        "spectrum_stop_caching_step": (
            "INT",
            {
                "default": -1,
                "min": -1,
                "max": 200,
                "step": 1,
                "advanced": True,
                "tooltip": "予測を止める最終ステップです。-1 で自動停止になります。",
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

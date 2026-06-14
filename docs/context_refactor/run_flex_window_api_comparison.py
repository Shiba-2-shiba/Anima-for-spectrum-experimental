import argparse
import json
import math
import time
import urllib.error
import urllib.request
import uuid
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops
from PIL import ImageDraw


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / "docs" / "context_refactor" / "workflows" / "image_anima_base_v1_spectrum_debug(api).json"
OUTPUT_DIR = Path(r"C:\ComfyUI\output")
LOG_DIR = ROOT / "docs" / "context_refactor" / "logs"
REPORT_DIR = ROOT / "docs" / "context_refactor"
VISUAL_DIR = REPORT_DIR / "visual_review"

PROMPT_M04 = (
    "Anime wide portrait of a cybernetic priestess in a cathedral server room, luminous mechanical halo, "
    "porcelain face plates, black cables like stained glass, blue white monochrome lighting, precise ink hatching, "
    "high detail sci fi ornament"
)
NEGATIVE_PROMPT = "worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, sepia"


INITIAL_CASES = [
    {
        "id": "Baseline",
        "prefix": "AnimaFlex_M04_Baseline",
        "mode": "baseline",
        "debug_logging": False,
    },
    {
        "id": "W14F05Debug",
        "prefix": "AnimaFlex_M04_W14F05Debug",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "debug_logging": True,
    },
    {
        "id": "W18Stop0",
        "prefix": "AnimaFlex_M04_W18Stop0",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "debug_logging": False,
    },
    {
        "id": "W16F05",
        "prefix": "AnimaFlex_M04_W16F05",
        "mode": "replace",
        "warmup": 16,
        "flex": 0.5,
        "debug_logging": False,
    },
    {
        "id": "W14F05",
        "prefix": "AnimaFlex_M04_W14F05",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "debug_logging": False,
    },
    {
        "id": "W12F05",
        "prefix": "AnimaFlex_M04_W12F05",
        "mode": "replace",
        "warmup": 12,
        "flex": 0.5,
        "debug_logging": False,
    },
]

REFINE_CASES = [
    {
        "id": "Baseline",
        "prefix": "AnimaFlexRefine_M04_Baseline",
        "mode": "baseline",
        "debug_logging": False,
    },
    {
        "id": "W18F025Debug",
        "prefix": "AnimaFlexRefine_M04_W18F025Debug",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.25,
        "debug_logging": True,
    },
    {
        "id": "W18F025",
        "prefix": "AnimaFlexRefine_M04_W18F025",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.25,
        "debug_logging": False,
    },
    {
        "id": "W18F05",
        "prefix": "AnimaFlexRefine_M04_W18F05",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.5,
        "debug_logging": False,
    },
    {
        "id": "W17F00",
        "prefix": "AnimaFlexRefine_M04_W17F00",
        "mode": "replace",
        "warmup": 17,
        "flex": 0.0,
        "debug_logging": False,
    },
    {
        "id": "W17F025",
        "prefix": "AnimaFlexRefine_M04_W17F025",
        "mode": "replace",
        "warmup": 17,
        "flex": 0.25,
        "debug_logging": False,
    },
]

SHADOW_CASES = [
    {
        "id": "Baseline",
        "prefix": "AnimaFlexShadow_M04_Baseline",
        "mode": "baseline",
        "debug_logging": False,
    },
    {
        "id": "ShadowW18F00",
        "prefix": "AnimaFlexShadow_M04_W18F00",
        "mode": "shadow",
        "warmup": 18,
        "flex": 0.0,
        "debug_logging": True,
    },
    {
        "id": "ShadowW14F05",
        "prefix": "AnimaFlexShadow_M04_W14F05",
        "mode": "shadow",
        "warmup": 14,
        "flex": 0.5,
        "debug_logging": True,
    },
]

PREDICTOR_CASES = [
    {
        "id": "Baseline",
        "prefix": "AnimaPredictor_M04_Baseline",
        "mode": "baseline",
        "debug_logging": False,
    },
    {
        "id": "W18Stop0",
        "prefix": "AnimaPredictor_M04_W18Stop0",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "debug_logging": False,
    },
    {
        "id": "W14F05Current",
        "prefix": "AnimaPredictor_M04_W14F05Current",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "debug_logging": True,
    },
    {
        "id": "W14F05M4L01W005",
        "prefix": "AnimaPredictor_M04_W14F05M4L01W005",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "w": 0.05,
        "m": 4,
        "lam": 0.1,
        "debug_logging": False,
    },
    {
        "id": "W14F05M4L01W02",
        "prefix": "AnimaPredictor_M04_W14F05M4L01W02",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "w": 0.2,
        "m": 4,
        "lam": 0.1,
        "debug_logging": False,
    },
    {
        "id": "W14F05M4L01W05",
        "prefix": "AnimaPredictor_M04_W14F05M4L01W05",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "w": 0.5,
        "m": 4,
        "lam": 0.1,
        "debug_logging": False,
    },
    {
        "id": "W14F05M8L01W02",
        "prefix": "AnimaPredictor_M04_W14F05M8L01W02",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "w": 0.2,
        "m": 8,
        "lam": 0.1,
        "debug_logging": False,
    },
]

GUARD_CASES = [
    {
        "id": "Baseline",
        "prefix": "AnimaGuard_M04_Baseline",
        "mode": "baseline",
        "debug_logging": False,
    },
    {
        "id": "W18Stop0",
        "prefix": "AnimaGuard_M04_W18Stop0",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "debug_logging": False,
    },
    {
        "id": "W14F05Stop24",
        "prefix": "AnimaGuard_M04_W14F05Stop24",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "stop": 24,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "debug_logging": True,
    },
    {
        "id": "W14F05Stop26",
        "prefix": "AnimaGuard_M04_W14F05Stop26",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "stop": 26,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "debug_logging": True,
    },
    {
        "id": "W15F05Stop26",
        "prefix": "AnimaGuard_M04_W15F05Stop26",
        "mode": "replace",
        "warmup": 15,
        "flex": 0.5,
        "stop": 26,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "debug_logging": False,
    },
    {
        "id": "W16F05Stop26",
        "prefix": "AnimaGuard_M04_W16F05Stop26",
        "mode": "replace",
        "warmup": 16,
        "flex": 0.5,
        "stop": 26,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "debug_logging": False,
    },
]

DAMPING_CASES = [
    {
        "id": "Baseline",
        "prefix": "AnimaDamping_M04_Baseline",
        "mode": "baseline",
        "debug_logging": False,
    },
    {
        "id": "W18Stop0D100",
        "prefix": "AnimaDamping_M04_W18Stop0D100",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "debug_logging": False,
    },
    {
        "id": "W14F05D100",
        "prefix": "AnimaDamping_M04_W14F05D100",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "debug_logging": True,
    },
    {
        "id": "W14F05D075",
        "prefix": "AnimaDamping_M04_W14F05D075",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 0.75,
        "debug_logging": False,
    },
    {
        "id": "W14F05D050",
        "prefix": "AnimaDamping_M04_W14F05D050",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 0.5,
        "debug_logging": False,
    },
    {
        "id": "W14F05D025",
        "prefix": "AnimaDamping_M04_W14F05D025",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 0.25,
        "debug_logging": False,
    },
    {
        "id": "W16F05D050",
        "prefix": "AnimaDamping_M04_W16F05D050",
        "mode": "replace",
        "warmup": 16,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 0.5,
        "debug_logging": False,
    },
]

GAP_DAMPING_CASES = [
    {
        "id": "Baseline",
        "prefix": "AnimaGapDamping_M04_Baseline",
        "mode": "baseline",
        "debug_logging": False,
    },
    {
        "id": "W18Stop0MS000",
        "prefix": "AnimaGapDamping_M04_W18Stop0MS000",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.0,
        "debug_logging": False,
    },
    {
        "id": "W14F05MS100",
        "prefix": "AnimaGapDamping_M04_W14F05MS100",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 1.0,
        "debug_logging": True,
    },
    {
        "id": "W14F05MS075",
        "prefix": "AnimaGapDamping_M04_W14F05MS075",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.75,
        "debug_logging": False,
    },
    {
        "id": "W14F05MS050",
        "prefix": "AnimaGapDamping_M04_W14F05MS050",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.5,
        "debug_logging": False,
    },
    {
        "id": "W14F05MS025",
        "prefix": "AnimaGapDamping_M04_W14F05MS025",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.25,
        "debug_logging": False,
    },
    {
        "id": "W14F05MS000",
        "prefix": "AnimaGapDamping_M04_W14F05MS000",
        "mode": "replace",
        "warmup": 14,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.0,
        "debug_logging": False,
    },
]

GAP_DAMPING_REFINE_CASES = [
    {
        "id": "Baseline",
        "prefix": "AnimaGapRefine_M04_Baseline",
        "mode": "baseline",
        "debug_logging": False,
    },
    {
        "id": "W18Stop0MS000",
        "prefix": "AnimaGapRefine_M04_W18Stop0MS000",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.0,
        "debug_logging": False,
    },
    {
        "id": "W16F05MS000",
        "prefix": "AnimaGapRefine_M04_W16F05MS000",
        "mode": "replace",
        "warmup": 16,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.0,
        "debug_logging": True,
    },
    {
        "id": "W16F05MS025",
        "prefix": "AnimaGapRefine_M04_W16F05MS025",
        "mode": "replace",
        "warmup": 16,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.25,
        "debug_logging": False,
    },
    {
        "id": "W15F05MS000",
        "prefix": "AnimaGapRefine_M04_W15F05MS000",
        "mode": "replace",
        "warmup": 15,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.0,
        "debug_logging": False,
    },
    {
        "id": "W15F05MS025",
        "prefix": "AnimaGapRefine_M04_W15F05MS025",
        "mode": "replace",
        "warmup": 15,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.25,
        "debug_logging": False,
    },
]

EXTRA_STEP_CASES = [
    {
        "id": "Baseline",
        "prefix": "AnimaExtraStep_M04_Baseline",
        "mode": "baseline",
        "debug_logging": False,
    },
    {
        "id": "W18Stop0",
        "prefix": "AnimaExtraStep_M04_W18Stop0",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 1.0,
        "extra_steps": "",
        "debug_logging": True,
    },
    {
        "id": "W18Extra21",
        "prefix": "AnimaExtraStep_M04_W18Extra21",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 1.0,
        "extra_steps": "21",
        "debug_logging": True,
    },
    {
        "id": "W18Extra23",
        "prefix": "AnimaExtraStep_M04_W18Extra23",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 1.0,
        "extra_steps": "23",
        "debug_logging": True,
    },
    {
        "id": "W18Extra25",
        "prefix": "AnimaExtraStep_M04_W18Extra25",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 1.0,
        "extra_steps": "25",
        "debug_logging": True,
    },
    {
        "id": "W18Extra21_25",
        "prefix": "AnimaExtraStep_M04_W18Extra21_25",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 1.0,
        "extra_steps": "21,25",
        "debug_logging": True,
    },
]

EXTRA_DAMPING_CASES = [
    {
        "id": "Baseline",
        "prefix": "AnimaExtraDamping_M04_Baseline",
        "mode": "baseline",
        "debug_logging": False,
    },
    {
        "id": "W18Stop0",
        "prefix": "AnimaExtraDamping_M04_W18Stop0",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 1.0,
        "extra_steps": "",
        "debug_logging": True,
    },
    {
        "id": "W18Extra25MS100",
        "prefix": "AnimaExtraDamping_M04_W18Extra25MS100",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 1.0,
        "extra_steps": "25",
        "debug_logging": True,
    },
    {
        "id": "W18Extra25MS050",
        "prefix": "AnimaExtraDamping_M04_W18Extra25MS050",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.5,
        "extra_steps": "25",
        "debug_logging": True,
    },
    {
        "id": "W18Extra25MS025",
        "prefix": "AnimaExtraDamping_M04_W18Extra25MS025",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.25,
        "extra_steps": "25",
        "debug_logging": True,
    },
    {
        "id": "W18Extra25MS000",
        "prefix": "AnimaExtraDamping_M04_W18Extra25MS000",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 0.0,
        "extra_steps": "25",
        "debug_logging": True,
    },
]

W18_PROFILE_CASES = [
    {
        "id": "Baseline",
        "prefix": "AnimaW18Profile_M04_Baseline",
        "mode": "baseline",
        "debug_logging": False,
    },
    {
        "id": "W18Stop0Profile",
        "prefix": "AnimaW18Profile_M04_W18Stop0Profile",
        "mode": "replace",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 1.0,
        "extra_steps": "",
        "debug_logging": True,
    },
    {
        "id": "ShadowW18Stop0Profile",
        "prefix": "AnimaW18Profile_M04_ShadowW18Stop0Profile",
        "mode": "shadow",
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "damping": 1.0,
        "multistep_damping": 1.0,
        "extra_steps": "",
        "debug_logging": True,
    },
]

CASE_SETS = {
    "damping": DAMPING_CASES,
    "extra": EXTRA_STEP_CASES,
    "extradamping": EXTRA_DAMPING_CASES,
    "gapdamping": GAP_DAMPING_CASES,
    "gaprefine": GAP_DAMPING_REFINE_CASES,
    "guard": GUARD_CASES,
    "initial": INITIAL_CASES,
    "predictor": PREDICTOR_CASES,
    "refine": REFINE_CASES,
    "shadow": SHADOW_CASES,
    "w18profile": W18_PROFILE_CASES,
}


def request_json(url: str, *, method: str = "GET", payload=None, timeout: int = 30):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body}") from exc


def patch_workflow(base: dict, case: dict, seed: int) -> dict:
    workflow = deepcopy(base)
    workflow["46"]["inputs"]["filename_prefix"] = case["prefix"]
    workflow["76"]["inputs"]["seed"] = seed
    workflow["77"]["inputs"]["text"] = PROMPT_M04
    workflow["75"]["inputs"]["text"] = NEGATIVE_PROMPT

    if case["mode"] == "baseline":
        workflow["76"]["inputs"]["model"] = ["78", 0]
        workflow["79"]["inputs"]["debug_logging"] = False
        return workflow

    workflow["76"]["inputs"]["model"] = ["79", 0]
    spectrum = workflow["79"]["inputs"]
    spectrum.update(
        {
            "spectrum_preset": "Manual",
            "spectrum_w": float(case.get("w", 0.05)),
            "spectrum_warmup_steps": int(case["warmup"]),
            "spectrum_window_size": 2,
            "enable_calibration": False,
            "calibration_strength": 0.35,
            "calibration_mode": "ema",
            "spectrum_m": int(case.get("m", 16)),
            "spectrum_lam": float(case.get("lam", 0.5)),
            "spectrum_taylor_damping": float(case.get("damping", 1.0)),
            "spectrum_multistep_damping": float(case.get("multistep_damping", 1.0)),
            "spectrum_flex_window": float(case["flex"]),
            "spectrum_stop_caching_step": int(case.get("stop", 0)),
            "spectrum_extra_forecast_steps": str(case.get("extra_steps", "")),
            "debug_enable_spectrum": True,
            "feature_site": "pre_decoder_head",
            "target_block_index": 13,
            "forecast_mode": case["mode"],
            "debug_logging": bool(case["debug_logging"]),
        }
    )
    return workflow


def submit_and_wait(url: str, workflow: dict) -> dict:
    client_id = str(uuid.uuid4())
    submitted = request_json(f"{url}/prompt", method="POST", payload={"prompt": workflow, "client_id": client_id})
    prompt_id = submitted["prompt_id"]
    while True:
        history = request_json(f"{url}/history/{prompt_id}", timeout=10)
        if prompt_id in history:
            item = history[prompt_id]
            status = item.get("status", {})
            if status.get("completed"):
                return item
            if status.get("status_str") == "error":
                raise RuntimeError(json.dumps(status, indent=2))
        time.sleep(0.5)


def extract_output_image(history_item: dict) -> Path:
    outputs = history_item.get("outputs", {})
    for node_output in outputs.values():
        for image in node_output.get("images", []):
            filename = image["filename"]
            subfolder = image.get("subfolder") or ""
            return OUTPUT_DIR / subfolder / filename
    raise RuntimeError("No output image found in ComfyUI history.")


def image_metrics(candidate: Path, baseline: Path) -> dict:
    with Image.open(candidate).convert("RGB") as cand, Image.open(baseline).convert("RGB") as base:
        if cand.size != base.size:
            raise RuntimeError(f"Image size mismatch: {candidate} {cand.size} vs {baseline} {base.size}")
        diff = ImageChops.difference(cand, base)
        hist = diff.histogram()
        pixels = cand.size[0] * cand.size[1]
        channels = 3
        total_values = pixels * channels
        sum_abs = sum((value % 256) * count for value, count in enumerate(hist))
        sum_sq = sum((value % 256) ** 2 * count for value, count in enumerate(hist))
        mse = sum_sq / total_values
        mae = sum_abs / total_values
        rmse = math.sqrt(mse)
        psnr = float("inf") if mse == 0 else 20.0 * math.log10(255.0 / rmse)
        bbox = diff.getbbox()
        changed_pixels = 0
        if bbox is not None:
            diff_luma = diff.convert("L")
            changed_pixels = pixels - diff_luma.point(lambda p: 255 if p == 0 else 0).histogram()[255]
        return {
            "mse": round(mse, 6),
            "mae": round(mae, 6),
            "rmse": round(rmse, 6),
            "psnr": round(psnr, 3) if math.isfinite(psnr) else "inf",
            "max_abs": max(index % 256 for index, count in enumerate(hist) if count),
            "changed_ratio": round(changed_pixels / pixels, 6),
        }


def collect_new_logs(start_time: float, previous_logs: set[Path] | None = None) -> list[Path]:
    if not LOG_DIR.exists():
        return []
    previous_logs = previous_logs or set()
    return sorted(
        [
            path
            for path in LOG_DIR.glob("*.jsonl")
            if path not in previous_logs and path.stat().st_mtime >= start_time
        ],
        key=lambda path: path.stat().st_mtime,
    )


def summarize_log(path: Path) -> dict:
    steps_by_kind = {}
    error_rows = []
    timing_totals = {}
    timing_counts = {}
    records = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if payload.get("event") != "step":
                continue
            records += 1
            kind = payload.get("step_kind") or payload.get("actual_or_forecast")
            steps_by_kind.setdefault(kind, []).append(payload.get("step_index"))
            errors = payload.get("errors") or {}
            if errors:
                error_rows.append(
                    {
                        "kind": kind,
                        "step": int(payload.get("step_index")),
                        "raw_vs_actual_rel_l2": errors.get("raw_vs_actual_rel_l2"),
                        "raw_vs_actual_cosine": errors.get("raw_vs_actual_cosine"),
                        "raw_vs_actual_mse": errors.get("raw_vs_actual_mse"),
                    }
                )
            timings = payload.get("timings") or {}
            for key, value in timings.items():
                timing_key = f"{kind}.{key}"
                timing_totals[timing_key] = timing_totals.get(timing_key, 0.0) + float(value)
                timing_counts[timing_key] = timing_counts.get(timing_key, 0) + 1
    return {
        "path": str(path.relative_to(ROOT)),
        "records": records,
        "steps_by_kind": {key: sorted(set(value)) for key, value in steps_by_kind.items()},
        "worst_errors": sorted(
            error_rows,
            key=lambda item: float(item.get("raw_vs_actual_rel_l2") or 0.0),
            reverse=True,
        )[:10],
        "timings": {
            key: {
                "total_ms": round(total, 3),
                "avg_ms": round(total / max(timing_counts[key], 1), 3),
                "count": timing_counts[key],
            }
            for key, total in sorted(timing_totals.items())
        },
    }


def make_contact_sheet(results: list[dict], path: Path) -> None:
    images = []
    for result in results:
        image_path = result.get("image_path")
        if image_path:
            images.append((result["id"], Path(image_path)))
    if not images:
        return

    thumbs = []
    for label, image_path in images:
        with Image.open(image_path).convert("RGB") as image:
            thumb = image.copy()
            thumb.thumbnail((320, 320))
            canvas = Image.new("RGB", (320, 350), "white")
            canvas.paste(thumb, ((320 - thumb.size[0]) // 2, 0))
            ImageDraw.Draw(canvas).text((8, 328), label, fill="black")
            thumbs.append((label, canvas))

    sheet = Image.new("RGB", (320 * len(thumbs), 350), "white")
    for index, (_label, thumb) in enumerate(thumbs):
        sheet.paste(thumb, (index * 320, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def write_report(
    results: list[dict],
    json_path: Path,
    markdown_path: Path,
    contact_sheet: Path,
    title: str,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"# {title} - 2026-06-13",
        "",
        "Prompt: M04 worst-case prompt from the previous W18Stop0 validation.",
        "",
        f"Raw JSON: `{json_path.relative_to(ROOT)}`",
        f"Contact sheet: `{contact_sheet.relative_to(ROOT)}`",
        "",
        "| Case | Seconds | Speedup vs baseline | Warmup | Flex | Stop | Extra steps | w | m | lam | Damping | Multi-step | PSNR | MAE | MSE | Forecast steps | Image |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    baseline_seconds = next(item["seconds"] for item in results if item["id"] == "Baseline")
    for item in results:
        metrics = item.get("metrics") or {}
        speedup = baseline_seconds - item["seconds"]
        forecast_steps = "-"
        if item.get("logs"):
            steps = sorted(
                {
                    step
                    for log in item["logs"]
                    for step in log.get("steps_by_kind", {}).get("forecast", [])
                }
            )
            forecast_steps = ",".join(str(step) for step in steps) or "-"
        lines.append(
            "| {id} | {seconds:.3f} | {speedup:.3f} | {warmup} | {flex} | {stop} | {extra_steps} | {w} | {m} | {lam} | {damping} | {multistep_damping} | {psnr} | {mae} | {mse} | {steps} | `{image}` |".format(
                id=item["id"],
                seconds=item["seconds"],
                speedup=speedup,
                warmup=item.get("warmup", "-"),
                flex=item.get("flex", "-"),
                stop=item.get("stop", "-"),
                extra_steps=item.get("extra_steps", "-"),
                w=item.get("w", "-"),
                m=item.get("m", "-"),
                lam=item.get("lam", "-"),
                damping=item.get("damping", "-"),
                multistep_damping=item.get("multistep_damping", "-"),
                psnr=metrics.get("psnr", "-"),
                mae=metrics.get("mae", "-"),
                mse=metrics.get("mse", "-"),
                steps=forecast_steps,
                image=Path(item["image_path"]).name if item.get("image_path") else "-",
            )
        )
    timing_rows = []
    for item in results:
        for log in item.get("logs", []):
            for key, summary in (log.get("timings") or {}).items():
                timing_rows.append((item["id"], key, summary))
    if timing_rows:
        lines.extend(
            [
                "",
                "## Timing summary",
                "",
                "| Case | Timing key | Total ms | Avg ms | Count |",
                "| --- | --- | ---: | ---: | ---: |",
            ]
        )
        for case_id, key, summary in timing_rows:
            lines.append(
                f"| {case_id} | {key} | {summary['total_ms']:.3f} | {summary['avg_ms']:.3f} | {summary['count']} |"
            )
    error_rows = []
    for item in results:
        for log in item.get("logs", []):
            for row in log.get("worst_errors", []):
                error_rows.append((item["id"], row))
    if error_rows:
        lines.extend(
            [
                "",
                "## Worst forecast errors",
                "",
                "| Case | Kind | Step | Rel L2 | Cosine | MSE |",
                "| --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for case_id, row in sorted(
            error_rows,
            key=lambda item: float(item[1].get("raw_vs_actual_rel_l2") or 0.0),
            reverse=True,
        )[:20]:
            lines.append(
                "| {case} | {kind} | {step} | {rel_l2:.6f} | {cosine:.6f} | {mse:.6f} |".format(
                    case=case_id,
                    kind=row.get("kind", "-"),
                    step=row.get("step", -1),
                    rel_l2=float(row.get("raw_vs_actual_rel_l2") or 0.0),
                    cosine=float(row.get("raw_vs_actual_cosine") or 0.0),
                    mse=float(row.get("raw_vs_actual_mse") or 0.0),
                )
            )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--seed", type=int, default=202606132004)
    parser.add_argument("--case-set", choices=sorted(CASE_SETS), default="initial")
    parser.add_argument("--recompute-json", type=Path)
    args = parser.parse_args()

    if args.recompute_json is not None:
        results = json.loads(args.recompute_json.read_text(encoding="utf-8"))
        baseline_path = Path(next(item["image_path"] for item in results if item["id"] == "Baseline"))
        for result in results:
            if result["id"] == "Baseline":
                result["metrics"] = {"psnr": "inf", "mae": 0.0, "mse": 0.0}
            else:
                result["metrics"] = image_metrics(Path(result["image_path"]), baseline_path)
            result["logs"] = [
                summarize_log(ROOT / log["path"])
                for log in result.get("logs", [])
                if (ROOT / log["path"]).exists()
            ]
        stamp = datetime.now().strftime("%Y-%m-%d")
        stem = args.recompute_json.stem
        json_path = VISUAL_DIR / f"{stem}.json"
        contact_sheet = VISUAL_DIR / f"anima_{stem}.png"
        markdown_path = REPORT_DIR / f"{stem.replace('_', '-')}.md"
        make_contact_sheet(results, contact_sheet)
        write_report(results, json_path, markdown_path, contact_sheet, "Flex window API comparison")
        print(f"Recomputed {json_path}")
        print(f"Recomputed {markdown_path}")
        print(f"Recomputed {contact_sheet}")
        return

    base = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    results = []
    baseline_path = None

    cases = CASE_SETS[args.case_set]
    for case in cases:
        workflow = patch_workflow(base, case, args.seed)
        existing_logs = set(LOG_DIR.glob("*.jsonl")) if LOG_DIR.exists() else set()
        start = time.perf_counter()
        log_start = time.time()
        history = submit_and_wait(args.url.rstrip("/"), workflow)
        seconds = time.perf_counter() - start
        image_path = extract_output_image(history)
        new_logs = [
            summarize_log(path)
            for path in collect_new_logs(log_start, previous_logs=existing_logs)
        ] if case.get("debug_logging") else []

        result = {
            "id": case["id"],
            "mode": case["mode"],
            "warmup": case.get("warmup"),
            "flex": case.get("flex"),
            "w": case.get("w"),
            "m": case.get("m"),
            "lam": case.get("lam"),
            "stop": case.get("stop"),
            "extra_steps": case.get("extra_steps"),
            "damping": case.get("damping"),
            "multistep_damping": case.get("multistep_damping"),
            "debug_logging": case.get("debug_logging", False),
            "seed": args.seed,
            "seconds": round(seconds, 3),
            "image_path": str(image_path),
            "logs": new_logs,
        }

        if case["mode"] == "baseline":
            baseline_path = image_path
            result["metrics"] = {"psnr": "inf", "mae": 0.0, "mse": 0.0}
        else:
            result["metrics"] = image_metrics(image_path, baseline_path)

        results.append(result)
        print(json.dumps(result, ensure_ascii=False))

    stamp = datetime.now().strftime("%Y-%m-%d")
    stem = f"flex_window_api_{args.case_set}_{stamp}"
    json_path = VISUAL_DIR / f"{stem}.json"
    contact_sheet = VISUAL_DIR / f"anima_{stem}.png"
    markdown_path = REPORT_DIR / f"{stem.replace('_', '-')}.md"
    make_contact_sheet(results, contact_sheet)
    write_report(results, json_path, markdown_path, contact_sheet, f"Flex window API {args.case_set} comparison")
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    print(f"Wrote {contact_sheet}")


if __name__ == "__main__":
    main()

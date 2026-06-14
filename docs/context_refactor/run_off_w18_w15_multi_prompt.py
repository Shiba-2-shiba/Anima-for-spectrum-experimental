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

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / "docs" / "context_refactor" / "workflows" / "image_anima_base_v1_spectrum_debug(api).json"
OUTPUT_DIR = Path(r"C:\ComfyUI\output")
REPORT_DIR = ROOT / "docs" / "context_refactor"
VISUAL_DIR = REPORT_DIR / "visual_review"

NEGATIVE_PROMPT = "worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, sepia"

PROMPTS = [
    {
        "id": "M01",
        "seed": 202606132801,
        "text": (
            "Anime monochrome cyberpunk female android portrait, transparent cheek panels, glowing blue eyes, "
            "braided silver hair, exposed neck servos, rain-soaked circuit city background, sharp ink linework, "
            "high contrast cinematic lighting, ultra fine mechanical detail"
        ),
    },
    {
        "id": "M02",
        "seed": 202606132802,
        "text": (
            "Anime full body cybernetic swordsman standing in a ruined neon station, flowing coat, mechanical right arm, "
            "luminous blade, tangled cables, dramatic backlight, crisp manga shadows, detailed armor plates, blue monochrome palette"
        ),
    },
    {
        "id": "M03",
        "seed": 202606132803,
        "text": (
            "Anime close portrait of an elegant male pilot inside a dark cockpit, half organic half machine face, "
            "glowing interface reflections, dense cable halo, clean white hair, intense expression, intricate sci fi panel detail, cinematic chiaroscuro"
        ),
    },
    {
        "id": "M04",
        "seed": 202606132804,
        "text": (
            "Anime wide portrait of a cybernetic priestess in a cathedral server room, luminous mechanical halo, "
            "porcelain face plates, black cables like stained glass, blue white monochrome lighting, precise ink hatching, high detail sci fi ornament"
        ),
    },
]

W15_CASES = [
    {
        "id": "Off",
        "mode": "replace",
        "debug_enable_spectrum": False,
    },
    {
        "id": "W18Stop0",
        "mode": "replace",
        "debug_enable_spectrum": True,
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "taylor_damping": 1.0,
        "multistep_damping": 1.0,
    },
    {
        "id": "W15F05MS000",
        "mode": "replace",
        "debug_enable_spectrum": True,
        "warmup": 15,
        "flex": 0.5,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "taylor_damping": 1.0,
        "multistep_damping": 0.0,
    },
]

EXTRA25_CASES = [
    {
        "id": "Off",
        "mode": "replace",
        "debug_enable_spectrum": False,
    },
    {
        "id": "W18Stop0",
        "mode": "replace",
        "debug_enable_spectrum": True,
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "taylor_damping": 1.0,
        "multistep_damping": 1.0,
        "extra_steps": "",
    },
    {
        "id": "W18Extra25MS025",
        "mode": "replace",
        "debug_enable_spectrum": True,
        "warmup": 18,
        "flex": 0.0,
        "stop": 0,
        "w": 0.05,
        "m": 16,
        "lam": 0.5,
        "taylor_damping": 1.0,
        "multistep_damping": 0.25,
        "extra_steps": "25",
    },
]

CASE_SETS = {
    "w15": {
        "cases": W15_CASES,
        "title": "Spectrum off vs W18Stop0 vs W15F05MS000",
        "stem": "off_w18_w15_multi_prompt",
        "report_stem": "off-w18-w15-multi-prompt",
        "contact_stem": "anima_off_w18_w15_multi_prompt",
    },
    "extra25": {
        "cases": EXTRA25_CASES,
        "title": "Spectrum off vs W18Stop0 vs W18Extra25MS025",
        "stem": "off_w18_extra25_multi_prompt",
        "report_stem": "off-w18-extra25-multi-prompt",
        "contact_stem": "anima_off_w18_extra25_multi_prompt",
    },
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


def patch_workflow(base: dict, prompt: dict, case: dict, prefix: str) -> dict:
    workflow = deepcopy(base)
    workflow["46"]["inputs"]["filename_prefix"] = prefix
    workflow["76"]["inputs"]["seed"] = int(prompt["seed"])
    workflow["77"]["inputs"]["text"] = prompt["text"]
    workflow["75"]["inputs"]["text"] = NEGATIVE_PROMPT
    workflow["76"]["inputs"]["model"] = ["79", 0]

    spectrum = workflow["79"]["inputs"]
    spectrum.update(
        {
            "spectrum_preset": "Manual",
            "debug_enable_spectrum": bool(case["debug_enable_spectrum"]),
            "spectrum_w": float(case.get("w", 0.05)),
            "spectrum_warmup_steps": int(case.get("warmup", 18)),
            "spectrum_window_size": 2,
            "enable_calibration": False,
            "calibration_strength": 0.35,
            "calibration_mode": "ema",
            "spectrum_m": int(case.get("m", 16)),
            "spectrum_lam": float(case.get("lam", 0.5)),
            "spectrum_taylor_damping": float(case.get("taylor_damping", 1.0)),
            "spectrum_multistep_damping": float(case.get("multistep_damping", 1.0)),
            "spectrum_flex_window": float(case.get("flex", 0.0)),
            "spectrum_stop_caching_step": int(case.get("stop", 0)),
            "spectrum_extra_forecast_steps": str(case.get("extra_steps", "")),
            "feature_site": "pre_decoder_head",
            "target_block_index": 13,
            "forecast_mode": case.get("mode", "replace"),
            "debug_logging": False,
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
    for node_output in history_item.get("outputs", {}).values():
        for image in node_output.get("images", []):
            return OUTPUT_DIR / (image.get("subfolder") or "") / image["filename"]
    raise RuntimeError("No output image found in ComfyUI history.")


def image_metrics(candidate: Path, baseline: Path) -> dict:
    with Image.open(candidate).convert("RGB") as cand, Image.open(baseline).convert("RGB") as base:
        if cand.size != base.size:
            raise RuntimeError(f"Image size mismatch: {candidate} {cand.size} vs {baseline} {base.size}")
        diff = ImageChops.difference(cand, base)
        hist = diff.histogram()
        pixels = cand.size[0] * cand.size[1]
        total_values = pixels * 3
        sum_abs = sum((value % 256) * count for value, count in enumerate(hist))
        sum_sq = sum((value % 256) ** 2 * count for value, count in enumerate(hist))
        mse = sum_sq / total_values
        mae = sum_abs / total_values
        rmse = math.sqrt(mse)
        psnr = float("inf") if mse == 0 else 20.0 * math.log10(255.0 / rmse)
        changed_pixels = 0
        if diff.getbbox() is not None:
            diff_luma = diff.convert("L")
            changed_pixels = pixels - diff_luma.point(lambda p: 255 if p == 0 else 0).histogram()[255]
        return {
            "mse": round(mse, 6),
            "mae": round(mae, 6),
            "rmse": round(rmse, 6),
            "psnr": round(psnr, 3) if math.isfinite(psnr) else "inf",
            "changed_ratio": round(changed_pixels / pixels, 6),
        }


def make_contact_sheet(results: list[dict], path: Path) -> None:
    rows = []
    for prompt in PROMPTS:
        row_items = [item for item in results if item["prompt_id"] == prompt["id"]]
        thumbs = []
        for item in row_items:
            with Image.open(item["image_path"]).convert("RGB") as image:
                thumb = image.copy()
                thumb.thumbnail((260, 260))
                canvas = Image.new("RGB", (260, 290), "white")
                canvas.paste(thumb, ((260 - thumb.size[0]) // 2, 0))
                ImageDraw.Draw(canvas).text((8, 268), f"{prompt['id']} {item['case_id']}", fill="black")
                thumbs.append(canvas)
        row = Image.new("RGB", (260 * len(thumbs), 290), "white")
        for index, thumb in enumerate(thumbs):
            row.paste(thumb, (260 * index, 0))
        rows.append(row)

    sheet = Image.new("RGB", (max(row.width for row in rows), 290 * len(rows)), "white")
    for index, row in enumerate(rows):
        sheet.paste(row, (0, 290 * index))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def write_report(
    results: list[dict],
    json_path: Path,
    markdown_path: Path,
    contact_sheet: Path,
    *,
    title: str,
    cases: list[dict],
) -> None:
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"# {title} - 2026-06-13",
        "",
        "Baseline for quality metrics is `Off` for each prompt.",
        "",
        f"Raw JSON: `{json_path.relative_to(ROOT)}`",
        f"Contact sheet: `{contact_sheet.relative_to(ROOT)}`",
        "",
        "| Prompt | Case | Seconds | Speedup vs Off | PSNR vs Off | MAE | MSE | Image |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for prompt in PROMPTS:
        prompt_results = [item for item in results if item["prompt_id"] == prompt["id"]]
        off_seconds = next(item["seconds"] for item in prompt_results if item["case_id"] == "Off")
        for item in prompt_results:
            metrics = item["metrics"]
            lines.append(
                "| {prompt} | {case} | {seconds:.3f} | {speedup:.3f} | {psnr} | {mae} | {mse} | `{image}` |".format(
                    prompt=prompt["id"],
                    case=item["case_id"],
                    seconds=item["seconds"],
                    speedup=off_seconds - item["seconds"],
                    psnr=metrics.get("psnr", "-"),
                    mae=metrics.get("mae", "-"),
                    mse=metrics.get("mse", "-"),
                    image=Path(item["image_path"]).name,
                )
            )

    lines.extend(["", "## Averages", ""])
    for case in cases:
        case_results = [item for item in results if item["case_id"] == case["id"]]
        avg_seconds = sum(item["seconds"] for item in case_results) / len(case_results)
        if case["id"] == "Off":
            lines.append(f"- {case['id']}: avg seconds `{avg_seconds:.3f}`")
            continue
        off_by_prompt = {item["prompt_id"]: item["seconds"] for item in results if item["case_id"] == "Off"}
        avg_speedup = sum(off_by_prompt[item["prompt_id"]] - item["seconds"] for item in case_results) / len(case_results)
        avg_psnr = sum(float(item["metrics"]["psnr"]) for item in case_results) / len(case_results)
        avg_mae = sum(float(item["metrics"]["mae"]) for item in case_results) / len(case_results)
        lines.append(
            f"- {case['id']}: avg seconds `{avg_seconds:.3f}`, avg speedup `{avg_speedup:.3f}`, "
            f"avg PSNR `{avg_psnr:.3f}`, avg MAE `{avg_mae:.3f}`"
        )

    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--case-set", choices=sorted(CASE_SETS), default="w15")
    args = parser.parse_args()

    base = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    results = []
    selected = CASE_SETS[args.case_set]
    cases = selected["cases"]

    for prompt in PROMPTS:
        off_image = None
        for case in cases:
            prefix = f"AnimaOffW18W15_{prompt['id']}_{case['id']}"
            if args.case_set != "w15":
                prefix = f"AnimaOffW18Extra25_{prompt['id']}_{case['id']}"
            workflow = patch_workflow(base, prompt, case, prefix)
            start = time.perf_counter()
            history = submit_and_wait(args.url.rstrip("/"), workflow)
            seconds = time.perf_counter() - start
            image_path = extract_output_image(history)
            if case["id"] == "Off":
                off_image = image_path
                metrics = {"psnr": "inf", "mae": 0.0, "mse": 0.0, "rmse": 0.0, "changed_ratio": 0.0}
            else:
                metrics = image_metrics(image_path, off_image)
            result = {
                "prompt_id": prompt["id"],
                "seed": prompt["seed"],
                "case_id": case["id"],
                "seconds": round(seconds, 3),
                "image_path": str(image_path),
                "settings": case,
                "metrics": metrics,
            }
            results.append(result)
            print(json.dumps(result, ensure_ascii=False))

    stamp = datetime.now().strftime("%Y-%m-%d")
    json_path = VISUAL_DIR / f"{selected['stem']}_{stamp}.json"
    markdown_path = REPORT_DIR / f"{selected['report_stem']}-{stamp}.md"
    contact_sheet = VISUAL_DIR / f"{selected['contact_stem']}_{stamp}.png"
    make_contact_sheet(results, contact_sheet)
    write_report(results, json_path, markdown_path, contact_sheet, title=selected["title"], cases=cases)
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    print(f"Wrote {contact_sheet}")


if __name__ == "__main__":
    main()

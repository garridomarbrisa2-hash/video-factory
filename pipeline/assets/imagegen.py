"""AI still generation via the ModelScope inference API.

Route C (auto-generate): a scene that needs a still and has no local/generated
file gets one synthesized here, chosen by topic between two ModelScope models:

  - Z-Image        (Tongyi-MAI/Z-Image)        — default: photoreal documentary,
                                                 bilingual text (EN+中文), detailed prompts
  - Krea-2-Turbo   (krea-community/Krea-2-Turbo) — stylized/concept/illustrative/
                                                 cinematic-grain beats, concise prompts

API (docs/API/modelscope.md + research): async-only.
  POST {base}/v1/images/generations  (X-ModelScope-Async-Mode: true) -> {task_id}
  GET  {base}/v1/tasks/{task_id}     (X-ModelScope-Task-Type: image_generation)
       -> task_status SUCCEED => output_images[0] URL (download + cache)

Env: MODELSCOPE_API_KEY. Quota ~2000 calls/day/user; HTTP 429 = daily quota ->
treated as a miss (caller falls back to a style plate, never aborts).
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from pipeline import ensure_dir, project_path

_BASE = "https://api-inference.modelscope.ai/"

# Per-model request params (research: docs/plans/PHASE_9_GENERATED_ASSETS.md).
# Both are Turbo-class (guidance off, negative prompts ignored) — constraints go
# in the positive prompt. ModelScope takes a `size` STRING in "WxH" format (NOT
# width/height ints — those are silently ignored and yield a portrait default).
# Sizes are 16:9 within each model's comfort zone; the FFmpeg normalize step
# upscales to 1920x1080.
_MODELS: dict[str, dict[str, Any]] = {
    "z-image": {
        "model": "Tongyi-MAI/Z-Image",
        "size": "1536x864",  # 16:9 @ 1280² budget
        "num_inference_steps": 9,
        "guidance_scale": 0.0,
    },
    "krea-2-turbo": {
        "model": "krea-community/Krea-2-Turbo",
        "size": "1280x720",  # 16:9, multiple of 16
        "num_inference_steps": 8,
        "guidance_scale": 0.0,
    },
}

_NO_ARTIFACTS = (
    "text, watermark, logo, collage, duplicate subjects, malformed anatomy"
)

# Beats that read as stylized / concept / illustrative / atmospheric -> Krea.
# Everything else (real-world, documentary, people/places/things, text, Chinese)
# -> Z-Image. Krea-only trigger: an explicit LoRA request.
_STYLIZED_HINTS = (
    "concept art", "illustration", "illustrated", "painterly", "painting",
    "stylized", "stylised", "graphic", "poster art", "comic", "anime",
    "watercolor", "watercolour", "sketch", "low-poly", "isometric", "vector",
    "cinematic grain", "film grain", "dreamlike", "surreal", "ethereal",
    "abstract", "impressionist", "storybook", "fantasy art", "matte painting",
)


class ImageGenMiss(Exception):
    """Generation failed or quota exhausted; caller falls back to a plate."""


def choose_image_model(prompt: str, loras: Any = None) -> str:
    """Topic/prompt -> 'z-image' | 'krea-2-turbo'.

    Z-Image is the general default (photoreal, instruction-adherent, bilingual
    text). Krea-2-Turbo only when the beat is explicitly stylized/atmospheric,
    or a LoRA look is requested (Krea has the LoRA path; Z-Image Turbo does not).
    """
    if loras:
        return "krea-2-turbo"
    text = prompt.lower()
    return "krea-2-turbo" if any(h in text for h in _STYLIZED_HINTS) else "z-image"


def image_prompt(prompt: str) -> str:
    """Keep Turbo-model prompts short: subject, setting, period, light, medium."""
    clean = " ".join(prompt.split())
    if not clean:
        raise ValueError("image prompt cannot be empty")
    parts = [part.strip(" .") for part in clean.split(",") if part.strip(" .")]
    clean = ", ".join(parts[:6])
    words = clean.split()
    if len(words) > 55:
        clean = " ".join(words[:55]).rstrip(" ,.;:")
    return (
        f"{clean}. Single 16:9 scene, one clear subject, natural composition. "
        "No text, watermark, logo, collage, or duplicate subjects."
    )


def _cache_path(cache_dir: Path, request: dict[str, Any]) -> Path:
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    key = hashlib.sha256(canonical.encode()).hexdigest()[:20]
    return cache_dir / f"gen_{key}.png"


def generate_image(
    prompt: str,
    cache_dir: Path,
    seed: int | None = None,
    model: str | None = None,
    loras: Any = None,
    poll_interval: float = 5.0,
    timeout: float = 300.0,
) -> Path:
    """Generate one still from a prompt. Returns the cached PNG path.

    Raises ImageGenMiss on missing key, quota (429), task failure, or timeout —
    the caller (orchestrator) falls back to a style plate and never aborts.
    ModelScope cold-starts can exceed 120s on the first call, so the default
    timeout is generous; cached results return instantly.
    """
    api_key = os.environ.get("MODELSCOPE_API_KEY", "").strip()
    if not api_key:
        raise ImageGenMiss("MODELSCOPE_API_KEY not set (https://modelscope.ai -> token)")

    chosen = model or choose_image_model(prompt, loras)
    spec = _MODELS.get(chosen, _MODELS["z-image"])
    prepared_prompt = image_prompt(prompt)
    body: dict[str, Any] = {
        "model": spec["model"],
        "prompt": prepared_prompt,
        "size": spec["size"],  # "WxH" string — width/height ints are ignored by the API
        "num_inference_steps": spec["num_inference_steps"],
        "guidance_scale": spec["guidance_scale"],
    }
    # Z-Image upstream strongly recommends negative prompts for control. Krea's
    # prompt guide does not document them, so do not send unsupported baggage.
    if chosen == "z-image":
        body["negative_prompt"] = _NO_ARTIFACTS
    if seed is not None:
        body["seed"] = seed
    if loras:
        body["loras"] = loras
    dest = _cache_path(cache_dir, body)
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{_BASE}v1/images/generations",
                headers={**headers, "X-ModelScope-Async-Mode": "true"},
                json=body,
            )
            if resp.status_code == 429:
                raise ImageGenMiss("ModelScope daily quota exhausted (HTTP 429)")
            resp.raise_for_status()
            task_id = resp.json()["task_id"]

            deadline = time.time() + timeout
            while True:
                if time.time() > deadline:
                    raise ImageGenMiss(f"ModelScope task {task_id} timed out ({timeout}s)")
                time.sleep(poll_interval)
                result = client.get(
                    f"{_BASE}v1/tasks/{task_id}",
                    headers={**headers, "X-ModelScope-Task-Type": "image_generation"},
                )
                if result.status_code == 429:
                    raise ImageGenMiss("ModelScope daily quota exhausted (HTTP 429)")
                result.raise_for_status()
                data = result.json()
                status = data.get("task_status")
                if status == "SUCCEED":
                    url = data["output_images"][0]
                    break
                if status == "FAILED":
                    raise ImageGenMiss(f"ModelScope task {task_id} FAILED")

        ensure_dir(cache_dir)
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            img = client.get(url)
            img.raise_for_status()
            if not img.headers.get("content-type", "").lower().startswith("image/"):
                raise ImageGenMiss("ModelScope returned non-image content")
            try:
                with Image.open(io.BytesIO(img.content)) as decoded:
                    decoded.verify()
                with Image.open(io.BytesIO(img.content)) as decoded:
                    width, height = decoded.size
            except Exception as e:
                raise ImageGenMiss(f"ModelScope returned an invalid image: {e}") from e
            if width < 1024 or height < 576 or abs(width / height - 16 / 9) > 0.03:
                raise ImageGenMiss(f"ModelScope image has invalid dimensions: {width}x{height}")
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(img.content)
            tmp.replace(dest)
        return dest
    except httpx.HTTPStatusError as e:
        raise ImageGenMiss(f"ModelScope HTTP {e.response.status_code}: {e.response.text[:200]}") from e
    except httpx.HTTPError as e:
        raise ImageGenMiss(f"ModelScope request failed: {e}") from e


def generate_image_for_scene(
    prompt: str,
    scene_id: int,
    pipeline_cfg: dict[str, Any],
    seed: int | None = None,
    model: str | None = None,
    loras: Any = None,
) -> Path:
    """Scene-facing wrapper: resolve cache dir from config and generate."""
    gen_cfg = pipeline_cfg.get("generate", {})
    cache_dir = ensure_dir(
        project_path(pipeline_cfg.get("assets_cache_dir", "pipeline/assets/cache")) / "generated"
    )
    return generate_image(
        prompt,
        cache_dir,
        seed=seed if seed is not None else scene_id,
        model=model or gen_cfg.get("model"),
        loras=loras or gen_cfg.get("loras"),
        poll_interval=float(gen_cfg.get("poll_interval", 5.0)),
        timeout=float(gen_cfg.get("timeout", 120.0)),
    )

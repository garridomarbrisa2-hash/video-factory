"""Stock footage search + download. User provides API keys via env."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

from pipeline import ensure_dir, load_json, project_path


class StockMissError(Exception):
    """No stock match; user must provide manual asset or generate from prompt."""

    def __init__(self, keyword: str, fallback_prompt: str | None = None) -> None:
        self.keyword = keyword
        self.fallback_prompt = fallback_prompt
        msg = f"No stock footage for keyword={keyword!r}."
        if fallback_prompt:
            msg += f" Generate with: {fallback_prompt}"
        super().__init__(msg)


# Animation/abstract/background/loop keywords route to Pixabay video_type=animation
# (Pexels has no animation corpus). Real-world subjects stay on Pexels film.
_ABSTRACT_HINTS = (
    "animation", "animated", "abstract", "background loop", "loop", "particles",
    "geometric", "data visualization", "motion graphic", "gradient", "bokeh",
    "smoke overlay", "light streaks", "tunnel animation", "fractal", "waveform",
)


def _is_abstract_keyword(keyword: str) -> bool:
    text = (keyword or "").lower()
    return any(h in text for h in _ABSTRACT_HINTS)


def _cache_path(cache_dir: Path, keyword: str, source: str, url: str) -> Path:
    key = hashlib.sha256(f"{source}|{keyword}|{url}".encode()).hexdigest()[:20]
    return cache_dir / f"{source}_{key}.mp4"


def search_pexels(keyword: str, api_key: str, min_width: int = 1920) -> list[dict[str, Any]]:
    headers = {"Authorization": api_key}
    # /v1/videos/search (legacy /videos/search is deprecated). size=medium pre-filters
    # server-side to >=Full HD sources; per_page max is 80.
    url = (
        "https://api.pexels.com/v1/videos/search"
        f"?query={quote_plus(keyword)}&per_page=15&orientation=landscape&size=medium"
    )
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    results: list[dict[str, Any]] = []
    for video in data.get("videos", []):  # relevance-ordered server-side
        files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4"]
        if not files:
            continue
        hi = [f for f in files if (f.get("width") or 0) >= min_width and (f.get("height") or 0) >= 1080]
        if hi:
            # Prefer closest to 1080p (avoid a 4K download + downscale), tie-break fps ~30
            hi.sort(key=lambda f: (abs((f.get("height") or 0) - 1080), abs((f.get("fps") or 30) - 30)))
            best = hi[0]
        else:
            # No >=1080p file: take the largest available, normalize upscales
            best = max(files, key=lambda f: (f.get("width") or 0) * (f.get("height") or 0))
        results.append(
            {
                "id": video.get("id"),
                "url": best.get("link"),
                "width": best.get("width"),
                "height": best.get("height"),
                "duration": video.get("duration"),
                "source": "pexels",
            }
        )
    return results


def _pixabay_fetch(url: str, cache_dir: Path | None = None) -> dict[str, Any]:
    # Pixabay ToS requires caching API responses >=24h (and prohibits re-querying
    # identical searches). Disk-cache the JSON keyed on the request URL.
    if cache_dir is not None:
        key = hashlib.sha256(url.encode()).hexdigest()[:20]
        cached = ensure_dir(cache_dir) / f"search_{key}.json"
        if cached.exists() and (time.time() - cached.stat().st_mtime) < 24 * 3600:
            return json.loads(cached.read_text(encoding="utf-8"))
        data = _pixabay_http(url)
        cached.write_text(json.dumps(data), encoding="utf-8")
        return data
    return _pixabay_http(url)


def _pixabay_http(url: str) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


def search_pixabay(
    keyword: str,
    api_key: str,
    min_width: int = 1920,
    video_type: str = "film",
    editors_choice: bool = False,
    cache_dir: Path | None = None,
) -> list[dict[str, Any]]:
    url = (
        "https://pixabay.com/api/videos/"
        f"?key={api_key}&q={quote_plus(keyword)}&per_page=10&safesearch=true"
        f"&order=popular&video_type={video_type}&min_width={min_width}"
    )
    if editors_choice:
        url += "&editors_choice=true"
    data = _pixabay_fetch(url, cache_dir)

    results: list[dict[str, Any]] = []
    # Rank by downloads (popularity proxy) then views
    hits = sorted(
        data.get("hits", []),
        key=lambda h: (h.get("downloads") or 0, h.get("views") or 0),
        reverse=True,
    )
    for hit in hits:
        videos = hit.get("videos", {})
        # medium is usually exactly 1920x1080; large is 4K (skip unless medium is
        # sub-1080p, e.g. older clips). Read the real width/height, never assume.
        medium = videos.get("medium") or {}
        large = videos.get("large") or {}
        if (medium.get("width") or 0) >= min_width and medium.get("url"):
            v = medium
        elif (large.get("width") or 0) >= min_width and large.get("url"):
            v = large
        elif medium.get("url"):  # best available under 1080p; normalize upscales
            v = medium
        else:
            continue
        results.append(
            {
                "id": hit.get("id"),
                "url": v.get("url"),
                "width": v.get("width"),
                "height": v.get("height"),
                "duration": hit.get("duration"),
                "source": "pixabay",
            }
        )
    return results


def download_file(url: str, dest: Path) -> Path:
    ensure_dir(dest.parent)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            tmp = dest.with_suffix(dest.suffix + ".part")
            with open(tmp, "wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
            tmp.replace(dest)
    return dest


def _probe_duration(path: Path) -> float | None:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            text=True,
        ).strip()
        return float(out)
    except Exception:
        return None


def normalize_clip(
    src: Path,
    dest: Path,
    duration: float,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> Path:
    """GPU-friendly normalize: scale + trim + NVENC. Falls back to software scale.

    A cached dest is reused only when its measured duration matches the request
    within ~1 frame, so a VO-retimed scene never picks up a clip cut to a stale
    length (Path A §6 duration-safe caching)."""
    ensure_dir(dest.parent)
    if dest.exists() and dest.stat().st_size > 0:
        have = _probe_duration(dest)
        if have is None or abs(have - duration) <= (1.0 / fps) + 0.05:
            return dest
        # stale length — re-render to the new duration
        dest.unlink(missing_ok=True)

    # Try CUDA path first
    cuda_filter = (
        f"scale_cuda={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}"
    )
    args_cuda = [
        "ffmpeg", "-y",
        "-hwaccel", "cuda",
        "-i", str(src),
        "-t", f"{duration:.3f}",
        "-vf", cuda_filter,
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-b:v", "8M",
        "-an",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        str(dest),
    ]
    proc = subprocess.run(args_cuda, capture_output=True)
    if proc.returncode == 0 and dest.exists():
        return dest

    # Software fallback
    soft_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1"
    )
    args = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-t", f"{duration:.3f}",
        "-vf", soft_filter,
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-b:v", "8M",
        "-an",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        str(dest),
    ]
    subprocess.run(args, check=True, capture_output=True)
    return dest


def resolve_broll(
    broll: dict[str, Any],
    scene_id: int,
    duration: float,
    pipeline_cfg: dict[str, Any] | None = None,
) -> Path:
    """
    Resolve B-roll for a scene.
    Returns path to normalized 1080p clip.
    Raises StockMissError if stock miss and no local/manual asset.
    """
    pipeline_cfg = pipeline_cfg or load_json(project_path("pipeline", "config", "pipeline.json"))
    stock_cfg = pipeline_cfg.get("stock", {})
    cache_dir = ensure_dir(pipeline_cfg.get("assets_cache_dir", "pipeline/assets/cache") + "/broll")
    in_dir = ensure_dir(pipeline_cfg.get("assets_in_dir", "pipeline/assets/in"))

    source = broll.get("source", stock_cfg.get("preferred_source", "pexels"))
    keyword = broll.get("keyword", "")
    fallback_prompt = broll.get("fallback_prompt")
    local_path = broll.get("local_path")

    # Manual / local / generated first (Path B: generated assets are dropped into
    # assets/in/ by the user, so they resolve exactly like manual files — stills
    # loop to a clip, clips normalize).
    if source in ("manual", "local", "generated") or local_path:
        candidate = Path(local_path) if local_path else in_dir / f"scene_{scene_id:02d}.mp4"
        if not candidate.is_absolute():
            candidate = project_path(str(candidate)) if not str(candidate).startswith("pipeline") else project_path(str(candidate))
            if not candidate.exists():
                candidate = in_dir / Path(local_path).name if local_path else in_dir / f"scene_{scene_id:02d}.mp4"
        # Try common extensions
        if not candidate.exists():
            for ext in (".mp4", ".mov", ".png", ".jpg", ".jpeg", ".webm"):
                alt = in_dir / f"scene_{scene_id:02d}{ext}"
                if alt.exists():
                    candidate = alt
                    break
        if not candidate.exists():
            raise StockMissError(keyword or f"scene_{scene_id}", fallback_prompt)
        frames = max(1, int(round(duration * 30)))
        dest = cache_dir / f"norm_scene_{scene_id:02d}_{candidate.stem}_{frames}f.mp4"
        if candidate.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            # Still → short clip via loop
            return _still_to_clip(candidate, dest, duration)
        return normalize_clip(candidate, dest, duration)

    min_width = int(stock_cfg.get("min_width", 1920))
    hits = _search_hits(source, keyword, stock_cfg, min_width, cache_dir)
    if not hits:
        raise StockMissError(keyword, fallback_prompt)

    hit = hits[0]
    raw = _cache_path(cache_dir, keyword, hit["source"], hit["url"])
    download_file(hit["url"], raw)
    frames = max(1, int(round(duration * 30)))
    dest = cache_dir / f"norm_scene_{scene_id:02d}_{raw.stem}_{frames}f.mp4"
    return normalize_clip(raw, dest, duration)


def _search_hits(
    source: str,
    keyword: str,
    stock_cfg: dict[str, Any],
    min_width: int,
    cache_dir: Path,
) -> list[dict[str, Any]]:
    """Run the stock search and return the ranked hit list (shared by the
    single-clip resolver and the multi-clip fetch-to-cover resolver)."""
    hits: list[dict[str, Any]] = []
    if source in ("pexels", "pixabay") and _is_abstract_keyword(keyword):
        pb_key = os.environ.get(stock_cfg.get("pixabay_api_key_env", "PIXABAY_API_KEY"), "")
        if pb_key:
            hits = search_pixabay(keyword, pb_key, min_width=min_width, video_type="animation", cache_dir=cache_dir)
            if not hits:
                hits = search_pixabay(keyword, pb_key, min_width=min_width, video_type="animation", editors_choice=True, cache_dir=cache_dir)
        if not hits:
            p_key = os.environ.get(stock_cfg.get("pexels_api_key_env", "PEXELS_API_KEY"), "")
            if p_key:
                hits = search_pexels(keyword, p_key, min_width=min_width)
        if not hits and not pb_key:
            raise RuntimeError("No stock API key set (PEXELS_API_KEY / PIXABAY_API_KEY)")
    elif source == "pexels":
        key = os.environ.get(stock_cfg.get("pexels_api_key_env", "PEXELS_API_KEY"), "")
        if key:
            hits = search_pexels(keyword, key, min_width=min_width)
        else:
            print("[stock] PEXELS_API_KEY not set — trying Pixabay fallback")
        if not hits:
            pb_key = os.environ.get(stock_cfg.get("pixabay_api_key_env", "PIXABAY_API_KEY"), "")
            if pb_key:
                hits = search_pixabay(keyword, pb_key, min_width=min_width, cache_dir=cache_dir)
                if not hits:
                    hits = search_pixabay(keyword, pb_key, min_width=min_width, editors_choice=True, cache_dir=cache_dir)
        if not hits and not key:
            raise RuntimeError(
                "No stock API key set. Export PEXELS_API_KEY (https://www.pexels.com/api/) "
                "or PIXABAY_API_KEY (https://pixabay.com/api/docs/)"
            )
    elif source == "pixabay":
        key = os.environ.get(stock_cfg.get("pixabay_api_key_env", "PIXABAY_API_KEY"), "")
        if not key:
            raise RuntimeError(
                "PIXABAY_API_KEY not set. Export your free key from https://pixabay.com/api/docs/"
            )
        hits = search_pixabay(keyword, key, min_width=min_width, cache_dir=cache_dir)
        if not hits:
            hits = search_pixabay(keyword, key, min_width=min_width, editors_choice=True, cache_dir=cache_dir)
    else:
        raise ValueError(f"Unknown stock source: {source}")
    return hits


def resolve_broll_segments(
    broll: dict[str, Any],
    scene_id: int,
    duration: float,
    pipeline_cfg: dict[str, Any] | None = None,
    max_clips_per_scene: int = 4,
) -> list[dict[str, Any]]:
    """Fetch-to-cover, trim-to-fit (Path A §5.2): resolve a video scene to an
    ordered list of RAW source segments that together cover `duration` seconds.

    Returns [{path, source_start, target_duration}, ...] — raw downloaded clips
    with per-segment trim targets. Normalization, grade, and joining happen at
    render time in pipeline/render/footage.py (FFmpeg), NOT here, so footage
    never gets baked into a Remotion-bound MP4.

    Strategy (most VidRush-like first):
      1. Trim a longer source down to the VO segment (default).
      2. Source shorter than the segment → hard-cut to additional clips to fill.
      3. Coverage still short → the render layer loops/holds the final clip.
    """
    pipeline_cfg = pipeline_cfg or load_json(project_path("pipeline", "config", "pipeline.json"))
    stock_cfg = pipeline_cfg.get("stock", {})
    cache_dir = ensure_dir(pipeline_cfg.get("assets_cache_dir", "pipeline/assets/cache") + "/broll")
    in_dir = ensure_dir(pipeline_cfg.get("assets_in_dir", "pipeline/assets/in"))

    source = broll.get("source", stock_cfg.get("preferred_source", "pexels"))
    keyword = broll.get("keyword", "")
    fallback_prompt = broll.get("fallback_prompt")
    local_path = broll.get("local_path")

    # Manual / local / generated drop-in: a single clip, trimmed to fit.
    if source in ("manual", "local", "generated") or local_path:
        candidate = Path(local_path) if local_path else in_dir / f"scene_{scene_id:02d}.mp4"
        if not candidate.is_absolute():
            candidate = project_path(str(candidate))
            if not candidate.exists():
                candidate = in_dir / Path(local_path).name if local_path else in_dir / f"scene_{scene_id:02d}.mp4"
        if not candidate.exists():
            for ext in (".mp4", ".mov", ".webm"):
                alt = in_dir / f"scene_{scene_id:02d}{ext}"
                if alt.exists():
                    candidate = alt
                    break
        if not candidate.exists():
            raise StockMissError(keyword or f"scene_{scene_id}", fallback_prompt)
        return [{"path": str(candidate), "source_start": 0.0, "target_duration": duration}]

    min_width = int(stock_cfg.get("min_width", 1920))
    hits = _search_hits(source, keyword, stock_cfg, min_width, cache_dir)
    if not hits:
        raise StockMissError(keyword, fallback_prompt)

    # Walk ranked hits, downloading and accumulating coverage until we reach the
    # target duration. Prefer a single clip that covers the whole segment.
    segments: list[dict[str, Any]] = []
    covered = 0.0
    for hit in hits[: max_clips_per_scene * 2]:  # don't over-download on thin pools
        if covered >= duration or len(segments) >= max_clips_per_scene:
            break
        try:
            raw = _cache_path(cache_dir, keyword, hit["source"], hit["url"])
            download_file(hit["url"], raw)
        except Exception as e:
            print(f"[stock] download failed for {hit.get('url')}: {e} — trying next hit")
            continue
        src_dur = hit.get("duration") or _probe_duration(raw) or 0.0
        if src_dur <= 0:
            continue
        remaining = duration - covered
        take = min(src_dur, remaining)
        segments.append(
            {"path": str(raw), "source_start": 0.0, "target_duration": round(take, 3)}
        )
        covered += take

    if not segments:
        raise StockMissError(keyword, fallback_prompt)
    return segments


def _still_to_clip(src: Path, dest: Path, duration: float) -> Path:
    ensure_dir(dest.parent)
    if dest.exists() and dest.stat().st_size > 0:
        have = _probe_duration(dest)
        if have is None or abs(have - duration) <= (1.0 / 30) + 0.05:
            return dest
        dest.unlink(missing_ok=True)
    args = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(src),
        "-t", f"{duration:.3f}",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1",
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-b:v", "8M",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        str(dest),
    ]
    subprocess.run(args, check=True, capture_output=True)
    return dest

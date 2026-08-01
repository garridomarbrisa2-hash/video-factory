"""FFmpeg real-footage scene renderer (Path A — footage-type router).

A video scene is edited by FFmpeg with MINIMAL work — trim-to-fit, normalize,
and one fixed per-style grade — so FFmpeg's weak typography can never ruin the
theme (text/motion graphics ride in via a separate Remotion alpha overlay, see
orchestrator Option A). Footage never goes through Chrome; Remotion never edits
real footage.

Public API:
  - ffmpeg_grade_filter(style_id) -> FFmpeg -vf grade chain for a style
  - render_footage_scene(segments, style_id, target_duration, out_path)
    -> normalized, graded scene clip of exactly target_duration seconds
"""

from __future__ import annotations

import hashlib
import subprocess
import time
import tempfile
from pathlib import Path
from typing import Any

from pipeline import ensure_dir

FPS = 30
WIDTH = 1920
HEIGHT = 1080


def ffmpeg_capabilities(ffmpeg: str = "ffmpeg") -> set[str]:
    """Return relevant acceleration capabilities advertised by FFmpeg."""
    capabilities: set[str] = set()
    for flag, names in (
        ("-hwaccels", ("cuda",)),
        ("-filters", ("scale_cuda", "crop_cuda")),
        ("-encoders", ("h264_nvenc",)),
    ):
        proc = subprocess.run([ffmpeg, "-hide_banner", flag], capture_output=True, text=True)
        if proc.returncode == 0:
            text = proc.stdout + proc.stderr
            capabilities.update(name for name in names if name in text)
    return capabilities


def build_cuda_normalization_command(
    source: Path,
    output: Path,
    capabilities: set[str] | None = None,
    ffmpeg: str = "ffmpeg",
) -> list[str]:
    """Build single-clip CUDA normalization; creative CPU grades are unsupported."""
    available = ffmpeg_capabilities(ffmpeg) if capabilities is None else capabilities
    required = {"cuda", "scale_cuda", "crop_cuda", "h264_nvenc"}
    if missing := required - available:
        raise RuntimeError(f"CUDA normalization unavailable: missing {', '.join(sorted(missing))}")
    return [
        ffmpeg, "-y", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda",
        "-i", str(source), "-vf",
        f"scale_cuda={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop_cuda={WIDTH}:{HEIGHT}",
        "-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq",
        "-b:v", "8M", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an", str(output),
    ]


def benchmark_command(command: list[str]) -> float:
    """Run one FFmpeg command and return elapsed wall-clock seconds."""
    started = time.perf_counter()
    proc = subprocess.run(command, capture_output=True, text=True)
    elapsed = time.perf_counter() - started
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg benchmark failed:\n{proc.stderr[-1500:]}")
    return elapsed


def benchmark_normalization(source: Path, ffmpeg: str = "ffmpeg") -> dict[str, float | str]:
    """Compare equivalent no-grade CPU/CUDA normalization; report fastest path."""
    capabilities = ffmpeg_capabilities(ffmpeg)
    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)
        cpu = temp_dir / "cpu.mp4"
        gpu = temp_dir / "gpu.mp4"
        cpu_command = [
            ffmpeg, "-y", "-i", str(source), "-vf",
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT}",
            "-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq",
            "-b:v", "8M", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an", str(cpu),
        ]
        cpu_sec = benchmark_command(cpu_command)
        result: dict[str, float | str] = {"cpu_sec": cpu_sec, "selected": "cpu"}
        try:
            cuda_sec = benchmark_command(
                build_cuda_normalization_command(source, gpu, capabilities, ffmpeg)
            )
        except (RuntimeError, OSError):
            return result
        result["cuda_sec"] = cuda_sec
        if cuda_sec < cpu_sec * 0.9:
            result["selected"] = "cuda"
        return result


def ffmpeg_grade_filter(style_id: str) -> str:
    """One boring, fixed FFmpeg grade chain per canonical style.

    These are deliberately simple tonal approximations of the Remotion theme
    grade (which lives in CSS/TS and can't be reproduced 1:1 in FFmpeg). The
    goal is that an image scene and a footage scene sitting side by side do not
    show an obvious grade jump. Values are `design_decision` — tune against a
    representative frame rendered through SceneShell. Kept conservative: grade
    is the ONLY creative op FFmpeg is allowed to do on footage.
    """
    sid = (style_id or "standard").lower()
    # eq=brightness:contrast:saturation  (slightly desaturated, gently crushed)
    table = {
        # silver-desaturated, crushed — crime dossier
        "crime": "eq=brightness=-0.05:contrast=1.10:saturation=0.72",
        # warm, slightly faded archival
        "history": "eq=brightness=-0.02:contrast=1.04:saturation=0.82,colorbalance=rs=0.06:gs=0.03:bs=-0.05",
        # clean, near-neutral, crisp
        "modern": "eq=brightness=0.0:contrast=1.05:saturation=1.00",
        # flat, desaturated, bright
        "minimalist": "eq=brightness=0.02:contrast=0.98:saturation=0.88",
        # neutral reference
        "standard": "eq=brightness=0.0:contrast=1.02:saturation=0.95",
    }
    return table.get(sid, table["standard"])


def _scene_cache_key(segments: list[dict[str, Any]], style_id: str, target_duration: float) -> str:
    raw = "|".join(
        f"{s['path']}:{s.get('source_start', 0)}:{s.get('target_duration', 0)}" for s in segments
    )
    raw += f"|{style_id}|{int(round(target_duration * FPS))}f|{WIDTH}x{HEIGHT}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


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


def render_footage_scene(
    segments: list[dict[str, Any]],
    style_id: str,
    target_duration: float,
    cache_dir: Path,
) -> Path:
    """Render a real-footage scene clip via FFmpeg (trim-to-fit + grade).

    segments: [{path, source_start, target_duration}, ...] from
      stock.resolve_broll_segments (fetch-to-cover). Joined with hard cuts and
      trimmed so the final clip is exactly target_duration seconds. If coverage
      is short, the final segment is looped to fill (never stretched <0.8x).
    Returns the cached/normalized scene clip path.
    """
    if not segments:
        raise ValueError("render_footage_scene: no segments")
    cache_dir = ensure_dir(cache_dir)
    key = _scene_cache_key(segments, style_id, target_duration)
    out = cache_dir / f"footage_{key}.mp4"
    if out.exists() and out.stat().st_size > 0:
        have = _probe_duration(out)
        if have is None or abs(have - target_duration) <= (1.0 / FPS) + 0.05:
            return out
        out.unlink(missing_ok=True)

    grade = ffmpeg_grade_filter(style_id)
    norm = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},format=yuv420p"
    )

    # Build per-segment normalized+graded streams, then hard-concat them, then
    # trim the joined stream to exactly target_duration. CPU filters + NVENC
    # encode (no CUDA filter graph — known-good path only, Path A §7.3).
    inputs: list[str] = []
    for s in segments:
        inputs += ["-ss", f"{float(s.get('source_start', 0)):.3f}", "-i", str(s["path"])]

    fc_parts: list[str] = []
    labels: list[str] = []
    total_coverage = 0.0
    for i, s in enumerate(segments):
        take = float(s.get("target_duration", 0.0))
        # Coverage is bounded by the ACTUAL source length, not the requested take —
        # a 3s clip asked for 4s only yields 3s, so the shortfall must loop-fill.
        src_len = _probe_duration(Path(s["path"]))
        avail = take if src_len is None else min(take, max(0.0, src_len - float(s.get("source_start", 0.0))))
        total_coverage += avail
        lbl = f"n{i}"
        fc_parts.append(f"[{i}:v]trim=0:{take:.3f},setpts=PTS-STARTPTS,{norm},{grade}[{lbl}]")
        labels.append(f"[{lbl}]")

    join = "".join(labels)
    if len(segments) == 1:
        # single segment: video passthrough (anull is AUDIO — use null/copy for video)
        fc_parts.append(f"{labels[0]}null[jv]")
    else:
        fc_parts.append(f"{join}concat=n={len(segments)}:v=1:a=0[jv]")

    # If coverage is short, loop the joined stream to fill, then trim to target.
    if total_coverage < target_duration - 0.01:
        fc_parts.append(f"[jv]loop=loop=-1:size=1[jl]")
        fc_parts.append(f"[jl]trim=0:{target_duration:.3f},setpts=PTS-STARTPTS[vout]")
    else:
        fc_parts.append(f"[jv]trim=0:{target_duration:.3f},setpts=PTS-STARTPTS[vout]")

    filter_complex = ";".join(fc_parts)
    args = (
        ["ffmpeg", "-y"]
        + inputs
        + [
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq",
            "-b:v", "8M", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-an",
            str(out),
        ]
    )
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"footage scene ffmpeg failed:\n{proc.stderr[-1500:]}")
    return out

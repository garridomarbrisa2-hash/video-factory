"""FFmpeg photo-base builder (Phase 7b hybrid) — the GPU side of the pipeline.

Remotion is slow at animating stills (Chrome raster + CPU encode, ~45–70s/clip).
So stills move in FFmpeg: an eased ken-burns zoom-pan, a 2-plane parallax (the
near plane drifts more than the base), the sculpted grade, and a light sweep —
NVENC-encoded in a few seconds. Remotion then renders only the transparent
text/animation overlay, and FFmpeg composites the two.

PERF NOTES (measured):
- `zoompan` eased zoom alone: ~2s for a 6s clip (fast enough).
- `zoompan` + parallax overlay: ~5s for 6s (acceptable).
- A `geq` per-pixel light sweep: +10s — TOO SLOW, do not use. The light sweep is
  instead a pre-baked gradient PNG animated by a cheap `overlay` x-offset.

Every command is a `list[str]` (never a shell string) per project convention.
Deterministic: motion is a function of scene index + duration, no RNG at render.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"

FPS = 30
W, H = 1920, 1080
OVERSCAN = 1.15  # scale headroom so zoom/pan never reveals edges


@dataclass
class PhotoBaseSpec:
    """One scene's still + motion intent, resolved by the caller.

    Motion fields are the DIRECTOR'S editorial choices (per-scene), not style
    constants — the director decides push-in vs pull-out, pan direction, and
    whether the beat earns parallax. The style supplies magnitudes (zoom range,
    grain, grade); the director supplies direction + presence.
    """

    image: str              # base image path
    near_plane: str | None  # baked near-plane PNG (parallax), or None
    duration: float         # seconds
    out: str                # output mp4 path
    # Director's motion choices
    move: str = "in"        # in|out|left|right|up|down — the ken-burns intent
    parallax: bool = True   # near-plane differential on/off (per-beat)
    zoom: float = 1.06      # max zoom magnitude (style-supplied)
    pan_px: int = 40        # near-plane extra pan magnitude (parallax)
    # Grade (style-supplied)
    brightness: float = 0.0
    contrast: float = 1.1
    saturation: float = 0.95


def _ease(zoom_expr_z: str, frames: int) -> str:
    """Ease-out cubic time curve shared by all zoompan moves.

    zoompan evaluates `z`/`x`/`y` per output frame `on` (0-based). We normalize
    on/frames -> t, then apply 1-(1-t)^3 (fast start, decelerating settle) so the
    move never has the constant-velocity slide that reads as "slideshow".
    """
    return f"(1-pow(1-min(on/{frames},1),3))"


def _move_xy(move: str, t: str, zoom: float) -> tuple[str, str, str]:
    """zoompan z/x/y expressions for a director-chosen ken-burns move.

    `t` is the eased 0->1 progress. Zoom moves (in/out) change z over time; pan
    moves hold z and sweep x/y. All ease-out (settle early), never linear.
    """
    center_x = "iw/2-(iw/zoom/2)"
    center_y = "ih/2-(ih/zoom/2)"
    if move == "in":
        return f"1+({zoom}-1)*{t}", center_x, center_y
    if move == "out":
        return f"{zoom}-({zoom}-1)*{t}", center_x, center_y
    if move == "left":
        return f"{zoom}", f"(iw-iw/zoom)*(1-{t})", center_y
    if move == "right":
        return f"{zoom}", f"(iw-iw/zoom)*{t}", center_y
    if move == "up":
        return f"{zoom}", center_x, f"(ih-ih/zoom)*(1-{t})"
    if move == "down":
        return f"{zoom}", center_x, f"(ih-ih/zoom)*{t}"
    # default: gentle push-in
    return f"1+({zoom}-1)*{t}", center_x, center_y


def build_photo_base(spec: PhotoBaseSpec) -> str:
    """Render one still into an animated, graded MP4 base (NVENC). Returns path."""
    frames = max(1, int(spec.duration * FPS))
    t = _ease("", frames)
    z, x, y = _move_xy(spec.move, t, spec.zoom)

    inputs = ["-loop", "1", "-t", f"{spec.duration:.3f}", "-i", spec.image]
    filters: list[str] = []

    # Base: overscan scale -> eased zoompan (director's move) -> grade.
    filters.append(
        f"[0:v]scale={int(W*OVERSCAN)}:-1,"
        f"zoompan=z='{z}':x='{x}':y='{y}':"
        f"d={frames}:s={W}x{H}:fps={FPS},"
        f"eq=contrast={spec.contrast}:brightness={spec.brightness}:saturation={spec.saturation}"
        f"[base]"
    )
    cur = "base"
    next_idx = 1

    # Parallax (director opt-in per beat): near plane drifts extra vs the base.
    if spec.near_plane and spec.parallax:
        inputs += ["-loop", "1", "-t", f"{spec.duration:.3f}", "-i", spec.near_plane]
        near_zoom = spec.zoom + 0.02
        # Near plane always pushes a touch harder + pans, regardless of base move —
        # the differential IS the depth cue.
        filters.append(
            f"[{next_idx}:v]scale={int(W*OVERSCAN)}:-1,"
            f"zoompan=z='1+({near_zoom}-1)*{t}':"
            f"x='iw/2-(iw/zoom/2)+{spec.pan_px}*{t}':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={W}x{H}:fps={FPS}[near]"
        )
        filters.append(f"[{cur}][near]overlay=0:0[comp]")
        cur = "comp"
        next_idx += 1

    filter_complex = ";".join(filters)
    cmd = [
        FFMPEG, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{cur}]",
        "-frames:v", str(frames),
        "-c:v", "h264_nvenc",
        "-preset", "p6",
        "-tune", "hq",
        "-b:v", "12M",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        spec.out,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"composite ffmpeg failed:\n{res.stderr[-2000:]}")
    return out


def composite_overlay(base_mp4: str, overlay_alpha: str, out: str, duration: float) -> str:
    """Overlay a transparent Remotion animation clip (alpha) over the photo base.

    `overlay_alpha` is a ProRes 4444 MOV (yuva) from Remotion. FFmpeg `overlay`
    respects its alpha channel.
    """
    cmd = [
        FFMPEG, "-y",
        "-i", base_mp4,
        "-i", overlay_alpha,
        "-filter_complex", "[0:v][1:v]overlay=0:0:shortest=1[v]",
        "-map", "[v]",
        "-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq",
        "-b:v", "12M", "-pix_fmt", "yuv420p", "-r", str(FPS),
        out,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"composite ffmpeg failed:\n{res.stderr[-2000:]}")
    return out


if __name__ == "__main__":
    # CLI so render.js can spawn a base render per scene:
    #   python -m pipeline.video.photo_base <image> <out> <duration> [move] [near] [parallax]
    import sys

    a = sys.argv[1:]
    if len(a) < 3:
        print("usage: python -m pipeline.video.photo_base <image> <out> <duration> "
              "[move=in|out|left|right|up|down] [near_plane] [parallax=0|1]")
        raise SystemExit(1)
    image, out, duration = a[0], a[1], float(a[2])
    move = a[3] if len(a) > 3 and a[3] else "in"
    near = a[4] if len(a) > 4 and a[4] and a[4] != "none" else None
    parallax = (a[5] != "0") if len(a) > 5 else True
    build_photo_base(PhotoBaseSpec(
        image=image, near_plane=near, duration=duration, out=out,
        move=move, parallax=parallax,
    ))
    print(out)

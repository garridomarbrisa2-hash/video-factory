"""Validated local hard-cut assembly."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def probe_clip(path: Path, ffprobe: str = "ffprobe") -> dict[str, Any]:
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=codec_name,width,height,pix_fmt,r_frame_rate,time_base", "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise ValueError(f"Cannot probe clip {path}: {proc.stderr.strip()}")
    streams = json.loads(proc.stdout).get("streams", [])
    if not streams:
        raise ValueError(f"Clip has no video stream: {path}")
    return streams[0]


def validate_compatible_clips(clips: list[Path], ffprobe: str = "ffprobe") -> dict[str, Any]:
    if not clips:
        raise ValueError("No clips to assemble")
    signatures = [probe_clip(Path(clip), ffprobe) for clip in clips]
    if any(signature != signatures[0] for signature in signatures[1:]):
        raise ValueError("Hard-cut stream copy requires identical video stream signatures")
    return signatures[0]


def assemble_clips(
    clips: list[Path],
    output: Path,
    transition_intents: list[str | None] | None = None,
    *,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> Path:
    """Assemble compatible all-hard-cut clips with concat demuxer stream copy."""
    intents = transition_intents or ["cut"] * max(0, len(clips) - 1)
    if len(intents) != max(0, len(clips) - 1):
        raise ValueError("transition_intents must contain one entry per cut")
    if any(intent not in (None, "cut", "hard_cut") for intent in intents):
        raise ValueError("assemble_clips supports hard cuts only")
    validate_compatible_clips(clips, ffprobe)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as handle:
        concat_path = Path(handle.name)
        for clip in clips:
            escaped = str(Path(clip).resolve()).replace("'", "'\\''")
            handle.write(f"file '{escaped}'\n")
    try:
        proc = subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path),
             "-c", "copy", str(output)], capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"hard-cut assembly failed:\n{proc.stderr[-1500:]}")
    finally:
        concat_path.unlink(missing_ok=True)
    return output

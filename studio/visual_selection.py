"""Automatically assemble a stock-first, permission-aware visual shot list."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from studio.media_search import _tokens


STOCK_PROVIDERS = {"pexels", "pixabay"}
AUTHORIZED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
MAX_AUTHORIZED_CLIPS = 10


def _safe_video_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    return value.strip()


def _candidate_score(
    scene: dict[str, Any], candidate: dict[str, Any], used: set[str]
) -> tuple[int, int, int, int]:
    identity = f"{candidate.get('provider')}:{candidate.get('id')}"
    wanted = _tokens(str(scene.get("query") or ""))
    searchable = " ".join(
        str(candidate.get(field) or "")
        for field in ("matched_query", "title", "description", "tags")
    )
    overlap = len(wanted & _tokens(searchable))
    width = int(candidate.get("width") or 0)
    height = int(candidate.get("height") or 0)
    suitable_resolution = int(width >= 1280 and height >= 720)
    suitable_duration = int(float(candidate.get("duration_sec") or 0) >= 3)
    return int(identity not in used), overlap, suitable_resolution, suitable_duration


def _automatic_window(identity: str, duration: float, desired: float = 5.0) -> tuple[float, float]:
    if duration <= 0:
        return 0.0, round(desired, 3)
    length = min(max(3.0, desired), 5.0, duration)
    remaining = max(0.0, duration - length)
    if remaining <= 0:
        return 0.0, round(length, 3)
    digest = int.from_bytes(hashlib.sha256(identity.encode("utf-8")).digest()[:4], "big")
    fraction = 0.15 + (digest / (2**32 - 1)) * 0.7
    start = round(remaining * fraction, 3)
    return start, round(min(duration, start + length), 3)


def _probe_duration(path: Path) -> float:
    binary = shutil.which("ffprobe")
    if not binary:
        raise RuntimeError("ffprobe não está disponível para analisar arquivos autorizados.")
    result = subprocess.run(
        [binary, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return float(json.loads(result.stdout).get("format", {}).get("duration") or 0)


def _scene_boundaries(path: Path) -> list[float]:
    binary = shutil.which("ffmpeg")
    if not binary:
        return []
    try:
        result = subprocess.run(
            [
                binary,
                "-hide_banner",
                "-i",
                str(path),
                "-vf",
                "select=gt(scene\\,0.32),showinfo",
                "-frames:v",
                "24",
                "-an",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return [float(value) for value in re.findall(r"pts_time:\s*([0-9.]+)", result.stderr)]


def _extract_authorized_clip(
    project_root: Path, project_dir: Path, episode: int, source: Path, scene: dict[str, Any]
) -> dict[str, Any]:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("ffmpeg não está disponível para recortar arquivos autorizados.")
    duration = _probe_duration(source)
    if duration < 3:
        raise RuntimeError("O arquivo autorizado possui menos de 3 segundos.")
    scene_id = int(scene["scene_id"])
    start, end = _automatic_window(f"{source.name}:{scene_id}", duration)
    valid_boundaries = [point for point in _scene_boundaries(source) if point + 3 <= duration]
    if valid_boundaries:
        start = min(valid_boundaries, key=lambda point: abs(point - start))
        end = min(duration, start + 5)
    output_dir = project_dir / "assets" / "authorized-clips"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "-", source.stem)[:48] or "authorized"
    output = output_dir / f"Ep{episode}_scene_{scene_id:03d}_{safe_name}.mp4"
    temporary = output.with_name(f"{output.stem}.partial.mp4")
    try:
        subprocess.run(
            [
                binary,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{start:.3f}",
                "-i",
                str(source),
                "-t",
                f"{end - start:.3f}",
                "-an",
                "-c:v",
                "libx264",
                "-movflags",
                "+faststart",
                str(temporary),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "scene_id": scene_id,
        "provider": "authorized_local",
        "source_file": str(source.relative_to(project_root)),
        "media_path": str(output.relative_to(project_root)),
        "start_seconds": round(start, 3),
        "end_seconds": round(end, 3),
        "rights_basis": "user_supplied_authorized_media",
    }


def _authorized_local_clips(
    project_root: Path, project_dir: Path, episode: int, scenes: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    authorized_dir = project_dir / "assets" / "authorized"
    if not authorized_dir.is_dir() or authorized_dir.is_symlink() or not scenes:
        return [], []
    clips: list[dict[str, Any]] = []
    warnings: list[str] = []
    assigned: set[int] = set()
    sources = (
        path
        for path in sorted(authorized_dir.iterdir())
        if path.is_file() and not path.is_symlink() and path.suffix.lower() in AUTHORIZED_EXTENSIONS
    )
    for source in sources:
        if len(clips) >= MAX_AUTHORIZED_CLIPS:
            break
        available = [scene for scene in scenes if int(scene["scene_id"]) not in assigned]
        if not available:
            break
        source_tokens = _tokens(source.stem.replace("-", " ").replace("_", " "))
        selected = max(
            available,
            key=lambda scene: len(source_tokens & _tokens(str(scene.get("context") or ""))),
        )
        try:
            clips.append(_extract_authorized_clip(project_root, project_dir, episode, source, selected))
            assigned.add(int(selected["scene_id"]))
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError):
            warnings.append(f"Não foi possível analisar o arquivo autorizado {source.name}.")
    return clips, warnings


def select_visual_assets(
    project_root: Path, project_slug: str, episode: int, *, refresh: bool = False
) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9-]{1,64}", project_slug) or not 1 <= episode <= 999:
        raise ValueError("Projeto ou episódio inválido.")
    project_dir = project_root / "projects" / project_slug
    candidates_path = project_dir / f"Ep{episode}_media_candidates.json"
    output_path = project_dir / f"Ep{episode}_visual_selection.json"
    if not candidates_path.is_file():
        raise ValueError("Faça primeiro a busca dos elementos visuais.")
    if output_path.exists() and not refresh:
        raise ValueError("Este episódio já possui uma seleção visual salva.")

    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    scenes = [scene for scene in candidates.get("scenes", []) if isinstance(scene, dict)]
    if not scenes:
        raise ValueError("A busca de mídia não possui cenas para selecionar.")

    selected: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    used: set[str] = set()
    counts = {"pexels": 0, "pixabay": 0}
    for scene in scenes:
        scene_id = int(scene.get("scene_id") or 0)
        stock = [
            item
            for item in scene.get("candidates", [])
            if isinstance(item, dict)
            and item.get("provider") in STOCK_PROVIDERS
            and _safe_video_url(item.get("video_url"))
        ]
        for item in scene.get("candidates", []):
            if isinstance(item, dict) and item.get("provider") == "youtube":
                references.append({
                    "scene_id": scene_id,
                    "title": str(item.get("title") or ""),
                    "youtube_url": str(item.get("youtube_url") or ""),
                    "status": "reference_only_requires_authorized_access",
                })
        if not stock:
            selected.append({
                "scene_id": scene_id,
                "query": str(scene.get("query") or ""),
                "status": "missing_authorized_stock",
            })
            continue
        chosen = max(stock, key=lambda item: _candidate_score(scene, item, used))
        provider = str(chosen["provider"])
        identity = f"{provider}:{chosen.get('id')}"
        used.add(identity)
        counts[provider] += 1
        start, end = _automatic_window(
            f"{identity}:{scene_id}", float(chosen.get("duration_sec") or 0)
        )
        selected.append({
            "scene_id": scene_id,
            "query": str(scene.get("query") or ""),
            "status": "selected",
            "provider": provider,
            "source_id": str(chosen.get("id") or ""),
            "video_url": chosen["video_url"],
            "source_page": chosen.get(f"{provider}_url"),
            "creator": chosen.get("creator"),
            "start_seconds": start,
            "end_seconds": end,
            "selection_reason": "contextual_stock_match",
        })

    local_clips, warnings = _authorized_local_clips(project_root, project_dir, episode, scenes)
    payload = {
        "strategy": "automatic-stock-first-authorized-local",
        "downloaded_stock_media": False,
        "youtube_policy": "reference_only_when_remote_access_is_denied",
        "provider_counts": counts,
        "scenes": selected,
        "youtube_references": references[:MAX_AUTHORIZED_CLIPS],
        "authorized_local_clips": local_clips,
        "warnings": warnings,
    }
    temporary = output_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output_path)
    selected_count = sum(item.get("status") == "selected" for item in selected)
    return {
        "ok": True,
        "scene_count": len(selected),
        "selected_count": selected_count,
        "missing_count": len(selected) - selected_count,
        "provider_counts": counts,
        "authorized_local_clip_count": len(local_clips),
        "youtube_reference_count": min(len(references), MAX_AUTHORIZED_CLIPS),
        "warnings": warnings,
        "path": str(output_path.relative_to(project_root)),
        "message": "Cenas escolhidas automaticamente, priorizando Pexels e Pixabay.",
    }

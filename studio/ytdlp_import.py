"""Permission-gated YouTube clip import through the local yt-dlp binary."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


class YouTubeImportError(RuntimeError):
    """A safe, user-facing yt-dlp import failure."""


def installed_version() -> str | None:
    binary = shutil.which("yt-dlp")
    if not binary:
        return None
    try:
        result = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=15, check=True
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip().splitlines()[0] if result.stdout.strip() else None


def _youtube_id(url: str) -> str | None:
    patterns = (
        r"^https://(?:www\.|m\.)?youtube\.com/watch\?(?:[^#]*&)?v=([A-Za-z0-9_-]{11})(?:[&#].*)?$",
        r"^https://youtu\.be/([A-Za-z0-9_-]{11})(?:[?&#].*)?$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, url.strip())
        if match:
            return match.group(1)
    return None


def _candidate_for_scene(project_dir: Path, episode: int, scene_id: int, url: str) -> dict[str, Any]:
    path = project_dir / f"Ep{episode}_media_candidates.json"
    if not path.is_file():
        raise ValueError("Faça primeiro a busca dos elementos visuais.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    for scene in payload.get("scenes") or []:
        if int(scene.get("scene_id") or 0) != scene_id:
            continue
        for candidate in scene.get("candidates") or []:
            if candidate.get("youtube_url") == url:
                return candidate
    raise ValueError("Esse vídeo não pertence aos candidatos encontrados para a cena.")


def import_authorized_clip(
    project_root: Path,
    project_slug: str,
    episode: int,
    *,
    scene_id: int,
    youtube_url: str,
    start_seconds: float,
    end_seconds: float,
    rights_confirmed: bool,
) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9-]{1,64}", project_slug) or not 1 <= episode <= 999:
        raise ValueError("Projeto ou episódio inválido.")
    if not rights_confirmed:
        raise ValueError("Confirme que você possui autorização para usar esse trecho.")
    if not 1 <= scene_id <= 9999:
        raise ValueError("Cena inválida.")
    video_id = _youtube_id(youtube_url)
    if not video_id:
        raise ValueError("Use um link válido de vídeo do YouTube.")
    if start_seconds < 0 or end_seconds <= start_seconds or end_seconds - start_seconds > 5:
        raise ValueError("Escolha um trecho de até 5 segundos, com início e fim válidos.")
    binary = shutil.which("yt-dlp")
    if not binary:
        raise YouTubeImportError("O yt-dlp ainda não está instalado neste Mac.")

    project_dir = project_root / "projects" / project_slug
    candidate = _candidate_for_scene(project_dir, episode, scene_id, youtube_url)
    output_dir = project_dir / "assets" / "youtube"
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"Ep{episode}_scene_{scene_id:03d}_{video_id}"
    output_template = output_dir / f"{stem}.%(ext)s"
    command = [
        binary,
        "--no-playlist",
        "--no-overwrites",
        "--restrict-filenames",
        "--download-sections",
        f"*{start_seconds:.3f}-{end_seconds:.3f}",
        "--force-keyframes-at-cuts",
        "--merge-output-format",
        "mp4",
        "--remux-video",
        "mp4",
        "-f",
        "bv*[height<=1080]+ba/b[height<=1080]",
        "-o",
        str(output_template),
        youtube_url,
    ]
    try:
        subprocess.run(command, capture_output=True, text=True, timeout=900, check=True)
    except subprocess.TimeoutExpired as exc:
        raise YouTubeImportError("O download demorou demais e foi interrompido.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").lower()
        if "sign in" in detail or "cookies" in detail:
            message = "O YouTube exige login para esse vídeo. Escolha outro candidato."
        elif "unavailable" in detail or "private" in detail:
            message = "Esse vídeo não está disponível para importação."
        else:
            message = "Não foi possível importar esse trecho do YouTube."
        raise YouTubeImportError(message) from exc

    files = sorted(output_dir.glob(f"{stem}.*"))
    media = next((path for path in files if path.suffix.lower() in {".mp4", ".mkv", ".webm"}), None)
    if media is None:
        raise YouTubeImportError("O yt-dlp terminou, mas não criou o arquivo esperado.")
    metadata = {
        "source": "youtube",
        "youtube_url": youtube_url,
        "video_id": video_id,
        "title": candidate.get("title"),
        "channel": candidate.get("channel"),
        "scene_id": scene_id,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "rights_confirmed": True,
        "license_filter": candidate.get("license_filter"),
        "media_path": str(media.relative_to(project_root)),
    }
    metadata_path = output_dir / f"{stem}.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "scene_id": scene_id,
        "duration_seconds": round(end_seconds - start_seconds, 3),
        "media_path": metadata["media_path"],
        "metadata_path": str(metadata_path.relative_to(project_root)),
    }

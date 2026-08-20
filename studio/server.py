"""Zero-dependency local web interface for Video Factory.

Run from the repository root:
    python -m studio.server

The server binds to localhost only. The first milestone creates a safe episode
brief; rendering and paid API calls are deliberately not started here.
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import unicodedata
import webbrowser
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pipeline.intelligence.select_style import load_style, select_style
from studio.anthropic import (
    AnthropicConnectionError,
    configured_key,
    masked_key,
    save_key,
    test_connection,
)
from studio.script_generation import generate_script
from studio.script_review import review_script
from studio.elevenlabs import (
    ElevenLabsConnectionError,
    configured_settings as configured_elevenlabs,
    masked_key as masked_elevenlabs_key,
    save_settings as save_elevenlabs_settings,
    test_connection as test_elevenlabs_connection,
)
from studio.narration import NarrationError, generate_narration
from studio.director import generate_direction
from studio.pexels import (
    PexelsConnectionError,
    configured_key as configured_pexels_key,
    masked_key as masked_pexels_key,
    save_key as save_pexels_key,
    test_connection as test_pexels_connection,
)
from studio.pixabay import (
    PixabayConnectionError,
    configured_key as configured_pixabay_key,
    masked_key as masked_pixabay_key,
    save_key as save_pixabay_key,
    test_connection as test_pixabay_connection,
)
from studio.youtube import (
    YouTubeConnectionError,
    configured_key as configured_youtube_key,
    masked_key as masked_youtube_key,
    save_key as save_youtube_key,
    test_connection as test_youtube_connection,
)
from studio.media_search import find_media_candidates


ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / "static"
MAX_BODY_BYTES = 64 * 1024
STYLE_IDS = ("crime", "history", "modern", "minimalist", "standard")
LANGUAGES = {"pt-BR", "es", "en"}
ASSET_MODES = {"auto", "stock", "generated"}


def _slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:56] or "novo-projeto"


def _clean_line(value: Any, *, limit: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text[:limit]


def _validate_project(data: dict[str, Any]) -> dict[str, Any]:
    topic = _clean_line(data.get("topic"), limit=500)
    if len(topic) < 8:
        raise ValueError("Descreva o assunto do vídeo com pelo menos 8 caracteres.")

    language = _clean_line(data.get("language") or "pt-BR", limit=10)
    if language not in LANGUAGES:
        raise ValueError("Idioma inválido.")

    try:
        duration = int(data.get("duration", 8))
    except (TypeError, ValueError) as exc:
        raise ValueError("Duração inválida.") from exc
    if duration < 8 or duration > 20:
        raise ValueError("Este gerador trabalha com vídeos de 8 a 20 minutos.")

    requested_style = _clean_line(data.get("style") or "auto", limit=20)
    if requested_style != "auto" and requested_style not in STYLE_IDS:
        raise ValueError("Estilo visual inválido.")

    asset_mode = _clean_line(data.get("asset_mode") or "auto", limit=20)
    if asset_mode not in ASSET_MODES:
        raise ValueError("Modo de imagens inválido.")

    suggested_style, scores = select_style(topic, return_scores=True)
    style = suggested_style if requested_style == "auto" else requested_style
    return {
        "topic": topic,
        "language": language,
        "duration": duration,
        "style": style,
        "requested_style": requested_style,
        "asset_mode": asset_mode,
        "scores": scores,
    }


def _next_episode(project_dir: Path) -> int:
    numbers = []
    for path in project_dir.glob("Ep*.md"):
        match = re.fullmatch(r"Ep(\d+)\.md", path.name)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def create_project(data: dict[str, Any]) -> dict[str, Any]:
    project = _validate_project(data)
    slug = _slugify(_clean_line(data.get("name") or project["topic"], limit=100))
    project_dir = ROOT / "projects" / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    episode = _next_episode(project_dir)
    brief_path = project_dir / f"Ep{episode}.md"

    style_data = load_style(project["style"])
    style_label = style_data.get("label") or style_data.get("name") or project["style"].title()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    brief = f"""# Episódio {episode}

status: brief
created_at: {created_at}
language: {project['language']}
target_duration_min: {project['duration']}
global_style: {project['style']}
asset_mode: {project['asset_mode']}

## Assunto

{project['topic']}

## Direção inicial

- Estilo visual: {style_label}
- O roteiro ainda não foi criado.
- Nenhuma API foi chamada.
- Nenhum vídeo foi renderizado.
"""
    brief_path.write_text(brief, encoding="utf-8")

    tracker_path = project_dir / "tracker.md"
    if not tracker_path.exists():
        tracker_path.write_text(
            f"# {slug}\n\n- [ ] Ep{episode}: brief criado\n",
            encoding="utf-8",
        )
    else:
        with tracker_path.open("a", encoding="utf-8") as tracker:
            tracker.write(f"- [ ] Ep{episode}: brief criado\n")

    return {
        "ok": True,
        "project": slug,
        "episode": episode,
        "style": project["style"],
        "style_label": style_label,
        "brief_path": str(brief_path.relative_to(ROOT)),
        "message": "Projeto criado. Nenhuma API foi chamada e nenhum vídeo foi renderizado.",
    }


def recent_episodes(limit: int = 8) -> list[dict[str, Any]]:
    episodes: list[dict[str, Any]] = []
    projects_dir = ROOT / "projects"
    if not projects_dir.exists():
        return episodes
    for brief in projects_dir.glob("*/Ep*.md"):
        match = re.fullmatch(r"Ep(\d+)\.md", brief.name)
        if not match:
            continue
        episode = int(match.group(1))
        project_dir = brief.parent
        script = project_dir / f"Ep{episode}_script.md"
        reviewed = project_dir / f"Ep{episode}_reviewed.md"
        narration = project_dir / f"Ep{episode}_narration.mp3"
        direction = project_dir / f"Ep{episode}_director.json"
        media_candidates = project_dir / f"Ep{episode}_media_candidates.json"
        if not script.exists():
            continue
        topic = ""
        text = brief.read_text(encoding="utf-8", errors="ignore")
        topic_match = re.search(r"^## Assunto\s*\n+(.+?)(?=\n## |\Z)", text, re.M | re.S)
        if topic_match:
            topic = " ".join(topic_match.group(1).split())
        episodes.append(
            {
                "project": project_dir.name,
                "episode": episode,
                "topic": topic or project_dir.name.replace("-", " ").title(),
                "reviewed": reviewed.exists(),
                "narration": narration.exists(),
                "direction": direction.exists(),
                "media_candidates": media_candidates.exists(),
                "modified": script.stat().st_mtime,
            }
        )
    episodes.sort(key=lambda item: item["modified"], reverse=True)
    for item in episodes:
        item.pop("modified", None)
    return episodes[:limit]


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "VideoFactoryStudio/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[studio] {self.address_string()} - {fmt % args}")

    def _json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _static(self, filename: str, content_type: str) -> None:
        path = STATIC / filename
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        raw = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(raw)

    def _audio(self, project_slug: str, episode: int) -> None:
        path = ROOT / "projects" / project_slug / f"Ep{episode}_narration.mp3"
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        raw = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        audio_match = re.fullmatch(
            r"/api/projects/([a-z0-9-]{1,64})/episodes/(\d+)/narration/audio", path
        )
        if path == "/":
            self._static("index.html", "text/html; charset=utf-8")
        elif path == "/styles.css":
            self._static("styles.css", "text/css; charset=utf-8")
        elif path == "/app.js":
            self._static("app.js", "text/javascript; charset=utf-8")
        elif path == "/api/health":
            self._json({"ok": True, "stage": "multi-source-media-search", "version": "1.0"})
        elif path == "/api/styles":
            styles = []
            for style_id in STYLE_IDS:
                data = load_style(style_id)
                styles.append(
                    {
                        "id": style_id,
                        "label": data.get("label") or data.get("name") or style_id.title(),
                        "description": data.get("description") or "",
                    }
                )
            self._json({"styles": styles})
        elif path == "/api/settings":
            key = configured_key(ROOT)
            elevenlabs = configured_elevenlabs(ROOT)
            pexels = configured_pexels_key(ROOT)
            pixabay = configured_pixabay_key(ROOT)
            youtube = configured_youtube_key(ROOT)
            self._json(
                {
                    "anthropic": {
                        "configured": bool(key),
                        "masked_key": masked_key(key) if key else None,
                    },
                    "elevenlabs": {
                        "configured": bool(elevenlabs),
                        "masked_key": masked_elevenlabs_key(elevenlabs["api_key"]) if elevenlabs else None,
                        "voice_id": elevenlabs["voice_id"] if elevenlabs else None,
                        "voice_name": elevenlabs["voice_name"] if elevenlabs else None,
                    },
                    "pexels": {
                        "configured": bool(pexels),
                        "masked_key": masked_pexels_key(pexels) if pexels else None,
                    },
                    "pixabay": {
                        "configured": bool(pixabay),
                        "masked_key": masked_pixabay_key(pixabay) if pixabay else None,
                    },
                    "youtube": {
                        "configured": bool(youtube),
                        "masked_key": masked_youtube_key(youtube) if youtube else None,
                    },
                }
            )
        elif path == "/api/projects/recent":
            self._json({"episodes": recent_episodes()})
        elif audio_match:
            self._audio(audio_match.group(1), int(audio_match.group(2)))
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        script_match = re.fullmatch(
            r"/api/projects/([a-z0-9-]{1,64})/episodes/(\d+)/script", path
        )
        review_match = re.fullmatch(
            r"/api/projects/([a-z0-9-]{1,64})/episodes/(\d+)/review", path
        )
        narration_match = re.fullmatch(
            r"/api/projects/([a-z0-9-]{1,64})/episodes/(\d+)/narration", path
        )
        director_match = re.fullmatch(
            r"/api/projects/([a-z0-9-]{1,64})/episodes/(\d+)/director", path
        )
        media_match = re.fullmatch(
            r"/api/projects/([a-z0-9-]{1,64})/episodes/(\d+)/media-search", path
        )
        settings_paths = {
            "/api/projects", "/api/settings/anthropic", "/api/settings/elevenlabs",
            "/api/settings/pexels", "/api/settings/pixabay", "/api/settings/youtube",
        }
        if path not in settings_paths and not script_match and not review_match and not narration_match and not director_match and not media_match:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValueError("Pedido vazio ou grande demais.")
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("Formato inválido.")
            if media_match:
                self._json(
                    find_media_candidates(
                        ROOT, media_match.group(1), int(media_match.group(2))
                    ),
                    HTTPStatus.CREATED,
                )
            elif director_match:
                key = configured_key(ROOT)
                if not key:
                    raise ValueError("Configure a API da Anthropic antes de usar o Diretor.")
                self._json(
                    generate_direction(
                        ROOT, director_match.group(1), int(director_match.group(2)), key
                    ),
                    HTTPStatus.CREATED,
                )
            elif narration_match:
                if not configured_elevenlabs(ROOT):
                    raise ValueError("Configure a ElevenLabs antes de gerar a narração.")
                self._json(
                    generate_narration(
                        ROOT, narration_match.group(1), int(narration_match.group(2))
                    ),
                    HTTPStatus.CREATED,
                )
            elif script_match or review_match:
                key = configured_key(ROOT)
                if not key:
                    raise ValueError("Configure a API da Anthropic antes de usar a IA.")
                match = script_match or review_match
                operation = generate_script if script_match else review_script
                self._json(
                    operation(
                        ROOT,
                        match.group(1),
                        int(match.group(2)),
                        key,
                    ),
                    HTTPStatus.CREATED,
                )
            elif path == "/api/settings/anthropic":
                key = str(body.get("api_key") or "")
                connection = test_connection(key)
                save_key(ROOT, key)
                self._json(
                    {
                        "ok": True,
                        "configured": True,
                        "masked_key": masked_key(key.strip()),
                        "model_count": connection["model_count"],
                        "message": "Conexão confirmada. A chave ficou salva somente neste Mac.",
                    }
                )
            elif path == "/api/settings/elevenlabs":
                key = str(body.get("api_key") or "")
                connection = test_elevenlabs_connection(key)
                requested_voice = str(body.get("voice_id") or "")
                if not requested_voice:
                    self._json(
                        {
                            "ok": True,
                            "configured": False,
                            "voices": connection["voices"],
                            "message": "Conexão confirmada. Agora escolha a voz.",
                        }
                    )
                    return
                selected = next(
                    (voice for voice in connection["voices"] if voice["voice_id"] == requested_voice),
                    connection["voices"][0],
                )
                save_elevenlabs_settings(
                    ROOT, key, selected["voice_id"], selected["name"]
                )
                self._json(
                    {
                        "ok": True,
                        "configured": True,
                        "masked_key": masked_elevenlabs_key(key.strip()),
                        "voice_id": selected["voice_id"],
                        "voice_name": selected["name"],
                        "voices": connection["voices"],
                        "message": "ElevenLabs conectada. A chave ficou salva somente neste Mac.",
                    }
                )
            elif path == "/api/settings/pexels":
                key = str(body.get("api_key") or "")
                test_pexels_connection(key)
                save_pexels_key(ROOT, key)
                self._json({"ok": True, "configured": True, "masked_key": masked_pexels_key(key.strip()), "message": "Pexels conectado. A chave ficou salva somente neste Mac."})
            elif path == "/api/settings/pixabay":
                key = str(body.get("api_key") or "")
                test_pixabay_connection(key)
                save_pixabay_key(ROOT, key)
                self._json({"ok": True, "configured": True, "masked_key": masked_pixabay_key(key.strip()), "message": "Pixabay conectado. A chave ficou salva somente neste Mac."})
            elif path == "/api/settings/youtube":
                key = str(body.get("api_key") or "")
                test_youtube_connection(key)
                save_youtube_key(ROOT, key)
                self._json({"ok": True, "configured": True, "masked_key": masked_youtube_key(key.strip()), "message": "YouTube conectado para busca de links e informações. A chave ficou salva somente neste Mac."})
            else:
                self._json(create_project(body), HTTPStatus.CREATED)
        except (ValueError, json.JSONDecodeError, AnthropicConnectionError, ElevenLabsConnectionError, PexelsConnectionError, PixabayConnectionError, YouTubeConnectionError, NarrationError) as exc:
            self._json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # keep the local UI responsive, log details
            print(f"[studio] unexpected error: {exc!r}")
            self._json(
                {"ok": False, "error": "Não foi possível criar o projeto."},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Video Factory local studio")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)

    address = f"http://127.0.0.1:{args.port}"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), StudioHandler)
    print(f"Video Factory aberto em {address}")
    print("Para encerrar, pressione Control+C.")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(address)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nVideo Factory encerrado.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

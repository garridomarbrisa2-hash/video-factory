"""Safe YouTube Data API search: metadata only, Creative Commons candidates."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


class YouTubeConnectionError(RuntimeError):
    pass


def validate_key_shape(key: str) -> str:
    cleaned = key.strip()
    if len(cleaned) < 20 or any(char.isspace() for char in cleaned):
        raise ValueError("A chave da API do YouTube não parece válida.")
    return cleaned


def _request(
    key: str,
    query: str,
    max_results: int,
    timeout: float,
    *,
    creative_common_only: bool = False,
) -> dict[str, Any]:
    params = {
        "key": validate_key_shape(key), "part": "snippet", "q": query[:120],
        "type": "video", "maxResults": max(1, min(max_results, 10)),
        "videoEmbeddable": "true", "safeSearch": "strict", "order": "relevance",
    }
    if creative_common_only:
        params["videoLicense"] = "creativeCommon"
    request = Request(f"{SEARCH_URL}?{urlencode(params)}", headers={"Accept": "application/json", "User-Agent": "VideoFactory/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS URL
            return json.load(response)
    except HTTPError as exc:
        messages = {400: "O YouTube recusou a busca.", 403: "A chave não possui acesso à YouTube Data API ou a cota terminou."}
        raise YouTubeConnectionError(messages.get(exc.code, f"O YouTube respondeu com erro {exc.code}.")) from exc
    except (URLError, TimeoutError) as exc:
        raise YouTubeConnectionError("Não foi possível alcançar a API do YouTube.") from exc


def test_connection(key: str, *, timeout: float = 20.0) -> dict[str, Any]:
    payload = _request(key, "documentary", 1, timeout)
    if not isinstance(payload.get("items"), list):
        raise YouTubeConnectionError("O YouTube devolveu uma resposta inesperada.")
    return {"ok": True}


def search_videos(key: str, query: str, *, max_results: int = 3, timeout: float = 25.0) -> list[dict[str, Any]]:
    payload = _request(key, " ".join(query.split()).strip(), max_results, timeout)
    results = []
    for item in payload.get("items", []):
        video_id = str((item.get("id") or {}).get("videoId") or "")
        snippet = item.get("snippet") or {}
        if not video_id:
            continue
        thumbnails = snippet.get("thumbnails") or {}
        preview = (thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default") or {}).get("url", "")
        results.append({
            "id": video_id,
            "title": str(snippet.get("title") or ""),
            "channel": str(snippet.get("channelTitle") or ""),
            "description": str(snippet.get("description") or ""),
            "published_at": str(snippet.get("publishedAt") or ""),
            "preview_image": str(preview),
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
            "license_filter": "unverified",
            "download_allowed": False,
        })
    return results


def save_key(project_root: Path, key: str) -> Path:
    cleaned = validate_key_shape(key)
    path = project_root / "docs" / "API" / "youtube.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# YouTube Data API\n\nYOUTUBE_API_KEY: {cleaned}\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    os.environ["YOUTUBE_API_KEY"] = cleaned
    return path


def configured_key(project_root: Path) -> str | None:
    if os.environ.get("YOUTUBE_API_KEY"):
        return os.environ["YOUTUBE_API_KEY"].strip()
    path = project_root / "docs" / "API" / "youtube.md"
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            name, marker, value = line.partition(":")
            if marker and name.strip() == "YOUTUBE_API_KEY":
                return value.strip() or None
    return None


def masked_key(key: str) -> str:
    return "••••••••" + key[-4:]

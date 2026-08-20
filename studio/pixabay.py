"""Secure Pixabay API setup and normalized video search."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SEARCH_URL = "https://pixabay.com/api/videos/"


class PixabayConnectionError(RuntimeError):
    pass


def validate_key_shape(key: str) -> str:
    cleaned = key.strip()
    if len(cleaned) < 10 or any(char.isspace() for char in cleaned):
        raise ValueError("A chave do Pixabay não parece válida. Copie novamente.")
    return cleaned


def _request(key: str, query: str, per_page: int, timeout: float) -> dict[str, Any]:
    params = {"key": validate_key_shape(key), "q": query[:100], "per_page": max(3, min(per_page, 10)), "safesearch": "true"}
    request = Request(f"{SEARCH_URL}?{urlencode(params)}", headers={"Accept": "application/json", "User-Agent": "VideoFactory/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS URL
            return json.load(response)
    except HTTPError as exc:
        messages = {400: "O Pixabay recusou a chave ou a busca.", 429: "O limite temporário do Pixabay foi atingido."}
        raise PixabayConnectionError(messages.get(exc.code, f"O Pixabay respondeu com erro {exc.code}.")) from exc
    except (URLError, TimeoutError) as exc:
        raise PixabayConnectionError("Não foi possível alcançar o Pixabay.") from exc


def test_connection(key: str, *, timeout: float = 20.0) -> dict[str, Any]:
    payload = _request(key, "nature", 3, timeout)
    if not isinstance(payload.get("hits"), list):
        raise PixabayConnectionError("O Pixabay devolveu uma resposta inesperada.")
    return {"ok": True}


def search_videos(key: str, query: str, *, per_page: int = 3, timeout: float = 25.0) -> list[dict[str, Any]]:
    clean_query = " ".join(query.split()).strip()
    payload = _request(key, clean_query, per_page, timeout)
    candidates = []
    for item in payload.get("hits", []):
        variants = item.get("videos") or {}
        selected = variants.get("large") or variants.get("medium") or variants.get("small") or {}
        if not selected.get("url"):
            continue
        candidates.append({
            "id": int(item.get("id") or 0),
            "duration_sec": float(item.get("duration") or 0),
            "width": int(selected.get("width") or 0),
            "height": int(selected.get("height") or 0),
            "preview_image": "",
            "pixabay_url": str(item.get("pageURL") or ""),
            "video_url": str(selected.get("url") or ""),
            "creator": str(item.get("user") or "Pixabay contributor"),
            "creator_url": f"https://pixabay.com/users/{item.get('user')}-{item.get('user_id')}/",
        })
    return candidates


def save_key(project_root: Path, key: str) -> Path:
    cleaned = validate_key_shape(key)
    path = project_root / "docs" / "API" / "pixabay.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Pixabay API\n\nPIXABAY_API_KEY: {cleaned}\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    os.environ["PIXABAY_API_KEY"] = cleaned
    return path


def configured_key(project_root: Path) -> str | None:
    if os.environ.get("PIXABAY_API_KEY"):
        return os.environ["PIXABAY_API_KEY"].strip()
    path = project_root / "docs" / "API" / "pixabay.md"
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            name, marker, value = line.partition(":")
            if marker and name.strip() == "PIXABAY_API_KEY":
                return value.strip() or None
    return None


def masked_key(key: str) -> str:
    return "••••••••" + key[-4:]

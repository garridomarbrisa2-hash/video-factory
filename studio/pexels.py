"""Secure local Pexels configuration and connection test."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SEARCH_URL = "https://api.pexels.com/v1/videos/search"


class PexelsConnectionError(RuntimeError):
    """Friendly Pexels failure that never includes the secret key."""


def validate_key_shape(key: str) -> str:
    cleaned = key.strip()
    if len(cleaned) < 20 or any(char.isspace() for char in cleaned):
        raise ValueError("A chave do Pexels não parece válida. Copie novamente.")
    return cleaned


def test_connection(key: str, *, timeout: float = 20.0) -> dict[str, Any]:
    """Run a one-result stock search without downloading any media."""
    cleaned = validate_key_shape(key)
    url = f"{SEARCH_URL}?{urlencode({'query': 'nature', 'per_page': 1})}"
    request = Request(url, headers={"Authorization": cleaned, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS URL
            payload = json.load(response)
    except HTTPError as exc:
        messages = {
            401: "O Pexels recusou a chave. Confira se ela está ativa.",
            403: "A chave não possui permissão para usar a busca do Pexels.",
            429: "O Pexels limitou o teste temporariamente. Tente novamente em instantes.",
        }
        raise PexelsConnectionError(messages.get(exc.code, f"O Pexels respondeu com erro {exc.code}.")) from exc
    except (URLError, TimeoutError) as exc:
        raise PexelsConnectionError("Não foi possível alcançar o Pexels. Verifique sua internet.") from exc
    if not isinstance(payload.get("videos"), list):
        raise PexelsConnectionError("O Pexels devolveu uma resposta inesperada.")
    return {"ok": True}


def save_key(project_root: Path, key: str) -> Path:
    cleaned = validate_key_shape(key)
    api_dir = project_root / "docs" / "API"
    api_dir.mkdir(parents=True, exist_ok=True)
    path = api_dir / "pexels.md"
    path.write_text(f"# Pexels API\n\nPEXELS_API_KEY: {cleaned}\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    os.environ["PEXELS_API_KEY"] = cleaned
    return path


def configured_key(project_root: Path) -> str | None:
    environment = os.environ.get("PEXELS_API_KEY")
    if environment:
        return environment.strip()
    path = project_root / "docs" / "API" / "pexels.md"
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            name, marker, value = line.partition(":")
            if marker and name.strip() == "PEXELS_API_KEY":
                return value.strip() or None
    return None


def masked_key(key: str) -> str:
    return "••••••••" + key[-4:]

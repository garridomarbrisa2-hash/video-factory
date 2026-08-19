"""Anthropic connection helpers for the local Studio.

Secrets are stored only in the gitignored docs/API directory on the user's
machine. Connection validation uses the Models endpoint, which does not create
a message or consume generation tokens.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MODELS_URL = "https://api.anthropic.com/v1/models?limit=20"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicConnectionError(RuntimeError):
    """A friendly, non-secret-bearing Anthropic connection failure."""


def validate_key_shape(key: str) -> str:
    cleaned = key.strip()
    if not cleaned.startswith("sk-ant-") or len(cleaned) < 30:
        raise ValueError("A chave não parece válida. Ela deve começar com sk-ant-.")
    if any(char.isspace() for char in cleaned):
        raise ValueError("A chave contém espaços. Copie novamente na Anthropic.")
    return cleaned


def test_connection(key: str, *, timeout: float = 20.0) -> dict[str, Any]:
    """Validate a regular API key without generating text or spending tokens."""
    cleaned = validate_key_shape(key)
    request = Request(
        MODELS_URL,
        headers={
            "x-api-key": cleaned,
            "anthropic-version": ANTHROPIC_VERSION,
            "accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS URL
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code == 401:
            message = "A Anthropic recusou a chave. Confira se ela está ativa."
        elif exc.code == 402:
            message = "A Anthropic informou um problema de saldo ou cobrança."
        elif exc.code == 403:
            message = "A chave não possui permissão para acessar os modelos."
        elif exc.code == 429:
            message = "A Anthropic limitou o teste temporariamente. Tente novamente em instantes."
        else:
            message = f"A Anthropic respondeu com erro {exc.code}."
        raise AnthropicConnectionError(message) from exc
    except (URLError, TimeoutError) as exc:
        raise AnthropicConnectionError(
            "Não foi possível alcançar a Anthropic. Verifique sua internet."
        ) from exc

    models = [item.get("id") for item in payload.get("data", []) if item.get("id")]
    return {"ok": True, "models": models, "model_count": len(models)}


def save_key(project_root: Path, key: str) -> Path:
    """Persist the key in a gitignored local file with owner-only permissions."""
    cleaned = validate_key_shape(key)
    api_dir = project_root / "docs" / "API"
    api_dir.mkdir(parents=True, exist_ok=True)
    path = api_dir / "anthropic.md"
    path.write_text(
        "# Anthropic API\n\nANTHROPIC_API_KEY: " + cleaned + "\n",
        encoding="utf-8",
    )
    try:
        path.chmod(0o600)
    except OSError:
        pass
    os.environ["ANTHROPIC_API_KEY"] = cleaned
    return path


def configured_key(project_root: Path) -> str | None:
    env_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if env_key:
        return env_key
    path = project_root / "docs" / "API" / "anthropic.md"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("ANTHROPIC_API_KEY:"):
            value = line.partition(":")[2].strip()
            return value or None
    return None


def masked_key(key: str) -> str:
    return "••••••••" + key[-4:]


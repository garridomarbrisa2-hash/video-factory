"""Secure local ElevenLabs configuration and connection test."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


VOICES_URL = "https://api.elevenlabs.io/v1/voices"


class ElevenLabsConnectionError(RuntimeError):
    """Friendly ElevenLabs failure that never includes the secret key."""


def validate_key_shape(key: str) -> str:
    cleaned = key.strip()
    if len(cleaned) < 20 or any(char.isspace() for char in cleaned):
        raise ValueError("A chave da ElevenLabs não parece válida. Copie novamente.")
    return cleaned


def test_connection(key: str, *, timeout: float = 20.0) -> dict[str, Any]:
    """List available voices without generating audio or spending characters."""
    cleaned = validate_key_shape(key)
    request = Request(
        VOICES_URL,
        headers={"xi-api-key": cleaned, "accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS URL
            payload = json.load(response)
    except HTTPError as exc:
        messages = {
            401: "A ElevenLabs recusou a chave. Confira se ela está ativa.",
            403: "A chave não possui permissão para listar vozes.",
            429: "A ElevenLabs limitou o teste temporariamente. Tente novamente em instantes.",
        }
        raise ElevenLabsConnectionError(
            messages.get(exc.code, f"A ElevenLabs respondeu com erro {exc.code}.")
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise ElevenLabsConnectionError(
            "Não foi possível alcançar a ElevenLabs. Verifique sua internet."
        ) from exc

    voices = [
        {
            "voice_id": str(item.get("voice_id") or ""),
            "name": str(item.get("name") or "Voz sem nome"),
            "category": str(item.get("category") or ""),
        }
        for item in payload.get("voices", [])
        if item.get("voice_id")
    ]
    if not voices:
        raise ElevenLabsConnectionError("A conta não retornou nenhuma voz disponível.")
    voices.sort(key=lambda item: item["name"].casefold())
    return {"ok": True, "voices": voices, "voice_count": len(voices)}


def save_settings(project_root: Path, key: str, voice_id: str, voice_name: str) -> Path:
    cleaned = validate_key_shape(key)
    safe_voice_id = " ".join(voice_id.split()).strip()
    safe_voice_name = " ".join(voice_name.split()).strip()[:100]
    if not safe_voice_id or len(safe_voice_id) > 100:
        raise ValueError("Escolha uma voz válida.")
    api_dir = project_root / "docs" / "API"
    api_dir.mkdir(parents=True, exist_ok=True)
    path = api_dir / "elevenlabs.md"
    path.write_text(
        "# ElevenLabs API\n\n"
        f"ELEVENLABS_API_KEY: {cleaned}\n"
        f"ELEVENLABS_VOICE_ID: {safe_voice_id}\n"
        f"ELEVENLABS_VOICE_NAME: {safe_voice_name}\n",
        encoding="utf-8",
    )
    try:
        path.chmod(0o600)
    except OSError:
        pass
    os.environ["ELEVENLABS_API_KEY"] = cleaned
    os.environ["ELEVENLABS_VOICE_ID"] = safe_voice_id
    return path


def configured_settings(project_root: Path) -> dict[str, str] | None:
    path = project_root / "docs" / "API" / "elevenlabs.md"
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            key, marker, value = line.partition(":")
            if marker:
                values[key.strip()] = value.strip()
    api_key = os.environ.get("ELEVENLABS_API_KEY") or values.get("ELEVENLABS_API_KEY")
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID") or values.get("ELEVENLABS_VOICE_ID")
    if not api_key or not voice_id:
        return None
    return {
        "api_key": api_key,
        "voice_id": voice_id,
        "voice_name": values.get("ELEVENLABS_VOICE_NAME", "Voz selecionada"),
    }


def masked_key(key: str) -> str:
    return "••••••••" + key[-4:]

"""Generate measured ElevenLabs narration for a Studio episode."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import httpx

from pipeline.assets.vo import synthesize_script_plan
from pipeline.vo_plan import script_paragraphs


class NarrationError(RuntimeError):
    """Friendly narration error suitable for the local Studio UI."""


def _concat_audio(beats: list[dict[str, Any]], output: Path) -> None:
    inputs = [Path(beat["audio_path"]).resolve() for beat in beats]
    if not inputs:
        raise NarrationError("Nenhum trecho de áudio foi gerado.")
    concat_file = output.with_suffix(".concat.txt")
    concat_file.write_text(
        "".join(f"file '{str(path).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n" for path in inputs),
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                "-i", str(concat_file), "-c", "copy", str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not output.exists() or output.stat().st_size == 0:
            raise NarrationError("O FFmpeg não conseguiu juntar os trechos da narração.")
    finally:
        concat_file.unlink(missing_ok=True)


def generate_narration(project_root: Path, project_slug: str, episode: int) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9-]{1,64}", project_slug):
        raise ValueError("Nome de projeto inválido.")
    if episode < 1 or episode > 999:
        raise ValueError("Número de episódio inválido.")
    project_dir = project_root / "projects" / project_slug
    reviewed = project_dir / f"Ep{episode}_reviewed.md"
    source = reviewed if reviewed.is_file() else project_dir / f"Ep{episode}_script.md"
    plan_path = project_dir / f"Ep{episode}_voice_plan.json"
    audio_path = project_dir / f"Ep{episode}_narration.mp3"
    if not source.is_file():
        raise ValueError("O roteiro do episódio não foi encontrado.")
    if plan_path.exists() or audio_path.exists():
        raise ValueError("Este episódio já possui uma narração.")

    paragraphs = script_paragraphs(source.read_text(encoding="utf-8"))
    if not paragraphs:
        raise ValueError("O roteiro não contém parágrafos de narração.")
    try:
        plan = synthesize_script_plan(paragraphs)
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code == 401:
            message = "A ElevenLabs recusou a chave durante a geração."
        elif code == 402:
            message = "A ElevenLabs informou saldo insuficiente."
        elif code == 429:
            message = "A ElevenLabs atingiu um limite temporário. Tente novamente depois."
        else:
            message = f"A ElevenLabs respondeu com erro {code}."
        raise NarrationError(message) from exc
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        raise NarrationError("A conexão com a ElevenLabs foi interrompida.") from exc

    total = float(plan["total_vo_sec"])
    status = "approved" if 480 <= total <= 1200 else "needs_script_adjustment"
    plan.update(
        {
            "script": str(source.relative_to(project_root)),
            "provider": "elevenlabs",
            "status": status,
        }
    )
    try:
        _concat_audio(plan["beats"], audio_path)
    except Exception:
        audio_path.unlink(missing_ok=True)
        raise
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "status": status,
        "total_seconds": round(total, 1),
        "total_minutes": round(total / 60, 1),
        "beat_count": len(plan["beats"]),
        "audio_path": str(audio_path.relative_to(project_root)),
        "plan_path": str(plan_path.relative_to(project_root)),
        "source_path": str(source.relative_to(project_root)),
        "message": "Narração gerada e medida.",
    }

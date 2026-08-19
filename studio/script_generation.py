"""Generate the script stage through the Anthropic Messages API."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pipeline.intelligence.select_style import load_style
from studio.anthropic import ANTHROPIC_VERSION, AnthropicConnectionError, test_connection


MESSAGES_URL = "https://api.anthropic.com/v1/messages"
LANGUAGE_NAMES = {"pt-BR": "Português do Brasil", "es": "Espanhol", "en": "Inglês"}


def choose_script_model(models: list[str]) -> str:
    """Prefer the current Sonnet model, while remaining forward-compatible."""
    for preferred in ("claude-sonnet-5", "claude-sonnet-4-6", "claude-sonnet-4-5"):
        if preferred in models:
            return preferred
    for model in models:
        if "sonnet" in model.lower():
            return model
    for model in models:
        if "haiku" in model.lower():
            return model
    if models:
        return models[0]
    raise AnthropicConnectionError("Sua chave não retornou nenhum modelo disponível.")


def _metadata(brief: str) -> dict[str, Any]:
    fields: dict[str, str] = {}
    for line in brief.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if key in {"language", "target_duration_min", "global_style", "asset_mode"}:
            fields[key] = value.strip()

    topic_match = re.search(r"^## Assunto\s*\n+(.+?)(?=\n## |\Z)", brief, re.M | re.S)
    topic = " ".join(topic_match.group(1).split()) if topic_match else ""
    if not topic:
        raise ValueError("O brief não contém um assunto.")
    try:
        duration = int(fields.get("target_duration_min", "8"))
    except ValueError as exc:
        raise ValueError("A duração do brief é inválida.") from exc
    return {
        "topic": topic,
        "language": fields.get("language", "pt-BR"),
        "duration": duration,
        "style": fields.get("global_style", "standard"),
        "asset_mode": fields.get("asset_mode", "auto"),
    }


def _system_prompt(project_root: Path) -> str:
    skill_path = project_root / "pipeline" / "intelligence" / "skills" / "01_script_writer.md"
    skill = skill_path.read_text(encoding="utf-8")
    return (
        "Você é o roteirista do Video Factory. Obedeça integralmente às regras "
        "abaixo. Escreva somente o roteiro solicitado, sem conversar com o usuário.\n\n"
        + skill
    )


def _user_prompt(meta: dict[str, Any]) -> str:
    style = load_style(meta["style"])
    target_words = int(meta["duration"] * 135)
    language = LANGUAGE_NAMES.get(meta["language"], meta["language"])
    script_rules = json.dumps(style.get("script", {}), ensure_ascii=False, indent=2)
    return f"""Crie um roteiro original para YouTube.

ASSUNTO:
{meta['topic']}

REQUISITOS OBRIGATÓRIOS:
- Idioma: {language}.
- Duração pretendida: {meta['duration']} minutos.
- Aproximadamente {target_words} palavras, com tolerância de 10%.
- Estilo global: {meta['style']}.
- Comece com uma abertura forte; nunca use "No vídeo de hoje" ou equivalente.
- Estrutura Markdown: metadados, # HOOK, # BODY com blocos narrativos, # CTA.
- Texto pronto para narração, sem instruções de câmera, edição, música ou imagens.
- Não invente fontes, citações, pesquisas ou números. Quando um fato exato não for
  seguro, use formulação responsável em vez de fabricar precisão.
- Termine com as linhas "Style:" e "Tone:".

REGRAS DO ESTILO:
{script_rules}
"""


def _request_message(
    key: str,
    model: str,
    system: str,
    prompt: str,
    max_tokens: int,
    *,
    timeout: float = 300.0,
) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    request = Request(
        MESSAGES_URL,
        data=body,
        method="POST",
        headers={
            "x-api-key": key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
            "accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS URL
            return json.load(response)
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("error", {}).get("message")
        except Exception:
            detail = None
        if exc.code == 401:
            message = "A chave da Anthropic deixou de ser aceita."
        elif exc.code == 402:
            message = "Saldo insuficiente ou problema de cobrança na Anthropic."
        elif exc.code == 429:
            message = "Limite temporário da Anthropic. Aguarde um pouco e tente novamente."
        else:
            message = detail or f"A Anthropic respondeu com erro {exc.code}."
        raise AnthropicConnectionError(message) from exc
    except (URLError, TimeoutError) as exc:
        raise AnthropicConnectionError(
            "A conexão com a Anthropic demorou demais ou foi interrompida."
        ) from exc


def generate_script(
    project_root: Path,
    project_slug: str,
    episode: int,
    key: str,
) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9-]{1,64}", project_slug):
        raise ValueError("Nome de projeto inválido.")
    if episode < 1 or episode > 999:
        raise ValueError("Número de episódio inválido.")

    project_dir = project_root / "projects" / project_slug
    brief_path = project_dir / f"Ep{episode}.md"
    script_path = project_dir / f"Ep{episode}_script.md"
    if not brief_path.is_file():
        raise ValueError("Brief do projeto não encontrado.")
    if script_path.exists():
        raise ValueError("Este episódio já possui um roteiro.")

    meta = _metadata(brief_path.read_text(encoding="utf-8"))
    available = test_connection(key)["models"]
    model = choose_script_model(available)
    max_tokens = min(10_000, max(3_000, meta["duration"] * 500))
    payload = _request_message(
        key,
        model,
        _system_prompt(project_root),
        _user_prompt(meta),
        max_tokens,
    )
    text_blocks = [
        block.get("text", "")
        for block in payload.get("content", [])
        if block.get("type") == "text"
    ]
    script = "\n".join(text_blocks).strip()
    if len(script.split()) < 100:
        raise AnthropicConnectionError("A Anthropic devolveu um roteiro incompleto.")

    usage = payload.get("usage", {})
    header = (
        f"<!-- model: {model}; generated_by: Anthropic API; "
        f"input_tokens: {usage.get('input_tokens', 0)}; "
        f"output_tokens: {usage.get('output_tokens', 0)} -->\n\n"
    )
    script_path.write_text(header + script + "\n", encoding="utf-8")
    return {
        "ok": True,
        "model": model,
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "script_path": str(script_path.relative_to(project_root)),
        "word_count": len(script.split()),
        "message": "Roteiro gerado e salvo no projeto.",
    }


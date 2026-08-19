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
    minimum_words = int(target_words * 0.9)
    maximum_words = int(target_words * 1.1)
    language = LANGUAGE_NAMES.get(meta["language"], meta["language"])
    script_rules = json.dumps(style.get("script", {}), ensure_ascii=False, indent=2)
    return f"""Crie um roteiro original para YouTube.

ASSUNTO:
{meta['topic']}

REQUISITOS OBRIGATÓRIOS:
- Idioma: {language}.
- Duração pretendida: {meta['duration']} minutos.
- Entre {minimum_words} e {maximum_words} palavras. Este intervalo é obrigatório.
- Antes de responder, verifique silenciosamente se o texto completo está dentro
  desse intervalo. Se estiver curto, aprofunde contexto, consequências e exemplos.
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


def _extract_text(payload: dict[str, Any]) -> str:
    return "\n".join(
        block.get("text", "")
        for block in payload.get("content", [])
        if block.get("type") == "text"
    ).strip()


def _word_limits(duration: int) -> tuple[int, int, int]:
    target = duration * 135
    return int(target * 0.9), target, int(target * 1.1)


def _closer_to_target(first: str, second: str, target: int) -> str:
    first_distance = abs(len(first.split()) - target)
    second_distance = abs(len(second.split()) - target)
    return second if second_distance < first_distance else first


def _length_revision_prompt(script: str, meta: dict[str, Any]) -> str:
    minimum, target, maximum = _word_limits(meta["duration"])
    current = len(script.split())
    direction = "expanda" if current < minimum else "reduza"
    return f"""Revise integralmente o roteiro abaixo.

O texto tem aproximadamente {current} palavras, mas precisa ter entre
{minimum} e {maximum} palavras para alcançar {meta['duration']} minutos.
{direction.capitalize()} o conteúdo até perto de {target} palavras.

Preserve o assunto, o idioma, o estilo, a abertura e a estrutura Markdown.
Não acrescente instruções de edição e não invente fatos, fontes ou números.
Entregue o roteiro completo revisado, não apenas as partes modificadas.

ROTEIRO ATUAL:
{script}
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
    script = _extract_text(payload)
    if len(script.split()) < 100:
        raise AnthropicConnectionError("A Anthropic devolveu um roteiro incompleto.")

    minimum_words, target_words, maximum_words = _word_limits(meta["duration"])
    revised_for_length = False
    payloads = [payload]
    if not minimum_words <= len(script.split()) <= maximum_words:
        revised_payload = _request_message(
            key,
            model,
            _system_prompt(project_root),
            _length_revision_prompt(script, meta),
            max_tokens,
        )
        revised = _extract_text(revised_payload)
        if len(revised.split()) >= 100:
            script = _closer_to_target(script, revised, target_words)
        payloads.append(revised_payload)
        revised_for_length = True

    input_tokens = sum(p.get("usage", {}).get("input_tokens", 0) for p in payloads)
    output_tokens = sum(p.get("usage", {}).get("output_tokens", 0) for p in payloads)
    word_count = len(script.split())
    duration_ok = minimum_words <= word_count <= maximum_words
    header = (
        f"<!-- model: {model}; generated_by: Anthropic API; "
        f"input_tokens: {input_tokens}; output_tokens: {output_tokens}; "
        f"duration_check: {'approved' if duration_ok else 'review'} -->\n\n"
    )
    script_path.write_text(header + script + "\n", encoding="utf-8")
    return {
        "ok": True,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "script_path": str(script_path.relative_to(project_root)),
        "word_count": word_count,
        "estimated_minutes": round(word_count / 135, 1),
        "duration_ok": duration_ok,
        "target_min_words": minimum_words,
        "target_max_words": maximum_words,
        "revised_for_length": revised_for_length,
        "message": "Roteiro gerado e salvo no projeto.",
    }

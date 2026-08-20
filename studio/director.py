"""Create a timed visual direction plan from measured narration."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from studio.anthropic import AnthropicConnectionError, test_connection
from studio.script_generation import _extract_text, _metadata, _request_message, choose_script_model


ALLOWED_TYPES = {"intro", "content", "stat", "quote", "list", "comparison", "person", "document", "map", "outro"}
ALLOWED_LAYOUTS = {"plate", "keyword", "bare", "collage"}
ALLOWED_ENERGY = {"low", "mid", "high"}
ALLOWED_SOURCES = {"pexels", "pixabay", "web_image", "youtube", "generated"}


def _split_text(text: str, duration: float, target: float = 10.0) -> list[dict[str, Any]]:
    """Split a long narrated paragraph into visual beats without changing its timing."""
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if not parts:
        parts = [text.strip()]
    desired = max(1, round(duration / target))
    while len(parts) < desired:
        index = max(range(len(parts)), key=lambda i: len(parts[i]))
        words = parts[index].split()
        if len(words) < 8:
            break
        middle = len(words) // 2
        parts[index:index + 1] = [" ".join(words[:middle]), " ".join(words[middle:])]

    weights = [max(1, len(part.split())) for part in parts]
    total_weight = sum(weights)
    elapsed = 0.0
    result: list[dict[str, Any]] = []
    for index, (part, weight) in enumerate(zip(parts, weights)):
        part_duration = duration - elapsed if index == len(parts) - 1 else duration * weight / total_weight
        result.append({"text": part, "offset": round(elapsed, 3), "duration": round(part_duration, 3)})
        elapsed += part_duration
    return result


def visual_beats(plan: dict[str, Any]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    scene_id = 1
    for beat in plan.get("beats", []):
        duration = float(beat["duration_sec"])
        for part in _split_text(str(beat["text"]), duration):
            units.append(
                {
                    "id": scene_id,
                    "beat_index": int(beat["index"]),
                    "vo_start": round(float(beat["vo_start"]) + part["offset"], 3),
                    "duration": part["duration"],
                    "vo_text": part["text"],
                }
            )
            scene_id += 1
    return units


def _extract_json(text: str) -> dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    raw = fenced.group(1) if fenced else text[text.find("{"):text.rfind("}") + 1]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AnthropicConnectionError("O Diretor devolveu uma resposta inválida. Tente novamente.") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("scenes"), list):
        raise AnthropicConnectionError("O Diretor não devolveu uma lista de cenas.")
    return payload


def _prompt(topic: str, style: str, units: list[dict[str, Any]]) -> str:
    compact = [{"id": u["id"], "seconds": u["duration"], "narration": u["vo_text"]} for u in units]
    return f"""Atue como Diretor de um documentário para YouTube.

Assunto: {topic}
Estilo visual: {style}

Você receberá cenas já divididas e sincronizadas com a narração real. Não altere,
remova, junte ou crie cenas. Para CADA id, escolha a direção visual.

Regras:
- Retorne JSON puro, sem Markdown, exatamente no formato solicitado.
- Use texto na tela apenas para nome, data, número, termo ou ideia indispensável.
- Nunca transcreva toda a narração em props.text.
- Varie enquadramentos e tipos; não use mais de 2 content seguidos.
- energy high somente no hook ou grande revelação; a maioria deve ser mid/low.
- fallback_prompt deve descrever uma imagem ou filmagem concreta, realista,
  historicamente coerente, sem texto embutido e adequada ao assunto.
- keyword deve ter 2 a 6 palavras concretas em inglês para busca de material.
- source_route escolhe UMA rota: pexels, pixabay, web_image, youtube ou generated.
- Prefira Pexels/Pixabay para imagens genéricas e pessoas/locais; web_image para
  documentos ou fatos históricos; youtube apenas quando um trecho específico e
  identificável for editorialmente necessário; generated para conceito abstrato
  sem material adequado. O sistema verificará licença/permissão depois.
- because explica em uma frase curta por que a imagem serve à narração.

Tipos permitidos: intro, content, stat, quote, list, comparison, person, document, map, outro.
Layouts permitidos: plate, keyword, bare, collage.

Formato:
{{"scenes":[{{"id":1,"type":"intro","layout":"keyword","energy":"high","text":"texto curto ou vazio","emphasis":"1 a 3 palavras ou vazio","source_route":"pexels","keyword":"busca em inglês","fallback_prompt":"descrição visual detalhada","because":"justificativa curta"}}]}}

CENAS:
{json.dumps(compact, ensure_ascii=False)}
"""


def _validated_decisions(payload: dict[str, Any], units: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    expected = {unit["id"] for unit in units}
    decisions: dict[int, dict[str, str]] = {}
    for item in payload["scenes"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), int):
            continue
        scene_id = item["id"]
        scene_type = str(item.get("type") or "content")
        layout = str(item.get("layout") or "bare")
        energy = str(item.get("energy") or "mid")
        if scene_type not in ALLOWED_TYPES:
            scene_type = "content"
        if layout not in ALLOWED_LAYOUTS:
            layout = "bare"
        if energy not in ALLOWED_ENERGY:
            energy = "mid"
        source_route = str(item.get("source_route") or "pexels")
        if source_route not in ALLOWED_SOURCES:
            source_route = "pexels"
        decisions[scene_id] = {
            "type": scene_type,
            "layout": layout,
            "energy": energy,
            "source_route": source_route,
            "text": str(item.get("text") or "").strip()[:120],
            "emphasis": str(item.get("emphasis") or "").strip()[:60],
            "keyword": str(item.get("keyword") or "documentary footage").strip()[:120],
            "fallback_prompt": str(item.get("fallback_prompt") or "Cinematic documentary image").strip()[:700],
            "because": str(item.get("because") or "A imagem sustenta o trecho narrado.").strip()[:300],
        }
    if set(decisions) != expected:
        raise AnthropicConnectionError("O Diretor não planejou todas as cenas. Tente novamente.")
    return decisions


def generate_direction(project_root: Path, project_slug: str, episode: int, key: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9-]{1,64}", project_slug) or not 1 <= episode <= 999:
        raise ValueError("Projeto ou episódio inválido.")
    project_dir = project_root / "projects" / project_slug
    brief_path = project_dir / f"Ep{episode}.md"
    plan_path = project_dir / f"Ep{episode}_voice_plan.json"
    direction_path = project_dir / f"Ep{episode}_director.json"
    timeline_path = project_dir / f"Ep{episode}_timeline.json"
    if not brief_path.is_file() or not plan_path.is_file():
        raise ValueError("A narração medida é necessária antes do Diretor.")
    if direction_path.exists() or timeline_path.exists():
        raise ValueError("Este episódio já possui direção de cenas.")

    meta = _metadata(brief_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("status") != "approved":
        raise ValueError("A duração da narração ainda não foi aprovada.")
    units = visual_beats(plan)
    model = choose_script_model(test_connection(key)["models"])
    response = _request_message(
        key,
        model,
        "Você é o Diretor visual criterioso do Video Factory. Responda somente JSON válido.",
        _prompt(meta["topic"], meta["style"], units),
        min(16_000, max(5_000, len(units) * 220)),
    )
    decisions = _validated_decisions(_extract_json(_extract_text(response)), units)
    scenes = []
    notes = []
    for unit in units:
        decision = decisions[unit["id"]]
        text_props = {"text": decision["text"], "emphasis": decision["emphasis"]}
        scenes.append(
            {
                "id": unit["id"],
                "type": decision["type"],
                "duration": unit["duration"],
                "layout": decision["layout"],
                "energy": decision["energy"],
                "vo_text": unit["vo_text"],
                "vo_start": unit["vo_start"],
                "vo_duration": unit["duration"],
                "broll": {
                    "keyword": decision["keyword"],
                    "gen_kind": "image",
                    "fallback_prompt": decision["fallback_prompt"],
                },
                "props": text_props,
            }
        )
        notes.append(
            {
                "id": unit["id"],
                "source_route": decision["source_route"],
                "search_query": decision["keyword"],
                "because": decision["because"],
            }
        )

    timeline = {
        "title": meta["topic"],
        "global_style": meta["style"],
        "asset_mode": meta["asset_mode"],
        "total_sec": round(float(plan["total_vo_sec"]), 3),
        "scenes": scenes,
    }
    direction_path.write_text(json.dumps({"model": model, "notes": notes, "scenes": scenes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    usage = response.get("usage", {})
    return {
        "ok": True,
        "model": model,
        "scene_count": len(scenes),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "direction_path": str(direction_path.relative_to(project_root)),
        "timeline_path": str(timeline_path.relative_to(project_root)),
        "message": "Direção de cenas concluída.",
    }

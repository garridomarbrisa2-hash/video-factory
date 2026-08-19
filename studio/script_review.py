"""Editorial review gate for generated scripts.

This gate improves narration and epistemic care. It deliberately does not
claim external fact-checking; claims needing sources are written to a report.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from studio.anthropic import configured_key, test_connection
from studio.script_generation import (
    _extract_text,
    _metadata,
    _request_message,
    _word_limits,
    choose_script_model,
)


def _review_prompt(script: str, meta: dict[str, Any]) -> str:
    minimum, target, maximum = _word_limits(meta["duration"])
    return f"""Atue como Revisor Editorial do Video Factory.

Revise o roteiro abaixo antes de ele seguir para voz, direção e imagens.

OBJETIVOS OBRIGATÓRIOS:
- Preserve assunto, idioma e estrutura # HOOK, # BODY e # CTA.
- Mantenha entre {minimum} e {maximum} palavras, perto de {target}.
- Melhore fluidez oral, clareza, retenção e transições.
- Não acrescente números, citações, fontes, nomes ou acontecimentos novos.
- Quando propriedade, identidade, quantidade, intenção ou causalidade não
  estiverem demonstradas, troque certeza por linguagem responsável, como
  "estimativas", "análises sugerem", "é atribuído" ou "não há confirmação".
- Não declare que pesquisou a internet ou realizou checagem factual externa.
- Liste cada afirmação concreta que precisa de fonte primária ou verificação
  humana antes da publicação.
- Não inclua instruções de câmera, edição, música ou imagens no roteiro.

Responda EXATAMENTE neste formato:
<reviewed_script>
[roteiro completo revisado]
</reviewed_script>
<review_report>
{{"decision":"approved" ou "needs_sources","summary":"resumo curto","corrections":["..."],"verification_required":["..."]}}
</review_report>

ROTEIRO:
{script}
"""


def _parse_review(text: str) -> tuple[str, dict[str, Any]]:
    script_match = re.search(r"<reviewed_script>\s*(.*?)\s*</reviewed_script>", text, re.S)
    report_match = re.search(r"<review_report>\s*(.*?)\s*</review_report>", text, re.S)
    if not script_match or not report_match:
        raise ValueError("O Revisor devolveu uma resposta incompleta. Tente novamente.")
    reviewed = script_match.group(1).strip()
    try:
        report = json.loads(report_match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError("O relatório do Revisor veio em formato inválido.") from exc
    if not isinstance(report, dict):
        raise ValueError("O relatório do Revisor veio em formato inválido.")
    if not isinstance(report.get("verification_required", []), list):
        raise ValueError("A lista de verificação do Revisor é inválida.")
    if not isinstance(report.get("corrections", []), list):
        raise ValueError("A lista de correções do Revisor é inválida.")
    if len(reviewed.split()) < 100 or "# HOOK" not in reviewed or "# BODY" not in reviewed:
        raise ValueError("O roteiro revisado ficou incompleto.")
    return reviewed, report


def review_script(project_root: Path, project_slug: str, episode: int, key: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9-]{1,64}", project_slug):
        raise ValueError("Nome de projeto inválido.")
    if episode < 1 or episode > 999:
        raise ValueError("Número de episódio inválido.")

    project_dir = project_root / "projects" / project_slug
    brief_path = project_dir / f"Ep{episode}.md"
    script_path = project_dir / f"Ep{episode}_script.md"
    reviewed_path = project_dir / f"Ep{episode}_reviewed.md"
    report_path = project_dir / f"Ep{episode}_review.md"
    if not brief_path.is_file() or not script_path.is_file():
        raise ValueError("Brief ou roteiro do episódio não encontrado.")
    if reviewed_path.exists() or report_path.exists():
        raise ValueError("Este episódio já foi revisado.")

    meta = _metadata(brief_path.read_text(encoding="utf-8"))
    original = script_path.read_text(encoding="utf-8")
    model = choose_script_model(test_connection(key)["models"])
    payload = _request_message(
        key,
        model,
        "Você é um revisor editorial rigoroso, transparente e cuidadoso com fatos.",
        _review_prompt(original, meta),
        min(12_000, max(4_000, meta["duration"] * 600)),
    )
    reviewed, report = _parse_review(_extract_text(payload))
    minimum, _, maximum = _word_limits(meta["duration"])
    word_count = len(reviewed.split())
    duration_ok = minimum <= word_count <= maximum
    verification = [str(item).strip() for item in report.get("verification_required", []) if str(item).strip()]
    decision = "needs_sources" if verification or not duration_ok else "approved"

    reviewed_path.write_text(
        f"<!-- model: {model}; reviewed_by: Anthropic API; editorial_decision: {decision}; external_fact_check: not_performed -->\n\n{reviewed}\n",
        encoding="utf-8",
    )
    lines = [
        f"# Revisão do episódio {episode}", "", f"status: {decision}",
        "external_fact_check: not_performed", f"reviewed_script: {reviewed_path.name}",
        "", "## Resumo", "", str(report.get("summary") or "Revisão editorial concluída."),
        "", "## Correções editoriais", "",
    ]
    lines.extend(f"- {item}" for item in report.get("corrections", []))
    lines.extend(["", "## Verificação necessária", ""])
    lines.extend(f"- [ ] {item}" for item in verification)
    if not verification:
        lines.append("- Nenhuma afirmação adicional foi sinalizada pelo revisor.")
    lines.extend(["", "> Esta é uma revisão editorial. Aprovação factual exige fontes externas.", ""])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "ok": True, "decision": decision, "model": model, "word_count": word_count,
        "estimated_minutes": round(word_count / 135, 1), "duration_ok": duration_ok,
        "verification_count": len(verification),
        "reviewed_path": str(reviewed_path.relative_to(project_root)),
        "report_path": str(report_path.relative_to(project_root)),
        "message": "Revisão editorial concluída.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review a generated Video Factory script")
    parser.add_argument("--project", required=True)
    parser.add_argument("--episode", required=True, type=int)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    key = configured_key(root)
    if not key:
        parser.error("Configure a chave Anthropic no Studio primeiro.")
    print(json.dumps(review_script(root, args.project, args.episode, key), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

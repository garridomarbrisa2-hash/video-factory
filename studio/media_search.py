"""Find visual candidates for a finished Director plan without downloading media."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from studio.pexels import configured_key as configured_pexels, search_videos as search_pexels
from studio.pixabay import configured_key as configured_pixabay, search_videos as search_pixabay
from studio.youtube import configured_key as configured_youtube, search_videos as search_youtube


SearchFunction = Callable[[str, str], list[dict[str, Any]]]


def load_media_candidates(project_root: Path, project_slug: str, episode: int) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9-]{1,64}", project_slug) or not 1 <= episode <= 999:
        raise ValueError("Projeto ou episódio inválido.")
    path = project_root / "projects" / project_slug / f"Ep{episode}_media_candidates.json"
    if not path.is_file():
        raise ValueError("A busca de mídia ainda não foi concluída.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "project": project_slug,
        "episode": episode,
        "scenes": payload.get("scenes") or [],
    }


def _load_progress(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        searches = payload.get("searches") or {}
        return {str(key): value for key, value in searches.items() if isinstance(value, list)}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def find_media_candidates(project_root: Path, project_slug: str, episode: int) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9-]{1,64}", project_slug) or not 1 <= episode <= 999:
        raise ValueError("Projeto ou episódio inválido.")
    project_dir = project_root / "projects" / project_slug
    direction_path = project_dir / f"Ep{episode}_director.json"
    output_path = project_dir / f"Ep{episode}_media_candidates.json"
    progress_path = project_dir / f"Ep{episode}_media_search_progress.json"
    if not direction_path.is_file():
        raise ValueError("A direção de cenas precisa ser concluída primeiro.")
    if output_path.exists():
        raise ValueError("Este episódio já possui uma busca de mídia salva.")

    providers: dict[str, tuple[str | None, SearchFunction]] = {
        "pexels": (configured_pexels(project_root), search_pexels),
        "pixabay": (configured_pixabay(project_root), search_pixabay),
        "youtube": (configured_youtube(project_root), search_youtube),
    }
    if not any(key for key, _ in providers.values()):
        raise ValueError("Conecte pelo menos um banco de mídia antes da busca.")

    direction = json.loads(direction_path.read_text(encoding="utf-8"))
    notes = direction.get("notes") or []
    if not isinstance(notes, list) or not notes:
        raise ValueError("O plano do Diretor não possui cenas para pesquisar.")
    results: list[dict[str, Any]] = []
    query_cache = _load_progress(progress_path)
    queries_by_provider = {name: 0 for name in providers}
    scenes_by_provider = {name: 0 for name in providers}
    candidates_by_provider = {name: 0 for name in providers}
    for note in notes:
        scene_id = int(note.get("id") or 0)
        route = str(note.get("source_route") or "pexels")
        query = " ".join(str(note.get("search_query") or "documentary footage").split()).strip()
        if route not in providers:
            results.append({"scene_id": scene_id, "route": route, "query": query, "status": "awaiting_manual_or_generated_media", "candidates": []})
            continue
        scenes_by_provider[route] += 1
        key, search = providers[route]
        if not key:
            results.append({"scene_id": scene_id, "route": route, "query": query, "status": "awaiting_configuration", "candidates": []})
            continue
        cache_key = f"{route}\n{query.casefold()}"
        if cache_key not in query_cache:
            query_cache[cache_key] = search(key, query)
            queries_by_provider[route] += 1
            progress_path.write_text(json.dumps({"searches": query_cache}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        candidates = query_cache[cache_key]
        candidates_by_provider[route] += len(candidates)
        results.append({"scene_id": scene_id, "route": route, "query": query, "status": "found" if candidates else "no_results", "candidates": candidates})

    payload = {
        "providers": {
            name: {
                "configured": bool(key),
                "attribution": {
                    "pexels": "Videos provided by Pexels",
                    "pixabay": "Videos provided by Pixabay",
                    "youtube": "YouTube metadata only; verify permission before reuse",
                }[name],
                "queries_made": queries_by_provider[name],
                "scene_count": scenes_by_provider[name],
                "candidate_count": candidates_by_provider[name],
            }
            for name, (key, _) in providers.items()
        },
        "downloaded_media": False,
        "scenes": results,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    progress_path.unlink(missing_ok=True)
    searched = sum(queries_by_provider.values())
    found = sum(candidates_by_provider.values())
    return {
        "ok": True,
        "scene_count": len(results),
        "queries_made": searched,
        "candidate_count": found,
        "provider_counts": {name: {"scenes": scenes_by_provider[name], "candidates": candidates_by_provider[name]} for name in providers},
        "pending_scene_count": sum(1 for item in results if item["status"].startswith("awaiting_")),
        "path": str(output_path.relative_to(project_root)),
        "message": "Candidatos localizados. Nenhum vídeo foi baixado.",
    }

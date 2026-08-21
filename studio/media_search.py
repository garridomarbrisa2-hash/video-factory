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

STOP_WORDS = {
    "a", "as", "ao", "aos", "com", "como", "da", "das", "de", "do", "dos",
    "e", "em", "entre", "era", "essa", "esse", "esta", "este", "foi", "na",
    "nas", "no", "nos", "o", "os", "ou", "para", "por", "que", "se", "sem",
    "sua", "seu", "the", "a", "an", "and", "for", "from", "in", "of", "on",
    "or", "that", "this", "to", "with",
}

MAX_YOUTUBE_VIDEOS = 10


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]{3,}", text.casefold())
        if token not in STOP_WORDS
    }


def _topic(project_dir: Path, episode: int, project_slug: str) -> str:
    timeline_path = project_dir / f"Ep{episode}_timeline.json"
    if timeline_path.is_file():
        try:
            title = str(json.loads(timeline_path.read_text(encoding="utf-8")).get("title") or "")
            if title.strip():
                return " ".join(title.split())[:180]
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    return project_slug.replace("-", " ").strip().title()


def _youtube_theme_queries(topic: str) -> list[str]:
    """Use a small quota-friendly set of whole-topic searches."""
    queries = [topic, f"{topic} documentary"]
    return list(dict.fromkeys(" ".join(query.split())[:120] for query in queries if query.strip()))


def _rank_youtube(candidates: list[dict[str, Any]], context: str, limit: int = 3) -> list[dict[str, Any]]:
    wanted = _tokens(context)

    def score(candidate: dict[str, Any]) -> tuple[int, int]:
        searchable = " ".join(
            str(candidate.get(field) or "") for field in ("title", "description", "channel")
        )
        overlap = len(wanted & _tokens(searchable))
        return overlap, len(_tokens(str(candidate.get("title") or "")))

    ranked = sorted(candidates, key=score, reverse=True)
    return [dict(candidate, relevance_score=score(candidate)[0]) for candidate in ranked[:limit]]


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


def find_media_candidates(
    project_root: Path, project_slug: str, episode: int, *, refresh: bool = False
) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9-]{1,64}", project_slug) or not 1 <= episode <= 999:
        raise ValueError("Projeto ou episódio inválido.")
    project_dir = project_root / "projects" / project_slug
    direction_path = project_dir / f"Ep{episode}_director.json"
    output_path = project_dir / f"Ep{episode}_media_candidates.json"
    progress_path = project_dir / f"Ep{episode}_media_search_progress.json"
    if not direction_path.is_file():
        raise ValueError("A direção de cenas precisa ser concluída primeiro.")
    if output_path.exists() and not refresh:
        raise ValueError("Este episódio já possui uma busca de mídia salva.")
    if refresh:
        output_path.unlink(missing_ok=True)
        progress_path.unlink(missing_ok=True)

    providers: dict[str, tuple[str | None, SearchFunction]] = {
        "pexels": (configured_pexels(project_root), search_pexels),
        "pixabay": (configured_pixabay(project_root), search_pixabay),
        "youtube": (configured_youtube(project_root), search_youtube),
    }
    if not any(key for key, _ in providers.values()):
        raise ValueError("Conecte pelo menos um banco de mídia antes da busca.")

    direction = json.loads(direction_path.read_text(encoding="utf-8"))
    notes = direction.get("notes") or []
    scenes = {
        int(scene.get("id") or 0): scene
        for scene in (direction.get("scenes") or [])
        if isinstance(scene, dict)
    }
    if not isinstance(notes, list) or not notes:
        raise ValueError("O plano do Diretor não possui cenas para pesquisar.")
    results: list[dict[str, Any]] = []
    query_cache = _load_progress(progress_path)
    queries_by_provider = {name: 0 for name in providers}
    scenes_by_provider = {name: 0 for name in providers}
    candidates_by_provider = {name: 0 for name in providers}
    topic = _topic(project_dir, episode, project_slug)
    youtube_theme_candidates: list[dict[str, Any]] = []
    youtube_key, _ = providers["youtube"]
    youtube_queries: list[str] = []

    def save_progress() -> None:
        progress_path.write_text(
            json.dumps({"searches": query_cache}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def stock_candidates(provider: str, query: str) -> list[dict[str, Any]]:
        key, search = providers[provider]
        if not key:
            return []
        cache_key = f"{provider}\n{query.casefold()}"
        if cache_key not in query_cache:
            query_cache[cache_key] = search(key, query)
            queries_by_provider[provider] += 1
            save_progress()
        candidates = [
            dict(candidate, provider=provider, matched_query=query, priority="stock")
            for candidate in query_cache[cache_key]
        ]
        candidates_by_provider[provider] += len(candidates)
        return candidates

    def load_youtube_theme_candidates() -> None:
        nonlocal youtube_queries
        if youtube_theme_candidates or not youtube_key:
            return
        youtube_queries = _youtube_theme_queries(topic)
        for theme_query in youtube_queries:
            cache_key = f"youtube-theme\n{theme_query.casefold()}"
            if cache_key not in query_cache:
                query_cache[cache_key] = search_youtube(
                    youtube_key, theme_query, max_results=10
                )
                queries_by_provider["youtube"] += 1
                save_progress()
            for candidate in query_cache[cache_key]:
                candidate_id = str(candidate.get("id") or candidate.get("youtube_url") or "")
                if candidate_id and not any(
                    str(item.get("id") or item.get("youtube_url") or "") == candidate_id
                    for item in youtube_theme_candidates
                ):
                    youtube_theme_candidates.append(
                        dict(
                            candidate,
                            provider="youtube",
                            thematic_query=theme_query,
                            priority="supplemental",
                        )
                    )
    for note in notes:
        scene_id = int(note.get("id") or 0)
        route = str(note.get("source_route") or "pexels")
        query = " ".join(str(note.get("search_query") or "documentary footage").split()).strip()
        scene = scenes.get(scene_id, {})
        scene_context = " ".join(
            part for part in (
                topic,
                query,
                str(note.get("because") or ""),
                str(scene.get("vo_text") or ""),
            ) if part
        )
        # Stock footage is always the first choice. Search both connected banks so
        # the user has real alternatives instead of seeing YouTube for every scene.
        preferred_stock = "pixabay" if route == "pixabay" else "pexels"
        other_stock = "pexels" if preferred_stock == "pixabay" else "pixabay"
        candidates = stock_candidates(preferred_stock, query)
        candidates.extend(stock_candidates(other_stock, query))
        for provider in (preferred_stock, other_stock):
            if any(item.get("provider") == provider for item in candidates):
                scenes_by_provider[provider] += 1

        if candidates:
            status = "found"
        elif not any(key for key, _ in providers.values()):
            status = "awaiting_configuration"
        else:
            status = "no_results"
        results.append({
            "scene_id": scene_id,
            "route": route,
            "query": query,
            "topic": topic,
            "context": scene_context,
            "youtube_theme_queries": [],
            "youtube_used_as_fallback": False,
            "status": status,
            "candidates": candidates,
        })

    # Search the episode's subject once, not each scene separately. Distribute up
    # to ten distinct source videos across the scenes they actually fit; stock
    # candidates remain first and importing still requires explicit permission.
    if youtube_key and results:
        load_youtube_theme_candidates()
        selected_videos = _rank_youtube(
            youtube_theme_candidates, topic, limit=MAX_YOUTUBE_VIDEOS
        )
        youtube_scene_counts: dict[int, int] = {}
        for candidate in selected_videos:
            candidate_text = " ".join(
                str(candidate.get(field) or "")
                for field in ("title", "description", "channel")
            )
            candidate_tokens = _tokens(candidate_text)

            def scene_score(item: dict[str, Any]) -> tuple[int, int, int]:
                overlap = len(candidate_tokens & _tokens(str(item.get("context") or "")))
                requested = int(item.get("route") == "youtube")
                already_assigned = youtube_scene_counts.get(int(item["scene_id"]), 0)
                return requested, overlap - already_assigned * 3, -already_assigned

            chosen_scene = max(results, key=scene_score)
            scene_id = int(chosen_scene["scene_id"])
            matched = dict(
                candidate,
                relevance_score=scene_score(chosen_scene)[1],
                suggested_clip_seconds=5,
            )
            chosen_scene["candidates"].append(matched)
            chosen_scene["youtube_theme_queries"] = youtube_queries
            chosen_scene["youtube_used_as_fallback"] = not any(
                item.get("provider") in {"pexels", "pixabay"}
                for item in chosen_scene["candidates"]
            )
            chosen_scene["status"] = "found"
            youtube_scene_counts[scene_id] = youtube_scene_counts.get(scene_id, 0) + 1
            candidates_by_provider["youtube"] += 1
        scenes_by_provider["youtube"] = len(youtube_scene_counts)

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
        "search_strategy": "stock-first-with-thematic-youtube-supplements",
        "youtube_video_limit": MAX_YOUTUBE_VIDEOS,
        "topic": topic,
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

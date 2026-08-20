import json
from pathlib import Path

import pytest

from studio import media_search


def test_media_search_uses_each_configured_provider_without_downloading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "projects" / "bitcoin"
    project.mkdir(parents=True)
    (project / "Ep2_director.json").write_text(
        json.dumps(
            {
                "notes": [
                    {"id": 1, "source_route": "pexels", "search_query": "bitcoin mining"},
                    {"id": 2, "source_route": "pexels", "search_query": "bitcoin mining"},
                    {"id": 3, "source_route": "pixabay", "search_query": "computer code"},
                    {"id": 4, "source_route": "youtube", "search_query": "Satoshi interview"},
                    {"id": 5, "source_route": "web_image", "search_query": "Bitcoin whitepaper"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(media_search, "configured_pexels", lambda _: "pexels-key")
    monkeypatch.setattr(media_search, "configured_pixabay", lambda _: "pixabay-key")
    monkeypatch.setattr(media_search, "configured_youtube", lambda _: "youtube-key")
    calls: list[tuple[str, str]] = []

    def fake(provider: str):
        def search(_key: str, query: str):
            calls.append((provider, query))
            return [{"id": f"{provider}-1", "video_url": "metadata-only"}]
        return search

    monkeypatch.setattr(media_search, "search_pexels", fake("pexels"))
    monkeypatch.setattr(media_search, "search_pixabay", fake("pixabay"))
    monkeypatch.setattr(media_search, "search_youtube", fake("youtube"))

    result = media_search.find_media_candidates(tmp_path, "bitcoin", 2)
    saved = json.loads((project / "Ep2_media_candidates.json").read_text(encoding="utf-8"))

    assert result["scene_count"] == 5
    assert result["queries_made"] == 3
    assert calls == [
        ("pexels", "bitcoin mining"),
        ("pixabay", "computer code"),
        ("youtube", "Satoshi interview"),
    ]
    assert saved["downloaded_media"] is False
    assert saved["scenes"][4]["status"] == "awaiting_manual_or_generated_media"
    assert not (project / "Ep2_media_search_progress.json").exists()


def test_media_search_leaves_unconfigured_provider_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "projects" / "history"
    project.mkdir(parents=True)
    (project / "Ep1_director.json").write_text(
        json.dumps({"notes": [{"id": 1, "source_route": "pixabay", "search_query": "archive"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(media_search, "configured_pexels", lambda _: "pexels-key")
    monkeypatch.setattr(media_search, "configured_pixabay", lambda _: None)
    monkeypatch.setattr(media_search, "configured_youtube", lambda _: None)

    result = media_search.find_media_candidates(tmp_path, "history", 1)
    assert result["pending_scene_count"] == 1
    assert result["queries_made"] == 0

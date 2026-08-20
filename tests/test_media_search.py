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
        def search(_key: str, query: str, **_kwargs):
            calls.append((provider, query))
            candidate = {"id": f"{provider}-1", "video_url": "metadata-only"}
            if provider == "youtube":
                candidate["youtube_url"] = "https://www.youtube.com/watch?v=abcdefghijk"
                candidate["title"] = "Bitcoin Satoshi documentary"
            return [candidate]
        return search

    monkeypatch.setattr(media_search, "search_pexels", fake("pexels"))
    monkeypatch.setattr(media_search, "search_pixabay", fake("pixabay"))
    monkeypatch.setattr(media_search, "search_youtube", fake("youtube"))

    result = media_search.find_media_candidates(tmp_path, "bitcoin", 2)
    saved = json.loads((project / "Ep2_media_candidates.json").read_text(encoding="utf-8"))

    assert result["scene_count"] == 5
    assert result["queries_made"] == 10
    assert calls == [
        ("pexels", "bitcoin mining"),
        ("pixabay", "bitcoin mining"),
        ("pexels", "computer code"),
        ("pixabay", "computer code"),
        ("pexels", "Satoshi interview"),
        ("pixabay", "Satoshi interview"),
        ("youtube", "Bitcoin"),
        ("youtube", "Bitcoin documentary"),
        ("pexels", "Bitcoin whitepaper"),
        ("pixabay", "Bitcoin whitepaper"),
    ]
    assert saved["search_strategy"] == "stock-first-with-youtube-fallback"
    assert not any(candidate.get("youtube_url") for candidate in saved["scenes"][0]["candidates"])
    assert any(candidate.get("youtube_url") for candidate in saved["scenes"][3]["candidates"])
    assert saved["downloaded_media"] is False
    assert saved["scenes"][4]["status"] == "found"
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
    monkeypatch.setattr(media_search, "search_pexels", lambda _key, _query: [{"id": 7}])

    result = media_search.find_media_candidates(tmp_path, "history", 1)
    assert result["pending_scene_count"] == 0
    assert result["queries_made"] == 1


def test_youtube_is_only_used_when_stock_has_no_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "projects" / "history"
    project.mkdir(parents=True)
    (project / "Ep1_director.json").write_text(
        json.dumps({"notes": [{"id": 1, "source_route": "pexels", "search_query": "rare archive"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(media_search, "configured_pexels", lambda _: "pexels-key")
    monkeypatch.setattr(media_search, "configured_pixabay", lambda _: "pixabay-key")
    monkeypatch.setattr(media_search, "configured_youtube", lambda _: "youtube-key")
    monkeypatch.setattr(media_search, "search_pexels", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(media_search, "search_pixabay", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        media_search,
        "search_youtube",
        lambda *_args, **_kwargs: [{"id": "yt-1", "youtube_url": "https://youtu.be/abcdefghijk", "title": "Rare archive history"}],
    )

    media_search.find_media_candidates(tmp_path, "history", 1)
    saved = json.loads((project / "Ep1_media_candidates.json").read_text(encoding="utf-8"))

    assert saved["scenes"][0]["youtube_used_as_fallback"] is True
    assert saved["scenes"][0]["candidates"][0]["provider"] == "youtube"


def test_load_media_candidates_reads_only_requested_episode(tmp_path: Path) -> None:
    project = tmp_path / "projects" / "history"
    project.mkdir(parents=True)
    expected = {"scenes": [{"scene_id": 3, "candidates": [{"youtube_url": "https://youtu.be/abcdefghijk"}]}]}
    (project / "Ep1_media_candidates.json").write_text(json.dumps(expected), encoding="utf-8")
    result = media_search.load_media_candidates(tmp_path, "history", 1)
    assert result["project"] == "history"
    assert result["episode"] == 1
    assert result["scenes"] == expected["scenes"]


def test_media_search_refresh_replaces_previous_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "projects" / "history"
    project.mkdir(parents=True)
    (project / "Ep1_director.json").write_text(
        json.dumps({"notes": [{"id": 1, "source_route": "pexels", "search_query": "ancient map"}]}),
        encoding="utf-8",
    )
    (project / "Ep1_media_candidates.json").write_text('{"old": true}', encoding="utf-8")
    monkeypatch.setattr(media_search, "configured_pexels", lambda _: "pexels-key")
    monkeypatch.setattr(media_search, "configured_pixabay", lambda _: None)
    monkeypatch.setattr(media_search, "configured_youtube", lambda _: None)
    monkeypatch.setattr(media_search, "search_pexels", lambda _key, _query: [{"id": 7}])

    result = media_search.find_media_candidates(tmp_path, "history", 1, refresh=True)

    assert result["candidate_count"] == 1
    saved = json.loads((project / "Ep1_media_candidates.json").read_text(encoding="utf-8"))
    assert "old" not in saved

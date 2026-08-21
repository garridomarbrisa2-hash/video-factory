import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from studio import visual_selection


def _project(root: Path, scenes: list[dict]) -> Path:
    project = root / "projects" / "bitcoin"
    project.mkdir(parents=True)
    (project / "Ep1_media_candidates.json").write_text(
        json.dumps({"scenes": scenes}), encoding="utf-8"
    )
    return project


def _stock(provider: str, identity: str, *, query: str = "bitcoin archive") -> dict:
    return {
        "provider": provider,
        "id": identity,
        "matched_query": query,
        "video_url": f"https://media.example.com/{identity}.mp4",
        "duration_sec": 22,
        "width": 1920,
        "height": 1080,
    }


def test_selects_stock_automatically_and_keeps_youtube_as_reference(tmp_path: Path) -> None:
    project = _project(
        tmp_path,
        [{
            "scene_id": 1,
            "query": "bitcoin archive",
            "candidates": [
                {"provider": "youtube", "title": "Satoshi", "youtube_url": "https://youtu.be/abcdefghijk"},
                _stock("pexels", "pexels-one"),
            ],
        }],
    )

    result = visual_selection.select_visual_assets(tmp_path, "bitcoin", 1)
    saved = json.loads((project / "Ep1_visual_selection.json").read_text(encoding="utf-8"))

    assert result["selected_count"] == 1
    assert result["youtube_reference_count"] == 1
    assert saved["scenes"][0]["provider"] == "pexels"
    assert 3 <= saved["scenes"][0]["end_seconds"] - saved["scenes"][0]["start_seconds"] <= 5.001
    assert saved["youtube_references"][0]["status"] == "reference_only_requires_authorized_access"
    assert saved["downloaded_stock_media"] is False


def test_avoids_reusing_stock_clips_between_scenes(tmp_path: Path) -> None:
    candidates = [_stock("pexels", "one"), _stock("pixabay", "two")]
    project = _project(
        tmp_path,
        [
            {"scene_id": 1, "query": "bitcoin archive", "candidates": candidates},
            {"scene_id": 2, "query": "bitcoin archive", "candidates": candidates},
        ],
    )

    result = visual_selection.select_visual_assets(tmp_path, "bitcoin", 1)
    saved = json.loads((project / "Ep1_visual_selection.json").read_text(encoding="utf-8"))

    assert {scene["source_id"] for scene in saved["scenes"]} == {"one", "two"}
    assert result["provider_counts"] == {"pexels": 1, "pixabay": 1}


def test_youtube_without_authorized_stock_does_not_block_selection(tmp_path: Path) -> None:
    _project(
        tmp_path,
        [{
            "scene_id": 1,
            "query": "rare archive",
            "candidates": [{
                "provider": "youtube",
                "title": "Rare archive",
                "youtube_url": "https://youtu.be/abcdefghijk",
            }],
        }],
    )

    result = visual_selection.select_visual_assets(tmp_path, "bitcoin", 1)

    assert result["ok"] is True
    assert result["selected_count"] == 0
    assert result["missing_count"] == 1
    assert result["youtube_reference_count"] == 1


def test_local_authorized_video_is_analyzed_and_cut_automatically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _project(
        tmp_path,
        [{
            "scene_id": 1,
            "query": "satoshi documentary",
            "context": "satoshi documentary",
            "candidates": [_stock("pexels", "one")],
        }],
    )
    source = project / "assets" / "authorized" / "satoshi-documentary.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"authorized video")
    monkeypatch.setattr(visual_selection.shutil, "which", lambda binary: f"/bin/{binary}")

    def fake_run(command: list[str], **_kwargs):
        if command[0].endswith("ffprobe"):
            return SimpleNamespace(stdout='{"format": {"duration": "30"}}', stderr="")
        if "-vf" in command:
            return SimpleNamespace(stdout="", stderr="pts_time:7.5\n")
        Path(command[-1]).write_bytes(b"automatic clip")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(visual_selection.subprocess, "run", fake_run)
    result = visual_selection.select_visual_assets(tmp_path, "bitcoin", 1)
    saved = json.loads((project / "Ep1_visual_selection.json").read_text(encoding="utf-8"))
    clip = saved["authorized_local_clips"][0]

    assert result["authorized_local_clip_count"] == 1
    assert clip["start_seconds"] == 7.5
    assert clip["end_seconds"] == 12.5
    assert (tmp_path / clip["media_path"]).read_bytes() == b"automatic clip"

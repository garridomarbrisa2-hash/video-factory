import json
from pathlib import Path

import pytest

from studio import ytdlp_import


def _candidates(root: Path) -> None:
    project = root / "projects" / "bitcoin"
    project.mkdir(parents=True)
    (project / "Ep2_media_candidates.json").write_text(
        json.dumps({"scenes": [{"scene_id": 4, "candidates": [{
            "youtube_url": "https://www.youtube.com/watch?v=abcdefghijk",
            "title": "Arquivo histórico", "channel": "Canal", "license_filter": "creativeCommon",
        }]}]}), encoding="utf-8"
    )


def test_requires_explicit_rights_confirmation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="autorização"):
        ytdlp_import.import_authorized_clip(
            tmp_path, "bitcoin", 2, scene_id=4,
            youtube_url="https://www.youtube.com/watch?v=abcdefghijk",
            start_seconds=0, end_seconds=10, rights_confirmed=False,
        )


def test_import_uses_argument_list_and_records_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _candidates(tmp_path)
    monkeypatch.setattr(ytdlp_import.shutil, "which", lambda _: "/opt/homebrew/bin/yt-dlp")

    def fake_run(command, **_kwargs):
        output = Path(command[command.index("-o") + 1].replace("%(ext)s", "mp4"))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"video")
        return type("Result", (), {"stdout": "", "stderr": ""})()

    monkeypatch.setattr(ytdlp_import.subprocess, "run", fake_run)
    result = ytdlp_import.import_authorized_clip(
        tmp_path, "bitcoin", 2, scene_id=4,
        youtube_url="https://www.youtube.com/watch?v=abcdefghijk",
        start_seconds=2.5, end_seconds=7.5, rights_confirmed=True,
    )
    metadata = json.loads((tmp_path / result["metadata_path"]).read_text(encoding="utf-8"))
    assert result["duration_seconds"] == 5
    assert metadata["rights_confirmed"] is True
    assert metadata["scene_id"] == 4


def test_rejects_url_not_found_for_scene(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _candidates(tmp_path)
    monkeypatch.setattr(ytdlp_import.shutil, "which", lambda _: "/opt/homebrew/bin/yt-dlp")
    with pytest.raises(ValueError, match="não pertence"):
        ytdlp_import.import_authorized_clip(
            tmp_path, "bitcoin", 2, scene_id=4,
            youtube_url="https://www.youtube.com/watch?v=zyxwvutsrqp",
            start_seconds=0, end_seconds=5, rights_confirmed=True,
        )


def test_rejects_clip_longer_than_five_seconds(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="até 5 segundos"):
        ytdlp_import.import_authorized_clip(
            tmp_path, "bitcoin", 2, scene_id=4,
            youtube_url="https://www.youtube.com/watch?v=abcdefghijk",
            start_seconds=0, end_seconds=6, rights_confirmed=True,
        )

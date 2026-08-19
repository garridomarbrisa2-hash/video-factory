from pathlib import Path

import pytest

from studio import server


def test_validate_project_auto_style() -> None:
    project = server._validate_project(
        {
            "topic": "A investigação criminal que abalou uma cidade inteira",
            "language": "pt-BR",
            "duration": 8,
            "style": "auto",
            "asset_mode": "auto",
        }
    )
    assert project["style"] in server.STYLE_IDS
    assert project["duration"] == 8


def test_validate_project_rejects_short_topic() -> None:
    with pytest.raises(ValueError, match="pelo menos 8"):
        server._validate_project({"topic": "curto"})


def test_create_project_writes_brief_without_rendering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "ROOT", tmp_path)
    result = server.create_project(
        {
            "name": "Meu Canal",
            "topic": "A história completa da primeira viagem à Lua",
            "language": "pt-BR",
            "duration": 8,
            "style": "history",
            "asset_mode": "auto",
        }
    )
    brief = tmp_path / result["brief_path"]
    assert brief.is_file()
    assert "global_style: history" in brief.read_text(encoding="utf-8")
    assert not list(tmp_path.rglob("*.mp4"))


from pathlib import Path

import pytest

from studio import server
from studio import anthropic
from studio import script_generation


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


def test_slugify_removes_accents_cleanly() -> None:
    assert server._slugify("A história da criação") == "a-historia-da-criacao"


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


def test_anthropic_key_is_saved_only_in_gitignored_api_dir(tmp_path: Path) -> None:
    key = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456"
    path = anthropic.save_key(tmp_path, key)
    assert path == tmp_path / "docs" / "API" / "anthropic.md"
    assert key in path.read_text(encoding="utf-8")


def test_anthropic_rejects_malformed_key() -> None:
    with pytest.raises(ValueError, match="começar com sk-ant"):
        anthropic.validate_key_shape("chave-invalida")


def test_choose_script_model_prefers_current_sonnet() -> None:
    assert script_generation.choose_script_model(
        ["claude-haiku-4-5", "claude-sonnet-5", "claude-sonnet-4-6"]
    ) == "claude-sonnet-5"


def test_script_metadata_reads_brief() -> None:
    meta = script_generation._metadata(
        """language: pt-BR
target_duration_min: 8
global_style: history
asset_mode: auto

## Assunto

A história da criação do Bitcoin

## Direção inicial
"""
    )
    assert meta["topic"] == "A história da criação do Bitcoin"
    assert meta["style"] == "history"

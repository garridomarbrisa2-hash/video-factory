from pathlib import Path

import pytest

from studio import server
from studio import anthropic
from studio import script_generation
from studio import script_review
from studio import elevenlabs
from studio import pexels
from studio import pixabay
from studio import youtube


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


def test_script_word_limits_for_eight_minutes() -> None:
    minimum, target, maximum = script_generation._word_limits(8)
    assert (minimum, target, maximum) == (972, 1080, 1188)


def test_closer_script_wins() -> None:
    short = "palavra " * 800
    corrected = "palavra " * 1075
    assert script_generation._closer_to_target(short, corrected, 1080) == corrected


def test_parse_editorial_review() -> None:
    script = "# HOOK\n" + ("palavra " * 100) + "\n# BODY\nTexto\n# CTA\nFim"
    raw = f'''<reviewed_script>{script}</reviewed_script>
<review_report>{{"decision":"needs_sources","summary":"ok","corrections":[],"verification_required":["Confirmar número"]}}</review_report>'''
    reviewed, report = script_review._parse_review(raw)
    assert reviewed.startswith("# HOOK")
    assert report["verification_required"] == ["Confirmar número"]


def test_elevenlabs_settings_stay_in_gitignored_api_dir(tmp_path: Path) -> None:
    key = "elevenlabs-secret-key-abcdefghijklmnopqrstuvwxyz"
    path = elevenlabs.save_settings(tmp_path, key, "voice-123", "Narrador")
    settings = elevenlabs.configured_settings(tmp_path)
    assert path == tmp_path / "docs" / "API" / "elevenlabs.md"
    assert settings == {"api_key": key, "voice_id": "voice-123", "voice_name": "Narrador"}


def test_elevenlabs_rejects_short_key() -> None:
    with pytest.raises(ValueError, match="não parece válida"):
        elevenlabs.validate_key_shape("curta")


def test_pexels_key_stays_in_gitignored_api_dir(tmp_path: Path) -> None:
    key = "pexels-secret-key-abcdefghijklmnopqrstuvwxyz"
    path = pexels.save_key(tmp_path, key)
    assert path == tmp_path / "docs" / "API" / "pexels.md"
    assert pexels.configured_key(tmp_path) == key
    assert pexels.masked_key(key).endswith("wxyz")


def test_pexels_rejects_short_key() -> None:
    with pytest.raises(ValueError):
        pexels.validate_key_shape("curta")


def test_pixabay_and_youtube_keys_stay_in_api_dir(tmp_path: Path) -> None:
    pixabay_key = "12345678-pixabay-secret-key"
    youtube_key = "youtube-secret-key-abcdefghijklmnopqrstuvwxyz"
    assert pixabay.save_key(tmp_path, pixabay_key) == tmp_path / "docs" / "API" / "pixabay.md"
    assert youtube.save_key(tmp_path, youtube_key) == tmp_path / "docs" / "API" / "youtube.md"
    assert pixabay.configured_key(tmp_path) == pixabay_key
    assert youtube.configured_key(tmp_path) == youtube_key


def test_recent_episodes_lists_script_ready_for_narration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(server, "ROOT", tmp_path)
    project = tmp_path / "projects" / "historia-do-bitcoin"
    project.mkdir(parents=True)
    (project / "Ep2.md").write_text(
        "## Assunto\n\nA história da criação do Bitcoin\n", encoding="utf-8"
    )
    (project / "Ep2_script.md").write_text("Roteiro pronto.", encoding="utf-8")

    assert server.recent_episodes() == [
        {
            "project": "historia-do-bitcoin",
            "episode": 2,
            "topic": "A história da criação do Bitcoin",
            "reviewed": False,
            "narration": False,
            "direction": False,
            "media_candidates": False,
        }
    ]

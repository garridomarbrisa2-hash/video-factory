from pathlib import Path

from pipeline.assets.vo import ElevenLabsProvider


def test_elevenlabs_provider_reads_local_settings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
    note = tmp_path / "docs" / "API"
    note.mkdir(parents=True)
    (note / "elevenlabs.md").write_text(
        "ELEVENLABS_API_KEY: secret-key-that-is-long-enough\n"
        "ELEVENLABS_VOICE_ID: voice-123\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("pipeline.assets.vo.project_path", lambda *parts: tmp_path.joinpath(*parts))
    provider = ElevenLabsProvider({}, tmp_path / "cache")
    assert provider._settings() == ("secret-key-that-is-long-enough", "voice-123")

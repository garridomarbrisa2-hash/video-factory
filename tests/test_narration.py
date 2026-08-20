from pathlib import Path

import pytest

from studio import narration


def test_generate_narration_uses_reviewed_script_and_measures_duration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "projects" / "bitcoin"
    project.mkdir(parents=True)
    (project / "Ep1_script.md").write_text("Versão antiga.", encoding="utf-8")
    (project / "Ep1_reviewed.md").write_text("Versão revisada.", encoding="utf-8")

    def fake_synthesis(paragraphs: list[str]) -> dict:
        assert paragraphs == ["Versão revisada."]
        return {
            "total_vo_sec": 481.2,
            "beats": [{"audio_path": str(tmp_path / "beat.mp3")}],
        }

    def fake_concat(beats: list[dict], output: Path) -> None:
        assert len(beats) == 1
        output.write_bytes(b"audio")

    monkeypatch.setattr(narration, "synthesize_script_plan", fake_synthesis)
    monkeypatch.setattr(narration, "_concat_audio", fake_concat)

    result = narration.generate_narration(tmp_path, "bitcoin", 1)

    assert result["status"] == "approved"
    assert result["total_minutes"] == 8.0
    assert result["source_path"] == "projects/bitcoin/Ep1_reviewed.md"
    assert (project / "Ep1_narration.mp3").is_file()
    assert (project / "Ep1_voice_plan.json").is_file()


def test_generate_narration_does_not_lock_retry_when_concat_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "projects" / "bitcoin"
    project.mkdir(parents=True)
    (project / "Ep1_script.md").write_text("Texto.", encoding="utf-8")
    monkeypatch.setattr(
        narration,
        "synthesize_script_plan",
        lambda paragraphs: {
            "total_vo_sec": 500,
            "beats": [{"audio_path": str(tmp_path / "beat.mp3")}],
        },
    )
    monkeypatch.setattr(
        narration,
        "_concat_audio",
        lambda beats, output: (_ for _ in ()).throw(narration.NarrationError("falhou")),
    )

    with pytest.raises(narration.NarrationError, match="falhou"):
        narration.generate_narration(tmp_path, "bitcoin", 1)

    assert not (project / "Ep1_voice_plan.json").exists()
    assert not (project / "Ep1_narration.mp3").exists()

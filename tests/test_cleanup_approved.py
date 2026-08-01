from pathlib import Path

from scripts.cleanup_approved import cleanup


def test_cleanup_preserves_approved_output_and_authored_files(tmp_path: Path) -> None:
    for path in (
        tmp_path / "output" / "approved.mp4",
        tmp_path / "output" / "old.mp4",
        tmp_path / "pipeline" / "assets" / "cache" / "vo" / "line.wav",
        tmp_path / "remotion" / "public" / "gen_old.png",
        tmp_path / "remotion" / "public" / "manual.png",
        tmp_path / "projects" / "series" / "Ep1_timeline.json",
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")

    cleanup(tmp_path, "approved.mp4")

    assert (tmp_path / "output" / "approved.mp4").exists()
    assert not (tmp_path / "output" / "old.mp4").exists()
    assert not (tmp_path / "pipeline" / "assets" / "cache").exists()
    assert not (tmp_path / "remotion" / "public" / "gen_old.png").exists()
    assert (tmp_path / "remotion" / "public" / "manual.png").exists()
    assert (tmp_path / "projects" / "series" / "Ep1_timeline.json").exists()

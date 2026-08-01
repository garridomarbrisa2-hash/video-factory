from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.orchestrator import validate_long_stills
from pipeline.render.assembly import assemble_clips, validate_compatible_clips
from pipeline.render.cloud import validate_cloud_clips
from pipeline.render.footage import build_cuda_normalization_command


def test_cuda_command_requires_capabilities(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="scale_cuda"):
        build_cuda_normalization_command(tmp_path / "in.mp4", tmp_path / "out.mp4", {"cuda"})
    command = build_cuda_normalization_command(
        tmp_path / "in.mp4", tmp_path / "out.mp4", {"cuda", "scale_cuda", "crop_cuda", "h264_nvenc"}
    )
    assert "-hwaccel_output_format" in command
    assert "scale_cuda=1920:1080" in " ".join(command)


def test_assembly_uses_concat_copy_for_matching_clips(tmp_path: Path) -> None:
    clips = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
    signature = {"codec_name": "h264", "width": 1920, "height": 1080}
    with patch("pipeline.render.assembly.probe_clip", return_value=signature), patch(
        "pipeline.render.assembly.subprocess.run"
    ) as run:
        run.return_value.returncode = 0
        output = assemble_clips(clips, tmp_path / "out.mp4")
    assert output == tmp_path / "out.mp4"
    assert run.call_args.args[0][-3:] == ["-c", "copy", str(output)]


def test_assembly_rejects_incompatible_clips(tmp_path: Path) -> None:
    with patch("pipeline.render.assembly.probe_clip", side_effect=[{"width": 1}, {"width": 2}]):
        with pytest.raises(ValueError, match="identical"):
            validate_compatible_clips([tmp_path / "a", tmp_path / "b"])


def test_validate_cloud_clips_exact_contract(tmp_path: Path) -> None:
    clips = tmp_path / "clips"
    clips.mkdir()
    (clips / "scene_01.mp4").write_bytes(b"x")
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps({"clips": [{"filename": "scene_01.mp4"}]}), encoding="utf-8")
    assert validate_cloud_clips(metadata, clips, {"clips": ["scene_01.mp4"]}) == [clips / "scene_01.mp4"]
    (clips / "wrong.mp4").write_bytes(b"x")
    with pytest.raises(ValueError, match="missing or unexpected"):
        validate_cloud_clips(metadata, clips, {"clips": ["scene_01.mp4"]})


def test_validate_cloud_clips_rejects_windows_path(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps({"clips": ["scene_01.mp4"], "source": "C:\\work\\x.json"}), encoding="utf-8")
    clips = tmp_path / "clips"
    clips.mkdir()
    with pytest.raises(ValueError, match="Windows absolute path"):
        validate_cloud_clips(metadata, clips, {"clips": ["scene_01.mp4"]})


def test_long_still_warns_but_footage_and_layered_stills_do_not() -> None:
    timeline = {"scenes": [
        {"id": 1, "duration": 13, "resolved_asset_kind": "image", "props": {}},
        {"id": 2, "duration": 20, "resolved_asset_kind": "video", "props": {}},
        {"id": 3, "duration": 20, "resolved_asset_kind": "plate", "props": {"foreground": ["x"]}},
    ]}
    warnings = validate_long_stills(timeline)
    assert len(warnings) == 1
    assert "scene[1]" in warnings[0]

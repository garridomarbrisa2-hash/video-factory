from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.render.assembly import assemble_clips
from pipeline.render.cloud import cloud_render_manifest, stage_cloud_payload, validate_cloud_clips
from pipeline.render.footage import build_cuda_normalization_command


def test_cloud_clip_metadata_matches_render_manifest(tmp_path: Path) -> None:
    clips = tmp_path / "clips"
    clips.mkdir()
    names = ["clip_00_intro.mp4", "overlay_01_content.mov"]
    for name in names:
        (clips / name).write_bytes(b"x")
    metadata = [
        {"scene_index": 0, "filename": names[0]},
        {"scene_index": 1, "filename": names[1]},
    ]
    metadata_path = clips / "clips.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    manifest = {
        "scenes": [
            {"type": "intro", "render_route": "remotion"},
            {"type": "content", "render_route": "ffmpeg", "needs_overlay": True},
            {"type": "content", "render_route": "ffmpeg", "needs_overlay": False},
        ]
    }

    probe = {"streams": [{"codec_name": "h264", "width": 1920, "height": 1080, "pix_fmt": "yuv420p", "nb_read_frames": "30", "r_frame_rate": "30/1"}]}
    metadata[0].update({"kind": "scene", "expected_frames": 30})
    metadata[1].update({"kind": "overlay", "expected_frames": 30})
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    overlay_probe = {"streams": [{**probe["streams"][0], "codec_name": "prores", "pix_fmt": "yuva444p10le"}]}
    with patch("pipeline.render.cloud.subprocess.run") as run:
        run.side_effect = [type("P", (), {"returncode": 0, "stdout": json.dumps(probe)})(), type("P", (), {"returncode": 0, "stdout": json.dumps(overlay_probe)})()]
        assert [path.name for path in validate_cloud_clips(metadata_path, clips, manifest)] == names


def test_cloud_manifest_rejects_windows_absolute_render_asset() -> None:
    with pytest.raises(ValueError, match="Windows absolute path"):
        cloud_render_manifest({"scenes": [{"props": {"bg_image": "C:\\cache\\still.png"}}]})


def test_cloud_render_manifest_removes_local_router_paths() -> None:
    manifest = {
        "output": "C:\\output\\silent.mp4",
        "scenes": [{"render_route": "ffmpeg", "footage_path": "C:\\cache\\clip.mp4", "props": {}}],
    }
    clean = cloud_render_manifest(manifest)
    assert "output" not in clean
    assert "footage_path" not in clean["scenes"][0]


def test_stage_cloud_payload_copies_remotion_assets_only(tmp_path: Path) -> None:
    public = tmp_path / "public"
    public.mkdir()
    (public / "still.png").write_bytes(b"png")
    manifest = tmp_path / "source.json"
    manifest.write_text(json.dumps({"scenes": [
        {"type": "content", "render_route": "remotion", "props": {"bg_image": "still.png"}},
        {"type": "content", "render_route": "ffmpeg", "footage_path": "C:\\x.mp4", "props": {}},
    ]}), encoding="utf-8")

    staged = stage_cloud_payload(manifest, tmp_path / "payload", public)
    data = json.loads(staged.read_text(encoding="utf-8"))
    assert data["scenes"][0]["props"]["bg_image"] == "assets/still.png"
    assert (tmp_path / "payload" / "assets" / "still.png").exists()


def test_stage_cloud_payload_copies_overlay_assets(tmp_path: Path) -> None:
    public = tmp_path / "public"
    public.mkdir()
    (public / "doc.png").write_bytes(b"png")
    manifest = tmp_path / "source.json"
    manifest.write_text(json.dumps({"scenes": [{
        "type": "document", "render_route": "ffmpeg", "needs_overlay": True,
        "footage_path": "C:\\local.mp4", "props": {"document_image": "doc.png"},
    }]}), encoding="utf-8")
    staged = stage_cloud_payload(manifest, tmp_path / "payload", public)
    data = json.loads(staged.read_text(encoding="utf-8"))
    assert data["scenes"][0]["props"]["document_image"] == "assets/doc.png"


def test_hard_cut_assembly_uses_stream_copy(tmp_path: Path) -> None:
    clips = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
    for clip in clips:
        clip.write_bytes(b"x")
    signature = {
        "codec_name": "h264", "width": 1920, "height": 1080,
        "pix_fmt": "yuv420p", "r_frame_rate": "30/1", "time_base": "1/15360",
    }
    with patch("pipeline.render.assembly.probe_clip", return_value=signature), patch(
        "pipeline.render.assembly.subprocess.run"
    ) as run:
        run.return_value.returncode = 0
        assemble_clips(clips, tmp_path / "out.mp4", ["hard_cut"])

    command = run.call_args.args[0]
    assert command[command.index("-c") + 1] == "copy"


def test_cuda_normalization_requires_complete_gpu_chain(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="crop_cuda"):
        build_cuda_normalization_command(
            tmp_path / "in.mp4", tmp_path / "out.mp4",
            {"cuda", "scale_cuda", "h264_nvenc"},
        )

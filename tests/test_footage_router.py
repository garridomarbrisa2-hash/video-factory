"""Tests for Path A footage router: FFmpeg grade, multi-clip trim-to-fit, routing.

Pure logic + mock (no real ffmpeg render or network beyond faked calls).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.assets import stock
from pipeline.render.footage import ffmpeg_grade_filter, render_footage_scene
from pipeline.orchestrator import _scene_needs_overlay, route_scenes


# --- grade filter -------------------------------------------------------------

def test_grade_filter_all_styles_present() -> None:
    for sid in ("crime", "history", "modern", "minimalist", "standard"):
        f = ffmpeg_grade_filter(sid)
        assert "eq=" in f


def test_grade_filter_unknown_falls_back_to_standard() -> None:
    assert ffmpeg_grade_filter("nope") == ffmpeg_grade_filter("standard")


def test_crime_is_desaturated() -> None:
    assert "saturation=0.72" in ffmpeg_grade_filter("crime")


# --- fetch-to-cover segment resolution ----------------------------------------

def _hits(durations: list[float]) -> list[dict]:
    return [
        {"id": i, "url": f"http://x/v{i}.mp4", "width": 1920, "height": 1080, "duration": d, "source": "pexels"}
        for i, d in enumerate(durations)
    ]


def test_segments_single_clip_covers_full_duration(tmp_path: Path) -> None:
    cfg = {"assets_cache_dir": str(tmp_path / "c"), "assets_in_dir": str(tmp_path / "in"),
           "stock": {"preferred_source": "pexels"}}
    with patch.object(stock, "_search_hits", return_value=_hits([12.0])), patch.object(
        stock, "download_file", lambda u, p: Path(p).write_bytes(b"x") or Path(p)
    ), patch.object(stock, "_probe_duration", return_value=12.0):
        segs = stock.resolve_broll_segments(
            {"keyword": "k", "source": "pexels"}, scene_id=1, duration=5.0, pipeline_cfg=cfg
        )
    # one 12s clip trimmed to 5s covers the whole segment
    assert len(segs) == 1
    assert segs[0]["target_duration"] == pytest.approx(5.0)


def test_segments_multiple_short_clips_fill_duration(tmp_path: Path) -> None:
    cfg = {"assets_cache_dir": str(tmp_path / "c"), "assets_in_dir": str(tmp_path / "in"),
           "stock": {"preferred_source": "pexels"}}
    with patch.object(stock, "_search_hits", return_value=_hits([2.0, 2.0, 3.0])), patch.object(
        stock, "download_file", lambda u, p: Path(p).write_bytes(b"x") or Path(p)
    ), patch.object(stock, "_probe_duration", side_effect=[2.0, 2.0, 3.0]):
        segs = stock.resolve_broll_segments(
            {"keyword": "k", "source": "pexels"}, scene_id=1, duration=5.0, pipeline_cfg=cfg
        )
    # 2 + 2 + 1 (trimmed from 3) = 5s of coverage across 3 hard-cut clips
    assert len(segs) == 3
    assert sum(s["target_duration"] for s in segs) == pytest.approx(5.0)


def test_segments_manual_dropin_single(tmp_path: Path) -> None:
    clip = tmp_path / "in" / "scene_03.mp4"
    clip.parent.mkdir(parents=True, exist_ok=True)
    clip.write_bytes(b"x")
    cfg = {"assets_cache_dir": str(tmp_path / "c"), "assets_in_dir": str(tmp_path / "in")}
    segs = stock.resolve_broll_segments(
        {"source": "manual"}, scene_id=3, duration=4.0, pipeline_cfg=cfg
    )
    assert len(segs) == 1
    assert segs[0]["target_duration"] == pytest.approx(4.0)


# --- footage scene render -----------------------------------------------------

def test_render_footage_scene_requires_segments(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        render_footage_scene([], "crime", 5.0, tmp_path)


def test_render_footage_scene_cache_reuse(tmp_path: Path) -> None:
    # Pre-create the expected cached output so the function returns it without ffmpeg.
    from pipeline.render.footage import _scene_cache_key
    segs = [{"path": "a.mp4", "source_start": 0.0, "target_duration": 5.0}]
    key = _scene_cache_key(segs, "crime", 5.0)
    out = tmp_path / f"footage_{key}.mp4"
    out.write_bytes(b"x")
    with patch("pipeline.render.footage._probe_duration", return_value=5.0):
        got = render_footage_scene(segs, "crime", 5.0, tmp_path)
    assert got == out


# --- overlay trigger + routing -------------------------------------------------

def test_overlay_only_for_authored_text() -> None:
    assert _scene_needs_overlay({"props": {"text": "Stat: 40%"}}) is True
    assert _scene_needs_overlay({"props": {}}) is False
    # vo_text alone must NOT caption a footage scene
    assert _scene_needs_overlay({"vo_text": "spoken narration", "props": {}}) is False


def test_route_scenes_video_with_segments_goes_ffmpeg(tmp_path: Path) -> None:
    timeline = {
        "global_style": "crime",
        "scenes": [
            {
                "id": 1, "type": "content", "duration": 5.0,
                "resolved_asset_kind": "video",
                "resolved_segments": [{"path": "a.mp4", "source_start": 0.0, "target_duration": 5.0}],
                "props": {},
            }
        ],
    }
    fake_clip = tmp_path / "footage_x.mp4"
    fake_clip.write_bytes(b"x")
    with patch("pipeline.render.footage.render_footage_scene", return_value=fake_clip):
        routed = route_scenes(timeline, tmp_path)
    assert routed[0]["route"] == "ffmpeg"
    assert routed[0]["footage_path"] == str(fake_clip)


def test_route_scenes_image_goes_remotion(tmp_path: Path) -> None:
    timeline = {
        "global_style": "standard",
        "scenes": [{"id": 1, "type": "content", "duration": 5.0, "resolved_asset_kind": "image", "props": {}}],
    }
    routed = route_scenes(timeline, tmp_path)
    assert routed[0]["route"] == "remotion"
    assert routed[0]["footage_path"] is None


def test_route_scenes_plate_goes_remotion_not_ffmpeg(tmp_path: Path) -> None:
    timeline = {
        "global_style": "standard",
        "scenes": [{"id": 1, "type": "content", "duration": 5.0, "resolved_asset_kind": "plate", "props": {}}],
    }
    routed = route_scenes(timeline, tmp_path)
    assert routed[0]["route"] == "remotion"

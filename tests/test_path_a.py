"""Tests for Path A — program clock, asset provenance, VO-master ordering.

Pure logic only (no ffmpeg render, no network). Covers the review-corrected
behaviors: xfade-overlap-aware vo_start, expected program duration, explicit
resolved_asset_kind routing, and the VO-before-assets failure policy.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.orchestrator import (
    expected_program_sec,
    resolve_cut_transition_sec,
    run,
    stage_retime_to_vo,
)


def _tl(transitions: list[str | None], durations: list[float]) -> dict:
    scenes = []
    for i, (tr, d) in enumerate(zip(transitions, durations)):
        s: dict = {
            "id": i,
            "type": "content",
            "duration": d,
            "props": {"bg_image": "1.png"},
        }
        if tr is not None:
            s["transition_out"] = tr
        scenes.append(s)
    return {"title": "T", "global_style": "standard", "transition_sec": 0.6, "scenes": scenes}


# --- transition overlap math ------------------------------------------------

def test_hard_cut_has_zero_overlap() -> None:
    assert resolve_cut_transition_sec("hard", 0.6) == 0.0


def test_style_and_dissolve_use_style_transition() -> None:
    assert resolve_cut_transition_sec("style", 0.6) == 0.6
    assert resolve_cut_transition_sec("dissolve", 0.6) == 0.6
    assert resolve_cut_transition_sec(None, 0.6) == 0.6


def test_whip_is_a_fixed_snap() -> None:
    assert resolve_cut_transition_sec("whip", 0.6) == pytest.approx(8 / 30)


def test_expected_program_subtracts_only_animated_overlaps() -> None:
    # 3 scenes 4s each = 12s; boundaries: style(0.6) + hard(0) = 0.6 overlap
    tl = _tl(["style", "hard", None], [4.0, 4.0, 4.0])
    assert expected_program_sec(tl) == pytest.approx(11.4)


def test_expected_program_all_hard_is_full_sum() -> None:
    tl = _tl(["hard", "hard", None], [4.0, 4.0, 4.0])
    assert expected_program_sec(tl) == pytest.approx(12.0)


# --- vo_start walks the assembled clock --------------------------------------

def test_retime_vo_start_accounts_for_xfade_overlap() -> None:
    tl = _tl(["style", "hard", None], [4.0, 4.0, 4.0])
    out = stage_retime_to_vo(tl)
    starts = [s["vo_start"] for s in out["scenes"]]
    # scene0 starts at 0; scene1 starts after 4.0 - 0.6 overlap = 3.4;
    # scene2 starts after 3.4 + 4.0 (hard cut, no overlap) = 7.4
    assert starts == pytest.approx([0.0, 3.4, 7.4])
    assert out["total_sec"] == pytest.approx(11.4)


def test_retime_hard_cuts_keep_full_scene_duration() -> None:
    tl = _tl(["hard", "hard", None], [4.0, 4.0, 4.0])
    out = stage_retime_to_vo(tl)
    starts = [s["vo_start"] for s in out["scenes"]]
    assert starts == pytest.approx([0.0, 4.0, 8.0])
    assert out["total_sec"] == pytest.approx(12.0)


# --- asset provenance --------------------------------------------------------

def test_resolve_tags_plate_provenance(tmp_path: Path) -> None:
    from pipeline.assets.stock import StockMissError
    from pipeline.orchestrator import stage_resolve_broll

    timeline = {
        "global_style": "crime",
        "scenes": [
            {
                "id": 1,
                "type": "content",
                "duration": 2.0,
                "props": {"text": "x"},
                "broll": {"keyword": "nothing", "source": "pexels"},
            }
        ],
    }
    cfg = {"assets_cache_dir": str(tmp_path / "c"), "assets_in_dir": str(tmp_path / "in")}
    # Keyword-only beat (no gen_kind) is a footage beat → resolve_broll_segments.
    with patch("pipeline.orchestrator.resolve_broll_segments", side_effect=StockMissError("nothing")), patch(
        "pipeline.orchestrator._style_plate"
    ) as plate:
        plate.return_value = tmp_path / "plate.mp4"
        plate.return_value.write_bytes(b"x")
        out = stage_resolve_broll(timeline, cfg)
    assert out["scenes"][0]["resolved_asset_kind"] == "plate"


def test_resolve_tags_local_video_as_footage(tmp_path: Path) -> None:
    from pipeline.orchestrator import stage_resolve_broll

    clip = tmp_path / "shot.mp4"
    clip.write_bytes(b"x")
    timeline = {
        "global_style": "standard",
        "scenes": [{"id": 1, "type": "content", "duration": 2.0, "props": {"bg_video": str(clip)}}],
    }
    cfg = {"assets_cache_dir": str(tmp_path / "c"), "assets_in_dir": str(tmp_path / "in")}
    out = stage_resolve_broll(timeline, cfg)
    assert out["scenes"][0]["resolved_asset_kind"] == "video"


def test_resolve_tags_generated_still_as_image(tmp_path: Path) -> None:
    from pipeline.orchestrator import stage_resolve_broll

    timeline = {
        "asset_mode": "auto",
        "global_style": "standard",
        "scenes": [
            {
                "id": 1,
                "type": "content",
                "duration": 2.0,
                "props": {"text": "x"},
                "broll": {"fallback_prompt": "p", "gen_kind": "image"},
            }
        ],
    }
    cfg = {"assets_cache_dir": str(tmp_path / "c"), "assets_in_dir": str(tmp_path / "in")}
    png = tmp_path / "gen.png"
    png.write_bytes(b"x")
    with patch("pipeline.assets.imagegen.generate_image_for_scene", return_value=png):
        out = stage_resolve_broll(timeline, cfg)
    assert out["scenes"][0]["resolved_asset_kind"] == "image"


# --- External VO failure policy ----------------------------------------------

def test_run_requires_external_vo_before_assets(tmp_path: Path) -> None:
    timeline = {
        "title": "VO fail",
        "global_style": "standard",
        "scenes": [
            {
                "id": 1,
                "type": "content",
                "duration": 2.0,
                "vo_text": "hello world",
                "props": {"text": "x"},
                "broll": {"keyword": "city", "source": "pexels"},
            }
        ],
    }
    tl_path = tmp_path / "timeline.json"
    tl_path.write_text(__import__("json").dumps(timeline), encoding="utf-8")
    cfg = {"output_dir": str(tmp_path / "out"), "assets_cache_dir": str(tmp_path / "c"), "assets_in_dir": str(tmp_path / "in")}
    with patch("pipeline.orchestrator.load_json", side_effect=[timeline, cfg]), patch(
        "pipeline.orchestrator.stage_resolve_broll"
    ) as assets:
        with pytest.raises(ValueError, match="pipeline.vo_plan"):
            run(tl_path)
    assets.assert_not_called()

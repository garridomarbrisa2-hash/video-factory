"""Tests for Phase 8, P8 — resilience & hygiene.

Covers stock-miss resilience (never abort, always fall back to a style plate +
flag for manual asset) and the Pexels -> Pixabay source fallback. No network or
ffmpeg render: resolve_broll/search/download/normalize are mocked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from pipeline.assets import stock
from pipeline.assets.stock import StockMissError
from pipeline.orchestrator import _style_plate, stage_resolve_broll


def test_stock_miss_does_not_abort_falls_back_and_flags(tmp_path: Path) -> None:
    timeline = {
        "global_style": "history",
        "scenes": [
            {
                "id": 1,
                "type": "content",
                "duration": 2.0,
                "props": {"text": "hello"},
                "broll": {"keyword": "no-such-thing", "source": "pexels"},
            }
        ],
    }
    cfg = {"assets_cache_dir": str(tmp_path / "cache"), "assets_in_dir": str(tmp_path / "in")}
    # A keyword-only beat with no gen_kind is a genuine footage beat → routes to
    # resolve_broll_segments (the FFmpeg footage path), which must also miss → plate.
    with patch(
        "pipeline.orchestrator.resolve_broll_segments",
        side_effect=StockMissError("no-such-thing", "gen this"),
    ), patch("pipeline.orchestrator._style_plate") as plate:
        plate.return_value = tmp_path / "plate.mp4"
        plate.return_value.write_bytes(b"x")
        out = stage_resolve_broll(timeline, cfg)
    scene = out["scenes"][0]
    assert scene["needs_manual_asset"] is True
    assert scene["resolved_asset_kind"] == "plate"  # a fallback was attached


def test_pexels_miss_falls_back_to_pixabay(tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_pexels(kw, key, min_width=1920):
        calls.append("pexels")
        return []

    def fake_pixabay(kw, key, min_width=1920, **kwargs):
        calls.append("pixabay")
        return [{"source": "pixabay", "url": "http://x/v.mp4"}]

    cfg = {"assets_cache_dir": str(tmp_path / "cache"), "assets_in_dir": str(tmp_path / "in")}
    with patch.dict("os.environ", {"PEXELS_API_KEY": "k1", "PIXABAY_API_KEY": "k2"}), patch.object(
        stock, "search_pexels", fake_pexels
    ), patch.object(stock, "search_pixabay", fake_pixabay), patch.object(
        stock, "download_file", lambda u, p: Path(p).write_bytes(b"x")
    ), patch.object(stock, "normalize_clip", lambda s, d, dur: Path(d)):
        stock.resolve_broll(
            {"keyword": "k", "source": "pexels"},
            scene_id=1,
            duration=2.0,
            pipeline_cfg=cfg,
        )
    assert calls == ["pexels", "pixabay"]


def test_style_plate_uses_style_bg(tmp_path: Path) -> None:
    # crime bg is a dark plate; just confirm it produces a clip at the cache path
    p = _style_plate("crime", 5, 1.0, tmp_path)
    assert p.exists() and p.stat().st_size > 0
    assert "plate_crime" in p.name


def test_style_plate_cache_key_includes_frames(tmp_path: Path) -> None:
    # Different target durations must not collide on one cached plate (Path A §6).
    a = _style_plate("crime", 5, 1.0, tmp_path)
    b = _style_plate("crime", 5, 3.0, tmp_path)
    assert a.name != b.name
    assert "30f" in a.name and "90f" in b.name


def test_asset_mode_generated_becomes_manual(tmp_path: Path) -> None:
    """Path B: a scene without broll.source inherits asset_mode=generated ->
    resolves as a manual drop-in (still loops / clip normalizes)."""
    timeline = {
        "asset_mode": "generated",
        "global_style": "crime",
        "scenes": [
            {
                "id": 2,
                "type": "content",
                "duration": 2.0,
                "props": {"text": "y"},
                "broll": {"fallback_prompt": "dark alley film still", "gen_kind": "image"},
            }
        ],
    }
    cfg = {"assets_cache_dir": str(tmp_path / "c"), "assets_in_dir": str(tmp_path / "in")}
    seen: dict = {}

    def fake_resolve(broll, scene_id, duration, pipeline_cfg=None):
        seen.update(broll)
        raise StockMissError("scene_02", broll.get("fallback_prompt"))

    with patch("pipeline.orchestrator.resolve_broll", side_effect=fake_resolve), patch(
        "pipeline.orchestrator._style_plate"
    ) as plate:
        plate.return_value = tmp_path / "plate.mp4"
        plate.return_value.write_bytes(b"x")
        out = stage_resolve_broll(timeline, cfg)
    assert seen.get("source") == "manual"  # generated -> manual drop-in
    assert out["scenes"][0]["needs_manual_asset"] is True


def test_asset_mode_stock_keeps_keyword_route(tmp_path: Path) -> None:
    """Path A: asset_mode=stock leaves scenes source-less -> a keyword-only beat is
    footage, routed to resolve_broll_segments with source untouched (pexels default)."""
    timeline = {
        "asset_mode": "stock",
        "global_style": "crime",
        "scenes": [
            {"id": 1, "type": "content", "duration": 2.0, "props": {"text": "x"}, "broll": {"keyword": "night city"}}
        ],
    }
    cfg = {"assets_cache_dir": str(tmp_path / "c"), "assets_in_dir": str(tmp_path / "in")}
    segs = [{"path": str(tmp_path / "clip.mp4"), "source_start": 0.0, "target_duration": 2.0}]
    with patch("pipeline.orchestrator.resolve_broll_segments", return_value=segs) as rb:
        out = stage_resolve_broll(timeline, cfg)
    # source untouched -> resolver default (pexels) applies
    assert rb.call_args[0][0].get("source") is None
    # footage beat resolved to segments, routed to the FFmpeg footage path
    assert out["scenes"][0]["resolved_asset_kind"] == "video"
    assert out["scenes"][0]["resolved_segments"] == segs

"""Tests for orchestrator style wiring (Phase 4).

Covers: style consistency validation (min scene = 2x transition),
manifest global_style emission, --style override application. Render
itself is exercised by the real E2E run, not here (slow + needs Chrome).
"""

from __future__ import annotations

from pathlib import Path
from inspect import signature

from pipeline.orchestrator import (
    safe_output_stem,
    stage_build_manifest,
    validate_external_vo,
    validate_long_stills,
    validate_style_consistency,
    run,
)
import pytest


def _timeline(style: str, durations: list[float]) -> dict:
    return {
        "title": "T",
        "global_style": style,
        "scenes": [
            {
                "id": i,
                "type": "content",
                "duration": d,
                "props": {"bg_image": "1.png"},
            }
            for i, d in enumerate(durations)
        ],
    }


def test_output_stem_is_windows_safe() -> None:
    assert safe_output_stem("$75M in Debt: Who Paid?") == "75m_in_debt_who_paid"
    assert ":" not in safe_output_stem("a:b")


def test_external_vo_required_before_orchestrator() -> None:
    timeline = {"scenes": [{"id": 3, "vo_text": "Narration"}]}
    with pytest.raises(ValueError, match="pipeline.vo_plan"):
        validate_external_vo(timeline)


def test_external_vo_metadata_passes() -> None:
    validate_external_vo({"scenes": [{
        "id": 3, "vo_text": "Narration", "vo_audio": "x.wav",
        "vo_duration": 8.0, "word_times": [],
    }]})


def test_consistency_no_warnings_when_scenes_long_enough() -> None:
    # crime transition = 12f -> 0.4s; min scene = 0.8s
    assert validate_style_consistency(_timeline("crime", [4.0, 5.0])) == []


def test_consistency_warns_on_short_scene() -> None:
    warnings = validate_style_consistency(_timeline("crime", [4.0, 0.5]))
    assert len(warnings) == 1
    assert "scene[1]" in warnings[0]
    assert "0.80s" in warnings[0]


def test_consistency_uses_style_specific_transition() -> None:
    # modern transition = 9f -> 0.3s; min scene = 0.6s
    assert validate_style_consistency(_timeline("modern", [0.7])) == []
    assert validate_style_consistency(_timeline("modern", [0.5]))


def test_consistency_resolves_legacy_alias() -> None:
    # documentary -> history (14f -> ~0.467s; min ~0.933s)
    warnings = validate_style_consistency(_timeline("documentary", [0.8]))
    assert len(warnings) == 1
    assert "history" in warnings[0]


def test_manifest_carries_global_style(tmp_path: Path) -> None:
    manifest_path = stage_build_manifest(
        _timeline("crime", [4.0]), tmp_path / "out.mp4"
    )
    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["global_style"] == "crime"
    assert manifest["edit_style"] == "crime"  # back-compat alias


def test_manifest_normalizes_legacy_style(tmp_path: Path) -> None:
    timeline = _timeline("storytelling", [4.0])
    timeline.pop("global_style")
    timeline["edit_style"] = "storytelling"
    manifest_path = stage_build_manifest(timeline, tmp_path / "out.mp4")
    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["global_style"] == "standard"


def test_long_still_requires_visual_variety() -> None:
    timeline = {
        "scenes": [{
            "id": 4, "duration": 18, "vo_duration": 17,
            "resolved_asset_kind": "image", "props": {},
        }]
    }
    assert "holds 17.00s" in validate_long_stills(timeline)[0]


def test_long_layered_still_and_footage_are_exempt() -> None:
    timeline = {"scenes": [
        {"id": 1, "duration": 18, "resolved_asset_kind": "image", "props": {"foreground": [{"src": "x.png"}]}},
        {"id": 2, "duration": 18, "resolved_asset_kind": "video", "props": {}},
    ]}
    assert validate_long_stills(timeline) == []


def test_github_render_is_default() -> None:
    params = signature(run).parameters
    assert params["render_mode"].default == "github"
    assert params["github_repo"].default == "srb991/video-factory"


def test_comparison_prompts_count_as_visual_variety() -> None:
    timeline = {"scenes": [{
        "id": 12,
        "type": "comparison",
        "duration": 15,
        "vo_duration": 14,
        "resolved_asset_kind": "image",
        "props": {"left_prompt": "before", "right_prompt": "after"},
    }]}
    assert validate_long_stills(timeline) == []

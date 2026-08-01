"""Tests for the VidRush-format brief template (Phase 2)."""

from __future__ import annotations

import pytest

from pipeline.intelligence.brief_template import (
    build_brief,
    style_line,
    talking_point_budget,
    tone_line,
)
from pipeline.intelligence.select_style import STYLE_IDS


def test_brief_ends_with_style_then_tone() -> None:
    brief = build_brief("The Theranos scam", "crime", 10)
    lines = brief.splitlines()
    assert lines[-2].startswith("Style: ")
    assert lines[-1].startswith("Tone: ")


def test_brief_contains_format_and_budget() -> None:
    brief = build_brief("The Roman Empire", "history", 12)
    assert "Format: documentary" in brief
    assert "Talking points: 6" in brief  # 12 min x 0.5
    assert "~1680 words" in brief  # 12 x 140


@pytest.mark.parametrize("duration", [7.99, 20.01])
def test_brief_rejects_out_of_range_duration(duration: float) -> None:
    with pytest.raises(ValueError, match="between 8 and 20"):
        build_brief("topic", "history", duration)


@pytest.mark.parametrize("duration,expected", [(6, 3), (8, 4), (10, 5), (12, 6), (30, 15), (40, 20)])
def test_talking_point_budget(duration: float, expected: int) -> None:
    # VidRush golden rule: ~0.5 points per minute.
    assert talking_point_budget("standard", duration) == expected


def test_talking_point_budget_floor() -> None:
    assert talking_point_budget("standard", 1) == 1


@pytest.mark.parametrize("sid", STYLE_IDS)
def test_style_and_tone_lines_render(sid: str) -> None:
    assert style_line(sid)
    assert tone_line(sid)


def test_brief_has_no_editing_instructions() -> None:
    # The template itself must pass the linter for every style.
    from pipeline.intelligence.lint_skill_output import lint_text

    for sid in STYLE_IDS:
        assert lint_text(build_brief("test topic", sid, 8)) == []


def test_integration_brief_to_timeline_shape() -> None:
    """Phase 2 integration: brief -> style -> style-constrained mock skill
    output -> timeline.json shape, with the linter gating the middle."""
    import json

    from pipeline.intelligence.lint_skill_output import lint_text
    from pipeline.intelligence.select_style import select_style

    topic = "The Theranos fraud investigation"
    style_id = select_style(topic)
    assert style_id == "crime"

    brief = build_brief(topic, style_id, 10)
    assert "Format: mystery investigation" in brief
    assert lint_text(brief) == []

    # Mock skill output honoring the style constraints.
    script_md = (
        "global_style: crime\n"
        "HOOK\n"
        "A single drop of blood — that was the promise.\n"
        "BODY\n"
        "The machine never worked... and everyone who said so was silenced.\n"
        "Style: Crime - low intense, mystery investigation\n"
        "Tone: suspenseful, mysterious, compelling\n"
    )
    assert lint_text(script_md) == []

    timeline = {
        "title": "The Theranos Fraud Investigation",
        "global_style": style_id,
        "scenes": [
            {
                "id": 0,
                "type": "intro",
                "duration": 6.0,
                "vo_text": "A single drop of blood — that was the promise.",
                "broll": {"keyword": "night city"},
                "props": {"hook_text": "Bad Blood"},
            }
        ],
    }
    assert timeline["global_style"] in STYLE_IDS
    json.dumps(timeline)  # serializable

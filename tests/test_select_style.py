"""Unit tests for global style selection (Phase 1 milestone).

Covers: 10 briefs → expected styles, tie/no-signal → standard, legacy
aliases, --style override, and style JSON structural validation.
"""

from __future__ import annotations

import json

import pytest

from pipeline.intelligence.select_style import (
    LEGACY_ALIASES,
    STYLE_IDS,
    STYLES_DIR,
    load_style,
    normalize_style_id,
    select_style,
)

# 10 briefs → expected canonical style (success criterion: ≥90% agreement
# with human pick — these ARE the human picks).
BRIEF_CASES = [
    ("The rise and fall of the Roman Empire", "history"),
    ("The Theranos fraud investigation", "crime"),
    ("Top 10 productivity apps you need in 2026", "standard"),
    ("How AI is changing the software industry", "modern"),
    ("How to set up a home office: step by step guide", "minimalist"),
    ("The unsolved disappearance of MH370", "crime"),
    ("World War 2: the battle that changed history", "history"),
    ("5 facts about the human brain", "standard"),
    ("Why every startup is moving to the cloud", "modern"),
    ("Introduction to personal finance basics", "minimalist"),
]


@pytest.mark.parametrize("brief,expected", BRIEF_CASES)
def test_brief_selects_expected_style(brief: str, expected: str) -> None:
    assert select_style(brief) == expected


def test_no_signal_defaults_to_standard() -> None:
    assert select_style("a video about stuff") == "standard"


def test_tie_defaults_to_standard() -> None:
    # Equal modern + standard signal, zero everything else → tie → standard.
    style_id, scores = select_style("the best tech", return_scores=True)
    assert scores["modern"] == scores["standard"] > 0
    assert style_id == "standard"


def test_override_wins() -> None:
    assert select_style("The Roman Empire", override="crime") == "crime"


def test_override_accepts_alias() -> None:
    assert select_style("anything", override="documentary") == "history"


def test_unknown_override_raises() -> None:
    with pytest.raises(ValueError, match="unknown style override"):
        select_style("anything", override="noir")


def test_unknown_load_raises() -> None:
    with pytest.raises(ValueError, match="unknown style"):
        load_style("noir")


@pytest.mark.parametrize("alias,canonical", LEGACY_ALIASES.items())
def test_legacy_aliases(alias: str, canonical: str) -> None:
    assert normalize_style_id(alias) == canonical
    assert load_style(alias)["style_id"] == canonical


def test_canonical_ids_pass_through() -> None:
    for sid in STYLE_IDS:
        assert normalize_style_id(sid) == sid


REQUIRED_STYLE_KEYS = {
    "style_id", "name", "source", "topic_keywords", "format_words",
    "script", "vo", "visual", "motion", "broll", "design_decisions",
}
REQUIRED_SCRIPT_KEYS = {
    "talking_points_per_min", "format", "sentence_rhythm", "hook_form", "tone_words",
}
REQUIRED_MOTION_KEYS = {
    "transition", "ken_burns_zoom", "wipe_frames", "plate_frames",
    "hard_titles", "allowed_easings", "spring_allowed",
}
ALLOWED_XFADE = {
    "fade", "dissolve", "wipeleft", "wiperight", "slideleft", "slideright",
    "circleopen", "fadeblack", "fadewhite",
}


@pytest.mark.parametrize("sid", STYLE_IDS)
def test_style_json_structure(sid: str) -> None:
    path = STYLES_DIR / f"{sid}.json"
    style = json.loads(path.read_text(encoding="utf-8"))

    assert REQUIRED_STYLE_KEYS <= set(style), f"{sid} missing keys"
    assert style["style_id"] == sid
    # Platform themes mirror VidRush; per-project styles cite their audit/audit doc.
    assert style["source"].startswith(("vidrush_theme:", "vidiq_audit:", "project:"))

    assert REQUIRED_SCRIPT_KEYS <= set(style["script"])
    assert style["script"]["talking_points_per_min"] == 0.5  # VidRush golden rule

    assert REQUIRED_MOTION_KEYS <= set(style["motion"])
    xfade = style["motion"]["transition"]["xfade"]
    assert xfade in ALLOWED_XFADE, f"{sid} has unmappable xfade {xfade}"
    assert style["motion"]["allowed_easings"] == ["linear"]  # editorial rule

    # Springs only in modern (PRO_EDIT_STYLE.md)
    assert style["motion"]["spring_allowed"] == (sid == "modern")

    palette = style["visual"]["palette"]
    for key in ("bg", "text", "accent"):
        assert palette[key].startswith("#"), f"{sid} palette.{key} not a hex color"

    assert isinstance(style["design_decisions"], list)

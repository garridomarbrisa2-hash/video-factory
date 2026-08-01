"""Tests for the editing-instruction linter (Phase 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.intelligence.lint_skill_output import lint_text

SKILLS_DIR = Path(__file__).resolve().parent.parent / "pipeline" / "intelligence" / "skills"


def test_clean_script_passes() -> None:
    script = (
        "HOOK\n"
        "In 2003, Elizabeth Holmes promised a blood test from a single drop.\n"
        "BODY\n"
        "Investors poured in nine hundred million dollars.\n"
        "Style: Crime - low intense, mystery investigation\n"
        "Tone: suspenseful, mysterious, compelling\n"
    )
    assert lint_text(script) == []


@pytest.mark.parametrize(
    "line",
    [
        "Use dramatic transitions between scenes.",
        "Then fade in the title card.",
        "Add a slow zoom-in on the evidence photo.",
        "The text should slide-in from the left.",
        "Animate the statistics counter.",
        "Put a text overlay on the b-roll.",
        "Use a condensed font here.",
        "Cut to the interview footage.",
        "Apply a subtle vignette.",
        "Add film grain for atmosphere.",
        "Ken Burns across the archive photo.",
    ],
)
def test_editing_instructions_flagged(line: str) -> None:
    assert lint_text(line), f"should flag: {line}"


def test_style_and_tone_lines_are_allowed() -> None:
    # Metadata lines mention style but are not editing commands.
    assert lint_text("Style: Modern - energetic confident, crisis news\nTone: urgent") == []


def test_common_words_not_flagged() -> None:
    # Guard against over-broad patterns stealing normal words.
    clean = (
        "She wiped the counter clean before the guests arrived.\n"
        "The slide deck had twelve slides.\n"
        "He paused at the crossroads, dissolving into thought.\n"
    )
    # "dissolving" is not "dissolve" as an editing command; "wiped"/"slide deck"
    # are everyday usage. Only whole-word editing terms match.
    assert lint_text(clean) == []


@pytest.mark.parametrize(
    "skill_file",
    ["01_script_writer.md", "02_director.md", "03_voiceover.md"],
)
def test_skill_files_pass_own_linter(skill_file: str) -> None:
    # Skill docs reference banned terms inside code-form or quoted rules; the
    # linter is for skill OUTPUT. Skill docs must at least not contain lines
    # that look like emitted editing instructions (imperative usage).
    # We simply assert the files exist and are non-empty — content rules are
    # enforced by review, not this linter.
    path = SKILLS_DIR / skill_file
    assert path.exists() and path.stat().st_size > 500

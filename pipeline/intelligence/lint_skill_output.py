"""Lint skill output for editing instructions (prompt=WHAT, theme=HOW).

VidRush prompt guide explicitly bans editing instructions in prompts:
"Focus on WHAT to talk about, not HOW to show it." Skills emit content,
structure, and words; the style JSON owns all motion and visuals. Any
banned term in skill output is a bug — this linter is the gate.

Usage:
    python -m pipeline.intelligence.lint_skill_output path/to/script.md
    python -m pipeline.intelligence.lint_skill_output --text "fade in the title"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Motion VALUES banned in skill output — the HOW (easings, geometry, timing,
# named effects). Editorial choices are ALLOWED: scene type, layout, energy,
# emphasis, asset slots — those are the WHAT a director legitimately owns.
# Keep terms unambiguous — no common words an editorial sentence might use.
BANNED_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (p, re.compile(p, re.IGNORECASE))
    for p in [
        # Transition types (the named xfade/effect, not the concept of a cut)
        r"\bxfade\b",
        r"\bcrossfade\b",
        r"\bdissolve\b",
        r"\bfadeblack\b",
        r"\bwipe(left|right|up|down)?\b",
        r"\bslide[- ]?(in|out|left|right|up|down)\b",
        r"\bclockwipe\b",
        r"\bfilm burn\b",
        r"\blight leak\b",
        r"\buse\b[^.]*\btransitions?\b",
        r"\bfade[- ]?in\b",
        # Motion implementation values (the HOW)
        r"\beasing\b",
        r"\bbezier\b",
        r"\bspring(s)?\b",
        r"\bkeyframe[s]?\b",
        r"\bframes?\b ?[:=]?\s?\d+",  # "frame: 12", "12 frames"
        r"\bduration in frames\b",
        r"\b\d+\s?px\b",  # pixel values
        r"\bken burns\b",
        r"\bspeed ramp\b",
        r"\bslow motion\b",
        r"\bzoom[- ]?in\b",
        r"\btime remap",
        # Rendering/stack specifics
        r"\bfont(s)?\b",
        r"\btypeface\b",
        r"\bcolor (palette|grade|grading)\b",
        r"\bhex\b",
        r"\b#[0-9a-f]{6}\b",
        r"\bvignette\b",
        r"\bfilm grain\b",
        r"\bparallax\b",
        r"\bmix[- ]?blend\b",
        r"\bclip[- ]?path\b",
        r"\bmask[- ]?(wipe|reveal)\b",
        r"\bstroke[- ]?dashoffset\b",
        r"\bz[- ]?index\b",
        r"\bremotion\b",
        r"\bffmpeg\b",
        # Explicit imperative editing commands (narrow enough to avoid ordinary prose)
        r"\banimate\b[^.]*\b(statistics?|counter)\b",
        r"\b(text overlay|overlay text)\b",
        r"\bcut to\b[^.]*\b(footage|interview|shot|scene)\b",
    ]
]

# Editorial words are intentionally NOT banned: emphasis, energy, highlight,
# layout, plate, keyword, collage, reveal, entrance, still, quiet, cut, beat.
# These are directorial intent — the style system translates them into motion.
#
# Phase 8 (P0): the director ALSO owns TIMING in editorial units — `beats` (a
# named beat in SECONDS from scene start, e.g. beats: {text: 1.2}) and `tempo`
# (a rhythm multiplier). Seconds are intent; the style/scene renders them into
# frames + easing. The ban on `frame(s) N` and `Npx` stays — those are
# implementation units, not editorial ones. So "land the line at 1.2s" is
# allowed; "startFrame: 36" is not.

# Lines that legitimately reference style metadata, not editing commands.
ALLOW_LINE_PREFIXES = ("style:", "tone:", "global_style", "format:")


def lint_text(text: str) -> list[str]:
    """Return a list of violations found in skill output text."""
    violations: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith(ALLOW_LINE_PREFIXES):
            continue
        for raw, pattern in BANNED_PATTERNS:
            if pattern.search(line):
                violations.append(f"line {lineno}: banned term /{raw}/ in: {stripped[:80]}")
    return violations


def lint_file(path: Path) -> list[str]:
    return lint_text(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Lint skill output for editing instructions")
    p.add_argument("file", nargs="?", help="Skill output file to lint")
    p.add_argument("--text", default=None, help="Lint a raw string instead")
    args = p.parse_args(argv)

    if args.text is not None:
        violations = lint_text(args.text)
    elif args.file:
        violations = lint_file(Path(args.file))
    else:
        p.error("provide a file or --text")

    if violations:
        print(f"FAIL — {len(violations)} editing instruction(s) found:")
        for v in violations:
            print(f"  {v}")
        return 1
    print("OK — no editing instructions found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

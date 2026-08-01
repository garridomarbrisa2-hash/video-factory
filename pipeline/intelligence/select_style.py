"""Select a global style from a brief, or load one by id.

Mirrors VidRush theme selection: score the brief against each style's
topic_keywords + format_words; highest score wins; tie or no signal →
``standard`` (VidRush: "if unsure, start here"). ``--style`` always
overrides. Legacy style names resolve through ``LEGACY_ALIASES`` so old
timelines keep working.

Usage:
    python -m pipeline.intelligence.select_style --brief "The Theranos scam"
    python -m pipeline.intelligence.select_style --brief "..." --style crime
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from pipeline import load_json, project_path

STYLES_DIR = Path(__file__).resolve().parent / "styles"

STYLE_IDS = ("crime", "history", "ledger", "modern", "minimalist", "standard")

# Old timeline names → canonical VidRush-parity ids (research doc §3).
LEGACY_ALIASES: dict[str, str] = {
    "documentary": "history",
    "storytelling": "standard",
    "listicle": "standard",
    "explainer": "minimalist",
    "commentary": "modern",
}

DEFAULT_STYLE = "standard"


@lru_cache(maxsize=len(STYLE_IDS))
def load_style(style_id: str) -> dict[str, Any]:
    """Load a style JSON by id (resolves legacy aliases first)."""
    canonical = LEGACY_ALIASES.get(style_id, style_id)
    path = STYLES_DIR / f"{canonical}.json"
    if not path.exists():
        raise ValueError(
            f"unknown style {style_id!r} — expected one of "
            f"{STYLE_IDS} or an alias {sorted(LEGACY_ALIASES)}"
        )
    style = load_json(path)
    style["style_id"] = canonical
    return style


def normalize_style_id(style_id: str | None) -> str | None:
    """Map any accepted style name/alias to its canonical id."""
    if style_id is None:
        return None
    sid = style_id.strip().lower()
    return LEGACY_ALIASES.get(sid, sid)


def _word_pattern(keyword: str) -> re.Pattern[str]:
    """Whole-phrase match, case-insensitive, tolerant of hyphen/space."""
    escaped = re.escape(keyword.lower()).replace(r"\ ", r"[\s\-]")
    return re.compile(rf"\b{escaped}\b")


def score_brief(brief: str, style: dict[str, Any]) -> int:
    """Score one style against the brief.

    topic_keywords are worth 1, format_words 2 (format is a stronger
    signal per VidRush prompt templates).
    """
    text = brief.lower()
    score = 0
    for kw in style.get("topic_keywords", []):
        if _word_pattern(kw).search(text):
            score += 1
    for fw in style.get("format_words", []):
        if _word_pattern(fw).search(text):
            score += 2
    return score


def select_style(
    brief: str,
    override: str | None = None,
    return_scores: bool = False,
) -> str | tuple[str, dict[str, int]]:
    """Pick the global style id for a brief.

    Args:
        brief: free-text video brief.
        override: explicit style id/alias (``--style`` flag); always wins.
        return_scores: also return the raw score table (for logging/tuning).

    Returns:
        canonical style id, or ``(style_id, scores)`` when return_scores.
    """
    if override:
        canonical = normalize_style_id(override)
        if canonical not in STYLE_IDS:
            raise ValueError(
                f"unknown style override {override!r} — expected one of "
                f"{STYLE_IDS} or an alias {sorted(LEGACY_ALIASES)}"
            )
        return (canonical, {}) if return_scores else canonical

    scores = {sid: score_brief(brief, load_style(sid)) for sid in STYLE_IDS}
    best = max(scores.values())
    if best == 0:
        chosen = DEFAULT_STYLE  # no signal → standard
    else:
        winners = [sid for sid, s in scores.items() if s == best]
        chosen = winners[0] if len(winners) == 1 else DEFAULT_STYLE  # tie → standard
    return (chosen, scores) if return_scores else chosen


def style_summary(style_id: str) -> dict[str, Any]:
    """Small dict the orchestrator/skills actually consume downstream."""
    style = load_style(style_id)
    return {
        "style_id": style["style_id"],
        "name": style["name"],
        "script": style["script"],
        "vo": style["vo"],
        "visual": style["visual"],
        "motion": style["motion"],
        "broll": style["broll"],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Select a global style from a brief")
    p.add_argument("--brief", required=True, help="Video brief text")
    p.add_argument("--style", default=None, help="Force a style (id or legacy alias)")
    p.add_argument("--json", action="store_true", help="Print full style summary JSON")
    args = p.parse_args(argv)

    try:
        style_id, scores = select_style(args.brief, override=args.style, return_scores=True)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if scores:
        print(f"[scores] {json.dumps(scores, sort_keys=True)}")
    print(f"[style] {style_id}")
    if args.json:
        print(json.dumps(style_summary(style_id), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build the LLM brief from a topic + global style (VidRush prompt format).

VidRush prompt guide: the prompt declares ``Style:`` and ``Tone:`` at the
END, carries the format, length, and talking-points budget — and never
contains editing instructions. This module renders that contract from the
selected style JSON so skills receive a consistent, style-aware brief.

Usage:
    python -m pipeline.intelligence.brief_template "The Theranos scam" --style crime
"""

from __future__ import annotations

import argparse

from pipeline.intelligence.select_style import load_style, select_style

WORDS_PER_MIN = 140  # VO rate used across the pipeline


def style_line(style_id: str) -> str:
    """Human-readable Style: declaration, e.g. 'Serious investigative journalism'."""
    style = load_style(style_id)
    tone = style["vo"]["energy"].replace("_", " ")
    return f"{style['name']} - {tone}, {style['script']['format'].replace('_', ' ')}"


def tone_line(style_id: str) -> str:
    """Tone: declaration from the style's tone_words."""
    style = load_style(style_id)
    return ", ".join(style["script"]["tone_words"])


def talking_point_budget(style_id: str, duration_min: float) -> int:
    """VidRush golden rule: ~0.5 talking points per minute."""
    style = load_style(style_id)
    return max(1, round(duration_min * style["script"]["talking_points_per_min"]))


def build_brief(
    topic: str,
    style_id: str,
    duration_min: float = 8.0,
) -> str:
    """Render the full prompt handed to the skills chain.

    Style:/Tone: lines go LAST per the VidRush prompt guide.
    """
    if not 8 <= duration_min <= 20:
        raise ValueError("target duration must be between 8 and 20 minutes")
    style = load_style(style_id)
    points = talking_point_budget(style_id, duration_min)
    words = round(duration_min * WORDS_PER_MIN)
    script = style["script"]
    return (
        f"Write a {duration_min:g}-minute YouTube video script about: {topic}\n"
        f"Format: {script['format'].replace('_', ' ')}\n"
        f"Length: ~{words} words ({duration_min:g} min at {WORDS_PER_MIN} wpm)\n"
        f"Talking points: {points} (do not exceed)\n"
        f"Structure: HOOK ({script['hook_form']}) -> BODY -> CTA\n"
        f"Sentence rhythm: {script['sentence_rhythm']}\n"
        f"Style: {style_line(style_id)}\n"
        f"Tone: {tone_line(style_id)}"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render a VidRush-format brief")
    p.add_argument("topic", help="Video topic/brief")
    p.add_argument("--style", default=None, help="Force style (else auto-select)")
    p.add_argument("--duration", type=float, default=8.0, help="Target minutes")
    args = p.parse_args(argv)

    style_id = select_style(args.topic, override=args.style)
    print(build_brief(args.topic, style_id, args.duration))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Synthesize measured narration before directing scenes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pipeline.assets.vo import synthesize_script_plan


def script_paragraphs(text: str) -> list[str]:
    """Return spoken Markdown paragraphs, excluding headings and production metadata."""
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        spoken = [
            line for line in lines
            if not line.startswith("#")
            and not line.startswith("global_style:")
            and not line.startswith("Style:")
            and not line.startswith("Tone:")
        ]
        if spoken:
            paragraphs.append(" ".join(spoken))
    return paragraphs


def build_vo_plan(script: Path, output: Path) -> Path:
    paragraphs = script_paragraphs(script.read_text(encoding="utf-8"))
    if not paragraphs:
        raise ValueError(f"No spoken paragraphs found in {script}")
    plan = synthesize_script_plan(paragraphs)
    total = float(plan["total_vo_sec"])
    if not 480 <= total <= 1200:
        raise ValueError(
            f"total VO is {total / 60:.2f} minutes; rewrite script to produce 8-20 minutes"
        )
    plan["script"] = str(script)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(f"[vo-plan] {len(plan['beats'])} beats, {total / 60:.2f} minutes -> {output}")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate measured VO plan before directing scenes")
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    build_vo_plan(args.script, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

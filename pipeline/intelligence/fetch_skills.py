"""
Fetch + combine skill sources into pipeline/intelligence/skills/.

Sources (user decision: fetch both, then combine):
  1. AI Labs script-writer skill(s)
  2. Luke Robins 7-Skill System

Usage:
  python -m pipeline.intelligence.fetch_skills
  python -m pipeline.intelligence.fetch_skills --script-writer-url URL --luke-url URL

If URLs are not set, writes stub skill templates that you can paste content into
after downloading from:
  - https://lukerobins.org/claude-system
  - AI Labs Claude Skills (script-writer)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline import ensure_dir, project_path

SKILLS_DIR = project_path("pipeline", "intelligence", "skills")

# Chain order after combine
CHAIN = [
    "01_script_writer.md",
    "02_director.md",
    "03_voiceover.md",
    "04_image_prompt.md",
    "05_video_prompt.md",
    "README.md",
]

STUBS = {
    "01_script_writer.md": """# Skill: Script Writer (AI Labs + combined)

> Paste / merge AI Labs `script-writer` skill content here after fetch.

## Role
Turn a brief/topic into a retention-optimized YouTube script (hook + body + CTA).

## Input
- topic / brief
- niche, tone, length target

## Output
- `script.md` with sections: HOOK, BODY, CTA
- word count matching target duration (~140 wpm)

## Rules
- No AI-slop openers ("In today's video...")
- Hook in first 8 seconds
- Pattern interrupt every 20-30s
""",
    "02_director.md": """# Skill: Director (Luke Robins 7-Skill — combined)

> Paste / merge Luke Robins directing skill content here after fetch.

## Role
Break `script.md` into timed scenes for Remotion.

## Input
- script.md
- available scene types: intro, content, stat, quote, list, comparison, person, outro

## Output
- `scenes.json` / contribution to `timeline.json`
- each scene: type, duration, props text, broll.keyword, fallback_prompt

## Rules
- Every scene MUST have B-roll keyword (no empty bg)
- Duration from VO word count when possible
- Alternate visual energy (stat after content, quote after list)
""",
    "03_voiceover.md": """# Skill: Voiceover (Luke Robins 7-Skill — combined)

> Paste / merge Luke Robins voiceover skill content here after fetch.

## Role
Polish script for TTS; add pause markers; pick voice per section.

## Input
- script.md + scenes

## Output
- per-scene `vo_text` (spoken form, not on-screen text)
- optional SSML-like pause markers the VO adapter understands
- voice name for custom TTS config

## Rules
- Shorter sentences for TTS clarity
- Numbers spoken as words when natural
- Match on-screen text ≠ VO text (VO can expand)
""",
    "04_image_prompt.md": """# Skill: Image Prompt (optional)

## Role
When stock miss: produce Midjourney/SDXL prompts for manual generation.

## Output
- `fallback_prompt` per scene in timeline.broll
- aspect 16:9, cinematic, no text in image
""",
    "05_video_prompt.md": """# Skill: Video Prompt (optional)

## Role
When stock miss and motion needed: Runway/Sora/Kling prompts.

## Output
- motion prompt + camera move + duration
""",
    "README.md": """# Combined Skills Chain

Fetch sources, then paste into numbered files:

1. **AI Labs** script-writer → `01_script_writer.md`
2. **Luke Robins 7-Skill** → map into `02_director.md`, `03_voiceover.md`, and optional prompt skills

## Run order

```
brief → 01_script_writer → script.md
      → 02_director      → scenes + broll keywords
      → 03_voiceover     → vo_text per scene
      → (04/05 if stock miss)
      → timeline.json
      → python -m pipeline.orchestrator --timeline timeline.json
```

## Fetch

```bash
python -m pipeline.intelligence.fetch_skills
# or with URLs once you have them:
python -m pipeline.intelligence.fetch_skills --script-writer-url ... --luke-url ...
```
""",
}


def write_stubs(force: bool = False) -> None:
    ensure_dir(SKILLS_DIR)
    for name, content in STUBS.items():
        path = SKILLS_DIR / name
        if path.exists() and not force:
            print(f"skip (exists): {path}")
            continue
        path.write_text(content, encoding="utf-8")
        print(f"wrote: {path}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="Overwrite existing skill stubs")
    p.add_argument("--script-writer-url", default=None, help="URL to AI Labs script-writer skill")
    p.add_argument("--luke-url", default=None, help="URL to Luke Robins skill pack")
    args = p.parse_args()

    if args.script_writer_url or args.luke_url:
        print("Remote fetch not automated yet (auth/paywalls).")
        print("Download manually, then paste into the stub files.")
        if args.script_writer_url:
            print(f"  script-writer: {args.script_writer_url}")
        if args.luke_url:
            print(f"  luke skills:   {args.luke_url}")

    write_stubs(force=args.force)
    print(f"\nSkills dir: {SKILLS_DIR}")
    print("Chain:", ", ".join(CHAIN))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

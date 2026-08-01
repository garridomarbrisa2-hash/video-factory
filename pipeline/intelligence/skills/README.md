# Combined Skills Chain

Fetch sources, then paste into numbered files:

1. **AI Labs** script-writer → `01_script_writer.md`
2. **Luke Robins 7-Skill** → map into `02_director.md`, `03_voiceover.md`, and optional prompt skills

## Run order

The chain is **agent/LLM work** — the skills below are markdown prompts the agent
follows, not Python to execute. `--brief` runs the deterministic front-end
(`select_style` + `brief_template`); the agent then runs 01→05 to author the
timeline and renders it. No CLI/SDK install needed.

```
brief → select_style.py          → global_style (crime|history|ledger|modern|minimalist|standard)
     → brief_template.py        → VidRush-format prompt (Style:/Tone: at end)
     → 01_script_writer         → script.md (style density + rhythm, 0.5 pts/min)
     → 03_voiceover (VO-FIRST)  → synthesize_script_plan(script paragraphs) →
                                  measured per-paragraph durations + audio files
     → 02_director              → scenes SPLIT to fit the measured VO beats; footage-only
                                  (silent) beats placed for variety; still_motion per still
     → (04/05 if stock miss)
     → timeline.json (global_style at top; narrated scenes carry the beat's audio/text)
     → lint_skill_output.py     → gate: zero editing instructions
     → python -m pipeline.orchestrator --timeline timeline.json
                                  (stage_vo reuses cached audio; stage_retime_to_vo snaps
                                   each narrated scene to its measured VO length)
```

**VO-first (Ep1 pilot fix):** the script's narration is synthesized BEFORE scenes
are locked, so the video's timing is driven by measured VO, not a 140wpm guess.
`pipeline.assets.vo.synthesize_script_plan(paragraphs)` returns per-paragraph
`duration_sec` + cached `audio_path` + `word_times`; the director splits scenes to
fit those beats, and footage-only beats (no VO, real video) are placed for breathing
room. The orchestrator's `stage_retime_to_vo` then makes it exact at render time.
Before direction, sum measured narration. Production requires 8:00–20:00 of VO.
If outside that range, return to `01_script_writer`, rewrite, and synthesize again;
never use silent padding or longer visuals to satisfy the runtime gate.

**Full-auto (`--brief` factory):** the agent performs every arrow above in one
pass — brief in, rendered video out. The orchestrator's P8 resilience means a
stock/VO miss never aborts the render; it falls back (style plate) and flags
the scene for a manual asset.

**Per-project styles.** A project-level audit (e.g. `projects/<series>-vidiq.md`)
may add its own style to `pipeline/intelligence/styles/`, registered alongside the
platform five. `ledger` is the american-ledger style: figure-led titles and hooks,
~85% text density, one focal object per scene, red reserved for loss and gold for
the ledger, no whip/glitch. Skills read the per-style "Ledger-specific rules" in
`02_director.md` and `04_image_prompt.md` when the timeline declares
`global_style: ledger`.

**Asset route (default = generated):** unless the brief says "use stock", the
director emits `fallback_prompt` + `gen_kind` per scene (Path B — you AI-generate
the assets into `pipeline/assets/in/`). Only a declared stock request flips the
timeline to `asset_mode: "stock"` with per-scene `broll.keyword`.
Generated still prompts use one subject/action/setting/period/light/medium, at
most six comma-separated parts and 55 words. Text and data graphics belong in
Remotion, never inside generated pixels.

**Visual variety:** measured VO beats over 12 seconds cannot sit on one still or
style plate. Director splits them into motivated sub-scenes with distinct assets,
preferably moving footage after an establishing still. Layered compositions or an
explicit asset sequence may exceed the ceiling. Asset references stay portable
and project-relative because GitHub renders Remotion clips and local FFmpeg owns
footage/final assembly.

**Series factory:** for a folder of episodes, see `docs/PROJECT_FACTORY.md` —
`projects/<series>/Ep*.md` briefs + a resumable `tracker.md` (`pipeline/projects.py`).

**The boundary (VidRush):** skills own **editorial choices** — scene type, layout
variant, energy level, emphasis words, asset slots. The global style owns the
**motion & look grammar** — easings, fonts, grades, transition types, durations.
`lint_skill_output.py` rejects motion *values* (easings, px, frames, font names,
transition types); editorial words (emphasis, energy, layout, reveal) are allowed.

## Fetch

```bash
python -m pipeline.intelligence.fetch_skills
# or with URLs once you have them:
python -m pipeline.intelligence.fetch_skills --script-writer-url ... --luke-url ...
```

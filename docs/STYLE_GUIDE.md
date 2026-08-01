# Global Style Guide

**For:** anyone picking, tuning, or extending styles in the Vidrush-style pipeline.
**Evidence base:** `docs/GLOBAL_STYLE_RESEARCH.md` (10 citations). Every style value either traces there or is flagged `design_decision` in the style JSON.

---

## 1. What a global style is

A **global style** is the single choice that decides *how the whole video looks and feels* — VidRush calls it a **theme**. One style drives five layers at once:

| Layer | What the style controls |
|-------|------------------------|
| **Script** | talking-points density (0.5/min), sentence rhythm, hook form, tone words |
| **VO** | pace, energy, allowed pause markers, voice hint |
| **Visual** | palette (bg/text/accent), typography, title animation, grade (darken/vignette/grain) |
| **Motion** | transition type + frames, Ken Burns zoom, wipe/plate frame counts, spring on/off |
| **B-roll** | search keywords (mood), avoid list, preferred stock source |

**The golden rule (VidRush):** the prompt says **WHAT** to talk about; the style says **HOW** to show it. Skills never emit editing instructions — the style JSON owns all motion.

---

## 2. The five styles

| Style | VidRush theme | Pick it for… | Transition | Palette mood | VO energy |
|-------|---------------|--------------|-----------|--------------|-----------|
| `crime` | Crime | true crime, mystery, conspiracy, investigation | `fadeblack` 0.40s | near-black + red accent | low, intense, long pauses |
| `history` | History | documentaries, period pieces, biographies | `dissolve` 0.47s (`circleopen` chapters) | sepia/parchment + muted gold | authoritative, measured |
| `modern` | Modern | tech, business, news, "explained" | `wipeleft` 0.30s | dark slate + teal accent | energetic, confident (Vox-style) |
| `minimalist` | Minimalist | how-to, corporate, product, clean education | `fade` 0.33s | light/neutral + one accent | calm, formal |
| `standard` | Standard | top-10/listicles, general, **unsure → start here** | `fade` 0.33s | neutral dark + #ff6b35 | adaptable |

**Legacy names still work** (resolved through the alias map everywhere):
`documentary→history` · `storytelling→standard` · `listicle→standard` · `explainer→minimalist` · `commentary→modern`

---

## 3. How to pick a style

**Let the pipeline pick (default):**

```bash
python -m pipeline.orchestrator --brief "The Theranos fraud investigation"
# [scores] {"crime": 4, "history": 0, "modern": 0, "minimalist": 0, "standard": 0}
# [style] crime
```

Selection = keyword scoring (`topic_keywords` 1pt, `format_words` 2pt). Tie or no signal → `standard` (VidRush: "if unsure, start here").

**Force it yourself:**

```bash
python -m pipeline.orchestrator --brief "..." --style crime
python -m pipeline.orchestrator --timeline timeline.json --style modern
```

**In a timeline.json:**

```json
{
  "title": "My Video",
  "global_style": "history",
  "scenes": [ ... ]
}
```

**Preview what a style will do** (no render):

```bash
python -m pipeline.intelligence.select_style --brief "..." --style crime --json
```

---

## 4. How to tune an existing style

Edit `pipeline/intelligence/styles/<id>.json`. Every field has a job:

| Field | Change it when… | Safe range / notes |
|-------|------------------|--------------------|
| `topic_keywords` / `format_words` | briefs mis-select this style | add specific phrases; avoid generic words like "why"/"story" (they steal points) |
| `script.talking_points_per_min` | never | VidRush golden rule = 0.5 — changing breaks the density contract |
| `vo.pace` / `vo.energy` / `vo.pause_markers` | VO rhythm feels wrong for the style | pause markers are a closed set — skills may only use these |
| `visual.palette.*` | brand/look adjustment | hex colors; `accent` drives rules, plates, stat underline |
| `visual.grade.darken` | b-roll too bright/dark under text | 0.3 (minimalist) – 0.6 (crime) |
| `visual.grade.vignette` | edge falloff strength | `none` / `subtle` / `medium` / `strong` |
| `visual.grade.grain` | film texture | 0.0 (off) – 0.05 |
| `motion.transition.xfade` | different cut feel | must be one of the 7 mapped: `fade`, `dissolve`, `wipeleft/right`, `slideleft/right`, `circleopen`, `fadeblack`, `fadewhite` |
| `motion.transition.frames` | transition speed | 8–15f (÷30 = seconds). Remember: min scene length = 2× this |
| `motion.ken_burns_zoom` | still-image push strength | 1.03–1.08 |
| `motion.wipe_frames` / `plate_frames` | title/lower-third speed | 8–12f |
| `motion.spring_allowed` | **leave false** except modern | springs = product-motion tell; only `modern` stat reveals use one (clamped) |
| `broll.keywords` / `broll.avoid` | stock results miss the mood | concrete nouns only (locations, people, objects) |

Ledger episode rule: keep figures visible, but reserve center placement for hook, thesis, and climax. Put routine numbers in plates, document margins, charts, comparisons, maps, and side anchors. Never stack more than two `stat` scenes or three `hero` scenes in a row.

**After any edit, run the tests** — they validate structure, xfade allow-list, spring rule, and palette format:

```bash
python -m pytest tests/ -q
```

---

## 5. How to add a new style

1. **Copy the closest existing style:**
   ```bash
   cp pipeline/intelligence/styles/standard.json pipeline/intelligence/styles/noir.json
   ```
2. **Edit it:** set `style_id`, `name`, `source`, keywords, and every visual/motion field.
3. **Trace or flag:** every value must either cite `docs/GLOBAL_STYLE_RESEARCH.md` in `source` or be listed in `design_decisions`. Never present our frame counts/darken values as platform-documented.
4. **Register the id** in four places:
   - `pipeline/intelligence/select_style.py` → `STYLE_IDS`
   - `pipeline/intelligence/timeline_schema.json` → `global_style` enum
   - `remotion/src/components/styleSystem.ts` → import + `STYLES` map + `GlobalStyleId` type
   - `remotion/src/components/effects/fonts.ts`, `grade.ts`, `textSkin.ts`, `tokens.ts` → per-style branch (lookup functions exhaust on `GlobalStyleId`)
   - `tests/test_select_style.py` → extend `STYLE_IDS`-driven tests + add a brief case

> **Per-project styles** (e.g. `ledger` for american-ledger) live alongside the platform five here. Set `source` to the project audit path (e.g. `vidiq_audit:projects/<series>-vidiq.md`); the platform five keep `vidrush_theme:` sources. Audit-driven styles tune palette/type/tone b-roll only — they never change a channel's niche or episode topics.
5. **Run tests + A/B render** against a sibling style to confirm it looks different.

> Keep the style count small and distinct. VidRush ships exactly five — add one only when a real content category isn't served.

---

## 6. Rules that protect the look

1. **Skills = WHAT, style = HOW.** Skill output is linted (`lint_skill_output.py`) for 30 banned editing terms — a hit is a bug, fix the skill output not the linter.
2. **Editorial motion is linear.** `Easing.linear` everywhere; the only spring in the system is `modern`'s clamped stat reveal. Banned: word stagger, scale pop, glow pills, glass cards, UI beziers (`docs/PRO_EDIT_STYLE.md`).
3. **Min scene length = 2× transition.** The orchestrator warns (`[style-warn]`) so the skills chain can fix pacing upstream.
4. **One transition per style.** A style never mixes transition types inside a video — the theme owns the feel.

---

## 7. Quick reference — commands

```bash
# Auto style + skills prompt
python -m pipeline.orchestrator --brief "..." [--duration 10]

# Forced style
python -m pipeline.orchestrator --brief "..." --style crime

# From a timeline (style from file, or override)
python -m pipeline.orchestrator --timeline timeline.json [--style modern]

# Style lookup / debug
python -m pipeline.intelligence.select_style --brief "..." --json

# Tests (style selection, template, linter, orchestrator)
python -m pytest tests/ -q
```
